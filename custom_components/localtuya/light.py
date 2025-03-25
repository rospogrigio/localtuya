"""Platform to locally control Tuya-based light devices."""

import base64
import logging
import textwrap
import homeassistant.util.color as color_util
import voluptuous as vol

from dataclasses import dataclass
from functools import partial
from homeassistant.helpers import selector
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    ATTR_WHITE,
    ColorMode,
    DOMAIN,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.const import CONF_BRIGHTNESS, CONF_COLOR_TEMP, CONF_SCENE

from .config_flow import col_to_select
from .entity import LocalTuyaEntity, async_setup_entry
from .const import (
    CONF_BRIGHTNESS_LOWER,
    CONF_BRIGHTNESS_UPPER,
    CONF_COLOR,
    CONF_COLOR_MODE,
    CONF_COLOR_MODE_SET,
    CONF_COLOR_TEMP_MAX_KELVIN,
    CONF_COLOR_TEMP_MIN_KELVIN,
    CONF_COLOR_TEMP_REVERSE,
    CONF_MUSIC_MODE,
    CONF_SCENE_VALUES,
    DictSelector,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_MIN_KELVIN = 2700  # MIRED 370
DEFAULT_MAX_KELVIN = 6500  # MIRED 153

DEFAULT_COLOR_TEMP_REVERSE = False

DEFAULT_LOWER_BRIGHTNESS = 10
DEFAULT_UPPER_BRIGHTNESS = 1000

MODE_MANUAL = "manual"
MODE_COLOR = "colour"
MODE_MUSIC = "music"
MODE_SCENE = "scene"
MODE_WHITE = "white"

SCENE_MUSIC = "Music"

MODES_SET = {"Colour, Music, Scene and White": 0, "Manual, Music, Scene and White": 1}

# https://developer.tuya.com/en/docs/iot/dj?id=K9i5ql3v98hn3#title-10-scene_data
SCENE_LIST_RGBW_255 = {
    "Night": "bd76000168ffff",
    "Read": "fffcf70168ffff",
    "Meeting": "cf38000168ffff",
    "Leisure": "3855b40168ffff",
    "Scenario 1": "scene_1",
    "Scenario 2": "scene_2",
    "Scenario 3": "scene_3",
    "Scenario 4": "scene_4",
}

# https://developer.tuya.com/en/docs/iot/dj?id=K9i5ql3v98hn3#title-11-scene_data_v2
SCENE_LIST_RGBW_1000 = {
    "Night 1": "000e0d0000000000000000c80000",
    "Night 2": "000e0d00002e03e802cc00000000",
    "Read 1": "010e0d0000000000000003e801f4",
    "Read 2": "010e0d000084000003e800000000",
    "Meeting": "020e0d0000000000000003e803e8",
    "Working": "020e0d00001403e803e800000000",
    "Leisure 1": "030e0d0000000000000001f401f4",
    "Leisure 2": "030e0d0000e80383031c00000000",
    "Soft": "04464602007803e803e800000000464602007803e8000a00000000",
    "Rainbow": "05464601000003e803e800000000464601007803e803e80000000046460100f003e803"
    + "e800000000",
    "Colorful": "06464601000003e803e800000000464601007803e803e80000000046460100f003e80"
    + "3e800000000464601003d03e803e80000000046460100ae03e803e800000000464601011303e803"
    + "e800000000",
    "Beautiful": "07464602000003e803e800000000464602007803e803e80000000046460200f003e8"
    + "03e800000000464602003d03e803e80000000046460200ae03e803e800000000464602011303e80"
    + "3e800000000",
    "Forest": "19464601007803e803e800000000464602006e0320025800000000464602005a038403e8"
    + "00000000",
    "Dream": "1c4646020104032003e800000000464602011802bc03e800000000464602011303e803e80"
    + "0000000",
    "F Style": "1e323201015e01f403e800000000323202003201f403e80000000032320200a001f403e"
    + "800000000",
    "A Style": "1f46460100dc02bc03e800000000464602006e03200258000000004646020014038403e"
    + "800000000464601012703e802ee0000000046460100000384028a00000000",
    "Halloween": "28464601011303e803e800000000464601001e03e803e800000000",
    "Christmas": "225a5a0100f003e803e8000000005a5a01003d03e803e800000000464601000003e80"
    + "3e8000000005a5a0100ae03e803e8000000005a5a01011303e803e800000000464601007803e803e"
    + "800000000",
    "Birthday": "20646401003d03e803e800000000646401007803e803e8000000005a5a01011303e803"
    + "e8000000005a5a0100ae03e803e800000000646401003201f403e800000000646401000003e803e8"
    + "00000000",
    "Wedding Anniversary": "21323202015e01f403e800000000323202011303e803e800000000",
}

# Same format as SCENE_LIST_RGBW_1000
SCENE_LIST_RGB_1000 = {
    "Night": "000e0d00002e03e802cc00000000",
    "Read": "010e0d000084000003e800000000",
    "Working": "020e0d00001403e803e800000000",
    "Leisure": "030e0d0000e80383031c00000000",
    "Soft": "04464602007803e803e800000000464602007803e8000a00000000",
    "Colorful": "05464601000003e803e800000000464601007803e803e80000000046460100f003e80"
    + "3e800000000464601003d03e803e80000000046460100ae03e803e800000000464601011303e803"
    + "e800000000",
    "Dazzling": "06464601000003e803e800000000464601007803e803e80000000046460100f003e80"
    + "3e800000000",
    "Gorgeous": "07464602000003e803e800000000464602007803e803e80000000046460200f003e803e8"
    + "00000000464602003d03e803e80000000046460200ae03e803e800000000464602011303e803e80"
    + "0000000",
}

SCENE_LIST_RGBW_BLE = {
    "Good Night": "AAAAAGQKQA==",
    "Reading": "AQAAAGRkCA==",
    "Work": "AgAAAGRkAQ==",
    "Leisure": "AwAAAGQ8BA==",
    "White Breath": "BgACADxkAYA=",
    "White Flashing": "BwABADJkAYA=",
    "Warm Breath": "BwABADJkAYA=",
    "Warm Flashing": "CQABADJkQIA=",
    "Rainbow": "CgACAUtkAQIEECAI",
    "Blue & Green Gradient": "CwACAUtkAgQ=",
    "Red & Green Gradient": "DAACAUtkAQQ=",
    "Red & Blue Gradient": "DQACAUtkAQI=",
    "Red & Blue & Green Gradient": "DgACATxkAYACgASA",
    "Red Breath": "DwACATxkAYA=",
    "Flash": "FAABATJkAQIEECAI",
}


@dataclass(frozen=True)
class Mode:
    color: str = MODE_COLOR
    music: str = MODE_MUSIC
    scene: str = MODE_SCENE
    white: str = MODE_WHITE

    def as_list(self) -> list:
        return [self.color, self.music, self.scene, self.white]

    def as_dict(self) -> dict[str, str]:
        default = {"Default": self.white}
        return {**default, "Mode Color": self.color, "Mode Scene": self.scene}


MAP_MODE_SET = {0: Mode(), 1: Mode(color=MODE_MANUAL)}


def map_range(
    value: int, from_min: int, from_max: int, to_min=0, to_max=255, reverse=False
):
    """Maps a value from one range to another."""

    if reverse:
        value = from_max - (value - from_min)

    scale = (to_max - to_min) / (from_max - from_min)
    mapped_value = to_min + (value - from_min) * scale

    return min(max(round(mapped_value), to_min), to_max)


def map_value_by_percent(value: int, value_max: int, target_max: int, percentage=100):
    """Convert a value from one range to another based on percentage."""
    raw_percent = (value / value_max) * percentage
    return round((raw_percent / percentage) * target_max)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_BRIGHTNESS): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_COLOR_TEMP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_BRIGHTNESS_LOWER, default=DEFAULT_LOWER_BRIGHTNESS): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=10000)
        ),
        vol.Optional(CONF_BRIGHTNESS_UPPER, default=DEFAULT_UPPER_BRIGHTNESS): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=10000)
        ),
        vol.Optional(CONF_COLOR_MODE): col_to_select(dps, is_dps=True),
        vol.Required(CONF_COLOR_MODE_SET, default="0"): col_to_select(MODES_SET),
        vol.Optional(CONF_COLOR): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_COLOR_TEMP_MIN_KELVIN, default=DEFAULT_MIN_KELVIN): vol.All(
            vol.Coerce(int), vol.Range(min=1500, max=8000)
        ),
        vol.Optional(CONF_COLOR_TEMP_MAX_KELVIN, default=DEFAULT_MAX_KELVIN): vol.All(
            vol.Coerce(int), vol.Range(min=1500, max=8000)
        ),
        vol.Optional(CONF_COLOR_TEMP_REVERSE, default=DEFAULT_COLOR_TEMP_REVERSE): bool,
        vol.Optional(CONF_SCENE): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_SCENE_VALUES, default={}): selector.ObjectSelector(),
        vol.Optional(CONF_MUSIC_MODE, default=False): selector.BooleanSelector(),
    }


