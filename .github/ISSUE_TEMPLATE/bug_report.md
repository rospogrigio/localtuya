---
name: Bug report
about: Create a report to help us improve localtuya
title: ''
labels: 'bug'
assignees: ''

---
<!-- READ THIS FIRST:
  - For a new device, first check if you can find a similar device in the https://github.com/rospogrigio/localtuya/wiki/Known-working-and-non-working-devices
  - Try to update to latest master version, your problem may be already fixed.
  - Do not report issues for already existing problems. Check that an issue is not already opened and enrich it.
  - Provide as many details as possible. Paste logs, configuration samples and code into the backticks.
-->
## The problem
<!-- 
  Describe the issue you are experiencing here to communicate to the
  maintainers. Tell us what you were trying to do and what happened.
-->


## Environment
<!--
  Provide details about your environment.
-->
- Localtuya version: <!-- plugin version from HACS, master, commit id --> 
- Home Assistant Core version: <!-- Configuration => Info --> 
- [] Does the device work using the Home Assistant Tuya Cloud component ? <!-- if yes, put a x between the two [] => [x] -->
- [] Does the device work using the Tinytuya (https://github.com/jasonacox/tinytuya) command line tool ? <!-- if yes, put a x between the two [] => [x] -->
- [] Was the device working with earlier versions of localtuya ? Which one? <!-- if yes, put a x between the two [] => [x] -->
- [] Are you using the Tuya/SmartLife App in parallel ? <!-- if yes, put a x between the two [] => [x] -->

## Steps to reproduce
<!--
  Clearly define how to reproduce the issue. 
-->
1.
2. 
3.


## DP dump
<!-- 
  Paste here a DP dump, see https://github.com/rospogrigio/localtuya/wiki/HOWTO-get-a-DPs-dump
  You can also try to qualify your device using the procedure described https://github.com/rospogrigio/localtuya/wiki/Qualifying-a-device
-->

## Provide Home Assistant traceback/logs
<!--
  Provide logs if they are relevant. In detail, it is useful to be able to compare working with non-working situations, such as HA logs compared to the output of the tuyadebug script or the tinytuya CLI tool. 
  To increase the debugging level of HA for the devices, check the "enable debug" button when configuring the device, and set the log level to debug for this component at least:
  In configuration.yaml:

  logger.set_level
  custom_components.localtuya: debug
  custom_components.localtuya.pytuya: debug
-->
```
put your log output between these markers
```


## Additional information
<!-- Put here any information that you think it may be relevant -->
