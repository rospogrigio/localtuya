"""Automatic cloud-to-LocalTuya device sync."""
from __future__ import annotations

import errno
import ipaddress
import logging
import re
import time
from typing import Any

from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_DEVICES,
    CONF_ENTITIES,
    CONF_FRIENDLY_NAME,
    CONF_HOST,
    CONF_NAME,
)

from .auto_config import build_dps_data, build_entities, merge_entity_capabilities
from .const import (
    ATTR_UPDATED_AT,
    CONF_CLOUD_IMPORTED,
    CONF_DPS_STRINGS,
    CONF_ENABLE_DEBUG,
    CONF_LOCAL_KEY,
    CONF_MODEL,
    CONF_PRODUCT_KEY,
    CONF_PRODUCT_NAME,
    CONF_PROTOCOL_VERSION,
    DATA_DISCOVERY,
    DOMAIN,
)
from .discovery import discover
from .host_resolver import (
    mac_from_device_id,
    normalize_mac,
    read_neighbour_hosts_by_mac,
)

_LOGGER = logging.getLogger(__name__)

UNCONFIRMED_HOST = "0.0.0.0"


class AutoSyncCannotConnect(Exception):
    """Raised when a local probe cannot connect."""


class AutoSyncInvalidAuth(Exception):
    """Raised when a local probe fails authentication."""


class AutoSyncEmptyDpsList(Exception):
    """Raised when a local probe finds no datapoints."""


def dps_string_list(dps_data):
    """Return list of friendly DPS values."""
    return [f"{id} (value: {value})" for id, value in dps_data.items()]


def dps_data_from_strings(dps_strings):
    """Parse stored friendly DPS strings back into a DP value mapping."""
    dps_data = {}
    for dps_string in dps_strings or []:
        match = re.match(r"^(\d+) \(value: (.*)\)$", str(dps_string))
        if match:
            dps_data[int(match.group(1))] = match.group(2)
    return dps_data


def merge_existing_dps_data(existing_dps, inferred_dps):
    """Preserve existing DPS values while adding newly inferred DP ids."""
    merged = dict(existing_dps)
    for dp_id, value in inferred_dps.items():
        merged.setdefault(dp_id, value)
    return dict(sorted(merged.items()))


def cloud_device_name(cloud_device, dev_id):
    """Return the user-facing Tuya Cloud name for a device."""
    return (
        cloud_device.get("custom_name")
        or cloud_device.get(CONF_NAME)
        or cloud_device.get("name")
        or dev_id
    )


def is_private_ip(host):
    """Return true if host is a private literal IP address."""
    try:
        ip_addr = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip_addr.is_private


def read_arp_hosts_by_mac():
    """Read the host ARP/neighbour cache if the platform exposes it."""
    return read_neighbour_hosts_by_mac()


async def async_get_discovered_devices(hass):
    """Return known LAN discovery results, falling back to a one-shot scan."""
    data = hass.data.get(DOMAIN)
    if data and DATA_DISCOVERY in data and data[DATA_DISCOVERY].devices:
        return data[DATA_DISCOVERY].devices

    try:
        return await discover()
    except OSError as ex:
        if ex.errno != errno.EADDRINUSE:
            _LOGGER.warning("Auto-import LAN discovery failed: %s", ex)
    except Exception as ex:  # pylint: disable=broad-except
        _LOGGER.exception("Auto-import LAN discovery failed: %s", ex)
    return {}


def resolve_local_device(dev_id, cloud_device, discovered_devices, arp_hosts_by_mac):
    """Resolve a cloud device to a local host candidate."""
    if dev_id in discovered_devices:
        discovered = discovered_devices[dev_id]
        return (
            discovered.get("ip"),
            discovered.get("version") or "3.3",
            discovered.get("productKey")
            or cloud_device.get(CONF_PRODUCT_KEY)
            or cloud_device.get("product_id")
            or cloud_device.get("productKey"),
            "LAN discovery",
        )

    cloud_mac = normalize_mac(
        cloud_device.get("mac") or cloud_device.get("mac_address")
    ) or mac_from_device_id(dev_id)
    if cloud_mac and cloud_mac in arp_hosts_by_mac:
        return (
            arp_hosts_by_mac[cloud_mac],
            cloud_device.get("version") or "3.3",
            cloud_device.get(CONF_PRODUCT_KEY)
            or cloud_device.get("product_id")
            or cloud_device.get("productKey"),
            "ARP/MAC match",
        )

    cloud_ip = cloud_device.get("ip")
    if cloud_ip and is_private_ip(cloud_ip):
        return (
            cloud_ip,
            cloud_device.get("version") or "3.3",
            cloud_device.get(CONF_PRODUCT_KEY)
            or cloud_device.get("product_id")
            or cloud_device.get("productKey"),
            "private cloud IP",
        )

    return None, None, None, None