class LocalTuyaLight(LocalTuyaEntity, LightEntity):
    """Representation of a Tuya light."""

    def __init__(
        self,
        device,
        config_entry,
        lightid,
        **kwargs,
    ):
        """Initialize the Tuya light."""
        super().__init__(device, config_entry, lightid, _LOGGER, **kwargs)
        # Light is an active device (mains powered). It should be able
        # to respond at any time. But Tuya BLE bulbs are write-only.
        self._write_only = self._device.is_write_only

        self._state = None
        self._color_temp = None
        self._lower_brightness = int(
            self._config.get(CONF_BRIGHTNESS_LOWER, DEFAULT_LOWER_BRIGHTNESS)
        )
        self._upper_brightness = int(
            self._config.get(CONF_BRIGHTNESS_UPPER, DEFAULT_UPPER_BRIGHTNESS)
        )
        self._brightness = None if not self._write_only else self._upper_brightness
        self._upper_color_temp = self._upper_brightness

        self._color_temp_reverse = self._config.get(CONF_COLOR_TEMP_REVERSE, False)
        self._modes = MAP_MODE_SET[int(self._config.get(CONF_COLOR_MODE_SET, 0))]
        self._hs = None
        self._effect = None
        self._effect_list = []
        self._scenes = DictSelector({})
        self._cached_status = {}

        if self._config.get(CONF_MUSIC_MODE):
            self._effect_list.append(SCENE_MUSIC)

        self._attr_min_color_temp_kelvin = int(
            self._config.get(CONF_COLOR_TEMP_MIN_KELVIN, DEFAULT_MIN_KELVIN)
        )
        self._attr_max_color_temp_kelvin = int(
            self._config.get(CONF_COLOR_TEMP_MAX_KELVIN, DEFAULT_MAX_KELVIN)
        )

        self.__to_color = self.__to_color_common
        self.__from_color = self.__from_color_common

    def connection_made(self):
        """The connection has made with the device and status retrieved, Configure the entity based on its reserved status."""
        super().connection_made()
        is_write_only = self._write_only

        if self.has_config(CONF_SCENE):
            if (cf_scenes := self._config.get(CONF_SCENE_VALUES)) and len(cf_scenes):
                scenes = {v: k for k, v in cf_scenes.items()}
            else:
                scene_value = self.dp_value(CONF_SCENE)
                if is_write_only and not scene_value:
                    scenes = SCENE_LIST_RGBW_BLE
                elif scene_value and len(scene_value) <= 20:
                    scenes = SCENE_LIST_RGBW_255
                elif self._config.get(CONF_BRIGHTNESS) is None:
                    scenes = SCENE_LIST_RGB_1000
                else:
                    scenes = SCENE_LIST_RGBW_1000
                scenes = {**self._modes.as_dict(), **scenes}
            self._scenes = DictSelector(scenes, reverse=True)

            self._effect_list = list(scenes.keys()) + self._effect_list

        if self.has_config(CONF_COLOR):
            color_data = self.dp_value(CONF_COLOR)
            if is_write_only and not color_data:
                self.__to_color = self.__to_color_raw
                self.__from_color = self.__from_color_raw
            else:
                self.__to_color = self.__to_color_common
                self.__from_color = self.__from_color_common

        if is_write_only and self._cached_status:
            self._status.update(self._cached_status)

    @property
    def extra_state_attributes(self):
        """Return entity specific state attributes to be saved.

        These attributes are then available for restore when the
        entity is restored at startup.
        """
        attributes = super().extra_state_attributes

        extra_attrs = (CONF_COLOR_MODE, CONF_COLOR, CONF_BRIGHTNESS, CONF_COLOR_TEMP)
        for attr in extra_attrs:
            dp = self._config.get(attr)
            if dp is not None and (state := self._status.get(dp)) is not None:
                attributes[f"raw_{attr}"] = state

        return attributes

    @property
    def is_on(self):
        """Check if Tuya light is on."""
        return self._state

    @property
    def brightness(self):
        """Return the brightness of the light."""
        brightness = self._brightness
        if brightness is not None and (self.is_color_mode or self.is_white_mode):
            return map_value_by_percent(brightness, self._upper_brightness, 255)

        return None

    @property
    def hs_color(self):
        """Return the hs color value."""
        if self.is_color_mode:
            return self._hs
        if (
            ColorMode.HS in self.supported_color_modes
            and not ColorMode.COLOR_TEMP in self.supported_color_modes
        ):
            return [0, 0]
        return None

    @property
    def color_temp_kelvin(self):
        """Return the color_temp of the light."""
        if self._color_temp is not None:
            return map_range(
                self._color_temp,
                self._lower_brightness,
                self._upper_brightness,
                self.min_color_temp_kelvin,
                self.max_color_temp_kelvin,
                self._color_temp_reverse,
            )

    @property
    def effect(self):
        """Return the current effect for this light."""
        if self.is_scene_mode or self.is_music_mode:
            return self._effect
        elif (color_mode := self.__get_color_mode()) in self._scenes.values:
            return self.__find_scene_by_scene_data(color_mode)
        return None

    @property
    def effect_list(self):
        """Return the list of supported effects for this light."""
        if len(self._effect_list) > 0:
            return self._effect_list
        return None

    @property
    def supported_color_modes(self) -> set[ColorMode] | set[str] | None:
        """Flag supported color modes."""
        color_modes: set[ColorMode] = set()

        if self.has_config(CONF_COLOR_TEMP):
            color_modes.add(ColorMode.COLOR_TEMP)
        elif self.has_config(CONF_BRIGHTNESS):
            color_modes.add(ColorMode.WHITE)
        if self.has_config(CONF_COLOR):
            color_modes.add(ColorMode.HS)

        if self.has_config(CONF_COLOR):
            color_modes.add(ColorMode.HS)

        if color_modes == {ColorMode.WHITE}:
            return {ColorMode.BRIGHTNESS}

        if not color_modes:
            return {ColorMode.ONOFF}

        return color_modes

    @property
    def supported_features(self) -> LightEntityFeature:
        """Flag supported features."""
        supports = LightEntityFeature(0)
        if self.has_config(CONF_SCENE) or self.has_config(CONF_MUSIC_MODE):
            supports |= LightEntityFeature.EFFECT
        return supports

    @property
    def is_white_mode(self):
        """Return true if the light is in white mode."""
        color_mode = self.__get_color_mode()
        return color_mode is None or color_mode == self._modes.white

    @property
    def is_color_mode(self):
        """Return true if the light is in color mode."""
        color_mode = self.__get_color_mode()
        return color_mode is not None and color_mode == self._modes.color

    @property
    def is_scene_mode(self):
        """Return true if the light is in scene mode."""
        color_mode = self.__get_color_mode()
        return color_mode is not None and color_mode.startswith(self._modes.scene)

    @property
    def is_music_mode(self):
        """Return true if the light is in music mode."""
        color_mode = self.__get_color_mode()
        return color_mode is not None and color_mode == self._modes.music

    @property
    def color_mode(self) -> ColorMode:
        """Return the color_mode of the light."""
        if len(self.supported_color_modes) == 1:
            return next(iter(self.supported_color_modes))

        if self.is_color_mode:
            return ColorMode.HS
        if self.is_white_mode:
            if self.has_config(CONF_COLOR_TEMP):
                return ColorMode.COLOR_TEMP
            else:
                return ColorMode.WHITE
        if self._brightness:
            return ColorMode.BRIGHTNESS

        return ColorMode.ONOFF

    def __is_color_rgb_encoded(self):
        # for now we will prefer non encoded if color is none "added by manual or cloud pull dp"
        color = self.dp_value(CONF_COLOR)
        return False if color is None else len(color) > 12

    def __find_scene_by_scene_data(self, data):
        return (
            next(
                (i for i in self._effect_list if self._scenes.to_tuya(i) == data),
                None,
            )
            if data is not None
            else None
        )

    def __get_color_mode(self):
        return (
            self.dp_value(CONF_COLOR_MODE)
            if self.has_config(CONF_COLOR_MODE)
            else self._modes.white
        )

    def __to_color_raw(self, hs, brightness):
        return base64.b64encode(
            # BASE64-encoded 4-byte value: HHSL
            bytes(
                [
                    round(hs[0]) // 256,
                    round(hs[0]) % 256,
                    round(hs[1]),
                    round(brightness * 100 / self._upper_brightness),
                ]
            )
        ).decode("ascii")

    def __to_color_(self, hs, brightness):
        # https://developer.tuya.com/en/docs/iot/dj?id=K9i5ql3v98hn3#title-8-colour_data
        return "{:04x}{:02x}{:02x}".format(
            round(hs[0]),
            round(hs[1] * 255 / 100),
            round(brightness * 255 / self._upper_brightness),
        )

    def __to_color_v2(self, hs, brightness):
        # https://developer.tuya.com/en/docs/iot/dj?id=K9i5ql3v98hn3#title-9-colour_data_v2
        return "{:04x}{:04x}{:04x}".format(
            round(hs[0]), round(hs[1] * 10.0), brightness
        )

    def __to_color_common(self, hs, brightness):
        """Converts HSB values to a string."""
        if self.__is_color_rgb_encoded():
            # Not documented format
            rgb = color_util.color_hsv_to_RGB(
                hs[0], hs[1], int(brightness * 100 / self._upper_brightness)
            )
            return "{:02x}{:02x}{:02x}{:04x}{:02x}{:02x}".format(
                round(rgb[0]),
                round(rgb[1]),
                round(rgb[2]),
                round(hs[0]),
                round(hs[1] * 255 / 100),
                brightness,
            )
        else:
            return self.__to_color_v2(hs, brightness)

    def __from_color_raw(self, color):
        # BASE64-encoded 4-byte value: HHSL
        hsl = int.from_bytes(base64.b64decode(color), byteorder="big", signed=False)
        hue = hsl // 65536
        sat = (hsl // 256) % 256
        value = (hsl % 256) * self._upper_brightness / 100
        self._hs = [hue, sat]
        self._brightness = value

    def __from_color_(self, color):
        # https://developer.tuya.com/en/docs/iot/dj?id=K9i5ql3v98hn3#title-8-colour_data
        hue, sat, value = [int(value, 16) for value in textwrap.wrap(color, 4)]
        self._hs = [hue, sat * 100 / 255]
        self._brightness = value * self._upper_brightness / 100

    def __from_color_v2(self, color):
        # https://developer.tuya.com/en/docs/iot/dj?id=K9i5ql3v98hn3#title-9-colour_data_v2
        hue, sat, value = [int(value, 16) for value in textwrap.wrap(color, 4)]
        self._hs = [hue, sat / 10.0]
        self._brightness = value

    def __from_color_common(self, color):
        """Convert a string to HSL values."""
        if self.__is_color_rgb_encoded():
            hue = int(color[6:10], 16)
            sat = int(color[10:12], 16)
            value = int(color[12:14], 16)
            self._hs = [hue, (sat * 100 / 255)]
            self._brightness = value
        else:
            self.__from_color_v2(color)

    async def async_turn_on(self, **kwargs):
        """Turn on or control the light."""
        states = {}
        if not self.is_on or self._write_only:
            states[self._dp_id] = True
        features = self.supported_features
        color_modes = self.supported_color_modes
        brightness = None
        color_mode = None
        if ATTR_EFFECT in kwargs and (features & LightEntityFeature.EFFECT):
            effect = kwargs[ATTR_EFFECT]
            scene = self._scenes.to_tuya(effect)
            if scene is not None:
                if scene.startswith(self._modes.scene) or scene in (
                    self._modes.white,
                    self._modes.color,
                ):
                    color_mode = scene
                else:
                    color_mode = self._modes.scene
                    states[self._config.get(CONF_SCENE)] = scene
            elif effect in self._modes.as_list():
                color_mode = effect
            elif effect == self._modes.music:
                color_mode = self._modes.music

        if ATTR_BRIGHTNESS in kwargs and (
            ColorMode.BRIGHTNESS in color_modes
            or self.has_config(CONF_BRIGHTNESS)
            or self.has_config(CONF_COLOR)
        ):
            brightness = map_value_by_percent(
                int(kwargs[ATTR_BRIGHTNESS]), 255, self._upper_brightness
            )
            brightness = max(brightness, self._lower_brightness)

            if self.is_color_mode and self._hs is not None:
                states[self._config.get(CONF_COLOR)] = self.__to_color(
                    self._hs, brightness
                )
                color_mode = self._modes.color
            else:
                states[self._config.get(CONF_BRIGHTNESS)] = brightness
                color_mode = self._modes.white

        if ATTR_HS_COLOR in kwargs and ColorMode.HS in color_modes:
            if brightness is None:
                brightness = self._brightness
            hs = kwargs[ATTR_HS_COLOR]
            if hs[1] == 0 and self.has_config(CONF_BRIGHTNESS):
                states[self._config.get(CONF_BRIGHTNESS)] = brightness
                color_mode = self._modes.white
            else:
                states[self._config.get(CONF_COLOR)] = self.__to_color(hs, brightness)
                color_mode = self._modes.color

        if ATTR_COLOR_TEMP_KELVIN in kwargs and ColorMode.COLOR_TEMP in color_modes:
            if brightness is None:
                brightness = self._brightness

            color_temp = map_range(
                int(kwargs[ATTR_COLOR_TEMP_KELVIN]),
                self.min_color_temp_kelvin,
                self.max_color_temp_kelvin,
                self._lower_brightness,
                self._upper_color_temp,
                self._color_temp_reverse,
            )

            color_mode = self._modes.white
            states[self._config.get(CONF_BRIGHTNESS)] = brightness
            states[self._config.get(CONF_COLOR_TEMP)] = color_temp

        if ATTR_WHITE in kwargs and ColorMode.WHITE in color_modes:
            if brightness is None:
                brightness = self._brightness
            color_mode = self._modes.white
            states[self._config.get(CONF_BRIGHTNESS)] = brightness

        if color_mode is not None:
            states[self._config.get(CONF_COLOR_MODE)] = color_mode

        await self._device.set_dps(states)

    async def async_turn_off(self, **kwargs):
        """Turn Tuya light off."""
        await self._device.set_dp(False, self._dp_id)

    def status_updated(self):
        """Device status was updated."""
        self._state = self.dp_value(self._dp_id)
        supported = self.supported_features
        self._effect = None

        if (brightness_dp_value := self.dp_value(CONF_BRIGHTNESS)) is not None:
            self._brightness = brightness_dp_value

        if ColorMode.HS in self.supported_color_modes:
            color = self.dp_value(CONF_COLOR)
            if color is not None and not self.is_white_mode:
                self.__from_color(color)
            elif self._brightness is None:
                self._brightness = self._upper_brightness

        if ColorMode.COLOR_TEMP in self.supported_color_modes:
            self._color_temp = self.dp_value(CONF_COLOR_TEMP)

        if self.is_scene_mode and supported & LightEntityFeature.EFFECT:
            color_mode = self.dp_value(CONF_COLOR_MODE)
            if color_mode != self._modes.scene:
                self._effect = self.__find_scene_by_scene_data(color_mode)
            else:
                self._effect = self.__find_scene_by_scene_data(
                    self.dp_value(CONF_SCENE)
                )
                if self._effect is None:
                    self._effect = self.__find_scene_by_scene_data(color_mode)

        if self.is_music_mode and supported & LightEntityFeature.EFFECT:
            self._effect = SCENE_MUSIC

    def status_restored(self, stored_state) -> None:
        """Device status was restored."""
        restore_attrs = (CONF_COLOR_MODE, CONF_COLOR, CONF_BRIGHTNESS, CONF_COLOR_TEMP)
        if self._write_only:
            for attr in restore_attrs:
                dp = self._config.get(attr)
                restored_value = stored_state.attributes.get(f"raw_{attr}")
                if None in (dp, restored_value):
                    continue
                self._cached_status[dp] = restored_value
                self._state = self._last_state


async_setup_entry = partial(async_setup_entry, DOMAIN, LocalTuyaLight, flow_schema)
