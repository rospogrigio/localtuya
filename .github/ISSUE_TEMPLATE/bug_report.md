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
- Last working localtuya version (if known and relevant): 
- Home Assistant Core version: <!-- Configuration => Info --> 
- [] Are you using the Home Assistant Tuya Cloud component ? <!-- if yes, put a x between the two [] => [x] -->
- [] Are you using the Tuya App in parallel ? <!-- if yes, put a x between the two [] => [x] -->

## Steps to reproduce
<!--
  Clearly define how to reproduce the issue. 
-->
1.
2. 
3.

## Configuration `configuration.yaml` or `config_flow`
<!--
  Fill this with the yaml or config_flow configuration of the failing device. Even if it seems unimportant to you. 
  Remove personal information and local key.
-->
```yaml

```

## DP dump
<!-- 
  Paste here a DP dump, see https://github.com/rospogrigio/localtuya/wiki/HOWTO-get-a-DPs-dump
  You can also try to qualify your device using the procedure described https://github.com/rospogrigio/localtuya/wiki/Qualifying-a-device
-->

## Provide Home Assistant taceback/logs
<!--
  Provide traces if they are relevant. If the problem is reproducible, try to set the log level to debug for this component at least:
  In Dev Tools => Services:

  logger.set_level
  custom_components.localtuya: debug

-->
```txt

```
## Additional information
<!-- Put here any information that you think it may be relevant -->
