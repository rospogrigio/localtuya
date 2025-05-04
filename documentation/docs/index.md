# Overview

LocalTuya is an [HomeAssistant](https://www.home-assistant.io/){target="_blank"} integration that enables you to control your Tuya-based smart devices directly within your local network. 


!!! info "LocalTuya is a Hub "
    `LocalTuya` serves as a hub. After setup, whether using `cloud` or `no cloud`, you can manage your devices through the entry configuration UI in `hub configuration`.
    <!-- `Each Tuya account can be add on it's own` -->


!!! info "Cloud API"
    LocalTuya uses the cloud only to obtain device data and pre-fill the required fields for you.

    It offers many features to simplify device setup.

    `LocalTuya` can be used independently of the cloud.

[:material-file-document: Usage](usage/installation.md){.md-button}
[:simple-homeassistantcommunitystore: Add repository to HACS](https://my.home-assistant.io/redirect/hacs_repository/?category=integration&repository=hass-localtuya&owner=xZetsubou){ target=_blank .md-button }


## Features
<!-- - Supported protocols: `3.1`, `3.2`, `3.3`, `3.4`, and `3.5` -->
- [Cloud API](cloud_api.md) `Optional - Only used to assist in the devices setup process`
- Supported Sub-devices: `Devices that function through gateways`
- Auto-configure devices - *`Requires a cloud API setup`*
- Automatic insertion - *`Requires a cloud API setup`*
- Devices discovery - *`Discovers Tuya devices on your network`* 

## Supported Platforms
- Binary Sensor
- Button
- Climate
- Cover
- Fan
- Humidifier
- Light
- Number
- Selector
- Sensor
- Siren
- Switch
- Vacuum
