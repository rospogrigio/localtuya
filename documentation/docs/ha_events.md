# Events
!!! note ""
    Your devices must be added to localtuya to use Events

Localtuya fires an [events](https://www.home-assistant.io/docs/configuration/events/){target="_blank"} on `homeassisstant` 
that can be used on automation or monitoring your device behaviour from [Developer tools -> events](https://my.home-assistant.io/redirect/developer_events/) (1)<Br>
{.annotate}

1. to monitor your device subscribe to any event below and trigger action on the device

With this you can automate `scene remote` (1) devices to trigger action on `homeassistant`
{.annotate}

1. e.g. `single click`, `double click` or `hold`.

| Event                             | Data                                  
| --------------------------------- | ------------------------------------ 
| `localtuya_device_triggered`      | `#!json {"data": {"device_id", "states"} }`                   
| `localtuya_device_dp_triggered`   | `#!json {"data": {"device_id", "dp", "value"} }`              
| `localtuya_states_update`         | `#!json {"data": {"device_id", "old_states", "new_states"} }` 

Exaples 
=== "localtuya_device_triggered"

    ```yaml

    trigger:
      - platform: event
        event_type: localtuya_device_triggered
    condition: []
    action:
      - service: persistent_notification.create
        data:
          message: "{{ trigger.event.data }}"

    ```

=== "localtuya_device_dp_triggered"

    ```yaml title=""
    
    trigger:
      - platform: event
        event_type: localtuya_device_dp_triggered
    condition: []
    action:
      - service: persistent_notification.create
        data:
          message: "{{ trigger.event.data }}"

    ```
    ???+ example "Automation for scene remote trigger if 1st button single clicked"
        ```yaml title=""
        
        trigger:
          - platform: event
            event_type: localtuya_device_dp_triggered
            event_data:
              device_id: bfa2f86e3068440a449dhd
              dp: "1" # quotes are important for dp
              value: single_click 
        condition: []
        action:
          - service: persistent_notification.create
            data:
              message: "{{ trigger.event.data }}"

        ```

=== "localtuya_states_update"

    ```yaml title=""

    trigger:
      - platform: event
        event_type: localtuya_states_update
    condition: []
    action:
      - service: persistent_notification.create
        data:
          message: "{{ trigger.event.data }}"

    ```