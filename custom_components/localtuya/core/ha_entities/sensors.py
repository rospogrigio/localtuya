"""
    This a file contains available tuya data
    https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq

    Credits: official HA Tuya integration.
    Modified by: xZetsubou
"""

from homeassistant.components.sensor import SensorStateClass, SensorDeviceClass
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTime,
    UnitOfPower,
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfTime,
    CONF_UNIT_OF_MEASUREMENT,
    UnitOfTemperature,
    UnitOfEnergy,
    UnitOfVolume,
    UnitOfElectricPotential,
    UnitOfMass,
    DEGREE,
    LIGHT_LUX,
    UnitOfLength,
)

from .base import (
    DPCode,
    LocalTuyaEntity,
    EntityCategory,
    CLOUD_VALUE,
)
from ...const import CONF_SCALING as SCALE_FACTOR


def localtuya_sensor(unit_of_measurement=None, scale_factor: float = 1) -> dict:
    """Define LocalTuya Configs for Sensor."""
    data = {CONF_UNIT_OF_MEASUREMENT: unit_of_measurement}
    data.update({SCALE_FACTOR: CLOUD_VALUE(scale_factor, "id", "scale")})

    return data


# Commonly used battery sensors, that are re-used in the sensors down below.
BATTERY_SENSORS: dict[str, tuple[LocalTuyaEntity, ...]] = (
    LocalTuyaEntity(
        id=DPCode.BATTERY_PERCENTAGE,
        name="Battery",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        custom_configs=localtuya_sensor(PERCENTAGE),
    ),
    LocalTuyaEntity(
        id=(DPCode.BATTERY_STATE, DPCode.BATTERYSTATUS),
        name="Battery Level",
        # name="battery_state",
        icon="mdi:battery",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    LocalTuyaEntity(
        id=DPCode.BATTERY_VALUE,
        name="Battery",
        device_class=SensorDeviceClass.BATTERY,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        custom_configs=localtuya_sensor(PERCENTAGE),
    ),
    LocalTuyaEntity(
        id=DPCode.VA_BATTERY,
        name="Battery",
        device_class=SensorDeviceClass.BATTERY,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        custom_configs=localtuya_sensor(PERCENTAGE),
    ),
    LocalTuyaEntity(
        id=DPCode.BATTERY,
        name="Battery",
        device_class=SensorDeviceClass.BATTERY,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        custom_configs=localtuya_sensor(PERCENTAGE),
    ),
)

# All descriptions can be found here. Mostly the Integer data types in the
# default status set of each category (that don't have a set instruction)
# end up being a sensor.
# https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq
SENSORS: dict[str, tuple[LocalTuyaEntity, ...]] = {
    # Wireless Switch  # also can come as knob switch.
    # https://developer.tuya.com/en/docs/iot/wxkg?id=Kbeo9t3ryuqm5
    "wxkg": (
        LocalTuyaEntity(
            id=DPCode.MODE_1,
            name="Switch 1 Mode",
            icon="mdi:information-slab-circle-outline",
        ),
        LocalTuyaEntity(
            id=DPCode.MODE_2,
            name="Switch 2 Mode",
            icon="mdi:information-slab-circle-outline",
        ),
        LocalTuyaEntity(
            id=DPCode.KNOB_SWITCH_MODE_1,
            name="Knob Mode",
            icon="mdi:knob",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        *BATTERY_SENSORS,
    ),
    # Smart panel with switches and zigbee hub ?
    # Not documented
    "dgnzk": (
        LocalTuyaEntity(
            id=DPCode.PLAY_INFO,
            name="Playing",
            icon="mdi:playlist-play",
        ),
    ),
    # Multi-functional Sensor
    # https://developer.tuya.com/en/docs/iot/categorydgnbj?id=Kaiuz3yorvzg3
    "dgnbj": (
        LocalTuyaEntity(
            id=DPCode.GAS_SENSOR_VALUE,
            # name="gas",
            icon="mdi:gas-cylinder",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.CH4_SENSOR_VALUE,
            # name="gas",
            name="Methane",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.VOC_VALUE,
            # name="voc",
            device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.PM25_VALUE,
            # name="pm25",
            device_class=SensorDeviceClass.PM25,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.CO_VALUE,
            # name="carbon_monoxide",
            icon="mdi:molecule-co",
            device_class=SensorDeviceClass.CO,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.CO2_VALUE,
            # name="carbon_dioxide",
            icon="mdi:molecule-co2",
            device_class=SensorDeviceClass.CO2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.CH2O_VALUE,
            # name="formaldehyde",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.BRIGHT_STATE,
            # name="luminosity",
            icon="mdi:brightness-6",
        ),
        LocalTuyaEntity(
            id=DPCode.BRIGHT_VALUE,
            # name="illuminance",
            icon="mdi:brightness-6",
            device_class=SensorDeviceClass.ILLUMINANCE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.TEMP_CURRENT,
            # name="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.HUMIDITY_VALUE,
            # name="humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.SMOKE_SENSOR_VALUE,
            # name="smoke_amount",
            icon="mdi:smoke-detector",
            entity_category=EntityCategory.DIAGNOSTIC,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        *BATTERY_SENSORS,
    ),
    # Smart Kettle
    # https://developer.tuya.com/en/docs/iot/fbh?id=K9gf484m21yq7
    "bh": (
        LocalTuyaEntity(
            id=DPCode.TEMP_CURRENT,
            # name="current_temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.TEMP_CURRENT_F,
            # name="current_temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.STATUS,
            # name="status",
        ),
    ),
    # CO2 Detector
    # https://developer.tuya.com/en/docs/iot/categoryco2bj?id=Kaiuz3wes7yuy
    "co2bj": (
        LocalTuyaEntity(
            id=DPCode.HUMIDITY_VALUE,
            # name="humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.TEMP_CURRENT,
            # name="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.CO2_VALUE,
            # name="carbon_dioxide",
            device_class=SensorDeviceClass.CO2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        *BATTERY_SENSORS,
    ),
    # Two-way temperature and humidity switch
    # "MOES Temperature and Humidity Smart Switch Module MS-103"
    # Documentation not found
    "wkcz": (
        LocalTuyaEntity(
            id=DPCode.HUMIDITY_VALUE,
            name="Humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.TEMP_CURRENT,
            name="Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    ),
    # CO Detector
    # https://developer.tuya.com/en/docs/iot/categorycobj?id=Kaiuz3u1j6q1v
    "cobj": (
        LocalTuyaEntity(
            id=DPCode.CO_VALUE,
            # name="carbon_monoxide",
            device_class=SensorDeviceClass.CO,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        *BATTERY_SENSORS,
    ),
    # Smart Pet Feeder
    # https://developer.tuya.com/en/docs/iot/categorycwwsq?id=Kaiuz2b6vydld
    "cwwsq": (
        LocalTuyaEntity(
            id=DPCode.FEED_REPORT,
            # name="last_amount",
            icon="mdi:counter",
            state_class=SensorStateClass.MEASUREMENT,
        ),
    ),
    # Air Quality Monitor
    # No specification on Tuya portal
    "hjjcy": (
        LocalTuyaEntity(
            id=DPCode.TEMP_CURRENT,
            # name="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.HUMIDITY_VALUE,
            # name="humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.CO2_VALUE,
            # name="carbon_dioxide",
            device_class=SensorDeviceClass.CO2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.CH2O_VALUE,
            # name="formaldehyde",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.VOC_VALUE,
            # name="voc",
            device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.PM25_VALUE,
            # name="pm25",
            device_class=SensorDeviceClass.PM25,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    ),
    # Formaldehyde Detector
    # Note: Not documented
    "jqbj": (
        LocalTuyaEntity(
            id=DPCode.CO2_VALUE,
            # name="carbon_dioxide",
            device_class=SensorDeviceClass.CO2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.VOC_VALUE,
            # name="voc",
            device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.PM25_VALUE,
            # name="pm25",
            device_class=SensorDeviceClass.PM25,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.VA_HUMIDITY,
            # name="humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.VA_TEMPERATURE,
            # name="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.CH2O_VALUE,
            # name="formaldehyde",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        *BATTERY_SENSORS,
    ),
    # Methane Detector
    # https://developer.tuya.com/en/docs/iot/categoryjwbj?id=Kaiuz40u98lkm
    "jwbj": (
        LocalTuyaEntity(
            id=DPCode.CH4_SENSOR_VALUE,
            # name="methane",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        *BATTERY_SENSORS,
    ),
    # Switch
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf7o5prgf7s
    "kg": (
        LocalTuyaEntity(
            id=DPCode.CUR_CURRENT,
            name="Current",
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfElectricCurrent.MILLIAMPERE),
        ),
        LocalTuyaEntity(
            id=DPCode.CUR_POWER,
            name="Power",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfPower.WATT, 0.1),
        ),
        LocalTuyaEntity(
            id=DPCode.CUR_VOLTAGE,
            name="Voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfElectricPotential.VOLT, 0.1),
        ),
        LocalTuyaEntity(
            id=DPCode.ADD_ELE,
            name="Electricity",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            custom_configs=localtuya_sensor(UnitOfEnergy.KILO_WATT_HOUR, 0.001),
        ),
        # CZ - Energy monitor?
        LocalTuyaEntity(
            id=DPCode.CUR_CURRENT1,
            name="Current 1",
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfElectricCurrent.MILLIAMPERE),
        ),
        LocalTuyaEntity(
            id=DPCode.CUR_CURRENT2,
            name="Current 2",
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfElectricCurrent.MILLIAMPERE),
        ),
        LocalTuyaEntity(
            id=DPCode.CUR_POWER1,
            name="Power 1",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfPower.WATT, 0.1),
        ),
        LocalTuyaEntity(
            id=DPCode.CUR_POWER2,
            name="Power 2",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfPower.WATT, 0.1),
        ),
        LocalTuyaEntity(
            id=DPCode.CUR_VOLTAGE1,
            name="Voltage 1",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfElectricPotential.VOLT, 0.1),
        ),
        LocalTuyaEntity(
            id=DPCode.CUR_VOLTAGE2,
            name="Voltage 2",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfElectricPotential.VOLT, 0.1),
        ),
        LocalTuyaEntity(
            id=DPCode.ADD_ELE1,
            name="Electricity 1",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            custom_configs=localtuya_sensor(UnitOfEnergy.KILO_WATT_HOUR, 0.001),
        ),
        LocalTuyaEntity(
            id=DPCode.ADD_ELE2,
            name="Electricity 2",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            custom_configs=localtuya_sensor(UnitOfEnergy.KILO_WATT_HOUR, 0.001),
        ),
        LocalTuyaEntity(
            id=DPCode.TOTAL_ENERGY,
            name="Total Energy",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            custom_configs=localtuya_sensor(UnitOfEnergy.KILO_WATT_HOUR, 0.001),
        ),
        LocalTuyaEntity(
            id=DPCode.TOTAL_ENERGY1,
            name="Total Energy 1",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            custom_configs=localtuya_sensor(UnitOfEnergy.KILO_WATT_HOUR, 0.001),
        ),
        LocalTuyaEntity(
            id=DPCode.TOTAL_ENERGY2,
            name="Total Energy 2",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            custom_configs=localtuya_sensor(UnitOfEnergy.KILO_WATT_HOUR, 0.001),
        ),
        LocalTuyaEntity(
            id=DPCode.TODAY_ACC_ENERGY,
            name="Today Energy",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            custom_configs=localtuya_sensor(UnitOfEnergy.KILO_WATT_HOUR, 0.001),
        ),
        LocalTuyaEntity(
            id=DPCode.TODAY_ACC_ENERGY1,
            name="Today Energy 1",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            custom_configs=localtuya_sensor(UnitOfEnergy.KILO_WATT_HOUR, 0.001),
        ),
        LocalTuyaEntity(
            id=DPCode.TODAY_ACC_ENERGY2,
            name="Today Energy 2",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            custom_configs=localtuya_sensor(UnitOfEnergy.KILO_WATT_HOUR, 0.001),
        ),
        LocalTuyaEntity(
            id=DPCode.TODAY_ENERGY_ADD,
            name="Today Energy Increase",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            custom_configs=localtuya_sensor(UnitOfEnergy.KILO_WATT_HOUR, 0.001),
        ),
        LocalTuyaEntity(
            id=DPCode.TODAY_ENERGY_ADD1,
            name="Today Energy 1 Increase",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            custom_configs=localtuya_sensor(UnitOfEnergy.KILO_WATT_HOUR, 0.001),
        ),
        LocalTuyaEntity(
            id=DPCode.TODAY_ENERGY_ADD2,
            name="Today Energy 2 Increase",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            custom_configs=localtuya_sensor(UnitOfEnergy.KILO_WATT_HOUR, 0.001),
        ),
        LocalTuyaEntity(
            id=DPCode.SYNC_REQUEST,
            name="Sync Request",
        ),
        LocalTuyaEntity(
            id=DPCode.DEVICE_STATE1,
            name="Device 1 State",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.DEVICE_STATE2,
            name="Device 2 State",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.NET_STATE,
            name="Connection state",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:network",
        ),
    ),
    # IoT Switch
    # Note: Undocumented
    "tdq": (
        LocalTuyaEntity(
            id=DPCode.CUR_CURRENT,
            name="Current",
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfElectricCurrent.MILLIAMPERE),
            # entity_registry_enabled_default=False,
        ),
        LocalTuyaEntity(
            id=DPCode.CUR_POWER,
            name="Power",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfPower.WATT, 0.1),
            # entity_registry_enabled_default=False,
        ),
        LocalTuyaEntity(
            id=DPCode.CUR_VOLTAGE,
            name="Voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfElectricPotential.VOLT, 0.1),
            # entity_registry_enabled_default=False,
        ),
        LocalTuyaEntity(
            id=DPCode.ADD_ELE,
            name="Electricity",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            custom_configs=localtuya_sensor(UnitOfEnergy.KILO_WATT_HOUR, 0.001),
        ),
    ),
    # Luminance Sensor
    # https://developer.tuya.com/en/docs/iot/categoryldcg?id=Kaiuz3n7u69l8
    "ldcg": (
        LocalTuyaEntity(
            id=DPCode.BRIGHT_STATE,
            # name="luminosity",
            icon="mdi:brightness-6",
        ),
        LocalTuyaEntity(
            id=DPCode.BRIGHT_VALUE,
            # name="illuminance",
            device_class=SensorDeviceClass.ILLUMINANCE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.TEMP_CURRENT,
            # name="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.HUMIDITY_VALUE,
            # name="humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.CO2_VALUE,
            # name="carbon_dioxide",
            device_class=SensorDeviceClass.CO2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        *BATTERY_SENSORS,
    ),
    # Door and Window Controller
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf48r5zjsy9
    "mc": BATTERY_SENSORS,
    # Door Window Sensor
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf48hm02l8m
    "mcs": BATTERY_SENSORS,
    # Sous Vide Cooker
    # https://developer.tuya.com/en/docs/iot/categorymzj?id=Kaiuz2vy130ux
    "mzj": (
        LocalTuyaEntity(
            id=DPCode.TEMP_CURRENT,
            # name="current_temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.STATUS,
            # name="sous_vide_status",
        ),
        LocalTuyaEntity(
            id=DPCode.REMAIN_TIME,
            name="Timer Remaining",
            custom_configs=localtuya_sensor(UnitOfTime.MINUTES),
            icon="mdi:timer",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
    ),
    # PIR Detector
    # https://developer.tuya.com/en/docs/iot/categorypir?id=Kaiuz3ss11b80
    "pir": (
        LocalTuyaEntity(
            id=DPCode.PM25_VALUE,
            # name="pm25",
            device_class=SensorDeviceClass.PM25,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.MOD_ON_TMR_CD,
            icon="mdi:timer-edit-outline",
            name="Timer left",
            entity_category=EntityCategory.DIAGNOSTIC,
            custom_configs=localtuya_sensor("s"),
        ),
        LocalTuyaEntity(
            id=DPCode.ILLUMINANCE_VALUE,
            name="Illuminance",
            entity_category=EntityCategory.DIAGNOSTIC,
            device_class=SensorDeviceClass.ILLUMINANCE,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(LIGHT_LUX),
        ),
        *BATTERY_SENSORS,
    ),
    # PM2.5 Sensor
    # https://developer.tuya.com/en/docs/iot/categorypm25?id=Kaiuz3qof3yfu
    "pm2.5": (
        LocalTuyaEntity(
            id=DPCode.PM25_VALUE,
            # name="pm25",
            device_class=SensorDeviceClass.PM25,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.CH2O_VALUE,
            # name="formaldehyde",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.VOC_VALUE,
            # name="voc",
            device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.TEMP_CURRENT,
            # name="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.CO2_VALUE,
            # name="carbon_dioxide",
            device_class=SensorDeviceClass.CO2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.HUMIDITY_VALUE,
            # name="humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.PM1,
            # name="pm1",
            device_class=SensorDeviceClass.PM1,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.PM10,
            # name="pm10",
            device_class=SensorDeviceClass.PM10,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        *BATTERY_SENSORS,
    ),
    # Heater
    # https://developer.tuya.com/en/docs/iot/categoryqn?id=Kaiuz18kih0sm
    "qn": (
        LocalTuyaEntity(
            id=DPCode.WORK_POWER,
            name="Power",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfPower.WATT, 0.1),
        ),
    ),
    # Gas Detector
    # https://developer.tuya.com/en/docs/iot/categoryrqbj?id=Kaiuz3d162ubw
    "rqbj": (
        LocalTuyaEntity(
            id=DPCode.GAS_SENSOR_VALUE,
            icon="mdi:gas-cylinder",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        *BATTERY_SENSORS,
    ),
    # Water Detector
    # https://developer.tuya.com/en/docs/iot/categorysj?id=Kaiuz3iub2sli
    "sj": (
        LocalTuyaEntity(
            id=DPCode.WATERSENSOR_STATE,
            icon="mdi:water",
        ),
        LocalTuyaEntity(
            id=DPCode.TEMP_STATUS,
            name="Temperature Status",
            icon="mdi:thermometer-check",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.HUMI_STATUS,
            name="Humidity Status",
            icon="mdi:water-percent-alert",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.POWER,
            icon="mdi:power",
            entity_category=EntityCategory.DIAGNOSTIC,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.HUMIDITY_VALUE,
            name="Humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(PERCENTAGE, 0.01),
        ),
        LocalTuyaEntity(
            id=(DPCode.TEMP_CURRENT, DPCode.TEMP_CURRENT_F),
            name="Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        *BATTERY_SENSORS,
    ),
    # Emergency Button
    # https://developer.tuya.com/en/docs/iot/categorysos?id=Kaiuz3oi6agjy
    "sos": BATTERY_SENSORS,
    # Smart Camera
    # https://developer.tuya.com/en/docs/iot/categorysp?id=Kaiuz35leyo12
    "sp": (
        LocalTuyaEntity(
            id=DPCode.SENSOR_TEMPERATURE,
            # name="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.SENSOR_HUMIDITY,
            # name="humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.WIRELESS_ELECTRICITY,
            name="Battery",
            device_class=SensorDeviceClass.BATTERY,
            entity_category=EntityCategory.DIAGNOSTIC,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    ),
    # Water Valve
    "sfkzq": (
        LocalTuyaEntity(
            id=DPCode.WORK_STATE,
            name="State",
            icon="mdi:state-machine",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.USE_TIME_ONE,
            name="Single Usage Time",
            icon="mdi:chart-arc",
            entity_category=EntityCategory.DIAGNOSTIC,
            custom_configs=localtuya_sensor(unit_of_measurement=UnitOfTime.SECONDS),
        ),
        LocalTuyaEntity(
            id=(DPCode.TIME_USE, DPCode.USE_TIME),
            name="Usage Time",
            icon="mdi:chart-arc",
            entity_category=EntityCategory.DIAGNOSTIC,
            custom_configs=localtuya_sensor(unit_of_measurement=UnitOfTime.SECONDS),
        ),
        *BATTERY_SENSORS,
    ),
    # Fingerbot
    "szjqr": BATTERY_SENSORS,
    # Solar Light
    # https://developer.tuya.com/en/docs/iot/tynd?id=Kaof8j02e1t98
    "tyndj": BATTERY_SENSORS,
    # Volatile Organic Compound Sensor
    # Note: Undocumented in cloud API docs, based on test device
    "voc": (
        LocalTuyaEntity(
            id=DPCode.CO2_VALUE,
            # name="carbon_dioxide",
            device_class=SensorDeviceClass.CO2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.PM25_VALUE,
            # name="pm25",
            device_class=SensorDeviceClass.PM25,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.CH2O_VALUE,
            # name="formaldehyde",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.HUMIDITY_VALUE,
            # name="humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.TEMP_CURRENT,
            # name="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.VOC_VALUE,
            # name="voc",
            device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        *BATTERY_SENSORS,
    ),
    # Thermostat
    # https://developer.tuya.com/en/docs/iot/f?id=K9gf45ld5l0t9
    "wk": {
        LocalTuyaEntity(
            id=(DPCode.TEMP_CURRENT, DPCode.TEMPFLOOR),
            name="External temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    },
    # Thermostatic Radiator Valve
    # Not documented
    "wkf": BATTERY_SENSORS,
    # Temperature and Humidity Sensor
    # https://developer.tuya.com/en/docs/iot/categorywsdcg?id=Kaiuz3hinij34
    "wsdcg": (
        LocalTuyaEntity(
            id=DPCode.VA_TEMPERATURE,
            name="Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=(DPCode.TEMP_CURRENT, DPCode.PRM_CONTENT),
            name="Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfTemperature.CELSIUS, 0.01),
        ),
        LocalTuyaEntity(
            id=(DPCode.HUMIDITY_VALUE, DPCode.PRM_CONTENT, DPCode.VA_HUMIDITY),
            name="Humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(PERCENTAGE, 0.01),
        ),
        LocalTuyaEntity(
            id=DPCode.BRIGHT_VALUE,
            name="Illuminance",
            device_class=SensorDeviceClass.ILLUMINANCE,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(LIGHT_LUX),
        ),
        *BATTERY_SENSORS,
    ),
    # Pressure Sensor
    # https://developer.tuya.com/en/docs/iot/categoryylcg?id=Kaiuz3kc2e4gm
    "ylcg": (
        LocalTuyaEntity(
            id=DPCode.PRESSURE_VALUE,
            device_class=SensorDeviceClass.PRESSURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        *BATTERY_SENSORS,
    ),
    # Smoke Detector
    # https://developer.tuya.com/en/docs/iot/categoryywbj?id=Kaiuz3f6sf952
    "ywbj": (
        LocalTuyaEntity(
            id=DPCode.SMOKE_SENSOR_VALUE,
            # name="smoke_amount",
            icon="mdi:smoke-detector",
            entity_category=EntityCategory.DIAGNOSTIC,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        *BATTERY_SENSORS,
    ),
    # Vibration Sensor
    # https://developer.tuya.com/en/docs/iot/categoryzd?id=Kaiuz3a5vrzno
    "zd": BATTERY_SENSORS,
    # Smart Electricity Meter
    # https://developer.tuya.com/en/docs/iot/smart-meter?id=Kaiuz4gv6ack7
    "zndb": (
        LocalTuyaEntity(
            id=DPCode.FORWARD_ENERGY_TOTAL,
            # name="total_energy",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            custom_configs=localtuya_sensor(UnitOfEnergy.KILO_WATT_HOUR, 0.01),
        ),
        LocalTuyaEntity(
            id=DPCode.REVERSE_ENERGY_TOTAL,
            name="Total Reverse Energy",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            custom_configs=localtuya_sensor(UnitOfEnergy.KILO_WATT_HOUR, 0.01),
        ),
        ## PHASE X Are probably encrypted values. since it duplicated it probably raw dict data.
        LocalTuyaEntity(
            id=DPCode.PHASE_A,
            name="Phase C Current",
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfElectricCurrent.MILLIAMPERE),
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.PHASE_A,
            name="Phase C Power",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfPower.WATT, 0.1),
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.PHASE_A,
            name="Phase A Voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfElectricPotential.VOLT, 0.1),
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.PHASE_B,
            name="Phase B",
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfElectricCurrent.MILLIAMPERE),
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.PHASE_B,
            name="Phase B Power",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfPower.WATT, 0.1),
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.PHASE_B,
            name="Phase B Voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfElectricPotential.VOLT, 0.1),
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.PHASE_C,
            name="Phase C Current",
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfElectricCurrent.MILLIAMPERE),
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.PHASE_C,
            name="Phase C Power",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfPower.WATT, 0.1),
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.PHASE_C,
            name="Phase C Voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfElectricPotential.VOLT, 0.1),
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        ## PHASE X Are probably encrypted values. since it duplicated it probably raw dict data.
        LocalTuyaEntity(
            id=DPCode.POWER_A,
            name="Power A",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfPower.WATT, 0.1),
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.POWER_B,
            name="Power B",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfPower.WATT, 0.1),
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.POWER_C,
            name="Power C",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfPower.WATT, 0.1),
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.ENERGY_FORWORD_A,
            name="Energy A",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            custom_configs=localtuya_sensor(UnitOfEnergy.KILO_WATT_HOUR, 0.1),
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.ENERGY_FORWORD_B,
            name="Energy B",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            custom_configs=localtuya_sensor(UnitOfEnergy.KILO_WATT_HOUR, 0.1),
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.ENERGY_FORWORD_C,
            name="Energy C",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            custom_configs=localtuya_sensor(UnitOfEnergy.KILO_WATT_HOUR, 0.1),
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=(DPCode.ENERGY_REVERSE_A, DPCode.ENERGY_RESERSE_A),
            name="Reverse Energy A",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            custom_configs=localtuya_sensor(UnitOfEnergy.KILO_WATT_HOUR, 0.1),
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=(DPCode.ENERGY_REVERSE_B, DPCode.ENERGY_RESERSE_B),
            name="Reverse Energy B",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            custom_configs=localtuya_sensor(UnitOfEnergy.KILO_WATT_HOUR, 0.1),
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=(DPCode.ENERGY_REVERSE_C, DPCode.ENERGY_RESERSE_C),
            name="Reverse Energy C",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            custom_configs=localtuya_sensor(UnitOfEnergy.KILO_WATT_HOUR, 0.1),
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=(DPCode.POWER_FACTOR, DPCode.POWER_FACTOR_A),
            name="Power Factor A",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.POWER_FACTOR_B,
            name="Power Factor B",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.POWER_FACTOR_C,
            name="Power Factor C",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.DIRECTION_A,
            name="Direction A",
            icon="mdi:arrow-up-down",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.DIRECTION_B,
            name="Direction B",
            icon="mdi:arrow-up-down",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.DIRECTION_C,
            name="Direction C",
            icon="mdi:arrow-up-down",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
    ),
    # Robot Vacuum
    # https://developer.tuya.com/en/docs/iot/fsd?id=K9gf487ck1tlo
    "sd": (
        LocalTuyaEntity(
            id=DPCode.CLEAN_AREA,
            # name="cleaning_area",
            icon="mdi:texture-box",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.CLEAN_TIME,
            # name="cleaning_time",
            icon="mdi:progress-clock",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.TOTAL_CLEAN_AREA,
            # name="total_cleaning_area",
            icon="mdi:texture-box",
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
        LocalTuyaEntity(
            id=DPCode.TOTAL_CLEAN_TIME,
            # name="total_cleaning_time",
            icon="mdi:history",
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
        LocalTuyaEntity(
            id=DPCode.TOTAL_CLEAN_COUNT,
            # name="total_cleaning_times",
            icon="mdi:counter",
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
        LocalTuyaEntity(
            id=DPCode.DUSTER_CLOTH,
            # name="duster_cloth_life",
            icon="mdi:ticket-percent-outline",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.EDGE_BRUSH,
            # name="side_brush_life",
            icon="mdi:ticket-percent-outline",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.FILTER_LIFE,
            # name="filter_life",
            icon="mdi:ticket-percent-outline",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.ROLL_BRUSH,
            # name="rolling_brush_life",
            icon="mdi:ticket-percent-outline",
            state_class=SensorStateClass.MEASUREMENT,
        ),
    ),
    # Curtain
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf48qy7wkre
    "cl": (
        LocalTuyaEntity(
            id=DPCode.TIME_TOTAL,
            # name="last_operation_duration",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:progress-clock",
        ),
    ),
    # Humidifier
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf48qwjz0i3
    "jsq": (
        LocalTuyaEntity(
            id=DPCode.HUMIDITY_CURRENT,
            name="Humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.TEMP_CURRENT,
            name="Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.TEMP_CURRENT_F,
            name="Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.LEVEL_CURRENT,
            name="Water Level",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:waves-arrow-up",
        ),
    ),
    # Air Purifier
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf48r41mn81
    "kj": (
        LocalTuyaEntity(
            id=DPCode.FILTER,
            # name="filter_utilization",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:ticket-percent-outline",
        ),
        LocalTuyaEntity(
            id=DPCode.PM25,
            # name="pm25",
            device_class=SensorDeviceClass.PM25,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:molecule",
        ),
        LocalTuyaEntity(
            id=DPCode.TEMP,
            # name="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.HUMIDITY,
            # name="humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.TVOC,
            # name="total_volatile_organic_compound",
            device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.ECO2,
            # name="concentration_carbon_dioxide",
            device_class=SensorDeviceClass.CO2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.TOTAL_TIME,
            # name="total_operating_time",
            icon="mdi:history",
            state_class=SensorStateClass.TOTAL_INCREASING,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.TOTAL_PM,
            # name="total_absorption_particles",
            icon="mdi:texture-box",
            state_class=SensorStateClass.TOTAL_INCREASING,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.AIR_QUALITY,
            # name="air_quality",
            icon="mdi:air-filter",
        ),
    ),
    # Fan
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf48quojr54
    "fs": (
        LocalTuyaEntity(
            id=DPCode.TEMP_CURRENT,
            # name="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    ),
    # eMylo Smart WiFi IR Remote
    # Air Conditioner Mate (Smart IR Socket)
    "wnykq": (
        LocalTuyaEntity(
            id=(DPCode.VA_TEMPERATURE, DPCode.TEMP_CURRENT, DPCode.TEMP_CURRENT_F),
            name="Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=(DPCode.VA_HUMIDITY, DPCode.HUMIDITY_VALUE),
            name="Humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.CUR_CURRENT,
            name="Current",
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            custom_configs=localtuya_sensor(UnitOfElectricCurrent.MILLIAMPERE),
            # entity_registry_enabled_default=False,
        ),
        LocalTuyaEntity(
            id=DPCode.CUR_POWER,
            name="Power",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            custom_configs=localtuya_sensor(UnitOfPower.WATT, 0.1),
            # entity_registry_enabled_default=False,
        ),
        LocalTuyaEntity(
            id=DPCode.CUR_VOLTAGE,
            name="Voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            custom_configs=localtuya_sensor(UnitOfElectricPotential.VOLT, 0.1),
            # entity_registry_enabled_default=False,
        ),
        LocalTuyaEntity(
            id=DPCode.ADD_ELE,
            name="Electricity",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            custom_configs=localtuya_sensor(UnitOfEnergy.KILO_WATT_HOUR, 0.001),
        ),
    ),
    # Dehumidifier
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf48r6jke8e
    "cs": (
        LocalTuyaEntity(
            id=DPCode.TEMP_INDOOR,
            name="Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.HUMIDITY_INDOOR,
            name="Humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.COUNTDOWN_LEFT,
            name="Timer Remaining",
            custom_configs=localtuya_sensor(UnitOfTime.MINUTES),
            icon="mdi:timer",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        # Sensors 'Micro Inverter' ?
        LocalTuyaEntity(
            id=DPCode.PV_POWER,
            name="PV Power",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfPower.WATT),
        ),
        LocalTuyaEntity(
            id=DPCode.EMISSION,
            name="Emission",
            device_class=SensorDeviceClass.WEIGHT,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfMass.KILOGRAMS),
        ),
        LocalTuyaEntity(
            id=DPCode.PV_VOLT,
            name="PV Voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfElectricPotential.VOLT),
        ),
        LocalTuyaEntity(
            id=DPCode.TEMPERATURE,
            name="Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfTemperature.CELSIUS),
        ),
        LocalTuyaEntity(
            id=DPCode.AC_CURRENT,
            name="AC Current",
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfElectricCurrent.AMPERE),
        ),
        LocalTuyaEntity(
            id=DPCode.PV_CURRENT,
            name="PV Current",
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfElectricCurrent.AMPERE),
        ),
        LocalTuyaEntity(
            id=DPCode.AC_VOLT,
            name="AC Voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfElectricPotential.VOLT),
        ),
        LocalTuyaEntity(
            id=DPCode.DAY_ENERGY,
            name="Daily Consumption",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            custom_configs=localtuya_sensor(UnitOfEnergy.KILO_WATT_HOUR),
        ),
        LocalTuyaEntity(
            id=DPCode.ENERGY,
            name="Energy",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            custom_configs=localtuya_sensor(UnitOfEnergy.KILO_WATT_HOUR),
        ),
        LocalTuyaEntity(
            id=DPCode.OUT_POWER,
            name="Out Power",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfPower.WATT),
        ),
        LocalTuyaEntity(
            id=DPCode.PLANT,
            name="Plant",
            custom_configs=localtuya_sensor("pcs"),
        ),
    ),
    # Soil sensor (Plant monitor)
    "zwjcy": (
        LocalTuyaEntity(
            id=DPCode.TEMP_CURRENT,
            # name="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.HUMIDITY,
            # name="humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        *BATTERY_SENSORS,
    ),
    # Alarm Host
    # https://developer.tuya.com/en/docs/iot/categorymal?id=Kaiuz33clqxaf
    "mal": (
        LocalTuyaEntity(
            id=DPCode.SUB_STATE,
            name="Sub-Device State",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.POWEREVENT,
            name="Power Event",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.ZONE_NUMBER,
            name="Zone Number",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.OTHEREVENT,
            name="Other Event",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
    ),
    # Lock
    "ms": (
        LocalTuyaEntity(
            id=DPCode.LOCK_MOTOR_STATE,
            name="Motor State",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
    ),
    # Smart Water Meter
    # https://developer.tuya.com/en/docs/iot/f?id=Ka8n052xu7w4c
    "znsb": (
        LocalTuyaEntity(
            id=DPCode.WATER_USE_DATA,
            name="Total Water Consumption",
            icon="mdi:water-outline",
            device_class=SensorDeviceClass.WATER,
            state_class=SensorStateClass.TOTAL_INCREASING,
            custom_configs=localtuya_sensor(UnitOfVolume.LITERS, 1),
        ),
        LocalTuyaEntity(
            id=DPCode.WATER_TEMP,
            name="Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfTemperature.CELSIUS, 0.01),
        ),
        LocalTuyaEntity(
            id=DPCode.VOLTAGE_CURRENT,
            name="Battery",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            custom_configs=localtuya_sensor(UnitOfElectricPotential.VOLT, 0.01),
        ),
    ),
    # Air conditioner
    # https://developer.tuya.com/en/docs/iot/categorykt?id=Kaiuz0z71ov2n
    "kt": (
        LocalTuyaEntity(
            id=DPCode.AIR_RETURN,
            name="AIR Return",
            icon="mdi:air-filter",
            custom_configs=localtuya_sensor(DEGREE, 0.1),
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.COIL_OUT,
            name="Coil Out",
            icon="mdi:heating-coil",
            custom_configs=localtuya_sensor(DEGREE, 0.1),
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.DEFROST,
            name="Defrosting",
            icon="mdi:snowflake-melt",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.COUNTDOWN,
            name="Timer State",
            icon="mdi:timer-sand",
            custom_configs=localtuya_sensor(UnitOfTime.MINUTES, 1),
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.COMPRESSOR_COMMAND,
            name="Compressor",
        ),
        LocalTuyaEntity(
            id=DPCode.FOUT_WAY_VALVE,
            name="Fout Way Valve",
        ),
        LocalTuyaEntity(
            id=DPCode.ODU_FAN_SPEED,
            name="ODU Fan Speed",
            icon="mdi:fan",
        ),
    ),
    # Ultrasonic level sensor
    "ywcgq": (
        LocalTuyaEntity(
            id=DPCode.LIQUID_STATE,
            name="State",
        ),
        LocalTuyaEntity(
            id=DPCode.LIQUID_DEPTH,
            name="Depth",
            icon="mdi:altimeter",
            custom_configs=localtuya_sensor(UnitOfLength.METERS, 1),
        ),
        LocalTuyaEntity(
            id=DPCode.LIQUID_LEVEL_PERCENT,
            name="Level",
            icon="mdi:altimeter",
            custom_configs=localtuya_sensor(PERCENTAGE, 1),
        ),
    ),
}


# Circuit Breaker
# https://developer.tuya.com/en/docs/iot/dlq?id=Kb0kidk9enyh8
SENSORS["dlq"] = SENSORS["zndb"]

# Socket (duplicate of `kg`)
# https://developer.tuya.com/en/docs/iot/s?id=K9gf7o5prgf7s
SENSORS["cz"] = SENSORS["kg"]

# Power Socket (duplicate of `kg`)
# https://developer.tuya.com/en/docs/iot/s?id=K9gf7o5prgf7s
SENSORS["pc"] = SENSORS["kg"]
