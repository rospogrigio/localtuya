"""
    This a file contains available tuya data
    https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq

    Credits: official HA Tuya integration.
    Modified by: xZetsubou
"""

from .base import DPCode, LocalTuyaEntity, CONF_DEVICE_CLASS, EntityCategory
from homeassistant.components.switch import SwitchDeviceClass

CHILD_LOCK = (
    LocalTuyaEntity(
        id=DPCode.CHILD_LOCK,
        name="Child Lock",
        icon="mdi:account-lock",
        entity_category=EntityCategory.CONFIG,
    ),
)
SWITCHES: dict[str, tuple[LocalTuyaEntity, ...]] = {
    # Smart Kettle
    # https://developer.tuya.com/en/docs/iot/fbh?id=K9gf484m21yq7
    "bh": (
        LocalTuyaEntity(
            id=DPCode.START,
            name="Start",
            icon="mdi:kettle-steam",
        ),
        LocalTuyaEntity(
            id=DPCode.WARM,
            name="Warm",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # EasyBaby
    # Undocumented, might have a wider use
    "cn": (
        LocalTuyaEntity(
            id=DPCode.DISINFECTION,
            name="Disinfection",
            icon="mdi:bacteria",
        ),
        LocalTuyaEntity(
            id=DPCode.WATER,
            name="Water",
            icon="mdi:water",
        ),
    ),
    # Smart Pet Feeder
    # https://developer.tuya.com/en/docs/iot/categorycwwsq?id=Kaiuz2b6vydld
    "cwwsq": (
        LocalTuyaEntity(
            id=DPCode.SLOW_FEED,
            name="Slow Feed",
            icon="mdi:speedometer-slow",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Pet Water Feeder
    # https://developer.tuya.com/en/docs/iot/f?id=K9gf46aewxem5
    "cwysj": (
        LocalTuyaEntity(
            id=DPCode.FILTER_RESET,
            name="Reset Filter",
            icon="mdi:filter",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.PUMP_RESET,
            name="Reset Water Pump",
            icon="mdi:pump",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH,
            name="Power",
        ),
        LocalTuyaEntity(
            id=DPCode.WATER_RESET,
            name="Reset Water",
            icon="mdi:water-sync",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.UV,
            name="UV Sterilization",
            icon="mdi:lightbulb",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Light
    # https://developer.tuya.com/en/docs/iot/f?id=K9i5ql3v98hn3
    "dj": (
        # There are sockets available with an RGB light
        # that advertise as `dj`, but provide an additional
        # switch to control the plug.
        LocalTuyaEntity(
            id=DPCode.SWITCH,
            name="Plug",
        ),
    ),
    # Circuit Breaker
    "dlq": (
        LocalTuyaEntity(
            id=DPCode.CHILD_LOCK,
            name="Child Lock",
            icon="mdi:account-lock",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH,
            name="Switch",
        ),
    ),
    # Wake Up Light II
    # Not documented
    "hxd": (
        LocalTuyaEntity(
            id=DPCode.SWITCH_1,
            name="Radio",
            icon="mdi:radio",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_2,
            name="Alarm 2",
            icon="mdi:alarm",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_3,
            name="Alarm 3",
            icon="mdi:alarm",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_4,
            name="Alarm 4",
            icon="mdi:alarm",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_5,
            name="Alarm 5",
            icon="mdi:alarm",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_6,
            name="Alarm 6",
            icon="mdi:power-sleep",
        ),
    ),
    # Two-way temperature and humidity switch
    # "MOES Temperature and Humidity Smart Switch Module MS-103"
    # Documentation not found
    "wkcz": (
        LocalTuyaEntity(
            id=DPCode.SWITCH_1,
            name="Switch 1",
            device_class=SwitchDeviceClass.OUTLET,
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_2,
            name="Switch 2",
            device_class=SwitchDeviceClass.OUTLET,
        ),
    ),
    # Switch
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf7o5prgf7s
    "kg": (
        LocalTuyaEntity(
            id=DPCode.CHILD_LOCK,
            name="Child lock",
            icon="mdi:account-lock",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH,
            name="Switch",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_1,
            name="Switch 1",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_2,
            name="Switch 2",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_3,
            name="Switch 3",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_4,
            name="Switch 4",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_5,
            name="Switch 5",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_6,
            name="Switch 6",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_7,
            name="Switch 7",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_8,
            name="Switch 8",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_USB1,
            name="USB",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_USB2,
            name="USB 2",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_USB3,
            name="USB 3",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_USB4,
            name="USB 4",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_USB5,
            name="USB 5",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_USB6,
            name="USB 6",
            device_class=SwitchDeviceClass.OUTLET,
        ),
    ),
    # Air Purifier
    # https://developer.tuya.com/en/docs/iot/f?id=K9gf46h2s6dzm
    "kj": (
        LocalTuyaEntity(
            id=DPCode.ANION,
            name="Ionizer",
            icon="mdi:minus-circle-outline",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.FILTER_RESET,
            name="Reset Filter Cartridge_",
            icon="mdi:filter",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.LOCK,
            name="Child Lock",
            icon="mdi:account-lock",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH,
            name="Power",
        ),
        LocalTuyaEntity(
            id=DPCode.WET,
            name="Humidification",
            icon="mdi:water-percent",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.UV,
            name="UV Sterilization",
            icon="mdi:minus-circle-outline",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Air conditioner
    # https://developer.tuya.com/en/docs/iot/categorykt?id=Kaiuz0z71ov2n
    "kt": (
        LocalTuyaEntity(
            id=DPCode.ANION,
            name="Ionizer",
            icon="mdi:minus-circle-outline",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.LOCK,
            name="Child Lock",
            icon="mdi:account-lock",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.SLEEP,
            name="Sleep",
            icon="mdi:sleep",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.SHAKE,
            name="Shake",
            # icon="mdi:vibrate",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.INNERDRY,
            name="Inner Dry",
            icon="mdi:water-outline",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Sous Vide Cooker
    # https://developer.tuya.com/en/docs/iot/categorymzj?id=Kaiuz2vy130ux
    "mzj": (
        LocalTuyaEntity(
            id=DPCode.SWITCH,
            name="Switch",
            icon="mdi:power",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.START,
            name="Start",
            icon="mdi:pot-steam",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Power Socket
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf7o5prgf7s
    "pc": (
        LocalTuyaEntity(
            id=DPCode.CHILD_LOCK,
            name="Child Lock",
            icon="mdi:account-lock",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.OVERCHARGE_SWITCH,
            name="Overcharge",
            icon="mdi:flash-alert",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_1,
            name="Switch 1",
            device_class=SwitchDeviceClass.OUTLET,
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_2,
            name="Switch 2",
            device_class=SwitchDeviceClass.OUTLET,
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_3,
            name="Switch 3",
            device_class=SwitchDeviceClass.OUTLET,
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_4,
            name="Switch 4",
            device_class=SwitchDeviceClass.OUTLET,
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_5,
            name="Switch 5",
            device_class=SwitchDeviceClass.OUTLET,
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_6,
            name="Switch 6",
            device_class=SwitchDeviceClass.OUTLET,
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_USB1,
            name="USB 1",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_USB2,
            name="USB 2",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_USB3,
            name="USB 3",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_USB4,
            name="USB 4",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_USB5,
            name="USB 5",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_USB6,
            name="USB 6",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH,
            name="Socket",
            device_class=SwitchDeviceClass.OUTLET,
        ),
    ),
    # Smart panel with switches and zigbee hub ?
    # Not documented
    "dgnzk": (
        LocalTuyaEntity(
            id=DPCode.SWITCH,
            name="Switch",
        ),
        LocalTuyaEntity(
            id=(DPCode.SWITCH_1, DPCode.SWITCH1),
            name="Switch 1",
        ),
        LocalTuyaEntity(
            id=(DPCode.SWITCH_2, DPCode.SWITCH2),
            name="Switch 2",
        ),
        LocalTuyaEntity(
            id=(DPCode.SWITCH_3, DPCode.SWITCH3),
            name="Switch 3",
        ),
        LocalTuyaEntity(
            id=(DPCode.SWITCH_4, DPCode.SWITCH4),
            name="Switch 4",
        ),
        LocalTuyaEntity(
            id=(DPCode.SWITCH_5, DPCode.SWITCH5),
            name="Switch 5",
        ),
        LocalTuyaEntity(
            id=(DPCode.SWITCH_6, DPCode.SWITCH6),
            name="Switch 6",
        ),
        LocalTuyaEntity(
            id=DPCode.VOICE_PLAY,
            name="Voice",
            icon="mdi:play",
        ),
        LocalTuyaEntity(
            id=DPCode.VOICE_BT_PLAY,
            name="BT Voice",
            icon="mdi:play",
        ),
        LocalTuyaEntity(
            id=DPCode.MUTE,
            name="Mute",
            icon="mdi:volume-off",
        ),
        LocalTuyaEntity(
            id=DPCode.VOICE_MIC,
            name="Microphone",
            icon="mdi:microphone-off",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_WELCOME,
            name="Welcome",
            icon="mdi:human-greeting",
        ),
    ),
    # Unknown product with switch capabilities
    # Fond in some diffusers, plugs and PIR flood lights
    # Not documented
    "qjdcz": (
        LocalTuyaEntity(
            id=DPCode.SWITCH_1,
            name="Switch",
        ),
    ),
    # Heater
    # https://developer.tuya.com/en/docs/iot/categoryqn?id=Kaiuz18kih0sm
    "qn": (
        LocalTuyaEntity(
            id=DPCode.ANION,
            name="Ionizer",
            icon="mdi:minus-circle-outline",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.LOCK,
            name="Child Lock",
            icon="mdi:account-lock",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Robot Vacuum
    # https://developer.tuya.com/en/docs/iot/fsd?id=K9gf487ck1tlo
    "sd": (
        LocalTuyaEntity(
            id=DPCode.SWITCH_DISTURB,
            name="Do Not Disturb",
            icon="mdi:minus-circle",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.VOICE_SWITCH,
            name="Mute Voice",
            icon="mdi:account-voice",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.RESET_MAP,
            name="Map Resetting",
            icon="mdi:backup-restore",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.BREAK_CLEAN,
            name="Resumable Cleaning",
            icon="mdi:cog-play-outline",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.Y_MOP,
            name="Mop Y",
            icon="mdi:dots-vertical",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Water Valve
    "sfkzq": (
        LocalTuyaEntity(
            id=DPCode.SWITCH,
            icon="mdi:valve",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_WEATHER,
            name="Smart Weather",
            icon="mdi:auto-mode",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Siren Alarm
    # https://developer.tuya.com/en/docs/iot/categorysgbj?id=Kaiuz37tlpbnu
    "sgbj": (
        LocalTuyaEntity(
            id=DPCode.MUFFLING,
            name="Mute",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Smart Camera
    # https://developer.tuya.com/en/docs/iot/categorysp?id=Kaiuz35leyo12
    "sp": (
        LocalTuyaEntity(
            id=DPCode.WIRELESS_BATTERYLOCK,
            name="Battery Lock",
            icon="mdi:battery-lock",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.CRY_DETECTION_SWITCH,
            name="Cry Detection",
            icon="mdi:emoticon-cry",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.DECIBEL_SWITCH,
            name="Sound Detection",
            icon="mdi:microphone-outline",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.RECORD_SWITCH,
            name="Video Recording",
            icon="mdi:record-rec",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.MOTION_RECORD,
            name="Motion Recording",
            icon="mdi:record-rec",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.BASIC_PRIVATE,
            name="Privacy Mode",
            icon="mdi:eye-off",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.BASIC_FLIP,
            name="Flip",
            icon="mdi:flip-horizontal",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.BASIC_OSD,
            name="Time Watermark",
            icon="mdi:watermark",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.BASIC_WDR,
            name="Wide Dynamic Range",
            icon="mdi:watermark",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.MOTION_TRACKING,
            name="Motion Tracking",
            icon="mdi:motion-sensor",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.MOTION_SWITCH,
            name="Motion Alarm",
            icon="mdi:motion-sensor",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.PTZ_STOP,
            name="PTZ Stop",
            icon="mdi:stop-circle",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Fingerbot
    "szjqr": (
        LocalTuyaEntity(
            id=DPCode.SWITCH,
            name="Switch",
            icon="mdi:cursor-pointer",
        ),
    ),
    # IoT Switch?
    # Note: Undocumented
    "tdq": (
        LocalTuyaEntity(
            id=DPCode.SWITCH_1,
            name="Switch 1",
            device_class=SwitchDeviceClass.OUTLET,
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_2,
            name="Switch 2",
            device_class=SwitchDeviceClass.OUTLET,
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_3,
            name="Switch 3",
            device_class=SwitchDeviceClass.OUTLET,
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_4,
            name="Switch 4",
            device_class=SwitchDeviceClass.OUTLET,
        ),
        LocalTuyaEntity(
            id=DPCode.CHILD_LOCK,
            name="Child Lock",
            icon="mdi:account-lock",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Solar Light
    # https://developer.tuya.com/en/docs/iot/tynd?id=Kaof8j02e1t98
    "tyndj": (
        LocalTuyaEntity(
            id=DPCode.SWITCH_SAVE_ENERGY,
            name="Energy Saving",
            icon="mdi:leaf",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # PIR Detector
    # https://developer.tuya.com/en/docs/iot/categorypir?id=Kaiuz3ss11b80
    "pir": (
        LocalTuyaEntity(
            id=DPCode.MOD_ON_TMR,
            icon="mdi:timer-play",
            entity_category=EntityCategory.CONFIG,
            name="Timer",
        ),
    ),
    # Thermostatic Radiator Valve
    # Not documented
    "wkf": (
        LocalTuyaEntity(
            id=DPCode.CHILD_LOCK,
            name="Child Lock",
            icon="mdi:account-lock",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=(DPCode.WINDOW_CHECK, DPCode.WINDOW_STATE),
            name="Open Window Detection",
            icon="mdi:window-open",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Air Conditioner Mate (Smart IR Socket)
    "wnykq": (
        LocalTuyaEntity(
            id=DPCode.SWITCH,
            name="Switch",
        ),
    ),
    # Zigbee Gateway (dunno if it's useful)
    # "wg2": (
    #     LocalTuyaEntity(
    #         id=DPCode.SWITCH_ALARM_SOUND,
    #         name="Switch",
    #     ),
    # ),
    # SIREN: Siren (switch) with Temperature and humidity sensor
    # https://developer.tuya.com/en/docs/iot/f?id=Kavck4sr3o5ek
    "wsdcg": (
        LocalTuyaEntity(
            id=DPCode.SWITCH,
            name="Switch",
            device_class=SwitchDeviceClass.OUTLET,
        ),
    ),
    # Ceiling Light
    # https://developer.tuya.com/en/docs/iot/ceiling-light?id=Kaiuz03xxfc4r
    "xdd": (
        LocalTuyaEntity(
            id=DPCode.DO_NOT_DISTURB,
            name="Do Not Disturb",
            icon="mdi:minus-circle-outline",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Diffuser
    # https://developer.tuya.com/en/docs/iot/categoryxxj?id=Kaiuz1f9mo6bl
    "xxj": (
        LocalTuyaEntity(
            id=DPCode.SWITCH,
            name="Power",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_SPRAY,
            name="Spray",
            icon="mdi:spray",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_VOICE,
            name="Voice",
            icon="mdi:account-voice",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Smart Electricity Meter
    # https://developer.tuya.com/en/docs/iot/smart-meter?id=Kaiuz4gv6ack7
    "zndb": (
        LocalTuyaEntity(
            id=DPCode.SWITCH,
            name="Switch",
        ),
    ),
    # Fan
    # https://developer.tuya.com/en/docs/iot/categoryfs?id=Kaiuz1xweel1c
    "fs": (
        LocalTuyaEntity(
            id=DPCode.ANION,
            name="Anion",
            icon="mdi:atom",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.HUMIDIFIER,
            name="Humidification",
            icon="mdi:air-humidifier",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.OXYGEN,
            name="Oxygen Bar",
            icon="mdi:molecule",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.FAN_COOL,
            name="Natural Wind",
            icon="mdi:weather-windy",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.FAN_BEEP,
            name="Sound",
            icon="mdi:minus-circle",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.CHILD_LOCK,
            name="Child Lock",
            icon="mdi:account-lock",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Fan switch
    "fskg": (
        LocalTuyaEntity(
            id=DPCode.BACKLIGHT_SWITCH,
            name="LED Siwtch",
            icon="mdi:led-outline",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Curtain
    # https://developer.tuya.com/en/docs/iot/f?id=K9gf46o5mtfyc
    "cl": (
        LocalTuyaEntity(
            id=DPCode.CONTROL_BACK,
            name="Reverse",
            icon="mdi:swap-horizontal",
            entity_category=EntityCategory.CONFIG,
            condition_contains_any=["true", "false"],
        ),
        LocalTuyaEntity(
            id=DPCode.OPPOSITE,
            name="Reverse",
            icon="mdi:swap-horizontal",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.UP_CONFIRM,
            name="Set Upper Limit",
            icon="mdi:arrow-collapse-up",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.MIDDLE_CONFIRM,
            name="Set Middle Limit",
            icon="mdi:format-vertical-align-center",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.DOWN_CONFIRM,
            name="Set Down Limit",
            icon="mdi:arrow-collapse-down",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Humidifier
    # https://developer.tuya.com/en/docs/iot/categoryjsq?id=Kaiuz1smr440b
    "jsq": (
        LocalTuyaEntity(
            id=DPCode.SWITCH_SOUND,
            name="Voice",
            icon="mdi:account-voice",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.SLEEP,
            name="Sleep",
            icon="mdi:power-sleep",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.STERILIZATION,
            name="Sterilization",
            icon="mdi:minus-circle-outline",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_SPRAY,
            name="Spray",
            icon="mdi:spray",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Alarm Host
    # https://developer.tuya.com/en/docs/iot/categorymal?id=Kaiuz33clqxaf
    "mal": (
        LocalTuyaEntity(
            id=DPCode.SWITCH_ALARM_SOUND,
            name="Sound",
            icon="mdi:volume-source",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_ALARM_LIGHT,
            name="Light",
            icon="mdi:alarm-light-outline",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_KB_SOUND,
            name="Key Tone Sound",
            icon="mdi:volume-source",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_KB_LIGHT,
            name="Keypad Light",
            icon="mdi:alarm-light-outline",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_ALARM_CALL,
            name="Call",
            icon="mdi:phone",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_ALARM_SMS,
            name="SMS",
            icon="mdi:message",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_ALARM_PROPEL,
            name="Push Notification",
            icon="mdi:bell-badge-outline",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.MUFFLING,
            name="Mute",
            icon="mdi:volume-mute",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Smart Water Meter
    # https://developer.tuya.com/en/docs/iot/f?id=Ka8n052xu7w4c
    "znsb": (
        LocalTuyaEntity(
            id=DPCode.SWITCH_COLD,
            name="Valve",
            icon="mdi:Valve",
        ),
        LocalTuyaEntity(
            id=DPCode.AUTO_CLEAN,
            name="Auto Clean",
            icon="mdi:auto-fix",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Thermostat
    # https://developer.tuya.com/en/docs/iot/f?id=K9gf45ld5l0t9
    "wk": (
        LocalTuyaEntity(
            id=DPCode.CHILD_LOCK,
            name="Child Lock",
            icon="mdi:account-lock",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.ECO,
            name="ECO",
            icon="mdi:sprout",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
}

# Scene Switch
# https://developer.tuya.com/en/docs/iot/f?id=K9gf7nx6jelo8
SWITCHES["cjkg"] = SWITCHES["kg"]

# Wireless Switch  # also can come as knob switch.
# https://developer.tuya.com/en/docs/iot/wxkg?id=Kbeo9t3ryuqm5
SWITCHES["wxkg"] = SWITCHES["kg"]

# Socket (duplicate of `pc`)
# https://developer.tuya.com/en/docs/iot/s?id=K9gf7o5prgf7s
SWITCHES["cz"] = SWITCHES["pc"]

# Climates / heaters
SWITCHES["wkf"] = SWITCHES["wk"]
SWITCHES["rs"] = SWITCHES["wk"]
SWITCHES["qn"] = SWITCHES["wk"]
SWITCHES["kt"] = SWITCHES["wk"]

# Dehumidifier
# https://developer.tuya.com/en/docs/iot/categorycs?id=Kaiuz1vcz4dha
SWITCHES["cs"] = SWITCHES["jsq"]