async def async_auto_import_devices(
    hass,
    config_entry,
    cloud_api,
    *,
    remove_missing=False,
    detect_available_dps=None,
    cannot_connect=AutoSyncCannotConnect,
    invalid_auth=AutoSyncInvalidAuth,
    empty_dps=AutoSyncEmptyDpsList,
):
    """Import, update, and optionally remove cloud-managed LocalTuya devices."""
    configured_devices = config_entry.data[CONF_DEVICES]
    candidate_ids = list(cloud_api.device_list.keys())
    result = {"imported": [], "updated": [], "removed": [], "skipped": []}
    if not candidate_ids:
        result["skipped"].append("No Tuya Cloud devices were found")
        return result

    await cloud_api.async_enrich_devices(candidate_ids)
    discovered_devices = await async_get_discovered_devices(hass)
    arp_hosts_by_mac = await hass.async_add_executor_job(read_arp_hosts_by_mac)

    new_devices = {}
    changed_existing = {}
    removed_devices = []

    for dev_id in candidate_ids:
        existing_config = configured_devices.get(dev_id)
        metadata = cloud_api.metadata_for(dev_id)
        cloud_device = {
            **metadata.get("device", {}),
            **metadata.get("details", {}),
        }
        device_name = cloud_device_name(cloud_device, dev_id)
        local_key = cloud_device.get(CONF_LOCAL_KEY) or (existing_config or {}).get(
            CONF_LOCAL_KEY
        )
        if not local_key:
            result["skipped"].append(f"{device_name}: missing local key")
            continue

        host, protocol_version, product_key, source = resolve_local_device(
            dev_id, cloud_device, discovered_devices, arp_hosts_by_mac
        )
        if existing_config:
            host = host or existing_config.get(CONF_HOST) or UNCONFIRMED_HOST
            protocol_version = (
                protocol_version or existing_config.get(CONF_PROTOCOL_VERSION) or "3.3"
            )
            product_key = product_key or existing_config.get(CONF_PRODUCT_KEY)
            source = source or "existing config"
        if not host:
            host = UNCONFIRMED_HOST
            protocol_version = cloud_device.get("version") or "3.3"
            product_key = (
                cloud_device.get(CONF_PRODUCT_KEY)
                or cloud_device.get("product_id")
                or cloud_device.get("productKey")
            )
            source = "cloud metadata with unconfirmed host"

        detected_dps = dps_data_from_strings((existing_config or {}).get(CONF_DPS_STRINGS))
        if detect_available_dps is not None and host != UNCONFIRMED_HOST:
            probe = {
                CONF_HOST: host,
                CONF_DEVICE_ID: dev_id,
                CONF_LOCAL_KEY: local_key,
                CONF_PROTOCOL_VERSION: protocol_version,
                CONF_ENABLE_DEBUG: False,
            }
            try:
                detected_dps.update(await detect_available_dps(hass, probe))
            except cannot_connect:
                source = f"{source}; offline during probe"
            except invalid_auth:
                result["skipped"].append(f"{device_name}: local key authentication failed")
                continue
            except empty_dps:
                source = f"{source}; no DPS detected during probe"
            except Exception as ex:  # pylint: disable=broad-except
                _LOGGER.exception("Auto-import probe failed for %s: %s", dev_id, ex)
                source = f"{source}; probe failed"

        dps_data = build_dps_data(detected_dps, metadata)
        auto_config = build_entities(metadata, dps_data)
        if not auto_config.entities:
            result["skipped"].append(f"{device_name}: no supported entities inferred")
            continue

        if existing_config:
            _handle_existing_device(
                dev_id,
                device_name,
                existing_config,
                auto_config,
                metadata,
                host,
                protocol_version,
                local_key,
                product_key,
                cloud_device,
                changed_existing,
                result,
            )
            continue

        config = {
            CONF_FRIENDLY_NAME: device_name,
            CONF_HOST: host,
            CONF_DEVICE_ID: dev_id,
            CONF_LOCAL_KEY: local_key,
            CONF_PROTOCOL_VERSION: protocol_version,
            CONF_ENABLE_DEBUG: False,
            CONF_DPS_STRINGS: dps_string_list(auto_config.dps_data),
            CONF_ENTITIES: auto_config.entities,
            CONF_CLOUD_IMPORTED: True,
        }
        if product_key:
            config[CONF_PRODUCT_KEY] = product_key
        if cloud_device.get(CONF_PRODUCT_NAME):
            config[CONF_MODEL] = cloud_device.get(CONF_PRODUCT_NAME)

        new_devices[dev_id] = config
        result["imported"].append(
            f"{device_name}: {len(auto_config.entities)} entities via {source}"
        )

    if remove_missing:
        _collect_removed_cloud_devices(configured_devices, candidate_ids, removed_devices, result)

    if new_devices or changed_existing or removed_devices:
        new_data = config_entry.data.copy()
        new_data[CONF_DEVICES] = configured_devices.copy()
        for dev_id in removed_devices:
            new_data[CONF_DEVICES].pop(dev_id, None)
        new_data[CONF_DEVICES].update(new_devices)
        new_data[CONF_DEVICES].update(changed_existing)
        new_data[ATTR_UPDATED_AT] = str(int(time.time() * 1000))
        hass.config_entries.async_update_entry(config_entry, data=new_data)

    return result


