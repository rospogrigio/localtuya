# Services


| Service     | Data                                                     | Description                         
| ----------- | ---------------------------------------------------------|-------------------------------------
| `localtuya.reload`          |                                                 | Reload All `localtuya` entries
| `localtuya.set_dp`          | `#!json {"data": {"device_id", "dp", "value"}}` | Set new value for one `DP` or multi 
| `localtuya.remote_add_code` | `#!json {"data": {"target", "device_name", "command_name", "base64", "head", "key" }}` | Manually add code into remote device. 


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

=== "Add Remote Code"
    Add a TV button using `head/key` or `base64`
    ```yaml 
    action: localtuya.remote_add_code
    data:
      target: c187a2102cb1e38161377eb4d4afb6f7
      device_name: TV
      command_name: volume_up
      head: "11111111111" # Head: Can be obtain from Tuya IoT device debug logs.
      key: "223123" # Key: Can be obtain from Tuya IoT device debug logs.
    ```
