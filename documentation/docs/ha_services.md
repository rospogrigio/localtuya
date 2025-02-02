# Services


| Service     | Data                                                     | Description                         
| ----------- | ---------------------------------------------------------|-------------------------------------
| `localtuya.reload`   |                                                 | Reload All `localtuya` entries
| `localtuya.set_dp`   | `#!json {"data": {"device_id", "dp", "value"}}` | Set new value for one `DP` or multi 


=== "Set DP Service"

    ```yaml title="Change the value of DP 1"
    service: localtuya.set_dp
    data:
      device_id: 11100118278aab4de001
      dp: 1
      value: true
    ```
    <br>
    ```yaml title="Change the values for multi DPs"
    service: localtuya.set_dp
    data:
      device_id: 11100118278aab4de001 #(1)!
      value:
        "1": true  # (2)!
        "2": true  # (3)!
        "3": false # (4)!
    ```
    
    1. Device with this ID must be added into `localtuya`
    2. Set `DP 1` Value to `true`
    3. Set `DP 2` Value to `true`
    4. Set `DP 3` Value to `false`

=== "Reload Service"
    Reload all `LocalTuya` Entries
    ```yaml 
    service: localtuya.reload
    ```
