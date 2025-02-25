This fork takes the work of [Darek Margas](https://github.dev/darek-margas/localtuya) to support CID in LocalTuya for the Holman WX Series Wifi Irrigation tap. 
My fork was for my own learning of the Home Assistant development environment and to debug some issues I was having with my Holman WX1 taps.

I added a line to pytuya _status_update method to ensure that the decoded payload data was for the right device (CID) as I found it to be overwriting DPs for the wrong CID.

Note:
* More than 3 devices on the Gateway Hub is ignoring/failing to connect to the remaining gateway connected devices. This was happening on Darak's repo also. Will investigate.
* From rospogrigio's localtuya repo from v4.0.0 (see [README.md](./README.md)), YAML configuration for localtuya devices is not supported. This works through the config flow now, but is
quite manual - I didn't get any auto discovered devices. You may though, just follow the mappings below.


## Adding a new Holman WX1 device 

This should work with other WXx devices, I just don't have the mappings

```
Name: Friendly name
Local Key: Local key of gateway (I used tuya-cli wizard to get this)
Host: Local IP address of gateway 
Device ID: CID of device you are adding, listed under subDevices in tuya-cli wizard output
Protocol Version: 3.3
Manual DPS to add: 101,102,103,106,107,108,125
```

Hit Submit then you'll be prompted to add entities that map to the DPS above. Make sure you uncheck to not add any more entities between each entity you add.

```
Platform: sensor
Friendly Name: Soil Temperature
Id: 101
Unit of Measurement: °C
Device Class: temperature

Platform: sensor
Friendly Name: "Soil Moisture"
Id: 102
Unit of Measurement: "%"
Device Class: humidity

Platform: sensor
Friendly Name: Water spent
Unit of Measurement: "litres"
Id: 103

Platform: sensor
Friendly Name: "Irrigation status"
Id: 106

Platform: number
Friendly Name: Countdown minutes
Min Value: 0
Max Value: 60
id: 107

Platform: switch
Friendly Name: "Irrigation Tap (negated)"
Id: 108

Platform: binary_sensor
Friendly Name: "Postponed due to moisture"
id: 125
```