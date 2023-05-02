[![](https://img.shields.io/github/release/rospogrigio/localtuya-homeassistant/all.svg?style=for-the-badge)](https://github.com/rospogrigio/localtuya-homeassistant/releases)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)
[![](https://img.shields.io/badge/MAINTAINER-%40rospogrigio-green?style=for-the-badge)](https://github.com/rospogrigio)

![logo](https://github.com/rospogrigio/localtuya-homeassistant/blob/master/img/logo-small.png)

A Home Assistant custom Integration for local handling of Tuya-based devices.

This custom integration updates device status via pushing updates instead of polling, so status updates are fast (even when manually operated).
The integration also supports the Tuya IoT Cloud APIs, for the retrieval of info and of the local_keys of the devices. 


**NOTE: The Cloud API account configuration is not mandatory (LocalTuya can work also without it) but is strongly suggested for easy retrieval (and auto-update after re-pairing a device) of local_keys. Cloud API calls are performed only at startup, and when a local_key update is needed.**


The following Tuya device types are currently supported:
* Switches
* Lights
* Covers
* Fans
* Climates
* Vacuums

Energy monitoring (voltage, current, watts, etc.) is supported for compatible devices.

> **Currently, Tuya protocols from 3.1 to 3.4 are supported.**

This repository's development began as code from [@NameLessJedi](https://github.com/NameLessJedi), [@mileperhour](https://github.com/mileperhour) and [@TradeFace](https://github.com/TradeFace). Their code was then deeply refactored to provide proper integration with Home Assistant environment, adding config flow and other features. Refer to the "Thanks to" section below.


# Installation:

The easiest way, if you are using [HACS](https://hacs.xyz/), is to install LocalTuya through HACS.

For manual installation, copy the localtuya folder and all of its contents into your Home Assistant's custom_components folder. This folder is usually inside your `/config` folder. If you are running Hass.io, use SAMBA to copy the folder over. If you are running Home Assistant Supervised, the custom_components folder might be located at `/usr/share/hassio/homeassistant`. You may need to create the `custom_components` folder and then copy the localtuya folder and all of its contents into it.


# Usage:

**NOTE: You must have your Tuya device's Key and ID in order to use LocalTuya. The easiest way is to configure the Cloud API account in the integration. If you choose not to do it, there are several ways to obtain the local_keys depending on your environment and the devices you own. A good place to start getting info is https://github.com/codetheweb/tuyapi/blob/master/docs/SETUP.md .**


**NOTE 2: If you plan to integrate these devices on a network that has internet and blocking their internet access, you must also block DNS requests (to the local DNS server, e.g. 192.168.1.1). If you only block outbound internet, then the device will sit in a zombie state; it will refuse / not respond to any connections with the localkey. Therefore, you must first connect the devices with an active internet connection, grab each device localkey, and implement the block.**


# Adding the Integration


**NOTE: starting from v4.0.0, configuration using YAML files is no longer supported. The integration can only be configured using the config flow.**


To start configuring the integration, just press the "+ADD INTEGRATION" button in the Settings - Integrations page, and select LocalTuya from the drop-down menu.
The Cloud API configuration page will appear, requesting to input your Tuya IoT Platform account credentials:

![cloud_setup](https://github.com/rospogrigio/localtuya-homeassistant/blob/master/img/9-cloud_setup.png)

To setup a Tuya IoT Platform account and setup a project in it, refer to the instructions for the official Tuya integration:
https://www.home-assistant.io/integrations/tuya/
The place to find the Client ID and Secret is described in this link (in the ["Get Authorization Key"](https://www.home-assistant.io/integrations/tuya/#get-authorization-key) paragraph), while the User ID can be found in the "Link Tuya App Account" subtab within the Cloud project:

![user_id.png](https://github.com/rospogrigio/localtuya-homeassistant/blob/master/img/8-user_id.png)

> **Note: as stated in the above link, if you already have an account and an IoT project, make sure that it was created after May 25, 2021 (due to changes introduced in the cloud for Tuya 2.0). Otherwise, you need to create a new project. See the following screenshot for where to check your project creation date:**

![project_date](https://github.com/rospogrigio/localtuya-homeassistant/blob/master/img/6-project_date.png)

After pressing the Submit button, the first setup is complete and the Integration will be added. 

> **Note: it is not mandatory to input the Cloud API credentials: you can choose to tick the "Do not configure a Cloud API account" button, and the Integration will be added anyway.**

After the Integration has been set up, devices can be added and configured pressing the Configure button in the Integrations page:

![integration_configure](https://github.com/rospogrigio/localtuya-homeassistant/blob/master/img/10-integration_configure.png)


# Integration Configuration menu

The configuration menu is the following:

![config_menu](https://github.com/rospogrigio/localtuya-homeassistant/blob/master/img/11-config_menu.png)

From this menu, you can select the "Reconfigure Cloud API account" to edit your Tuya Cloud credentials and settings, in case they have changed or if the integration was migrated from v.3.x.x versions.

You can then proceed Adding or Editing your Tuya devices.

# Adding/editing a device

If you select to "Add or Edit a device", a drop-down menu will appear containing the list of detected devices (using auto-discovery if adding was selected, or the list of already configured devices if editing was selected): you can select one of these, or manually input all the parameters selecting the "..." option.

> **Note: The tuya app on your device must be closed for the following steps to work reliably.**


![discovery](https://github.com/rospogrigio/localtuya-homeassistant/blob/master/img/1-discovery.png)

If you have selected one entry, you only need to input the device's Friendly Name and localKey. These values will be automatically retrieved if you have configured your Cloud API account, otherwise you will need to input them manually.

Setting the scan interval is optional, it is only needed if energy/power values are not updating frequently enough by default. Values less than 10 seconds may cause stability issues.

Setting the 'Manual DPS To Add' is optional, it is only needed if the device doesn't advertise the DPS correctly until the entity has been properly initiailised. This setting can often be avoided by first connecting/initialising the device with the Tuya App, then closing the app and then adding the device in the integration.

Setting the 'DPIDs to send in RESET command' is optional. It is used when a device doesn't respond to any Tuya commands after a power cycle, but can be connected to (zombie state). The DPids will vary between devices, but typically "18,19,20" is used (and will be the default if none specified). If the wrong entries are added here, then the device may not come out of the zombie state. Typically only sensor DPIDs entered here.

Once you press "Submit", the connection is tested to check that everything works.

![image](https://github.com/rospogrigio/localtuya-homeassistant/blob/master/img/2-device.png)

Then, it's time to add the entities: this step will take place several times. First, select the entity type from the drop-down menu to set it up.
After you have defined all the needed entities, leave the "Do not add more entities" checkbox checked: this will complete the procedure.

![entity_type](https://github.com/rospogrigio/localtuya-homeassistant/blob/master/img/3-entity_type.png)

For each entity, the associated DP has to be selected. All the options requiring to select a DP will provide a drop-down menu showing
all the available DPs found on the device (with their current status!!) for easy identification. Each entity type has different options
to be configured. Here is an example for the "switch" entity:

![entity](https://github.com/rospogrigio/localtuya-homeassistant/blob/master/img/4-entity.png)

Once you configure the entities, the procedure is complete. You can now associate the device with an Area in Home Assistant

![success](https://github.com/rospogrigio/localtuya-homeassistant/blob/master/img/5-success.png)


# Migration from LocalTuya v.3.x.x

If you upgrade LocalTuya from v3.x.x or older, the config entry will automatically be migrated to the new setup. Everything should work as it did before the upgrade, apart from the fact that in the Integration tab you will see just one LocalTuya integration (showing the number of devices and entities configured) instead of several Integrations grouped within the LocalTuya Box. This will happen both if the old configuration was done using YAML files and with the config flow. Once migrated, you can just input your Tuya IoT account credentials to enable the support for the Cloud API (and benefit from the local_key retrieval and auto-update): see [Configuration menu](https://github.com/rospogrigio/localtuya#integration-configuration-menu).

If you had configured LocalTuya using YAML files, you can delete all its references from within the YAML files because they will no longer be considered so they might bring confusion (only the logger configuration part needs to be kept, of course, see [Debugging](https://github.com/rospogrigio/localtuya#debugging) ).


# Energy monitoring values

You can obtain Energy monitoring (voltage, current) in two different ways:

1) Creating individual sensors, each one with the desired name.
  Note: Voltage and Consumption usually include the first decimal. You will need to scale the parament by 0.1 to get the correct values.
2) Access the voltage/current/current_consumption attributes of a switch, and define template sensors
  Note:  these values are already divided by 10 for Voltage and Consumption
3) On some devices, you may find that the energy values are not updating frequently enough by default. If so, set the scan interval (see above) to an appropriate value. Settings below 10 seconds may cause stability issues, 30 seconds is recommended.

```
       sensor:
         - platform: template
           sensors:
             tuya-sw01_voltage:
               value_template: >-
                 {{ states.switch.sw01.attributes.voltage }}
               unit_of_measurement: 'V'
             tuya-sw01_current:
               value_template: >-
                 {{ states.switch.sw01.attributes.current }}
               unit_of_measurement: 'mA'
             tuya-sw01_current_consumption:
               value_template: >-
                 {{ states.switch.sw01.attributes.current_consumption }}
               unit_of_measurement: 'W'
```

# Debugging

Whenever you write a bug report, it helps tremendously if you include debug logs directly (otherwise we will just ask for them and it will take longer). So please enable debug logs like this and include them in your issue:

```yaml
logger:
  default: warning
  logs:
    custom_components.localtuya: debug
    custom_components.localtuya.pytuya: debug
```

Then, edit the device that is showing problems and check the "Enable debugging for this device" button.

# Notes:

* Do not declare anything as "tuya", such as by initiating a "switch.tuya". Using "tuya" launches Home Assistant's built-in, cloud-based Tuya integration in lieu of localtuya.

# To-do list:

* Create a (good and precise) sensor (counter) for Energy (kWh) -not just Power, but based on it-.
      Ideas: Use: https://www.home-assistant.io/components/integration/ and https://www.home-assistant.io/components/utility_meter/

* Everything listed in https://github.com/rospogrigio/localtuya-homeassistant/issues/15

# Thanks to:

NameLessJedi https://github.com/NameLessJedi/localtuya-homeassistant and mileperhour https://github.com/mileperhour/localtuya-homeassistant being the major sources of inspiration, and whose code for switches is substantially unchanged.

TradeFace, for being the only one to provide the correct code for communication with the type_0d devices (in particular, the 0x0d command for the status instead of the 0x0a, and related needs such as double reply to be received): https://github.com/TradeFace/tuya/

sean6541, for the working (standard) Python Handler for Tuya devices.

jasonacox, for the TinyTuya project from where I could import the code to communicate with devices using protocol 3.4.

postlund, for the ideas, for coding 95% of the refactoring and boosting the quality of this repo to levels hard to imagine (by me, at least) and teaching me A LOT of how things work in Home Assistant.

<a href="https://www.buymeacoffee.com/rospogrigio" target="_blank"><img src="https://bmc-cdn.nyc3.digitaloceanspaces.com/BMC-button-images/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: auto !important;width: auto !important;" ></a>
<a href="https://paypal.me/rospogrigio" target="_blank"><img src="https://www.paypalobjects.com/webstatic/mktg/logo/pp_cc_mark_37x23.jpg" border="0" alt="PayPal Logo" style="height: auto !important;width: auto !important;"></a>
