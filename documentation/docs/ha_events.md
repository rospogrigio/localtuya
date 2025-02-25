# Events
!!! note ""
    Your device must be added to localtuya to use Events

Localtuya fires an [events](https://www.home-assistant.io/docs/configuration/events/){target="_blank"} on `homeassisstant` 
that can be used on automation or monitoring your device behaviour from [Developer tools -> events](https://my.home-assistant.io/redirect/developer_events/){target="_blank"} (1)<Br>
{.annotate}

1. to monitor your device subscribe to any event below and trigger action on the device using tuya app


!!! annotate tip ""
    With this you can automate devices such as `scene remote` (1) to trigger an action on `homeassistant`

1. e.g. `single click`, `double click` or `hold`.

| Event                             | Data                                  
| --------------------------------- | ------------------------------------ 
| `localtuya_status_update`         | `#!json {"data": {"device_id", "old_status", "new_status"} }` 
| `localtuya_device_dp_triggered`   | `#!json {"data": {"device_id", "dp", "value"} }`              


Examples 
=== "localtuya_states_update"

    ```yaml title=""
    # This will only triggers if status changed.
    trigger:
      - platform: event
        event_type: localtuya_status_update
    condition: []
    action:
      - service: persistent_notification.create
        data:
          message: "{{ trigger.event.data }}"

    ```

=== "localtuya_device_dp_triggered"

    ```yaml title=""
    # This will always triggers if DP used.
    trigger:
      - platform: event
        event_type: localtuya_device_dp_triggered
    condition: []
    action:
      - service: persistent_notification.create
        data:
          message: "{{ trigger.event.data }}"

    ```
    ??? example "example of an automation to trigger a scene when the first button on a remote is single-clicked"
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

!!! annotate warning "Database flooding"
    If the recorder is enabled, devices like temperature sensors may update frequently (e.g., every second). 
    This can cause excessive events and significantly increase database size. 
    It is recommended to exclude _localtuya_ events from the recorder to prevent database overload.
    !!! annotate tip ""
        ```yaml title=""
        recorder:
          exclude:
            event_types:
              - localtuya_status_update
              - localtuya_device_dp_triggered
        ```