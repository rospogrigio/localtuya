"""
    This a file contains available tuya data
    https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq

    Credits: official HA Tuya integration.
    Modified by: xZetsubou
"""

from homeassistant.components.number import NumberDeviceClass
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTime,
    UnitOfPower,
    UnitOfTemperature,
    CONF_UNIT_OF_MEASUREMENT,
    UnitOfLength,
)

from .base import DPCode, LocalTuyaEntity, EntityCategory, CLOUD_VALUE
from ...const import CONF_MIN_VALUE, CONF_MAX_VALUE, CONF_STEPSIZE, CONF_SCALING


def localtuya_numbers(_min, _max, _step=1, _scale=1, unit=None) -> dict:
    """Will return dict with CONF MIN AND CONF MAX, scale 1 is default, 1=1"""
    data = {
        CONF_MIN_VALUE: CLOUD_VALUE(_min, "id", "min"),
        CONF_MAX_VALUE: CLOUD_VALUE(_max, "id", "max"),
        CONF_STEPSIZE: CLOUD_VALUE(_step, "id", "step"),
        CONF_SCALING: CLOUD_VALUE(_scale, "id", "scale"),
    }

    if unit:
        data.update({CONF_UNIT_OF_MEASUREMENT: unit})

    return data


NUMBERS: dict[str, tuple[LocalTuyaEntity, ...]] = {
    # Smart panel with switches and zigbee hub ?
    # Not documented
    "dgnzk": (
        LocalTuyaEntity(
            id=DPCode.VOICE_VOL,
            name="Volume",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(0, 100),
            icon="mdi:volume-equal",
        ),
        LocalTuyaEntity(
            id=DPCode.PLAY_TIME,
            name="Play time",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(0, 7200, unit=UnitOfTime.SECONDS),
            icon="mdi:motion-play-outline",
        ),
        LocalTuyaEntity(
            id=DPCode.BASS_CONTROL,
            name="Bass",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(0, 15),
            icon="mdi:speaker",
        ),
        LocalTuyaEntity(
            id=DPCode.TREBLE_CONTROL,
            name="Treble",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(0, 15),
            icon="mdi:music-clef-treble",
        ),
    ),
    # Multi-functional Sensor
    # https://developer.tuya.com/en/docs/iot/categorydgnbj?id=Kaiuz3yorvzg3
    "dgnbj": (
        LocalTuyaEntity(
            id=DPCode.ALARM_TIME,
            name="Time",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(0, 60),
        ),
    ),
    # Smart Kettle
    # https://developer.tuya.com/en/docs/iot/fbh?id=K9gf484m21yq7
    "bh": (
        LocalTuyaEntity(
            id=DPCode.TEMP_SET,
            name="Temperature",
            device_class=NumberDeviceClass.TEMPERATURE,
            icon="mdi:thermometer",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(0, 100),
        ),
        LocalTuyaEntity(
            id=DPCode.TEMP_SET_F,
            name="Temperature",
            device_class=NumberDeviceClass.TEMPERATURE,
            icon="mdi:thermometer",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(32, 212),
        ),
        LocalTuyaEntity(
            id=DPCode.TEMP_BOILING_C,
            name="Temperature After Boiling",
            device_class=NumberDeviceClass.TEMPERATURE,
            icon="mdi:thermometer",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(0, 100),
        ),
        LocalTuyaEntity(
            id=DPCode.TEMP_BOILING_F,
            name="Temperature After Boiling",
            device_class=NumberDeviceClass.TEMPERATURE,
            icon="mdi:thermometer",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(32, 212),
        ),
        LocalTuyaEntity(
            id=DPCode.WARM_TIME,
            name="Heat preservation time",
            icon="mdi:timer",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(0, 360),
        ),
    ),
    # Smart Pet Feeder
    # https://developer.tuya.com/en/docs/iot/categorycwwsq?id=Kaiuz2b6vydld
    "cwwsq": (
        LocalTuyaEntity(
            id=DPCode.MANUAL_FEED,
            name="Feed",
            icon="mdi:bowl",
            custom_configs=localtuya_numbers(1, 12),
        ),
        LocalTuyaEntity(
            id=DPCode.VOICE_TIMES,
            name="Voice prompt",
            icon="mdi:microphone",
            custom_configs=localtuya_numbers(0, 10),
        ),
    ),
    # Light
    # https://developer.tuya.com/en/docs/iot/categorydj?id=Kaiuyzy3eheyy
    "dj": (
        LocalTuyaEntity(
            id=DPCode.COUNTDOWN_1,
            icon="mdi:timer",
            entity_category=EntityCategory.CONFIG,
            name="Light 1 Timer",
            custom_configs=localtuya_numbers(0, 86400, 1, 1, UnitOfTime.SECONDS),
        ),
        LocalTuyaEntity(
            id=DPCode.COUNTDOWN_2,
            icon="mdi:timer",
            entity_category=EntityCategory.CONFIG,
            name="Light 2 Timer",
            custom_configs=localtuya_numbers(0, 86400, 1, 1, UnitOfTime.SECONDS),
        ),
        LocalTuyaEntity(
            id=DPCode.COUNTDOWN_3,
            icon="mdi:timer",
            entity_category=EntityCategory.CONFIG,
            name="Light 3 Timer",
            custom_configs=localtuya_numbers(0, 86400, 1, 1, UnitOfTime.SECONDS),
        ),
        LocalTuyaEntity(
            id=DPCode.COUNTDOWN_4,
            icon="mdi:timer",
            entity_category=EntityCategory.CONFIG,
            name="Light 4 Timer",
            custom_configs=localtuya_numbers(0, 86400, 1, 1, UnitOfTime.SECONDS),
        ),
        LocalTuyaEntity(
            id=DPCode.COUNTDOWN,
            icon="mdi:timer",
            entity_category=EntityCategory.CONFIG,
            name="Timer",
            custom_configs=localtuya_numbers(0, 86400, 1, 1, UnitOfTime.SECONDS),
        ),
    ),
    # Human Presence Sensor
    # https://developer.tuya.com/en/docs/iot/categoryhps?id=Kaiuz42yhn1hs
    "hps": (
        LocalTuyaEntity(
            id=DPCode.SENSITIVITY,
            name="sensitivity",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(0, 9),
        ),
        LocalTuyaEntity(
            id=DPCode.NEAR_DETECTION,
            name="Near Detection CM",
            icon="mdi:signal-distance-variant",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(0, 1000),
        ),
        LocalTuyaEntity(
            id=DPCode.FAR_DETECTION,
            name="Far Detection CM",
            icon="mdi:signal-distance-variant",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(0, 1000),
        ),
    ),
    # Coffee maker
    # https://developer.tuya.com/en/docs/iot/categorykfj?id=Kaiuz2p12pc7f
    "kfj": (
        LocalTuyaEntity(
            id=DPCode.WATER_SET,
            name="Water Level",
            icon="mdi:cup-water",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(0, 500),
        ),
        LocalTuyaEntity(
            id=DPCode.TEMP_SET,
            name="Temperature",
            device_class=NumberDeviceClass.TEMPERATURE,
            icon="mdi:thermometer",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(0, 100),
        ),
        LocalTuyaEntity(
            id=DPCode.WARM_TIME,
            name="Heat preservation time",
            icon="mdi:timer",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(0, 1440),
        ),
        LocalTuyaEntity(
            id=DPCode.POWDER_SET,
            name="Powder",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(0, 24),
        ),
    ),
    # Switch
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf7o5prgf7s
    "kg": (
        LocalTuyaEntity(
            id=DPCode.COUNTDOWN_1,
            icon="mdi:timer",
            entity_category=EntityCategory.CONFIG,
            name="Switch 1 Timer",
            custom_configs=localtuya_numbers(0, 86400, 1, 1, UnitOfTime.SECONDS),
        ),
        LocalTuyaEntity(
            id=DPCode.COUNTDOWN_2,
            icon="mdi:timer",
            entity_category=EntityCategory.CONFIG,
            name="Switch 2 Timer",
            custom_configs=localtuya_numbers(0, 86400, 1, 1, UnitOfTime.SECONDS),
        ),
        LocalTuyaEntity(
            id=DPCode.COUNTDOWN_3,
            icon="mdi:timer",
            entity_category=EntityCategory.CONFIG,
            name="Switch 3 Timer",
            custom_configs=localtuya_numbers(0, 86400, 1, 1, UnitOfTime.SECONDS),
        ),
        LocalTuyaEntity(
            id=DPCode.COUNTDOWN_4,
            icon="mdi:timer",
            entity_category=EntityCategory.CONFIG,
            name="Switch 4 Timer",
            custom_configs=localtuya_numbers(0, 86400, 1, 1, UnitOfTime.SECONDS),
        ),
        LocalTuyaEntity(
            id=DPCode.COUNTDOWN_5,
            icon="mdi:timer",
            entity_category=EntityCategory.CONFIG,
            name="Switch 5 Timer",
            custom_configs=localtuya_numbers(0, 86400, 1, 1, UnitOfTime.SECONDS),
        ),
        LocalTuyaEntity(
            id=DPCode.COUNTDOWN_6,
            icon="mdi:timer",
            entity_category=EntityCategory.CONFIG,
            name="Switch 6 Timer",
            custom_configs=localtuya_numbers(0, 86400, 1, 1, UnitOfTime.SECONDS),
        ),
        LocalTuyaEntity(
            id=DPCode.COUNTDOWN_USB1,
            icon="mdi:timer",
            entity_category=EntityCategory.CONFIG,
            name="USB1 Timer",
            custom_configs=localtuya_numbers(0, 86400, 1, 1, UnitOfTime.SECONDS),
        ),
        LocalTuyaEntity(
            id=DPCode.COUNTDOWN_USB2,
            icon="mdi:timer",
            entity_category=EntityCategory.CONFIG,
            name="USB2 Timer",
            custom_configs=localtuya_numbers(0, 86400, 1, 1, UnitOfTime.SECONDS),
        ),
        LocalTuyaEntity(
            id=DPCode.COUNTDOWN_USB3,
            icon="mdi:timer",
            entity_category=EntityCategory.CONFIG,
            name="USB3 Timer",
            custom_configs=localtuya_numbers(0, 86400, 1, 1, UnitOfTime.SECONDS),
        ),
        LocalTuyaEntity(
            id=DPCode.COUNTDOWN_USB4,
            icon="mdi:timer",
            entity_category=EntityCategory.CONFIG,
            name="USB4 Timer",
            custom_configs=localtuya_numbers(0, 86400, 1, 1, UnitOfTime.SECONDS),
        ),
        LocalTuyaEntity(
            id=DPCode.COUNTDOWN_USB5,
            icon="mdi:timer",
            entity_category=EntityCategory.CONFIG,
            name="USB5 Timer",
            custom_configs=localtuya_numbers(0, 86400, 1, 1, UnitOfTime.SECONDS),
        ),
        LocalTuyaEntity(
            id=DPCode.COUNTDOWN_USB6,
            icon="mdi:timer",
            entity_category=EntityCategory.CONFIG,
            name="USB6 Timer",
            custom_configs=localtuya_numbers(0, 86400, 1, 1, UnitOfTime.SECONDS),
        ),
        LocalTuyaEntity(
            id=DPCode.COUNTDOWN,
            icon="mdi:timer",
            entity_category=EntityCategory.CONFIG,
            name="Switch Timer",
            custom_configs=localtuya_numbers(0, 86400, 1, 1, UnitOfTime.SECONDS),
        ),
        LocalTuyaEntity(
            id=DPCode.COUNTDOWN_USB,
            icon="mdi:timer",
            entity_category=EntityCategory.CONFIG,
            name="Switch Timer",
            custom_configs=localtuya_numbers(0, 86400, 1, 1, UnitOfTime.SECONDS),
        ),
        # CZ - Energy monitor?
        LocalTuyaEntity(
            id=DPCode.WARN_POWER,
            icon="mdi:alert-outline",
            entity_category=EntityCategory.CONFIG,
            name="Power Wanring Limit",
            custom_configs=localtuya_numbers(0, 50000, 1, 1, UnitOfPower.WATT),
        ),
        LocalTuyaEntity(
            id=DPCode.WARN_POWER1,
            icon="mdi:alert-outline",
            entity_category=EntityCategory.CONFIG,
            name="Power 1 Wanring Limit",
            custom_configs=localtuya_numbers(0, 50000, 1, 1, UnitOfPower.WATT),
        ),
        LocalTuyaEntity(
            id=DPCode.WARN_POWER2,
            icon="mdi:alert-outline",
            entity_category=EntityCategory.CONFIG,
            name="Power 2 Wanring Limit",
            custom_configs=localtuya_numbers(0, 50000, 1, 1, UnitOfPower.WATT),
        ),
        LocalTuyaEntity(
            id=DPCode.POWER_ADJUSTMENT,
            icon="mdi:generator-mobile",
            entity_category=EntityCategory.CONFIG,
            name="Power Adjustment",
            custom_configs=localtuya_numbers(20, 100, 1, 1, PERCENTAGE),
        ),
        # Fan "tdq"
        LocalTuyaEntity(
            id=DPCode.FAN_COUNTDOWN,
            icon="mdi:timer",
            entity_category=EntityCategory.CONFIG,
            name="Fan Timer",
            custom_configs=localtuya_numbers(0, 86400, 1, 1, UnitOfTime.SECONDS),
        ),
        LocalTuyaEntity(
            id=DPCode.FAN_COUNTDOWN_2,
            icon="mdi:timer",
            entity_category=EntityCategory.CONFIG,
            name="Fan 2 Timer",
            custom_configs=localtuya_numbers(0, 86400, 1, 1, UnitOfTime.SECONDS),
        ),
        LocalTuyaEntity(
            id=DPCode.FAN_COUNTDOWN_3,
            icon="mdi:timer",
            entity_category=EntityCategory.CONFIG,
            name="Fan 3 Timer",
            custom_configs=localtuya_numbers(0, 86400, 1, 1, UnitOfTime.SECONDS),
        ),
        LocalTuyaEntity(
            id=DPCode.FAN_COUNTDOWN_4,
            icon="mdi:timer",
            entity_category=EntityCategory.CONFIG,
            name="Fan 4 Timer",
            custom_configs=localtuya_numbers(0, 86400, 1, 1, UnitOfTime.SECONDS),
        ),
    ),
    # Smart Lock
    # https://developer.tuya.com/en/docs/iot/s?id=Kb0o2xhlkxbet
    "mc": (
        LocalTuyaEntity(
            id=(
                DPCode.UNLOCK_APP,
                DPCode.UNLOCK_FINGERPRINT,
                DPCode.UNLOCK_CARD,
                DPCode.UNLOCK_DYNAMIC,
                DPCode.UNLOCK_TEMPORARY,
            ),
            name="Temporary Unlock",
            icon="mdi:lock-open",
            custom_configs=localtuya_numbers(0, 999, 1, 1, UnitOfTime.SECONDS),
        ),
    ),
    # Sous Vide Cooker
    # https://developer.tuya.com/en/docs/iot/categorymzj?id=Kaiuz2vy130ux
    "mzj": (
        LocalTuyaEntity(
            id=DPCode.COOK_TEMPERATURE,
            name="Cooking temperature",
            icon="mdi:thermometer",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(0, 500),
        ),
        LocalTuyaEntity(
            id=DPCode.COOK_TIME,
            name="Cooking time",
            icon="mdi:timer",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(0, 360, 1, 1, UnitOfTime.MINUTES),
        ),
        LocalTuyaEntity(
            id=DPCode.CLOUD_RECIPE_NUMBER,
            name="Cloud Recipes",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(0, 999999),
        ),
        LocalTuyaEntity(
            id=DPCode.APPOINTMENT_TIME,
            name="Appointment time",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(0, 360),
        ),
    ),
    # PIR Detector
    # https://developer.tuya.com/en/docs/iot/categorypir?id=Kaiuz3ss11b80
    "pir": (
        LocalTuyaEntity(
            id=DPCode.SENS,
            icon="mdi:signal-distance-variant",
            entity_category=EntityCategory.CONFIG,
            name="Sensitivity",
            custom_configs=localtuya_numbers(0, 4),
        ),
        LocalTuyaEntity(
            id=DPCode.TIM,
            icon="mdi:timer-10",
            entity_category=EntityCategory.CONFIG,
            name="Timer Duration",
            custom_configs=localtuya_numbers(10, 900, 1, 1, UnitOfTime.SECONDS),
        ),
        LocalTuyaEntity(
            id=DPCode.LUX,
            icon="mdi:brightness-6",
            entity_category=EntityCategory.CONFIG,
            name="Light level",
            custom_configs=localtuya_numbers(0, 981, 1, 1, "lx"),
        ),
        LocalTuyaEntity(
            id=DPCode.INTERVAL_TIME,
            icon="mdi:timer-sand-complete",
            entity_category=EntityCategory.CONFIG,
            name="Interval",
            custom_configs=localtuya_numbers(1, 720, 1, 1, UnitOfTime.MINUTES),
        ),
    ),
    # Robot Vacuum
    # https://developer.tuya.com/en/docs/iot/fsd?id=K9gf487ck1tlo
    "sd": (
        LocalTuyaEntity(
            id=DPCode.VOLUME_SET,
            name="volume",
            icon="mdi:volume-high",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(0, 100),
        ),
    ),
    # Siren Alarm
    # https://developer.tuya.com/en/docs/iot/categorysgbj?id=Kaiuz37tlpbnu
    "sgbj": (
        LocalTuyaEntity(
            id=(DPCode.ALARM_TIME, DPCode.ALARMPERIOD),
            name="Alarm duration",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(1, 60),
        ),
    ),
    # Smart Camera
    # https://developer.tuya.com/en/docs/iot/categorysp?id=Kaiuz35leyo12
    "sp": (
        LocalTuyaEntity(
            id=DPCode.BASIC_DEVICE_VOLUME,
            name="volume",
            icon="mdi:volume-high",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(1, 10),
        ),
        LocalTuyaEntity(
            id=DPCode.FLOODLIGHT_LIGHTNESS,
            name="Floodlight brightness",
            icon="mdi:brightness-6",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(1, 100),
        ),
    ),
    # Dimmer Switch
    # https://developer.tuya.com/en/docs/iot/categorytgkg?id=Kaiuz0ktx7m0o
    "tgkg": (
        LocalTuyaEntity(
            id=DPCode.BRIGHTNESS_MIN_1,
            name="minimum_brightness",
            icon="mdi:lightbulb-outline",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(10, 1000),
        ),
        LocalTuyaEntity(
            id=DPCode.BRIGHTNESS_MAX_1,
            name="maximum_brightness",
            icon="mdi:lightbulb-on-outline",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(10, 1000),
        ),
        LocalTuyaEntity(
            id=DPCode.BRIGHTNESS_MIN_2,
            name="minimum_brightness_2",
            icon="mdi:lightbulb-outline",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(10, 1000),
        ),
        LocalTuyaEntity(
            id=DPCode.BRIGHTNESS_MAX_2,
            name="maximum_brightness_2",
            icon="mdi:lightbulb-on-outline",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(10, 1000),
        ),
        LocalTuyaEntity(
            id=DPCode.BRIGHTNESS_MIN_3,
            name="minimum_brightness_3",
            icon="mdi:lightbulb-outline",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(10, 1000),
        ),
        LocalTuyaEntity(
            id=DPCode.BRIGHTNESS_MAX_3,
            name="maximum_brightness_3",
            icon="mdi:lightbulb-on-outline",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(10, 1000),
        ),
    ),
    # Dimmer Switch
    # https://developer.tuya.com/en/docs/iot/categorytgkg?id=Kaiuz0ktx7m0o
    "tgq": (
        LocalTuyaEntity(
            id=DPCode.BRIGHTNESS_MIN_1,
            name="minimum_brightness",
            icon="mdi:lightbulb-outline",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(10, 1000),
        ),
        LocalTuyaEntity(
            id=DPCode.BRIGHTNESS_MAX_1,
            name="maximum_brightness",
            icon="mdi:lightbulb-on-outline",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(10, 1000),
        ),
        LocalTuyaEntity(
            id=DPCode.BRIGHTNESS_MIN_2,
            name="minimum_brightness_2",
            icon="mdi:lightbulb-outline",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(10, 1000),
        ),
        LocalTuyaEntity(
            id=DPCode.BRIGHTNESS_MAX_2,
            name="maximum_brightness_2",
            icon="mdi:lightbulb-on-outline",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(10, 1000),
        ),
    ),
    # Vibration Sensor
    # https://developer.tuya.com/en/docs/iot/categoryzd?id=Kaiuz3a5vrzno
    "zd": (
        LocalTuyaEntity(
            id=DPCode.SENSITIVITY,
            name="Sensitivity",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(0, 9),
        ),
    ),
    # Fingerbot
    # arm_down_percent: "{\"min\":50,\"max\":100,\"scale\":0,\"step\":1}"
    # arm_up_percent: "{\"min\":0,\"max\":50,\"scale\":0,\"step\":1}"
    # click_sustain_time: "values": "{\"unit\":\"s\",\"min\":2,\"max\":10,\"scale\":0,\"step\":1}"
    "szjqr": (
        LocalTuyaEntity(
            id=DPCode.ARM_DOWN_PERCENT,
            name="Move Down",
            icon="mdi:arrow-down-bold",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(50, 100, 1, 1, PERCENTAGE),
        ),
        LocalTuyaEntity(
            id=DPCode.ARM_UP_PERCENT,
            name="Move UP",
            icon="mdi:arrow-up-bold",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(0, 50, 1, 1, PERCENTAGE),
        ),
        LocalTuyaEntity(
            id=DPCode.CLICK_SUSTAIN_TIME,
            name="Down Delay",
            icon="mdi:timer",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(2, 10),
        ),
    ),
    # Fan
    # https://developer.tuya.com/en/docs/iot/categoryfs?id=Kaiuz1xweel1c
    "fs": (
        LocalTuyaEntity(
            id=DPCode.TEMP,
            name="Temperature",
            device_class=NumberDeviceClass.TEMPERATURE,
            icon="mdi:thermometer-lines",
        ),
    ),
    # Humidifier
    # https://developer.tuya.com/en/docs/iot/categoryjsq?id=Kaiuz1smr440b
    "jsq": (
        LocalTuyaEntity(
            id=DPCode.TEMP_SET,
            name="Temperature",
            device_class=NumberDeviceClass.TEMPERATURE,
            icon="mdi:thermometer-lines",
            custom_configs=localtuya_numbers(0, 50),
        ),
        LocalTuyaEntity(
            id=DPCode.TEMP_SET_F,
            name="Temperature",
            device_class=NumberDeviceClass.TEMPERATURE,
            icon="mdi:thermometer-lines",
            custom_configs=localtuya_numbers(32, 212, 1),
        ),
    ),
    # Thermostat
    "wk": (
        LocalTuyaEntity(
            id=DPCode.TEMPCOMP,
            name="Calibration offset",
            custom_configs=localtuya_numbers(-9, 9),
        ),
        LocalTuyaEntity(
            id=DPCode.TEMPACTIVATE,
            name="Calibration swing",
            custom_configs=localtuya_numbers(1, 9),
        ),
    ),
    # Temperature and Humidity Sensor
    # https://developer.tuya.com/en/docs/iot/categorywsdcg?id=Kaiuz3hinij34
    "wsdcg": (
        LocalTuyaEntity(
            id=(DPCode.MAXTEMP_SET, DPCode.UPPER_TEMP, DPCode.UPPER_TEMP_F),
            name="Max Temperature",
            icon="mdi:thermometer-high",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(-200, 600, unit=UnitOfTemperature.CELSIUS),
        ),
        LocalTuyaEntity(
            id=(DPCode.MINITEMP_SET, DPCode.LOWER_TEMP, DPCode.LOWER_TEMP_F),
            name="Min Temperature",
            icon="mdi:thermometer-low",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(-200, 600, unit=UnitOfTemperature.CELSIUS),
        ),
        LocalTuyaEntity(
            id=(DPCode.MAXHUM_SET, DPCode.MAX_HUMI),
            name="Max Humidity",
            icon="mdi:water-percent",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(0, 100, unit=PERCENTAGE),
        ),
        LocalTuyaEntity(
            id=(DPCode.MINIHUM_SET, DPCode.MIN_HUMI),
            name="Min Humidity",
            icon="mdi:water-percent",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(0, 100, unit=PERCENTAGE),
        ),
        LocalTuyaEntity(
            id=DPCode.TEMP_PERIODIC_REPORT,
            name="Report Temperature Period",
            icon="mdi:timer-sand",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(1, 120, unit=UnitOfTime.MINUTES),
        ),
        LocalTuyaEntity(
            id=DPCode.HUM_PERIODIC_REPORT,
            name="Report Humidity Period",
            icon="mdi:timer-sand",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(1, 120, unit=UnitOfTime.MINUTES),
        ),
        LocalTuyaEntity(
            id=DPCode.TEMP_SENSITIVITY,
            name="Temperature Sensitivity",
            icon="mdi:thermometer-lines",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(3, 20, unit=UnitOfTemperature.CELSIUS),
        ),
        LocalTuyaEntity(
            id=DPCode.HUM_SENSITIVITY,
            name="Humidity Sensitivity",
            icon="mdi:water-opacity",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_numbers(3, 20, unit=PERCENTAGE),
        ),
    ),
    # Alarm Host
    # https://developer.tuya.com/en/docs/iot/categorymal?id=Kaiuz33clqxaf
    "mal": (
        LocalTuyaEntity(
            id=DPCode.DELAY_SET,
            name="Delay Setting",
            custom_configs=localtuya_numbers(0, 65535),
            icon="mdi:clock-outline",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.ALARM_TIME,
            name="Duration",
            custom_configs=localtuya_numbers(0, 65535),
            icon="mdi:alarm",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.ALARM_DELAY_TIME,
            name="Delay Alarm",
            custom_configs=localtuya_numbers(0, 65535),
            icon="mdi:history",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Air conditioner
    # https://developer.tuya.com/en/docs/iot/categorykt?id=Kaiuz0z71ov2n
    "kt": (
        LocalTuyaEntity(
            id=DPCode.TIMER,
            name="Timer",
            custom_configs=localtuya_numbers(0, 24, unit=UnitOfTime.HOURS),
            icon="mdi:timer-outline",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Smart Electricity Meter
    # https://developer.tuya.com/en/docs/iot/smart-meter?id=Kaiuz4gv6ack7
    "zndb": (
        LocalTuyaEntity(
            id=DPCode.ENERGY_A_CALIBRATION_FWD,
            name="Energy A Calibrations",
            custom_configs=localtuya_numbers(800, 1200),
            icon="mdi:lightning-bolt-outline",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.ENERGY_B_CALIBRATION_FWD,
            name="Energy A Calibrations",
            custom_configs=localtuya_numbers(800, 1200),
            icon="mdi:lightning-bolt-outline",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.ENERGY_C_CALIBRATION_FWD,
            name="Energy A Calibrations",
            custom_configs=localtuya_numbers(800, 1200),
            icon="mdi:lightning-bolt-outline",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.ENERGY_A_CALIBRATION_REV,
            name="Reverse Energy A Calibrations",
            custom_configs=localtuya_numbers(800, 1200),
            icon="mdi:lightning-bolt-outline",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.ENERGY_B_CALIBRATION_REV,
            name="Reverse Energy B Calibrations",
            custom_configs=localtuya_numbers(800, 1200),
            icon="mdi:lightning-bolt-outline",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.ENERGY_C_CALIBRATION_REV,
            name="Reverse Energy C Calibrations",
            custom_configs=localtuya_numbers(800, 1200),
            icon="mdi:lightning-bolt-outline",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.CURRENT_A_CALIBRATION,
            name="Current A Calibrations",
            custom_configs=localtuya_numbers(800, 1200),
            icon="mdi:power-cycle",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.CURRENT_B_CALIBRATION,
            name="Current B Calibrations",
            custom_configs=localtuya_numbers(800, 1200),
            icon="mdi:power-cycle",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.CURRENT_C_CALIBRATION,
            name="Current C Calibrations",
            custom_configs=localtuya_numbers(800, 1200),
            icon="mdi:power-cycle",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.POWER_A_CALIBRATION,
            name="Power A Calibrations",
            custom_configs=localtuya_numbers(800, 1200),
            icon="mdi:power-cycle",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.POWER_B_CALIBRATION,
            name="Power B Calibrations",
            custom_configs=localtuya_numbers(800, 1200),
            icon="mdi:power-cycle",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.POWER_C_CALIBRATION,
            name="Power C Calibrations",
            custom_configs=localtuya_numbers(800, 1200),
            icon="mdi:power-cycle",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.FREQ_CALIBRATION,
            name="Frequency Calibrations",
            custom_configs=localtuya_numbers(800, 1200),
            icon="mdi:sine-wave",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.VOLTAGE_COEF,
            name="Voltage Calibrations",
            custom_configs=localtuya_numbers(800, 1200),
            icon="mdi:flash-triangle-outline",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.REPORT_RATE_CONTROL,
            name="Report Period",
            custom_configs=localtuya_numbers(3, 60, unit=UnitOfTime.SECONDS),
            icon="mdi:timer-sand",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Ultrasonic level sensor
    "ywcgq": (
        LocalTuyaEntity(
            id=DPCode.MAX_SET,
            name="Maximum",
            custom_configs=localtuya_numbers(0, 100, unit=PERCENTAGE),
            icon="mdi:pan-top-right",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.MINI_SET,
            name="Minimum",
            custom_configs=localtuya_numbers(0, 100, unit=PERCENTAGE),
            icon="mdi:pan-bottom-left",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.LIQUID_DEPTH_MAX,
            name="Depth Maximum",
            custom_configs=localtuya_numbers(100, 2400, unit=UnitOfLength.METERS),
            icon="mdi:arrow-collapse-down",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.INSTALLATION_HEIGHT,
            name="Installation Height",
            custom_configs=localtuya_numbers(
                200, 2500, _scale=0.001, unit=UnitOfLength.METERS
            ),
            icon="mdi:table-row-height",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
}

# Wireless Switch  # also can come as knob switch.
# https://developer.tuya.com/en/docs/iot/wxkg?id=Kbeo9t3ryuqm5
NUMBERS["wxkg"] = (
    LocalTuyaEntity(
        id=DPCode.TEMP_VALUE,
        name="Temperature",
        icon="mdi:thermometer",
        custom_configs=localtuya_numbers(0, 1000),
    ),
    *NUMBERS["kg"],
)

# Water Valve
NUMBERS["sfkzq"] = NUMBERS["kg"]

# Water Detector
# https://developer.tuya.com/en/docs/iot/categorysj?id=Kaiuz3iub2sli
NUMBERS["sj"] = NUMBERS["wsdcg"]

# Circuit Breaker
# https://developer.tuya.com/en/docs/iot/dlq?id=Kb0kidk9enyh8
NUMBERS["dlq"] = NUMBERS["zndb"]

# HDMI Sync Box A1
NUMBERS["hdmipmtbq"] = NUMBERS["dj"]

# Scene Switch
# https://developer.tuya.com/en/docs/iot/f?id=K9gf7nx6jelo8
NUMBERS["cjkg"] = NUMBERS["kg"]

NUMBERS["cz"] = NUMBERS["kg"]
NUMBERS["tdq"] = NUMBERS["kg"]
NUMBERS["pc"] = NUMBERS["kg"]

# Locker
NUMBERS["bxx"] = NUMBERS["mc"]
NUMBERS["gyms"] = NUMBERS["mc"]
NUMBERS["jtmspro"] = NUMBERS["mc"]
NUMBERS["hotelms"] = NUMBERS["mc"]
NUMBERS["ms_category"] = NUMBERS["mc"]
NUMBERS["jtmsbh"] = NUMBERS["mc"]
NUMBERS["mk"] = NUMBERS["mc"]
NUMBERS["videolock"] = NUMBERS["mc"]
NUMBERS["photolock"] = NUMBERS["mc"]
