# Introduction

Holman WX1 appears similar to Tuya Zigbee/Wifi gateway, except it is not Zigbee between tap and gateway just some UHF proprietary radio carrier. 
As such it can't be used with any Zigbee coordinator

To have tap integration working a few steps were required:
- I merged proposed gateway shortcut adding cid in "status" command
- I expanded it from "status" only to work on "set" command too.

I tested it as far, as I could, and so far:
- It does work on tap
- cid shortcut works with multiple devices on the same IP - tested with socket and tap
- So far it did not appear as breaking change for devices without gateway.

<b>Notes:</b>
CID/Node ID can be found by quering Tuya API (I use tuya-cli). They are not all the same.
Timer countdown counts down as it goes but gains back initial position after stop.

# Installation

## HACS install

1. You can watch my [Pull Request](https://github.com/rospogrigio/localtuya/pull/1305) and install the latest version of localtuya then, or install my fork via HACS.
2. Set up localtuya as per the README.md instructions. It's a bit of work.
3. Add your Holman device(s), one by one. Make sure to enter the Node ID correctly. Use the following configuration:

Use manual DPs:
`101,102,103,105,106,107,108,110,111,112,113,114,115,117,119,121,122,123,125,128`

### With sensor:
```
sensor
DPS 101
WX1 Soil Temperature
unit °C
class temperature

sensor
DPS 102
WX1 Soil Moisture
unit %
class humidity

sensor
id 103
WX1 Last Water Flow
unit L
class water

sensor
id 105
WX1 Battery Level

sensor
id 106
WX1 Tap Timer Status

sensor
id 110
WX1 Start A (encoded)

sensor
id 111
WX1 Start B (encoded)

sensor
id 112
WX1 Start C (encoded)

sensor
id 121
WX1 Flow Count (encoded)

sensor
id 122
WX1 Temperature Count (encoded)

sensor
id 123
WX1 Moisture Count (encoded)

sensor
id 128
WX1 Next Watering (encoded)
restore_on_reconnect true

number
id 107
WX1 Manual Watering Setting (mins)
min_value 1,
max_value 60
step_size 1

switch
id 108
WX1 Watering (inverse)

select
id 113
WX1 Watering Delay
select_options 0;24;48;72
select_options_friendly 0h;24h;48h;72h

select
id 114
WX1 24 Hour Time
select_options 12;24
select_options_friendly 12H;24H

select
id 119
WX1 Sensor Units
select_options 1;2
select_options_friendly L/°C;Gal/°F

binary_sensor
id 115
WX1 Soil Sensor Present

binary_sensor
id 116
WX1 Rain Sensor Present

binary_sensor
id 117
WX1 Soil Sensor Power OK

binary_sensor
id 125
WX1 Postponed Due To Rain
```

### Without sensor
```
sensor
id 103
WX1 Last Water Flow
unit L
class water

sensor
id 105
WX1 Battery Level

sensor
id 106
WX1 Tap Timer Status

sensor
id 110
WX1 Start A (encoded)

sensor
id 111
WX1 Start B (encoded)

sensor
id 112
WX1 Start C (encoded)

sensor
id 121
WX1 Flow Count (encoded)

sensor
id 128
WX1 Next Watering (encoded)
restore_on_reconnect true

number
id 107
WX1 Manual Watering Setting (mins)
min_value 1,
max_value 60
step_size 1

switch
id 108
WX1 Watering (inverse)

select
id 113
WX1 Watering Delay
select_options 0;24;48;72
select_options_friendly 0h;24h;48h;72h

select
id 114
WX1 24 Hour Time
select_options 12;24
select_options_friendly 12H;24H

select
id 119
WX1 Sensor Units
select_options 1;2
select_options_friendly L/°C;Gal/°F

binary_sensor
id 125
WX1 Postponed Due To Rain
```

## Additional entities setup

Once installed via HACS, the main entities should be there. There's a few little issues:

1. Some entities don't update reliably and may be unavailable for a while, especially after restart
2. Some values are not human readable
3. Some controls are not accessible
4. The manual switch is inverted

### Buffering Values

To remedy point 1,

1. Install the [Variables Integration](https://github.com/snarky-snark/home-assistant-variables)
2. Add buffer var entities to your setup under the `var:` section in your configuration. I'm using an `!include` directive, i.e. `var: !include var.yaml` and the following is the contents of that `var.yaml` file

For the Start entities (schedules):

```
  wx1_start_a_buffer:
    friendly_name: "WX1 Start A Buffer"
    initial_value: "AAAAAAAAAAAA"
    value_template: >
      {% if is_state('sensor.wx1_start_a_encoded','unavailable') or is_state('sensor.wx1_start_a_encoded','unknown') %}
        {{ states('var.wx1_start_a_buffer') }}
      {% else %}
        {{ states('sensor.wx1_start_a_encoded') }}
      {% endif %}
    tracked_entity_id:
      - sensor.wx1_start_a_encoded
  wx1_start_b_buffer:
    friendly_name: "WX1 Start B Buffer"
    initial_value: "AAAAAAAAAAAA"
    value_template: >
      {% if is_state('sensor.wx1_start_b_encoded','unavailable') or is_state('sensor.wx1_start_b_encoded','unknown') %}
        {{ states('var.wx1_start_b_buffer') }}
      {% else %}
        {{ states('sensor.wx1_start_b_encoded') }}
      {% endif %}
    tracked_entity_id:
      - sensor.wx1_start_b_encoded
  wx1_start_c_buffer:
    friendly_name: "WX1 Start C Buffer"
    initial_value: "AAAAAAAAAAAA"
    value_template: >
      {% if is_state('sensor.wx1_start_c_encoded','unavailable') or is_state('sensor.wx1_start_c_encoded','unknown') %}
        {{ states('var.wx1_start_c_buffer') }}
      {% else %}
        {{ states('sensor.wx1_start_c_encoded') }}
      {% endif %}
    tracked_entity_id:
      - sensor.wx1_start_c_encoded
```

For the sensor entities add this (if you have a sensor):

```
wx1_temperature_count_buffer:
    friendly_name: "WX1 Temperature Count Buffer"
    initial_value: 0
    value_template: >
      {% if is_state('sensor.wx1_temperature_count_encoded','unavailable') or is_state('sensor.wx1_temperature_count_encoded','unknown') %}
        {{ states('var.wx1_temperature_count_buffer') }}
      {% else %}
        {{ states('sensor.wx1_temperature_count_encoded') }}
      {% endif %}
    tracked_entity_id:
      - sensor.wx1_temperature_count_encoded
  wx1_moisture_count_buffer:
    friendly_name: "WX1 Moisture Count Buffer"
    initial_value: 0
    value_template: >
      {% if is_state('sensor.wx1_moisture_count_encoded','unavailable') or is_state('sensor.wx1_moisture_count_encoded','unknown') %}
        {{ states('var.wx1_moisture_count_buffer') }}
      {% else %}
        {{ states('sensor.wx1_moisture_count_encoded') }}
      {% endif %}
    tracked_entity_id:
      - sensor.wx1_moisture_count_encoded
  wx1_flow_count_buffer:
    friendly_name: "WX1 Flow Count Buffer"
    initial_value: 0
    value_template: >
      {% if is_state('sensor.wx1_flow_count_encoded','unavailable') or is_state('sensor.wx1_flow_count_encoded','unknown') %}
        {{ states('var.wx1_flow_count_buffer') }}
      {% else %}
        {{ states('sensor.wx1_flow_count_encoded') }}
      {% endif %}
    tracked_entity_id:
      - sensor.wx1_flow_count_encoded
```

Don't use these entities directly, we'll make use of them in the next step.

### Getting usable values

Next, we'll implement a number of switches and sensors that will deliver the correct values and allow interaction with the device.

Add the following sensor templates to your configuration. I use a separate file, `templates.yaml` again, and just have `template: !include templates.yaml` in my main `configuration.yaml`

For the main unit:

```
- sensor:
  - name: "WX1 Battery Status"
    state: >-
        {% set mapper = {
          '0':'Empty',
          '1':'Half',
          '2':'Full'
        } %}
        {% set state = states('sensor.wx1_battery_level') %}
        {{ mapper[state] if state in mapper else state }}
    icon: >-
        {% if is_state('sensor.wx1_battery_level', '0') %}
          mdi:battery-outline
        {% elif is_state('sensor.wx1_battery_level', '1') %}
          mdi:battery-50
        {% else %}
          mdi:battery
        {% endif %}
- sensor:
  - name: "WX1 Irrigation Status"
    state: >-
        {% set mapper = {
          '0':'Not Watering',
          '1':'Manual Watering',
          '2':'Watering A/B/C',
          '3':'Rain Delay Active'
        } %}
        {% set state = states('sensor.wx1_tap_timer_status') %}
        {{ mapper[state] if state in mapper else state }}
    icon: >-
        {% if is_state('sensor.wx1_tap_timer_status', '0') %}
          mdi:water-off
        {% elif is_state('sensor.wx1_tap_timer_status', '1') %}
          mdi:water-plus
        {% elif is_state('sensor.wx1_tap_timer_status', '2') %}
          mdi:water-sync
        {% else %}
          mdi:weather-pouring
        {% endif %}
- sensor:
  - name: "WX1 Next Watering"
    state: >-
      {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
      {% set data = namespace(xitems=[]) %}
      {% set lx = states('sensor.wx1_next_watering_encoded') | list %}
      {% for item in lx %}
        {% if item != "=" %}
          {% set data.xitems = data.xitems + [ base[item] ] %}
        {% endif %}
      {% endfor %}
      {% set bytecount = ( lx | length / 4 * 3 - ( lx | length - data.xitems | reject('undefined') | list | length )) | int %}
      {% set dataw = namespace(witems=[]) %}
      {% for cnt in range(0,lx | length, 4) %}
        {% if cnt + 1 < data.xitems | length %}
          {% set dataw.witems = dataw.witems + [ (data.xitems[cnt] | bitwise_and(63) * 4 + ( data.xitems[cnt + 1] | bitwise_and(48) / 16)) ] %}
        {% endif %}
        {% if cnt + 2 < data.xitems | length %}
          {% set dataw.witems = dataw.witems + [ (data.xitems[cnt + 1] | bitwise_and(15) * 16 + data.xitems[cnt + 2] | bitwise_and(60) / 4) ] %}
        {% endif %}
        {% if cnt + 3 < data.xitems | length %}
          {% set dataw.witems = dataw.witems + [ (data.xitems[cnt + 2] | bitwise_and(3) + data.xitems[cnt + 3]) ] %}
        {% endif %}
      {% endfor %}
      {{ "N/A" if dataw.witems[2] == 0 else "%02d" | format(dataw.witems[2]) ~ "/" ~ "%02d" | format(dataw.witems[1]) ~ "/20" ~ "%02d" | format(dataw.witems[0]) ~ " at " ~ "%01d" | format(dataw.witems[3]) ~ ":" ~ "%02d" | format(dataw.witems[4]) }}
- sensor:
  - name: "WX1 Flow Count"
    state: >-
          {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
          {% set data = namespace(xitems=[]) %}
          {% set lx = states('var.wx1_flow_count_buffer') | list %}
          {% for item in lx %}
            {% if item != "=" %}
              {% set data.xitems = data.xitems + [ base[item] ] %}
            {% endif %}
          {% endfor %}
          {% set bytecount = ( lx | length / 4 * 3 - ( lx | length - data.xitems | reject('undefined') | list | length )) | int %}
          {% set dataw = namespace(witems=[]) %}
          {% for cnt in range(0,lx | length, 4) %}
            {% if cnt + 1 < data.xitems | length %}
              {% set dataw.witems = dataw.witems + [ (data.xitems[cnt] | bitwise_and(63) * 4 + ( data.xitems[cnt + 1] | bitwise_and(48) / 16)) ] %}
            {% endif %}
            {% if cnt + 2 < data.xitems | length %}
              {% set dataw.witems = dataw.witems + [ (data.xitems[cnt + 1] | bitwise_and(15) * 16 + data.xitems[cnt + 2] | bitwise_and(60) / 4) ] %}
            {% endif %}
            {% if cnt + 3 < data.xitems | length %}
              {% set dataw.witems = dataw.witems + [ (data.xitems[cnt + 2] | bitwise_and(3) + data.xitems[cnt + 3]) ] %}
            {% endif %}
          {% endfor %}
          {% set dataf = namespace(fitems=[]) %}
          {% for cnt in range(0,dataw.witems | length, 2) %}
            {% if cnt + 1 < dataw.witems | length %}
              {% set dataf.fitems = dataf.fitems + [ (dataw.witems[cnt] * 256 + dataw.witems[cnt + 1] ) | int ] %}
            {% endif %}
          {% endfor %}
          {{ "Unavailable" if states('var.wx1_flow_count_buffer') == "unavailable" else dataf.fitems[0] }}
    attributes:
      values_list: >-
          {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
          {% set data = namespace(xitems=[]) %}
          {% set lx = states('var.wx1_flow_count_buffer') | list %}
          {% for item in lx %}
            {% if item != "=" %}
              {% set data.xitems = data.xitems + [ base[item] ] %}
            {% endif %}
          {% endfor %}
          {% set bytecount = ( lx | length / 4 * 3 - ( lx | length - data.xitems | reject('undefined') | list | length )) | int %}
          {% set dataw = namespace(witems=[]) %}
          {% for cnt in range(0,lx | length, 4) %}
            {% if cnt + 1 < data.xitems | length %}
              {% set dataw.witems = dataw.witems + [ (data.xitems[cnt] | bitwise_and(63) * 4 + ( data.xitems[cnt + 1] | bitwise_and(48) / 16)) ] %}
            {% endif %}
            {% if cnt + 2 < data.xitems | length %}
              {% set dataw.witems = dataw.witems + [ (data.xitems[cnt + 1] | bitwise_and(15) * 16 + data.xitems[cnt + 2] | bitwise_and(60) / 4) ] %}
            {% endif %}
            {% if cnt + 3 < data.xitems | length %}
              {% set dataw.witems = dataw.witems + [ (data.xitems[cnt + 2] | bitwise_and(3) + data.xitems[cnt + 3]) ] %}
            {% endif %}
          {% endfor %}
          {% set dataf = namespace(fitems=[]) %}
          {% for cnt in range(0,dataw.witems | length, 2) %}
            {% if cnt + 1 < dataw.witems | length %}
              {% set dataf.fitems = dataf.fitems + [ (dataw.witems[cnt] * 256 + dataw.witems[cnt + 1] ) | int ] %}
            {% endif %}
          {% endfor %}
          {{ [] if states('var.wx1_flow_count_buffer') == "unavailable" else dataf.fitems }}
    state_class: total
    device_class: water
    unit_of_measurement: L
- sensor:
  - name: "WX1 Start A"
    state: >-
      {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
      {% set data = namespace(items=[]) %}
      {% set l = states('var.wx1_start_a_buffer') | list %}
      {% for item in l %}
        {% set data.items = data.items + [ base[item] ] %}
      {% endfor %}
      {% set hs = data.items[1] | bitwise_and(15) * 16 + data.items[2] | bitwise_and(60) / 4 %}
      {% set ms = data.items[2] | bitwise_and(3) + data.items[3] %}
      {% set h = data.items[4] | bitwise_and(63) * 4 + data.items[5] | bitwise_and(48) / 16 %}
      {% set m = data.items[5] | bitwise_and(15) * 16 + data.items[6] | bitwise_and(60) / 4 %}
      {% set sun = "Sun" if data.items[6] | bitwise_and(2) > 0 else "" %}
      {% set mon = "Mon" if data.items[6] | bitwise_and(1) > 0 else "" %}
      {% set tue = "Tue" if data.items[7] | bitwise_and(32) > 0 else "" %}
      {% set wed = "Wed" if data.items[7] | bitwise_and(16) > 0 else "" %}
      {% set thu = "Thu" if data.items[7] | bitwise_and(8) > 0 else "" %}
      {% set fri = "Fri" if data.items[7] | bitwise_and(4) > 0 else "" %}
      {% set sat = "Sat" if data.items[7] | bitwise_and(2) > 0 else "" %}
      {% set enable = data.items[7] | bitwise_and(1) > 0 %}
      {% set d = [ sun , mon , tue , wed , thu , fri , sat ] | reject("equalto","") | join(',') %}
      {% set timing = "%02d" | format(hs) ~ ":" ~ "%02d" | format(ms) ~ " for " ~ "%02d" | format(h) ~ ":" ~  "%02d" | format(m) ~ "h" %}
      {{ "Unavailable" if states('var.wx1_start_a_buffer') == "unavailable" else "On "  + "(" + d + ") at " + timing if enable else "Off" }}
- sensor:
  - name: "WX1 Start B"
    state: >-
      {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
      {% set data = namespace(items=[]) %}
      {% set l = states('var.wx1_start_b_buffer') | list %}
      {% for item in l %}
        {% set data.items = data.items + [ base[item] ] %}
      {% endfor %}
      {% set hs = data.items[1] | bitwise_and(15) * 16 + data.items[2] | bitwise_and(60) / 4 %}
      {% set ms = data.items[2] | bitwise_and(3) + data.items[3] %}
      {% set h = data.items[4] | bitwise_and(63) * 4 + data.items[5] | bitwise_and(48) / 16 %}
      {% set m = data.items[5] | bitwise_and(15) * 16 + data.items[6] | bitwise_and(60) / 4 %}
      {% set sun = "Sun" if data.items[6] | bitwise_and(2) > 0 else "" %}
      {% set mon = "Mon" if data.items[6] | bitwise_and(1) > 0 else "" %}
      {% set tue = "Tue" if data.items[7] | bitwise_and(32) > 0 else "" %}
      {% set wed = "Wed" if data.items[7] | bitwise_and(16) > 0 else "" %}
      {% set thu = "Thu" if data.items[7] | bitwise_and(8) > 0 else "" %}
      {% set fri = "Fri" if data.items[7] | bitwise_and(4) > 0 else "" %}
      {% set sat = "Sat" if data.items[7] | bitwise_and(2) > 0 else "" %}
      {% set enable = data.items[7] | bitwise_and(1) > 0 %}
      {% set d = [ sun , mon , tue , wed , thu , fri , sat ] | reject("equalto","") | join(',') %}
      {% set timing = "%02d" | format(hs) ~ ":" ~ "%02d" | format(ms) ~ " for " ~ "%02d" | format(h) ~ ":" ~  "%02d" | format(m) ~ "h" %}
      {{ "Unavailable" if states('var.wx1_start_b_buffer') == "unavailable" else "On "  + "(" + d + ") at " + timing if enable else "Off" }}
- sensor:
  - name: "WX1 Start C"
    state: >-
      {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
      {% set data = namespace(items=[]) %}
      {% set l = states('var.wx1_start_c_buffer') | list %}
      {% for item in l %}
        {% set data.items = data.items + [ base[item] ] %}
      {% endfor %}
      {% set hs = data.items[1] | bitwise_and(15) * 16 + data.items[2] | bitwise_and(60) / 4 %}
      {% set ms = data.items[2] | bitwise_and(3) + data.items[3] %}
      {% set h = data.items[4] | bitwise_and(63) * 4 + data.items[5] | bitwise_and(48) / 16 %}
      {% set m = data.items[5] | bitwise_and(15) * 16 + data.items[6] | bitwise_and(60) / 4 %}
      {% set sun = "Sun" if data.items[6] | bitwise_and(2) > 0 else "" %}
      {% set mon = "Mon" if data.items[6] | bitwise_and(1) > 0 else "" %}
      {% set tue = "Tue" if data.items[7] | bitwise_and(32) > 0 else "" %}
      {% set wed = "Wed" if data.items[7] | bitwise_and(16) > 0 else "" %}
      {% set thu = "Thu" if data.items[7] | bitwise_and(8) > 0 else "" %}
      {% set fri = "Fri" if data.items[7] | bitwise_and(4) > 0 else "" %}
      {% set sat = "Sat" if data.items[7] | bitwise_and(2) > 0 else "" %}
      {% set enable = data.items[7] | bitwise_and(1) > 0 %}
      {% set d = [ sun , mon , tue , wed , thu , fri , sat ] | reject("equalto","") | join(',') %}
      {% set timing = "%02d" | format(hs) ~ ":" ~ "%02d" | format(ms) ~ " for " ~ "%02d" | format(h) ~ ":" ~  "%02d" | format(m) ~ "h" %}
      {{ "Unavailable" if states('var.wx1_start_c_buffer') == "unavailable" else "On "  + "(" + d + ") at " + timing if enable else "Off" }}
```

If you have the sensor attached, add these:

```
- sensor:
    - name: "WX1 Moisture Count"
      state: >-
        {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
        {% set data = namespace(xitems=[]) %}
        {% set lx = states('var.wx1_moisture_count_buffer') | list | reject('equalto','/') | list %}
        {% for item in lx %}
          {% if item != "=" %}
            {% set data.xitems = data.xitems + [ base[item] ] %}
          {% endif %}
        {% endfor %}
        {% set bytecount = ( lx | length / 4 * 3 - ( lx | length - data.xitems | reject('undefined') | list | length )) | int %}
        {% set dataw = namespace(witems=[]) %}
        {% for cnt in range(0,lx | length, 4) %}
          {% if cnt + 1 < data.xitems | length %}
            {% set dataw.witems = dataw.witems + [ ((data.xitems[cnt] | bitwise_and(63) * 4 + ( data.xitems[cnt + 1] | bitwise_and(48) / 16))) | int ] %}
          {% endif %}
          {% if cnt + 2 < data.xitems | length %}
            {% set dataw.witems = dataw.witems + [ ((data.xitems[cnt + 1] | bitwise_and(15) * 16 + data.xitems[cnt + 2] | bitwise_and(60) / 4)) | int ] %}
          {% endif %}
          {% if cnt + 3 < data.xitems | length %}
            {% set dataw.witems = dataw.witems + [ ((data.xitems[cnt + 2] | bitwise_and(3) + data.xitems[cnt + 3])) | int ] %}
          {% endif %}
        {% endfor %}
        {{ "Unavailable" if states('var.wx1_moisture_count_buffer') == "unavailable" else dataw.witems[0] }}
      state_class: measurement
      device_class: humidity
      unit_of_measurement: "%"
  - sensor:
    - name: "WX1 Temperature Count"
      state: >-
        {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
        {% set data = namespace(xitems=[]) %}
        {% set lx = states('var.wx1_temperature_count_buffer') | list | reject('equalto','/') | list %}
        {% for item in lx %}
          {% if item != "=" %}
            {% set data.xitems = data.xitems + [ base[item] ] %}
          {% endif %}
        {% endfor %}
        {% set bytecount = ( lx | length / 4 * 3 - ( lx | length - data.xitems | reject('undefined') | list | length )) | int %}
        {% set dataw = namespace(witems=[]) %}
        {% for cnt in range(0,lx | length, 4) %}
          {% if cnt + 1 < data.xitems | length %}
            {% set dataw.witems = dataw.witems + [ ((data.xitems[cnt] | bitwise_and(63) * 4 + ( data.xitems[cnt + 1] | bitwise_and(48) / 16))) | int ] %}
          {% endif %}
          {% if cnt + 2 < data.xitems | length %}
            {% set dataw.witems = dataw.witems + [ ((data.xitems[cnt + 1] | bitwise_and(15) * 16 + data.xitems[cnt + 2] | bitwise_and(60) / 4)) | int ] %}
          {% endif %}
          {% if cnt + 3 < data.xitems | length %}
            {% set dataw.witems = dataw.witems + [ ((data.xitems[cnt + 2] | bitwise_and(3) + data.xitems[cnt + 3])) | int ] %}
          {% endif %}
        {% endfor %}
        {{ "Unavailable" if states('var.wx1_temperature_count_buffer') == "unavailable" else dataw.witems[0] }}
      state_class: measurement
      device_class: temperature
      unit_of_measurement: °C
```

### Adding controls

To finalise the setup, I've added a number of controls. Firstly, there's the Manual Watering switch, which in the original version is inverted.

I've added `switch: !include switches.yaml` as per all the other additions above. These are the contents of the `switches.yaml` file:

Main Watering Switch:

```
- platform: template
  switches:
    wx1_wx1_manual_switch:
      friendly_name: "WX1 Manual Watering"
      availability_template: "{{ not is_state('switch.wx1_watering_inverse', 'unavailable') }}"
      value_template: "{{ is_state('switch.wx1_watering_inverse', 'off') }}"
      turn_on:
        service: switch.turn_off
        target:
          entity_id: switch.wx1_watering_inverse
      turn_off:
        service: switch.turn_on
        target:
          entity_id: switch.wx1_watering_inverse
      icon_template: >-
        {% if is_state('switch.wx1_watering_inverse', 'off') %}
          mdi:water
        {% else %}
          mdi:water-off
        {% endif %}
```

A switch that turns on or off a schedule (A, B, or C). This is the example for Start A:

<b>Note, you will need to insert your CID (replace `XXX`) for the service call in `device_id` and add the correct `dp` (see mappings above)! Start A is `110` in the example</b>

<pre>
    wx1_wx1_start_a_switch:
      friendly_name: "WX1 Start A Switch"
      value_template: >-
          {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
          {% set data = namespace(items=[]) %}
          {% set l = states('var.wx1_start_a_buffer') | list %}
          {% for item in l %}
            {% set data.items = data.items + [ base[item] ] %}
          {% endfor %}
          {% set enable = data.items[7] | bitwise_and(1) > 0 %}
          {{ enable }}
      availability_template: "{{ states('var.wx1_start_a_buffer') != \"unavailable\" }}"
      turn_on:
        service: localtuya.set_dp
        data:
          device_id: <i><u><b>"XXX"</b></u></i>
          dp: <i><u><b>110</b></u></i>
          value: >-
              {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
              {% set data = namespace(items=[]) %}
              {% set l = states('var.wx1_start_a_buffer') | list %}
              {% for item in l %}
                {% set data.items = data.items + [ base[item] ] %}
              {% endfor %}
              {% set data.items = data.items[:7] + [ (data.items[7] + 1 | bitwise_and(1)) + (data.items[7] | bitwise_and(254)) ] + data.items[8:] %}
              {% set res = namespace(items=[]) %}
              {% set char = base.keys() | list %}
              {% for item in data.items %}
                {% set res.items = res.items + [ char[item] ] %}
              {% endfor %}
              {{ res.items | join }}
      turn_off:
        service: localtuya.set_dp
        data:
          device_id: <i><u><b>"XXX"</b></u></i>
          dp: <i><u><b>110</b></u></i>
          value: >-
              {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
              {% set data = namespace(items=[]) %}
              {% set l = states('var.wx1_start_a_buffer') | list %}
              {% for item in l %}
                {% set data.items = data.items + [ base[item] ] %}
              {% endfor %}
              {% set data.items = data.items[:7] + [ ((data.items[7] + 1) | bitwise_and(1)) + (data.items[7] | bitwise_and(254)) ] + data.items[8:] %}
              {% set res = namespace(items=[]) %}
              {% set char = base.keys() | list %}
              {% for item in data.items %}
                {% set res.items = res.items + [ char[item] ] %}
              {% endfor %}
              {{ res.items | join }}
</pre>

If you want full control, you can insert these full controls for each desired scheduler to map each day of the scheduler to a switch. Again. change the values, as per the on/off switch above:

```
    wx1_wx1_start_a_sun_switch:
      friendly_name: "WX1 Start A Sunday Switch"
      value_template: >-
          {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
          {% set data = namespace(items=[]) %}
          {% set l = states('var.wx1_start_a_buffer') | list %}
          {% for item in l %}
            {% set data.items = data.items + [ base[item] ] %}
          {% endfor %}
          {% set day = data.items[6] | bitwise_and(2) > 0 %}
          {{ day }}
      availability_template: "{{ states('var.wx1_start_a_buffer') != \"unavailable\" }}"
      turn_on:
        service: localtuya.set_dp
        data:
          device_id: "XXX"
          dp: 110
          value: >-
              {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
              {% set data = namespace(items=[]) %}
              {% set l = states('var.wx1_start_a_buffer') | list %}
              {% for item in l %}
                {% set data.items = data.items + [ base[item] ] %}
              {% endfor %}
              {% set data.items = data.items[:6] + [ (data.items[6] | bitwise_and(253)) + 2 ] + data.items[7:] %}
              {% set res = namespace(items=[]) %}
              {% set char = base.keys() | list %}
              {% for item in data.items %}
                {% set res.items = res.items + [ char[item] ] %}
              {% endfor %}
              {{ res.items | join }}
      turn_off:
        service: localtuya.set_dp
        data:
          device_id: "XXX"
          dp: 110
          value: >-
              {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
              {% set data = namespace(items=[]) %}
              {% set l = states('var.wx1_start_a_buffer') | list %}
              {% for item in l %}
                {% set data.items = data.items + [ base[item] ] %}
              {% endfor %}
              {% set data.items = data.items[:6] + [ (data.items[6] | bitwise_and(253)) ] + data.items[7:] %}
              {% set res = namespace(items=[]) %}
              {% set char = base.keys() | list %}
              {% for item in data.items %}
                {% set res.items = res.items + [ char[item] ] %}
              {% endfor %}
              {{ res.items | join }}
    wx1_wx1_start_a_mon_switch:
      friendly_name: "WX1 Start A Monday Switch"
      value_template: >-
          {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
          {% set data = namespace(items=[]) %}
          {% set l = states('var.wx1_start_a_buffer') | list %}
          {% for item in l %}
            {% set data.items = data.items + [ base[item] ] %}
          {% endfor %}
          {% set day = data.items[6] | bitwise_and(1) > 0 %}
          {{ day }}
      availability_template: "{{ states('var.wx1_start_a_buffer') != \"unavailable\" }}"
      turn_on:
        service: localtuya.set_dp
        data:
          device_id: "XXX"
          dp: 110
          value: >-
              {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
              {% set data = namespace(items=[]) %}
              {% set l = states('var.wx1_start_a_buffer') | list %}
              {% for item in l %}
                {% set data.items = data.items + [ base[item] ] %}
              {% endfor %}
              {% set data.items = data.items[:6] + [ (data.items[6] | bitwise_and(254)) + 1 ] + data.items[7:] %}
              {% set res = namespace(items=[]) %}
              {% set char = base.keys() | list %}
              {% for item in data.items %}
                {% set res.items = res.items + [ char[item] ] %}
              {% endfor %}
              {{ res.items | join }}
      turn_off:
        service: localtuya.set_dp
        data:
          device_id: "XXX"
          dp: 110
          value: >-
              {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
              {% set data = namespace(items=[]) %}
              {% set l = states('var.wx1_start_a_buffer') | list %}
              {% for item in l %}
                {% set data.items = data.items + [ base[item] ] %}
              {% endfor %}
              {% set data.items = data.items[:6] + [ (data.items[6] | bitwise_and(254)) ] + data.items[7:] %}
              {% set res = namespace(items=[]) %}
              {% set char = base.keys() | list %}
              {% for item in data.items %}
                {% set res.items = res.items + [ char[item] ] %}
              {% endfor %}
              {{ res.items | join }}
    wx1_wx1_start_a_tue_switch:
      friendly_name: "WX1 Start A Tuesday Switch"
      value_template: >-
          {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
          {% set data = namespace(items=[]) %}
          {% set l = states('var.wx1_start_a_buffer') | list %}
          {% for item in l %}
            {% set data.items = data.items + [ base[item] ] %}
          {% endfor %}
          {% set day = data.items[7] | bitwise_and(32) > 0 %}
          {{ day }}
      availability_template: "{{ states('var.wx1_start_a_buffer') != \"unavailable\" }}"
      turn_on:
        service: localtuya.set_dp
        data:
          device_id: "XXX"
          dp: 110
          value: >-
              {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
              {% set data = namespace(items=[]) %}
              {% set l = states('var.wx1_start_a_buffer') | list %}
              {% for item in l %}
                {% set data.items = data.items + [ base[item] ] %}
              {% endfor %}
              {% set data.items = data.items[:7] + [ (data.items[7] | bitwise_and(223)) + 32 ] + data.items[8:] %}
              {% set res = namespace(items=[]) %}
              {% set char = base.keys() | list %}
              {% for item in data.items %}
                {% set res.items = res.items + [ char[item] ] %}
              {% endfor %}
              {{ res.items | join }}
      turn_off:
        service: localtuya.set_dp
        data:
          device_id: "XXX"
          dp: 110
          value: >-
              {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
              {% set data = namespace(items=[]) %}
              {% set l = states('var.wx1_start_a_buffer') | list %}
              {% for item in l %}
                {% set data.items = data.items + [ base[item] ] %}
              {% endfor %}
              {% set data.items = data.items[:7] + [ (data.items[7] | bitwise_and(223)) ] + data.items[8:] %}
              {% set res = namespace(items=[]) %}
              {% set char = base.keys() | list %}
              {% for item in data.items %}
                {% set res.items = res.items + [ char[item] ] %}
              {% endfor %}
              {{ res.items | join }}
    wx1_wx1_start_a_wed_switch:
      friendly_name: "WX1 Start A Wednesday Switch"
      value_template: >-
          {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
          {% set data = namespace(items=[]) %}
          {% set l = states('var.wx1_start_a_buffer') | list %}
          {% for item in l %}
            {% set data.items = data.items + [ base[item] ] %}
          {% endfor %}
          {% set day = data.items[7] | bitwise_and(16) > 0 %}
          {{ day }}
      availability_template: "{{ states('var.wx1_start_a_buffer') != \"unavailable\" }}"
      turn_on:
        service: localtuya.set_dp
        data:
          device_id: "XXX"
          dp: 110
          value: >-
              {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
              {% set data = namespace(items=[]) %}
              {% set l = states('var.wx1_start_a_buffer') | list %}
              {% for item in l %}
                {% set data.items = data.items + [ base[item] ] %}
              {% endfor %}
              {% set data.items = data.items[:7] + [ (data.items[7] | bitwise_and(239)) + 16 ] + data.items[8:] %}
              {% set res = namespace(items=[]) %}
              {% set char = base.keys() | list %}
              {% for item in data.items %}
                {% set res.items = res.items + [ char[item] ] %}
              {% endfor %}
              {{ res.items | join }}
      turn_off:
        service: localtuya.set_dp
        data:
          device_id: "XXX"
          dp: 110
          value: >-
              {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
              {% set data = namespace(items=[]) %}
              {% set l = states('var.wx1_start_a_buffer') | list %}
              {% for item in l %}
                {% set data.items = data.items + [ base[item] ] %}
              {% endfor %}
              {% set data.items = data.items[:7] + [ (data.items[7] | bitwise_and(239)) ] + data.items[8:] %}
              {% set res = namespace(items=[]) %}
              {% set char = base.keys() | list %}
              {% for item in data.items %}
                {% set res.items = res.items + [ char[item] ] %}
              {% endfor %}
              {{ res.items | join }}
    wx1_wx1_start_a_thu_switch:
      friendly_name: "WX1 Start A Thursday Switch"
      value_template: >-
          {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
          {% set data = namespace(items=[]) %}
          {% set l = states('var.wx1_start_a_buffer') | list %}
          {% for item in l %}
            {% set data.items = data.items + [ base[item] ] %}
          {% endfor %}
          {% set day = data.items[7] | bitwise_and(8) > 0 %}
          {{ day }}
      availability_template: "{{ states('var.wx1_start_a_buffer') != \"unavailable\" }}"
      turn_on:
        service: localtuya.set_dp
        data:
          device_id: "XXX"
          dp: 110
          value: >-
              {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
              {% set data = namespace(items=[]) %}
              {% set l = states('var.wx1_start_a_buffer') | list %}
              {% for item in l %}
                {% set data.items = data.items + [ base[item] ] %}
              {% endfor %}
              {% set data.items = data.items[:7] + [ (data.items[7] | bitwise_and(247)) + 8 ] + data.items[8:] %}
              {% set res = namespace(items=[]) %}
              {% set char = base.keys() | list %}
              {% for item in data.items %}
                {% set res.items = res.items + [ char[item] ] %}
              {% endfor %}
              {{ res.items | join }}
      turn_off:
        service: localtuya.set_dp
        data:
          device_id: "XXX"
          dp: 110
          value: >-
              {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
              {% set data = namespace(items=[]) %}
              {% set l = states('var.wx1_start_a_buffer') | list %}
              {% for item in l %}
                {% set data.items = data.items + [ base[item] ] %}
              {% endfor %}
              {% set data.items = data.items[:7] + [ (data.items[7] | bitwise_and(247)) ] + data.items[8:] %}
              {% set res = namespace(items=[]) %}
              {% set char = base.keys() | list %}
              {% for item in data.items %}
                {% set res.items = res.items + [ char[item] ] %}
              {% endfor %}
              {{ res.items | join }}
    wx1_wx1_start_a_fri_switch:
      friendly_name: "WX1 Start A Friday Switch"
      value_template: >-
          {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
          {% set data = namespace(items=[]) %}
          {% set l = states('var.wx1_start_a_buffer') | list %}
          {% for item in l %}
            {% set data.items = data.items + [ base[item] ] %}
          {% endfor %}
          {% set day = data.items[7] | bitwise_and(4) > 0 %}
          {{ day }}
      availability_template: "{{ states('var.wx1_start_a_buffer') != \"unavailable\" }}"
      turn_on:
        service: localtuya.set_dp
        data:
          device_id: "XXX"
          dp: 110
          value: >-
              {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
              {% set data = namespace(items=[]) %}
              {% set l = states('var.wx1_start_a_buffer') | list %}
              {% for item in l %}
                {% set data.items = data.items + [ base[item] ] %}
              {% endfor %}
              {% set data.items = data.items[:7] + [ (data.items[7] | bitwise_and(251)) + 4 ] + data.items[8:] %}
              {% set res = namespace(items=[]) %}
              {% set char = base.keys() | list %}
              {% for item in data.items %}
                {% set res.items = res.items + [ char[item] ] %}
              {% endfor %}
              {{ res.items | join }}
      turn_off:
        service: localtuya.set_dp
        data:
          device_id: "XXX"
          dp: 110
          value: >-
              {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
              {% set data = namespace(items=[]) %}
              {% set l = states('var.wx1_start_a_buffer') | list %}
              {% for item in l %}
                {% set data.items = data.items + [ base[item] ] %}
              {% endfor %}
              {% set data.items = data.items[:7] + [ (data.items[7] | bitwise_and(251)) ] + data.items[8:] %}
              {% set res = namespace(items=[]) %}
              {% set char = base.keys() | list %}
              {% for item in data.items %}
                {% set res.items = res.items + [ char[item] ] %}
              {% endfor %}
              {{ res.items | join }}
    wx1_wx1_start_a_sat_switch:
      friendly_name: "WX1 Start A Saturday Switch"
      value_template: >-
          {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
          {% set data = namespace(items=[]) %}
          {% set l = states('var.wx1_start_a_buffer') | list %}
          {% for item in l %}
            {% set data.items = data.items + [ base[item] ] %}
          {% endfor %}
          {% set day = data.items[7] | bitwise_and(2) > 0 %}
          {{ day }}
      availability_template: "{{ states('var.wx1_start_a_buffer') != \"unavailable\" }}"
      turn_on:
        service: localtuya.set_dp
        data:
          device_id: "XXX"
          dp: 110
          value: >-
              {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
              {% set data = namespace(items=[]) %}
              {% set l = states('var.wx1_start_a_buffer') | list %}
              {% for item in l %}
                {% set data.items = data.items + [ base[item] ] %}
              {% endfor %}
              {% set data.items = data.items[:7] + [ (data.items[7] | bitwise_and(253)) + 2 ] + data.items[8:] %}
              {% set res = namespace(items=[]) %}
              {% set char = base.keys() | list %}
              {% for item in data.items %}
                {% set res.items = res.items + [ char[item] ] %}
              {% endfor %}
              {{ res.items | join }}
      turn_off:
        service: localtuya.set_dp
        data:
          device_id: "XXX"
          dp: 110
          value: >-
              {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
              {% set data = namespace(items=[]) %}
              {% set l = states('var.wx1_start_a_buffer') | list %}
              {% for item in l %}
                {% set data.items = data.items + [ base[item] ] %}
              {% endfor %}
              {% set data.items = data.items[:7] + [ (data.items[7] | bitwise_and(253)) ] + data.items[8:] %}
              {% set res = namespace(items=[]) %}
              {% set char = base.keys() | list %}
              {% for item in data.items %}
                {% set res.items = res.items + [ char[item] ] %}
              {% endfor %}
              {{ res.items | join }}
```

Finally, to gain access to setting the time, add 2 input_datetime entities via `Settings -> Devices & Services -> Helpers`

1. "WX1 Start A Start Time"
2. "WX1 Start A Runtime"

Ensure they are "Time" only

Then add the following 3 automations, again ensuring to replace dp `110` and device_id `XXX`:

```
- trigger:
  - platform: state
    entity_id:
    - var.start_a_buffer
  condition: []
  action:
  - service: input_datetime.set_datetime
    data:
      time: "{% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6,
        'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P':
        15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23,
        'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g':
        32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40,
        'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x':
        49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57,
        '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %} {% set data = namespace(items=[])
        %} {% set l = states('var.start_a_buffer') | list %} {% for item in
        l %}\n  {% set data.items = data.items + [ base[item] ] %}\n{% endfor %} {%
        set hs = data.items[1] | bitwise_and(15) * 16 + data.items[2] | bitwise_and(60)
        / 4 %} {% set ms = data.items[2] | bitwise_and(3) + data.items[3] %} {{ \"%02d\"
        | format(hs) ~ \":\" ~ \"%02d\" | format(ms) ~ \":00\" }}"
    target:
      entity_id: input_datetime.wx1_start_a_start_time
  - service: input_datetime.set_datetime
    data:
      time: "{% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6,
        'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P':
        15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23,
        'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g':
        32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40,
        'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x':
        49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57,
        '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %} {% set data = namespace(items=[])
        %} {% set l = states('var.start_a_buffer') | list %} {% for item in
        l %}\n  {% set data.items = data.items + [ base[item] ] %}\n{% endfor %} {%
        set h = data.items[4] | bitwise_and(63) * 4 + data.items[5] | bitwise_and(48)
        / 16 %} {% set m = data.items[5] | bitwise_and(15) * 16 + data.items[6] |
        bitwise_and(60) / 4 %} {{ \"%02d\" | format(h) ~ \":\" ~  \"%02d\" | format(m)
        ~ \":00\" }}"
    target:
      entity_id: input_datetime.wx1_start_a_runtime
  mode: single
- trigger:
  - platform: state
    entity_id:
    - input_datetime.wx1_start_a_start_time
  condition:
  - condition: not
    conditions:
    - condition: template
      value_template: "  - \"{{ trigger.to_state.context.id != none }}\"\n  - \"{{
        trigger.to_state.context.parent_id == none }}\"\n  - \"{{ trigger.to_state.context.user_id
        == none }}\""
  action:
  - service: localtuya.set_dp
    data:
      device_id: XXX
      dp: 110
      value: "{% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G':
        6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P':
        15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23,
        'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g':
        32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40,
        'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x':
        49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57,
        '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %} {% set h = states(\"input_datetime.wx1_start_a_start_time\").split(\":\")[0]
        %} {% set m = states(\"input_datetime.wx1_start_a_start_time\").split(\":\")[1]
        | int %} {% set d1 = ( h | int | bitwise_and(240) / 16 ) | int %} {% set d2
        = ( h | int | bitwise_and(15) * 4 ) | int %} {% set data = namespace(items=[])
        %} {% set l = states('var.start_a_buffer') | list %} {% for item in
        l %}\n  {% set data.items = data.items + [ base[item] ] %}\n{% endfor %} {%
        set data.items = [ data.items[0], d1, d2, m ] + data.items[4:] %} {% set res
        = namespace(items=[]) %} {% set char = base.keys() | list %} {% for item in
        data.items %}\n  {% set res.items = res.items + [ char[item] ] %}\n{% endfor
        %} {{ res.items | join }}"
  mode: single
- trigger:
  - platform: state
    entity_id:
    - input_datetime.wx1_start_a_runtime
  condition:
  - condition: not
    conditions:
    - condition: template
      value_template: "  - \"{{ trigger.to_state.context.id != none }}\"\n  - \"{{
        trigger.to_state.context.parent_id == none }}\"\n  - \"{{ trigger.to_state.context.user_id
        == none }}\""
  action:
  - service: localtuya.set_dp
    data:
      device_id: XXX
      dp: 110
      value: "{% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G':
        6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P':
        15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23,
        'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g':
        32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40,
        'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x':
        49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57,
        '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %} {% set h = states(\"input_datetime.wx1_start_a_runtime\").split(\":\")[0]
        %} {% set m = states(\"input_datetime.wx1_start_a_runtime\").split(\":\")[1]
        | int %} {% set d1 = ( h | int | bitwise_and(252) / 4 ) | int %} {% set d2
        = ( h | int | bitwise_and(3) * 16 + m | int | bitwise_and(240) / 16 ) | int
        %} {% set data = namespace(items=[]) %} {% set l = states('var.start_a_buffer')
        | list %} {% for item in l %}\n  {% set data.items = data.items + [ base[item]
        ] %}\n{% endfor %} {% set d3 = ( m | int | bitwise_and(15) * 4) | int + data.items[6]
        | bitwise_and(3) %} {% set data.items = data.items[:4] + [ d1, d2, d3 ] +
        data.items[7:] %} {% set res = namespace(items=[]) %} {% set char = base.keys()
        | list %} {% for item in data.items %}\n  {% set res.items = res.items + [
        char[item] ] %}\n{% endfor %} {{ res.items | join }}"
  mode: single
```

You can add them in the `automations.yaml` file (usually there is a `automation: !include automations.yaml` set up in `configuration.yaml`), or via the UI. If setting up in the UI, use the following setup:

#### 1. WX1 Start A Watcher

Trigger: State
Entity: WX1 Start A Buffer

Conditions: None

Actions:
Call Service input_datetime.set_datetime (in yaml)
```
service: input_datetime.set_datetime
data:
  time: >-
    {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
    {% set data = namespace(items=[]) %}
    {% set l = states('var.wx1_start_a_buffer') | list %}
    {% for item in l %}
      {% set data.items = data.items + [ base[item] ] %}
    {% endfor %}
    {% set hs = data.items[1] | bitwise_and(15) * 16 + data.items[2] | bitwise_and(60) / 4 %}
    {% set ms = data.items[2] | bitwise_and(3) + data.items[3] %}
    {{ "%02d" | format(hs) ~ ":" ~ "%02d" | format(ms) ~ ":00" }}
target:
  entity_id: input_datetime.wx1_start_a_start_time
```
Call Service input_datetime.set_datetime (in yaml)
```
service: input_datetime.set_datetime
data:
  time: >-
    {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
    {% set data = namespace(items=[]) %}
    {% set l = states('var.wx1_start_a_buffer') | list %}
    {% for item in l %}
      {% set data.items = data.items + [ base[item] ] %}
    {% endfor %}
    {% set h = data.items[4] | bitwise_and(63) * 4 + data.items[5] | bitwise_and(48) / 16 %}
    {% set m = data.items[5] | bitwise_and(15) * 16 + data.items[6] | bitwise_and(60) / 4 %}
    {{ "%02d" | format(h) ~ ":" ~  "%02d" | format(m) ~ ":00" }}
target:
  entity_id: input_datetime.wx1_start_a_runtime
```

#### 2. WX1 Start A Start Time Setter

Trigger: State
Entity: WX1 Start A Start Time

Condition: Not
Sub-Condition: Template
```
  - "{{ trigger.to_state.context.id != none }}"
  - "{{ trigger.to_state.context.parent_id == none }}"
  - "{{ trigger.to_state.context.user_id == none }}"
```

Actions:
Call Service localtuya.set_dp (in yaml, replace `XXX` and `110` accordingly)
```
service: localtuya.set_dp
data:
  device_id: XXX
  dp: 110
  value: >-
    {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
    {% set h = states("input_datetime.wx1_start_a_start_time").split(":")[0] %}
    {% set m = states("input_datetime.wx1_start_a_start_time").split(":")[1] | int %}
    {% set d1 = ( h | int | bitwise_and(240) / 16 ) | int %}
    {% set d2 = ( h | int | bitwise_and(15) * 4 ) | int %}
    {% set data = namespace(items=[]) %}
    {% set l = states('var.wx1_start_a_buffer') | list %}
    {% for item in l %}
      {% set data.items = data.items + [ base[item] ] %}
    {% endfor %}
    {% set data.items = [ data.items[0], d1, d2, m ] + data.items[4:] %}
    {% set res = namespace(items=[]) %}
    {% set char = base.keys() | list %}
    {% for item in data.items %}
      {% set res.items = res.items + [ char[item] ] %}
    {% endfor %}
    {{ res.items | join }}
```

#### 2. WX1 Start A Start Runtime Setter

Trigger: State
Entity: WX1 Start A Start Runtime

Condition: Not
Sub-Condition: Template
```
  - "{{ trigger.to_state.context.id != none }}"
  - "{{ trigger.to_state.context.parent_id == none }}"
  - "{{ trigger.to_state.context.user_id == none }}"
```

Actions:
Call Service localtuya.set_dp (in yaml, replace `XXX` and `110` accordingly)
```
service: localtuya.set_dp
data:
  device_id: XXX
  dp: 110
  value: >-
    {% set base = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36, 'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48, 'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60, '9': 61, '+': 62, '/': 63} %}
    {% set h = states("input_datetime.wx1_start_a_runtime").split(":")[0] %}
    {% set m = states("input_datetime.wx1_start_a_runtime").split(":")[1] | int %}
    {% set d1 = ( h | int | bitwise_and(252) / 4 ) | int %}
    {% set d2 = ( h | int | bitwise_and(3) * 16 + m | int | bitwise_and(240) / 16 ) | int %}
    {% set data = namespace(items=[]) %}
    {% set l = states('var.wx1_start_a_buffer') | list %}
    {% for item in l %}
      {% set data.items = data.items + [ base[item] ] %}
    {% endfor %}
    {% set d3 = ( m | int | bitwise_and(15) * 4) | int + data.items[6] | bitwise_and(3) %}
    {% set data.items = data.items[:4] + [ d1, d2, d3 ] + data.items[7:] %}
    {% set res = namespace(items=[]) %}
    {% set char = base.keys() | list %}
    {% for item in data.items %}
      {% set res.items = res.items + [ char[item] ] %}
    {% endfor %}
    {{ res.items | join }}
```

## UI Setup

### Basics

The last step of the setup is in the UI. The following options exist by simply using the correct entities:

1. Add the Watering switch (use the templated switch)
2. Display Irrigation status (use the templated sensor)
3. Display and set Watering time
4. Display Next Watering (Use the templated sensor)
5. Display Schedules A, B, and/or C (use the templated sensor)
6. Display Last Water Flow
7. Display Yesterday's accumulated Water Flow (use the templated sensor)
8. Display and set Rain Delay
9. Display Battery Status (use the templated sensor)
10. Display if Soil Sensor is Present
11. Display and set 24H time format (on the unit's app)
12. Display and set sensor units (on the unit's app)

Yesterday's waterflow is set up so it supports statistics, so water usage can be graphed.

If you have a soil sensor, additionally, you can add these entities:

13. Display Soil Temperature
14. Display Soil Moisture
15. Display if the Sensor Battery Status is OK
16. Last Temperature Read
17. Last Moisture Read

Last Temperature and Moisture Reads also support statistics.

### Advanced Control

If you've set up the control entity templates and automations for a scheduler, you can set them up in the UI. I've used buttons for the days and the enable switch, and the custom [time-picker-card](https://github.com/GeorgeSG/lovelace-time-picker-card) for the start time and runtime, and built a control with vertical and horizontal stacks. Here's the yaml code for a Start A scheduler.

PS: I'm European originally, so I use 24H format, also because it fits better in the layout.

```
type: vertical-stack
cards:
  - type: horizontal-stack
    cards:
      - show_name: true
        show_icon: true
        type: button
        tap_action:
          action: toggle
        entity: switch.wx1_start_a_switch
        name: On/Off
      - type: custom:time-picker-card
        entity: input_datetime.wx1_start_a_start_time
        hour_mode: 24
        hour_step: 1
        minute_step: 1
        layout:
          hour_mode: double
          align_controls: center
          name: header
          thin: true
        hide:
          seconds: true
        name: Start Time
      - type: custom:time-picker-card
        entity: input_datetime.wx1_start_a_runtime
        hour_mode: 24
        hour_step: 1
        minute_step: 1
        layout:
          hour_mode: single
          align_controls: center
          name: header
          embedded: false
          thin: true
        hide:
          seconds: true
          icon: true
          name: false
        name: Runtime
  - type: horizontal-stack
    cards:
      - show_name: true
        show_icon: true
        type: button
        tap_action:
          action: toggle
        entity: switch.wx1_start_a_sun_switch
        name: Sun
      - show_name: true
        show_icon: true
        type: button
        tap_action:
          action: toggle
        entity: switch.wx1_start_a_mon_switch
        name: Mon
      - show_name: true
        show_icon: true
        type: button
        tap_action:
          action: toggle
        entity: switch.wx1_start_a_tue_switch
        name: Tue
      - show_name: true
        show_icon: true
        type: button
        tap_action:
          action: toggle
        entity: switch.wx1_start_a_wed_switch
        name: Wed
      - show_name: true
        show_icon: true
        type: button
        tap_action:
          action: toggle
        entity: switch.wx1_start_a_thu_switch
        name: Thu
      - show_name: true
        show_icon: true
        type: button
        tap_action:
          action: toggle
        entity: switch.wx1_start_a_fri_switch
        name: Fri
      - show_name: true
        show_icon: true
        type: button
        tap_action:
          action: toggle
        entity: switch.wx1_start_a_sat_switch
        name: Sat
```

### Templates

Lastly, some more yaml UI elements so you don't have to click it all together from scratch.

A full display of the standard entities without the sensor installed:

```
type: entities
entities:
  - entity: sensor.wx1_irrigation_status
    name: Irrigation Status
  - entity: switch.wx1_manual_switch
    name: Watering
  - entity: number.manual_watering_setting_mins
    name: Watering Time
  - entity: sensor.wx1_next_watering
    name: Next Watering
    icon: mdi:skip-next
  - entity: sensor.wx1_start_a
    name: Schedule
    icon: mdi:clock-time-eight-outline
  - entity: sensor.last_water_flow
    name: Last Water Flow
  - entity: sensor.wx1_flow_count
    name: Yesterday Water Flow
    icon: mdi:cup-water
  - entity: select.watering_delay
  - entity: sensor.wx1_battery_status
    name: Battery Status
  - entity: binary_sensor.soil_sensor_present
    name: Soil Sensor Present
    icon: mdi:home-assistant
title: Irrigation
state_color: false
```

A full display of the standard entities with the sensor installed:

```
type: entities
entities:
  - entity: sensor.wx1_irrigation_status
    name: Irrigation Status
  - entity: switch.wx1_manual_switch
    name: Watering
  - entity: number.manual_watering_setting_mins
    name: Watering Time
  - entity: sensor.wx1_next_watering
    name: Next Watering
    icon: mdi:skip-next
  - entity: sensor.wx1_start_a
    name: Schedule
    icon: mdi:clock-time-eight-outline
  - entity: sensor.last_water_flow
    name: Last Water Flow
  - entity: sensor.wx1_flow_count
    name: Yesterday Water Flow
    icon: mdi:cup-water
  - entity: select.watering_delay
  - entity: select.24_hour_time
  - entity: select.sensor_units
  - entity: sensor.soil_temperature
    name: Soil Temperature
  - entity: sensor.soil_moisture
    name: Soil Moisture
  - entity: sensor.wx1_battery_status
    name: Battery Status
  - entity: binary_sensor.soil_sensor_power_ok
    name: Soil Sensor Battery OK
    icon: mdi:battery-charging
  - entity: binary_sensor.soil_sensor_present
    name: Soil Sensor Present
    icon: mdi:home-assistant
  - entity: sensor.wx1_temperature_count
    name: Last Temperature Read
  - entity: sensor.wx1_moisture_count
    name: Last Moisture Read
title: Irrigation
state_color: false
```

Graph of recent water usage:

```
chart_type: bar
period: day
days_to_show: 10
type: statistics-graph
entities:
  - sensor.wx1_flow_count
title: Water Usage Per Day
stat_types:
  - state
```

That's all folks.