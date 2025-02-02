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
    UnitOfPower,
    UnitOfTime,
    CONF_UNIT_OF_MEASUREMENT,
)

from .base import DPCode, LocalTuyaEntity, CONF_DEVICE_CLASS, EntityCategory
from ...const import CONF_SCALING as SCALE_FACTOR


def localtuya_sensor(unit_of_measurement=None, scale_factor: float = None) -> dict:
    """Define LocalTuya Configs for Sensor."""
    data = {CONF_UNIT_OF_MEASUREMENT: unit_of_measurement}
    if scale_factor:
        data.update({SCALE_FACTOR: scale_factor})

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
        id=DPCode.BATTERY_STATE,
        # translation_id="battery_state",
        icon="mdi:battery",
        entity_category=EntityCategory.DIAGNOSTIC,
        custom_configs=localtuya_sensor(PERCENTAGE),
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
SENSORS: dict[LocalTuyaEntity] = {
    # Multi-functional Sensor
    # https://developer.tuya.com/en/docs/iot/categorydgnbj?id=Kaiuz3yorvzg3
    "dgnbj": (
        LocalTuyaEntity(
            id=DPCode.GAS_SENSOR_VALUE,
            # translation_id="gas",
            icon="mdi:gas-cylinder",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.CH4_SENSOR_VALUE,
            # translation_id="gas",
            name="Methane",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.VOC_VALUE,
            # translation_id="voc",
            device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.PM25_VALUE,
            # translation_id="pm25",
            device_class=SensorDeviceClass.PM25,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.CO_VALUE,
            # translation_id="carbon_monoxide",
            icon="mdi:molecule-co",
            device_class=SensorDeviceClass.CO,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.CO2_VALUE,
            # translation_id="carbon_dioxide",
            icon="mdi:molecule-co2",
            device_class=SensorDeviceClass.CO2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.CH2O_VALUE,
            # translation_id="formaldehyde",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.BRIGHT_STATE,
            # translation_id="luminosity",
            icon="mdi:brightness-6",
        ),
        LocalTuyaEntity(
            id=DPCode.BRIGHT_VALUE,
            # translation_id="illuminance",
            icon="mdi:brightness-6",
            device_class=SensorDeviceClass.ILLUMINANCE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.TEMP_CURRENT,
            # translation_id="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.HUMIDITY_VALUE,
            # translation_id="humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.SMOKE_SENSOR_VALUE,
            # translation_id="smoke_amount",
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
            # translation_id="current_temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.TEMP_CURRENT_F,
            # translation_id="current_temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.STATUS,
            # translation_id="status",
        ),
    ),
    # CO2 Detector
    # https://developer.tuya.com/en/docs/iot/categoryco2bj?id=Kaiuz3wes7yuy
    "co2bj": (
        LocalTuyaEntity(
            id=DPCode.HUMIDITY_VALUE,
            # translation_id="humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.TEMP_CURRENT,
            # translation_id="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.CO2_VALUE,
            # translation_id="carbon_dioxide",
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
            # translation_id="humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.TEMP_CURRENT,
            # translation_id="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    ),
    # CO Detector
    # https://developer.tuya.com/en/docs/iot/categorycobj?id=Kaiuz3u1j6q1v
    "cobj": (
        LocalTuyaEntity(
            id=DPCode.CO_VALUE,
            # translation_id="carbon_monoxide",
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
            # translation_id="last_amount",
            icon="mdi:counter",
            state_class=SensorStateClass.MEASUREMENT,
        ),
    ),
    # Air Quality Monitor
    # No specification on Tuya portal
    "hjjcy": (
        LocalTuyaEntity(
            id=DPCode.TEMP_CURRENT,
            # translation_id="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.HUMIDITY_VALUE,
            # translation_id="humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.CO2_VALUE,
            # translation_id="carbon_dioxide",
            device_class=SensorDeviceClass.CO2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.CH2O_VALUE,
            # translation_id="formaldehyde",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.VOC_VALUE,
            # translation_id="voc",
            device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.PM25_VALUE,
            # translation_id="pm25",
            device_class=SensorDeviceClass.PM25,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    ),
    # Formaldehyde Detector
    # Note: Not documented
    "jqbj": (
        LocalTuyaEntity(
            id=DPCode.CO2_VALUE,
            # translation_id="carbon_dioxide",
            device_class=SensorDeviceClass.CO2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.VOC_VALUE,
            # translation_id="voc",
            device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.PM25_VALUE,
            # translation_id="pm25",
            device_class=SensorDeviceClass.PM25,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.VA_HUMIDITY,
            # translation_id="humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.VA_TEMPERATURE,
            # translation_id="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.CH2O_VALUE,
            # translation_id="formaldehyde",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        *BATTERY_SENSORS,
    ),
    # Methane Detector
    # https://developer.tuya.com/en/docs/iot/categoryjwbj?id=Kaiuz40u98lkm
    "jwbj": (
        LocalTuyaEntity(
            id=DPCode.CH4_SENSOR_VALUE,
            # translation_id="methane",
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
            custom_configs=localtuya_sensor(UnitOfElectricCurrent.AMPERE),
        ),
        LocalTuyaEntity(
            id=DPCode.CUR_POWER,
            name="Power",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfPower.KILO_WATT, 0.1),
        ),
        LocalTuyaEntity(
            id=DPCode.CUR_VOLTAGE,
            name="Voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfElectricPotential.VOLT, 0.1),
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
            custom_configs=localtuya_sensor(UnitOfElectricCurrent.AMPERE),
            # entity_registry_enabled_default=False,
        ),
        LocalTuyaEntity(
            id=DPCode.CUR_POWER,
            name="Power",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfPower.KILO_WATT, 0.1),
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
    ),
    # Luminance Sensor
    # https://developer.tuya.com/en/docs/iot/categoryldcg?id=Kaiuz3n7u69l8
    "ldcg": (
        LocalTuyaEntity(
            id=DPCode.BRIGHT_STATE,
            # translation_id="luminosity",
            icon="mdi:brightness-6",
        ),
        LocalTuyaEntity(
            id=DPCode.BRIGHT_VALUE,
            # translation_id="illuminance",
            device_class=SensorDeviceClass.ILLUMINANCE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.TEMP_CURRENT,
            # translation_id="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.HUMIDITY_VALUE,
            # translation_id="humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.CO2_VALUE,
            # translation_id="carbon_dioxide",
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
            # translation_id="current_temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.STATUS,
            # translation_id="sous_vide_status",
        ),
        LocalTuyaEntity(
            id=DPCode.REMAIN_TIME,
            # translation_id="remaining_time",
            custom_configs=localtuya_sensor(UnitOfTime.MINUTES),
            icon="mdi:timer",
        ),
    ),
    # PIR Detector
    # https://developer.tuya.com/en/docs/iot/categorypir?id=Kaiuz3ss11b80
    "pir": BATTERY_SENSORS,
    # PM2.5 Sensor
    # https://developer.tuya.com/en/docs/iot/categorypm25?id=Kaiuz3qof3yfu
    "pm2.5": (
        LocalTuyaEntity(
            id=DPCode.PM25_VALUE,
            # translation_id="pm25",
            device_class=SensorDeviceClass.PM25,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.CH2O_VALUE,
            # translation_id="formaldehyde",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.VOC_VALUE,
            # translation_id="voc",
            device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.TEMP_CURRENT,
            # translation_id="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.CO2_VALUE,
            # translation_id="carbon_dioxide",
            device_class=SensorDeviceClass.CO2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.HUMIDITY_VALUE,
            # translation_id="humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.PM1,
            # translation_id="pm1",
            device_class=SensorDeviceClass.PM1,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.PM10,
            # translation_id="pm10",
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
            custom_configs=localtuya_sensor(UnitOfPower.KILO_WATT, 0.1),
        ),
    ),
    # Gas Detector
    # https://developer.tuya.com/en/docs/iot/categoryrqbj?id=Kaiuz3d162ubw
    "rqbj": (
        LocalTuyaEntity(
            id=DPCode.GAS_SENSOR_VALUE,
            name=None,
            icon="mdi:gas-cylinder",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        *BATTERY_SENSORS,
    ),
    # Water Detector
    # https://developer.tuya.com/en/docs/iot/categorysj?id=Kaiuz3iub2sli
    "sj": BATTERY_SENSORS,
    # Emergency Button
    # https://developer.tuya.com/en/docs/iot/categorysos?id=Kaiuz3oi6agjy
    "sos": BATTERY_SENSORS,
    # Smart Camera
    # https://developer.tuya.com/en/docs/iot/categorysp?id=Kaiuz35leyo12
    "sp": (
        LocalTuyaEntity(
            id=DPCode.SENSOR_TEMPERATURE,
            # translation_id="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.SENSOR_HUMIDITY,
            # translation_id="humidity",
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
            # translation_id="carbon_dioxide",
            device_class=SensorDeviceClass.CO2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.PM25_VALUE,
            # translation_id="pm25",
            device_class=SensorDeviceClass.PM25,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.CH2O_VALUE,
            # translation_id="formaldehyde",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.HUMIDITY_VALUE,
            # translation_id="humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.TEMP_CURRENT,
            # translation_id="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.VOC_VALUE,
            # translation_id="voc",
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
            translation_id="External temperature",
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
            # translation_id="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.TEMP_CURRENT,
            # translation_id="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.VA_HUMIDITY,
            # translation_id="humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.HUMIDITY_VALUE,
            # translation_id="humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.BRIGHT_VALUE,
            # translation_id="illuminance",
            device_class=SensorDeviceClass.ILLUMINANCE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        *BATTERY_SENSORS,
    ),
    # Pressure Sensor
    # https://developer.tuya.com/en/docs/iot/categoryylcg?id=Kaiuz3kc2e4gm
    "ylcg": (
        LocalTuyaEntity(
            id=DPCode.PRESSURE_VALUE,
            name=None,
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
            # translation_id="smoke_amount",
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
            # translation_id="total_energy",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
        LocalTuyaEntity(
            id=DPCode.PHASE_A,
            name="Phase C Current",
            device_class=SensorDeviceClass.CURRENT,
            custom_configs=localtuya_sensor(UnitOfElectricCurrent.AMPERE),
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.PHASE_A,
            name="Phase C Power",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfPower.KILO_WATT, 0.1),
        ),
        LocalTuyaEntity(
            id=DPCode.PHASE_A,
            name="Phase A Voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfElectricPotential.VOLT, 0.1),
        ),
        LocalTuyaEntity(
            id=DPCode.PHASE_B,
            name="Phase B Current",
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfElectricCurrent.AMPERE),
        ),
        LocalTuyaEntity(
            id=DPCode.PHASE_B,
            name="Phase B Power",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfPower.KILO_WATT, 0.1),
        ),
        LocalTuyaEntity(
            id=DPCode.PHASE_B,
            name="Phase B Voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfElectricPotential.VOLT, 0.1),
        ),
        LocalTuyaEntity(
            id=DPCode.PHASE_C,
            name="Phase C Current",
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfElectricCurrent.AMPERE),
        ),
        LocalTuyaEntity(
            id=DPCode.PHASE_C,
            name="Phase C Power",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfPower.KILO_WATT, 0.1),
        ),
        LocalTuyaEntity(
            id=DPCode.PHASE_C,
            name="Phase C Voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfElectricPotential.VOLT, 0.1),
        ),
    ),
    # Circuit Breaker
    # https://developer.tuya.com/en/docs/iot/dlq?id=Kb0kidk9enyh8
    "dlq": (
        LocalTuyaEntity(
            id=DPCode.TOTAL_FORWARD_ENERGY,
            # translation_id="total_energy",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
        LocalTuyaEntity(
            id=DPCode.PHASE_A,
            name="Phase C Current",
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfElectricCurrent.AMPERE),
        ),
        LocalTuyaEntity(
            id=DPCode.PHASE_A,
            name="Phase C Power",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfPower.KILO_WATT, 0.1),
        ),
        LocalTuyaEntity(
            id=DPCode.PHASE_A,
            name="Phase A Voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfElectricPotential.VOLT, 0.1),
        ),
        LocalTuyaEntity(
            id=DPCode.PHASE_B,
            name="Phase B Current",
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfElectricCurrent.AMPERE),
        ),
        LocalTuyaEntity(
            id=DPCode.PHASE_B,
            name="Phase B Power",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfPower.KILO_WATT, 0.1),
        ),
        LocalTuyaEntity(
            id=DPCode.PHASE_B,
            name="Phase B Voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfElectricPotential.VOLT, 0.1),
        ),
        LocalTuyaEntity(
            id=DPCode.PHASE_C,
            name="Phase C Current",
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfElectricCurrent.AMPERE),
        ),
        LocalTuyaEntity(
            id=DPCode.PHASE_C,
            name="Phase C Power",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfPower.KILO_WATT, 0.1),
        ),
        LocalTuyaEntity(
            id=DPCode.PHASE_C,
            name="Phase C Voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            custom_configs=localtuya_sensor(UnitOfElectricPotential.VOLT, 0.1),
        ),
    ),
    # Robot Vacuum
    # https://developer.tuya.com/en/docs/iot/fsd?id=K9gf487ck1tlo
    "sd": (
        LocalTuyaEntity(
            id=DPCode.CLEAN_AREA,
            # translation_id="cleaning_area",
            icon="mdi:texture-box",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.CLEAN_TIME,
            # translation_id="cleaning_time",
            icon="mdi:progress-clock",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.TOTAL_CLEAN_AREA,
            # translation_id="total_cleaning_area",
            icon="mdi:texture-box",
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
        LocalTuyaEntity(
            id=DPCode.TOTAL_CLEAN_TIME,
            # translation_id="total_cleaning_time",
            icon="mdi:history",
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
        LocalTuyaEntity(
            id=DPCode.TOTAL_CLEAN_COUNT,
            # translation_id="total_cleaning_times",
            icon="mdi:counter",
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
        LocalTuyaEntity(
            id=DPCode.DUSTER_CLOTH,
            # translation_id="duster_cloth_life",
            icon="mdi:ticket-percent-outline",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.EDGE_BRUSH,
            # translation_id="side_brush_life",
            icon="mdi:ticket-percent-outline",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.FILTER_LIFE,
            # translation_id="filter_life",
            icon="mdi:ticket-percent-outline",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.ROLL_BRUSH,
            # translation_id="rolling_brush_life",
            icon="mdi:ticket-percent-outline",
            state_class=SensorStateClass.MEASUREMENT,
        ),
    ),
    # Curtain
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf48qy7wkre
    "cl": (
        LocalTuyaEntity(
            id=DPCode.TIME_TOTAL,
            # translation_id="last_operation_duration",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:progress-clock",
        ),
    ),
    # Humidifier
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf48qwjz0i3
    "jsq": (
        LocalTuyaEntity(
            id=DPCode.HUMIDITY_CURRENT,
            # translation_id="humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.TEMP_CURRENT,
            # translation_id="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.TEMP_CURRENT_F,
            # translation_id="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.LEVEL_CURRENT,
            # translation_id="water_level",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:waves-arrow-up",
        ),
    ),
    # Air Purifier
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf48r41mn81
    "kj": (
        LocalTuyaEntity(
            id=DPCode.FILTER,
            # translation_id="filter_utilization",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:ticket-percent-outline",
        ),
        LocalTuyaEntity(
            id=DPCode.PM25,
            # translation_id="pm25",
            device_class=SensorDeviceClass.PM25,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:molecule",
        ),
        LocalTuyaEntity(
            id=DPCode.TEMP,
            # translation_id="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.HUMIDITY,
            # translation_id="humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.TVOC,
            # translation_id="total_volatile_organic_compound",
            device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.ECO2,
            # translation_id="concentration_carbon_dioxide",
            device_class=SensorDeviceClass.CO2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.TOTAL_TIME,
            # translation_id="total_operating_time",
            icon="mdi:history",
            state_class=SensorStateClass.TOTAL_INCREASING,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.TOTAL_PM,
            # translation_id="total_absorption_particles",
            icon="mdi:texture-box",
            state_class=SensorStateClass.TOTAL_INCREASING,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.AIR_QUALITY,
            # translation_id="air_quality",
            icon="mdi:air-filter",
        ),
    ),
    # Fan
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf48quojr54
    "fs": (
        LocalTuyaEntity(
            id=DPCode.TEMP_CURRENT,
            # translation_id="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    ),
    # eMylo Smart WiFi IR Remote
    # Air Conditioner Mate (Smart IR Socket)
    "wnykq": (
        LocalTuyaEntity(
            id=DPCode.VA_TEMPERATURE,
            # translation_id="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.VA_HUMIDITY,
            # translation_id="humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.CUR_CURRENT,
            name="Current",
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            custom_configs=localtuya_sensor(UnitOfElectricCurrent.AMPERE),
            # entity_registry_enabled_default=False,
        ),
        LocalTuyaEntity(
            id=DPCode.CUR_POWER,
            name="Power",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            custom_configs=localtuya_sensor(UnitOfPower.KILO_WATT, 0.1),
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
    ),
    # Dehumidifier
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf48r6jke8e
    "cs": (
        LocalTuyaEntity(
            id=DPCode.TEMP_INDOOR,
            # translation_id="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.HUMIDITY_INDOOR,
            # translation_id="humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    ),
    # Soil sensor (Plant monitor)
    "zwjcy": (
        LocalTuyaEntity(
            id=DPCode.TEMP_CURRENT,
            # translation_id="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        LocalTuyaEntity(
            id=DPCode.HUMIDITY,
            # translation_id="humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        *BATTERY_SENSORS,
    ),
}

# Socket (duplicate of `kg`)
# https://developer.tuya.com/en/docs/iot/s?id=K9gf7o5prgf7s
SENSORS["cz"] = SENSORS["kg"]

# Power Socket (duplicate of `kg`)
# https://developer.tuya.com/en/docs/iot/s?id=K9gf7o5prgf7s
SENSORS["pc"] = SENSORS["kg"]