def _handle_existing_device(
    dev_id: str,
    device_name: str,
    existing_config: dict[str, Any],
    auto_config,
    metadata: dict[str, Any],
    host: str,
    protocol_version: str,
    local_key: str,
    product_key: str | None,
    cloud_device: dict[str, Any],
    changed_existing: dict[str, dict[str, Any]],
    result: dict[str, list[str]],
):
    """Merge inferred capabilities into an existing device config."""
    sync_cloud_name = existing_config.get(CONF_CLOUD_IMPORTED)
    if sync_cloud_name:
        existing_entities = existing_config.get(CONF_ENTITIES, [])
        merged_entities = [entity.copy() for entity in auto_config.entities]
        changes = 0 if merged_entities == existing_entities else len(merged_entities)
    else:
        merged_entities, changes = merge_entity_capabilities(
            existing_config.get(CONF_ENTITIES, []), auto_config.entities
        )
    merged_dps_data = merge_existing_dps_data(
        dps_data_from_strings(existing_config.get(CONF_DPS_STRINGS)),
        auto_config.dps_data,
    )
    config = existing_config.copy()
    config[CONF_HOST] = host
    config[CONF_PROTOCOL_VERSION] = protocol_version
    config[CONF_LOCAL_KEY] = local_key
    config[CONF_DPS_STRINGS] = dps_string_list(merged_dps_data)
    config[CONF_ENTITIES] = merged_entities
    if sync_cloud_name:
        config[CONF_CLOUD_IMPORTED] = True
        config[CONF_FRIENDLY_NAME] = device_name
    if product_key:
        config[CONF_PRODUCT_KEY] = product_key
    if cloud_device.get(CONF_PRODUCT_NAME):
        config[CONF_MODEL] = cloud_device.get(CONF_PRODUCT_NAME)

    if config != existing_config:
        name_changed = config.get(CONF_FRIENDLY_NAME) != existing_config.get(
            CONF_FRIENDLY_NAME
        )
        changed_existing[dev_id] = config
        if name_changed and changes:
            summary = f"name and {changes} entity config(s)"
        elif name_changed:
            summary = "name"
        else:
            summary = f"{changes} capability fields"
        result["updated"].append(f"{device_name}: {summary}")


def _collect_removed_cloud_devices(configured_devices, candidate_ids, removed_devices, result):
    """Collect cloud-managed devices absent from a successful cloud device list."""
    cloud_ids = set(candidate_ids)
    for dev_id, config in configured_devices.items():
        if dev_id in cloud_ids or not config.get(CONF_CLOUD_IMPORTED):
            continue
        removed_devices.append(dev_id)
        result["removed"].append(config.get(CONF_FRIENDLY_NAME) or dev_id)


def auto_import_summary(result):
    """Build a short human-readable import result."""
    imported = result["imported"]
    updated = result["updated"]
    removed = result["removed"]
    skipped = result["skipped"]
    lines = [
        f"Imported {len(imported)} device(s).",
        f"Updated {len(updated)} existing device(s).",
        f"Removed {len(removed)} cloud-managed device(s).",
        f"Skipped {len(skipped)} device(s).",
    ]
    if imported:
        lines.append("Imported: " + "; ".join(imported[:8]))
        if len(imported) > 8:
            lines.append(f"...and {len(imported) - 8} more imported device(s).")
    if updated:
        lines.append("Updated: " + "; ".join(updated[:8]))
        if len(updated) > 8:
            lines.append(f"...and {len(updated) - 8} more updated device(s).")
    if removed:
        lines.append("Removed: " + "; ".join(removed[:8]))
        if len(removed) > 8:
            lines.append(f"...and {len(removed) - 8} more removed device(s).")
    if skipped:
        lines.append("Skipped: " + "; ".join(skipped[:8]))
        if len(skipped) > 8:
            lines.append(f"...and {len(skipped) - 8} more skipped device(s).")
    return "\n".join(lines)
