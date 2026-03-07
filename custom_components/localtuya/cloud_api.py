"""Cloud API definition and no-op implementation."""
from __future__ import annotations
import logging
from abc import abstractmethod
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.const import (
    CONF_REGION,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
)
from homeassistant.util.json import load_json

from .const import (
    CLOUD_TYPE_IOT,
    CLOUD_TYPE_NONE,
    CONF_CLOUD_TYPE,
    CONF_OEM_EMAIL,
    CONF_OEM_PASSWORD,
    CONF_USER_ID,
)

# A mapping of category codes to Home Assistant platform.
_TUYA_CATEGORY_PLATFORM = {"dj": "light"}

# A mapping of category codes to human-readable product types.
# Obtained via GET /v1.0/iot-03/device-categories with IoT Platform API,
# spelling mistakes and casing kept as is.
# See https://developer.tuya.com/en/docs/cloud/303a03de7e?id=Kb2us379ab2mi
_TUYA_CATEGORY_PRODUCT = load_json(
    str(Path(__file__).parent / "tuya_categories.json"), {}
)

_LOGGER = logging.getLogger(__name__)


class CloudApi:
    """Base class for Cloud API implementations."""

    @staticmethod
    def create_api(hass: HomeAssistant, config: dict) -> CloudApi:
        """Create a CloudApi instance from the provided LocalTuya config."""
        cloud_type = config.get(CONF_CLOUD_TYPE)

        if cloud_type == CLOUD_TYPE_NONE:
            return CloudApiNoOp()

        if cloud_type == CLOUD_TYPE_IOT:
            # pylint: disable=import-outside-toplevel
            from .cloud_api_iot import TuyaCloudApiIoT

            return TuyaCloudApiIoT(
                hass,
                config.get(CONF_REGION),
                config.get(CONF_CLIENT_ID),
                config.get(CONF_CLIENT_SECRET),
                config.get(CONF_USER_ID),
            )

        # pylint: disable=import-outside-toplevel
        from .cloud_api_oem import TuyaCloudApiOEM

        return TuyaCloudApiOEM(
            hass,
            cloud_type,
            config.get(CONF_REGION),
            config.get(CONF_OEM_EMAIL),
            config.get(CONF_OEM_PASSWORD),
            config.get(CONF_CLIENT_ID),
            config.get(CONF_CLIENT_SECRET),
        )

    @staticmethod
    def product_from_category(category: str):
        """
        Map Tuya category (e.g. dj) to a human readable product name.

        If the product is unknown a string "Unknown (category)" will be returned.
        """
        product = _TUYA_CATEGORY_PRODUCT.get(category)
        if product is None:
            product = f"Unknown-{category}"

        return product

    def __init__(self, cloud_type, mute=False):
        """Initialize the class."""
        self._cloud_type = cloud_type
        self._mute = mute
        self._device_list = {}
        _LOGGER.info("Cloud API [%s] configured.", self._cloud_type)

    @abstractmethod
    async def _async_authenticate(self):
        """Authenticate via the API and remember the authenticated state."""

    @abstractmethod
    async def _async_fetch_device_list(self):
        """Retrieve the device list via the API - implementation."""

    async def async_authenticate(self):
        """Authenticate via the API and remember the authenticated state."""
        res = await self._async_authenticate()
        if res == "ok":
            if not self._mute:
                _LOGGER.info(
                    "Cloud API [%s] authentication succeeded.", self._cloud_type
                )
        else:
            if not self._mute:
                _LOGGER.error(
                    "Cloud API [%s] authentication failed: %s", self._cloud_type, res
                )
        return res

    async def async_fetch_device_list(self):
        """Retrieve the device list via the API."""
        res = await self._async_fetch_device_list()
        if res == "ok":
            if not self._mute:
                _LOGGER.info("Cloud API [%s] get devices succeeded.", self._cloud_type)
                _LOGGER.debug(
                    "Cloud API [%s] device list: %s",
                    self._cloud_type,
                    self._device_list,
                )
        else:
            if not self._mute:
                _LOGGER.info(
                    "Cloud API [%s] get devices failed: %s", self._cloud_type, res
                )
        return res

    @property
    def device_list(self):
        """
        Return the fetched device list.

        Call async_fetch_device_list() first to fetch the list.
        """
        return self._device_list

    def device_property(self, dev_id: str, name: str, default=None):
        """
        Return a device property for device with id dev_id.

        Call async_fetch_device_list() first to fetch the list.
        """
        if dev_id in self.device_list and name in self.device_list[dev_id]:
            return self.device_list[dev_id][name]

        return default

    def device_platform(self, dev_id: str, default="switch"):
        """
        Return suggested device platform.

        The platform is determined from the the device category
        If the platform is unknown, "switch" will be returned as a sane default.
        """
        return _TUYA_CATEGORY_PLATFORM.get(
            self.device_property(dev_id, "category"), default
        )


class CloudApiNoOp(CloudApi):
    """
    No-op instance -- does nothing and returns an empty device list.

    This class won't print success/failure messages in the log to avoid confusion.
    """

    def __init__(self):
        """Initialize the class."""
        super().__init__(CLOUD_TYPE_NONE, mute=True)

    async def _async_authenticate(self):
        return "ok"

    async def _async_fetch_device_list(self):
        return "ok"
