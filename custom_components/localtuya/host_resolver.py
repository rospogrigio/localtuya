"""Resolve Tuya device LAN hosts from local network evidence."""
from __future__ import annotations

import concurrent.futures
import contextlib
import ipaddress
import logging
import re
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

_LOGGER = logging.getLogger(__name__)

_PROC_ARP = Path("/proc/net/arp")
_PING_WORKERS = 32
_PING_TIMEOUT_SECONDS = 1
_SCAN_TIMEOUT_SECONDS = 12
_TUYA_PORT = 6668
_TUYA_SCAN_WORKERS = 64
_TUYA_CONNECT_TIMEOUT_SECONDS = 1


@dataclass(frozen=True)
class HostResolution:
    """A resolved host and the evidence source."""

    host: str
    mac: str
    source: str


def normalize_mac(value):
    """Normalize a MAC address for comparisons."""
    if not value:
        return None
    parts = re.findall(r"[0-9a-fA-F]{2}", str(value))
    if len(parts) != 6:
        return None
    return ":".join(part.lower() for part in parts)


def mac_from_device_id(device_id):
    """Infer a Tuya device MAC from IDs that embed the MAC as a hex suffix."""
    match = re.search(r"([0-9a-fA-F]{12})$", str(device_id or ""))
    if not match:
        return None
    return normalize_mac(match.group(1))


def read_neighbour_hosts_by_mac():
    """Read local ARP/neighbour caches and return hosts by normalized MAC."""
    hosts_by_mac = {}
    _read_proc_arp(hosts_by_mac)
    _read_neighbour_commands(hosts_by_mac)
    return hosts_by_mac


def _read_proc_arp(hosts_by_mac):
    """Read Linux /proc ARP cache."""
    try:
        lines = _PROC_ARP.read_text(encoding="utf-8").splitlines()[1:]
    except OSError:
        return

    for line in lines:
        fields = line.split()
        if len(fields) < 4:
            continue
        mac = normalize_mac(fields[3])
        if mac:
            hosts_by_mac[mac] = fields[0]


def _read_neighbour_commands(hosts_by_mac):
    """Read platform ARP/neighbour commands when available."""
    commands = (["ip", "neigh"], ["arp", "-a"])
    for command in commands:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                check=False,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if result.returncode != 0:
            continue

        for line in result.stdout.splitlines():
            ip_match = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", line)
            mac_match = re.search(r"([0-9a-fA-F]{2}(?:[:-][0-9a-fA-F]{2}){5})", line)
            if not ip_match or not mac_match:
                continue
            mac = normalize_mac(mac_match.group(1))
            if mac:
                hosts_by_mac[mac] = ip_match.group(1)


def find_host_for_device_id(device_id, current_host=None, include_scan=False):
    """Find a current LAN host for a Tuya device ID."""
    mac = mac_from_device_id(device_id)
    if not mac:
        return None

    host = read_neighbour_hosts_by_mac().get(mac)
    if host:
        return HostResolution(host, mac, "neighbour cache")

    if not include_scan:
        return None

    host = scan_subnet_for_mac(current_host, mac)
    if host:
        return HostResolution(host, mac, "active subnet scan")

    return None


def scan_subnet_for_mac(current_host, mac):
    """Populate ARP by pinging the host /24, then look for the target MAC."""
    network = _network_from_host(current_host)
    if network is None:
        return None

    deadline = time.monotonic() + _SCAN_TIMEOUT_SECONDS
    hosts = [str(host) for host in network.hosts()]
    with concurrent.futures.ThreadPoolExecutor(max_workers=_PING_WORKERS) as executor:
        futures = {executor.submit(_ping_host, host): host for host in hosts}
        try:
            for future in concurrent.futures.as_completed(
                futures, timeout=_SCAN_TIMEOUT_SECONDS
            ):
                with contextlib.suppress(Exception):
                    future.result()
                host = read_neighbour_hosts_by_mac().get(mac)
                if host:
                    return host
                if time.monotonic() >= deadline:
                    return None
        except concurrent.futures.TimeoutError:
            return read_neighbour_hosts_by_mac().get(mac)
        finally:
            for future in futures:
                future.cancel()

    return read_neighbour_hosts_by_mac().get(mac)


def scan_subnet_for_tuya_hosts(current_host, exclude_hosts=None):
    """Return hosts in the current /24 that have the Tuya LAN port open."""
    network = _network_from_host(current_host)
    if network is None:
        return []

    exclude_hosts = set(exclude_hosts or [])
    hosts = [str(host) for host in network.hosts() if str(host) not in exclude_hosts]
    open_hosts = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=_TUYA_SCAN_WORKERS) as executor:
        futures = {executor.submit(_tcp_port_open, host, _TUYA_PORT): host for host in hosts}
        try:
            for future in concurrent.futures.as_completed(
                futures, timeout=_SCAN_TIMEOUT_SECONDS
            ):
                host = futures[future]
                with contextlib.suppress(Exception):
                    if future.result():
                        open_hosts.append(host)
        except concurrent.futures.TimeoutError:
            pass
        finally:
            for future in futures:
                future.cancel()

    return sorted(open_hosts, key=ipaddress.ip_address)


def _network_from_host(host):
    """Return the /24 network containing host."""
    try:
        ip_addr = ipaddress.ip_address(host)
    except ValueError:
        return None
    if not ip_addr.is_private or ip_addr.version != 4:
        return None
    return ipaddress.ip_network(f"{host}/24", strict=False)


def _ping_host(host):
    """Ping a host once to populate neighbour tables."""
    try:
        subprocess.run(
            ["ping", "-c", "1", "-W", str(_PING_TIMEOUT_SECONDS), host],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=_PING_TIMEOUT_SECONDS + 1,
        )
    except (OSError, subprocess.SubprocessError):
        _LOGGER.debug("Unable to ping %s while refreshing neighbour cache", host)


def _tcp_port_open(host, port):
    """Return whether a TCP port is reachable."""
    try:
        with socket.create_connection(
            (host, port), timeout=_TUYA_CONNECT_TIMEOUT_SECONDS
        ):
            return True
    except OSError:
        return False
