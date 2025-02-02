# Cloud API Setup

The Tuya integration integrates all Powered by Tuya devices you have added to the Tuya Smart and Tuya Smart Life apps.

!!! note
    LocalTuya utilizes the cloud to gather your device's data, making the configuration of devices much simpler.

## Configuration of the Tuya IoT Platform

### Prerequisites

- Your devices need first to be added in the [Tuya Smart or Smart Life app](https://developer.tuya.com/docs/iot/tuya-smart-app-smart-life-app-advantages?id=K989rqa49rluq#title-1-Download){target="_blank"}.
- You will also need to create an account in the [Tuya IoT Platform](https://iot.tuya.com/){target="_blank"}.
This is a separate account from the one you made for the app. You cannot log in with your app's credentials.

### Create a project

1. Log in to the [Tuya IoT Platform](https://iot.tuya.com/){target="_blank"}.
2. In the left navigation bar, click `Cloud` > `Development`. 
3. On the page that appears, click `Create Cloud Project`.
4. In the `Create Cloud Project` dialog box, configure `Project Name`, `Description`, `Industry`, and `Data Center`. For the `Development Method` field, select `Smart Home` from the dropdown list. For the `Data Center` field, select the zone you are located in. Refer to the country/data center mapping list [here](https://github.com/tuya/tuya-home-assistant/blob/main/docs/regions_dataCenters.md){target="_blank"} to choose the right data center for the country you are in.

    ![](https://www.home-assistant.io/images/integrations/tuya/image_001.png)

5. Click `Create` to continue with the project configuration.
6. In Configuration Wizard, make sure you add `Industry Basic Service`, `Smart Home Basic Service` and `Device Status Notification` APIs. The list of API should look like this:
  ![](https://www.home-assistant.io/images/integrations/tuya/image_002new.png)
7. Click `Authorize`.

### Link devices by app account

1. Navigate to the `Devices` tab.
2. Click `Link Tuya App Account` > `Add App Account`.
  ![](https://www.home-assistant.io/images/integrations/tuya/image_003.png)
3. Scan the QR code that appears using the `Tuya Smart` app or `Smart Life` app using the 'Me' section of the app.

    ![](https://www.home-assistant.io/images/integrations/tuya/image_004.png)

4. Click `Confirm` in the app.
5. To confirm that everything worked, navigate to the `All Devices` tab. Here you should be able to find the devices from the app.
6. If zero devices are imported, try changing the DataCenter and check the account used is the "Home Owner".
   You can change DataCenter by clicking the Cloud icon on the left menu, then clicking the Edit link in the Operation column for your newly created project. You can change DataCenter in the popup window.

![](https://www.home-assistant.io/images/integrations/tuya/image_005.png)

### Get authorization data

Click the created project to enter the `Project Overview` page and get the `Authorization Key`. You will need these for setting up the integration. in the next step.

![](images/tuya_iot_overview.png)

  `Data center region`: 
    Choose the country you picked when signing up.

  `Client ID`:
    Go to your cloud project on [Tuya IoT Platform](https://iot.tuya.com/){target="_blank"}. in the **Overview** tab.

  `Client Secret`:
    Go to your cloud project on [Tuya IoT Platform](https://iot.tuya.com/){target="_blank"}. in the **Overview** tab.

### Get USER ID
  Navigate to the `Devices` tab -> click on `Link Tuya App Account` Copy `UID <- is User ID`.

  ![](https://user-images.githubusercontent.com/46300268/246021288-25d56177-2cc1-45dd-adb0-458b6c5a25f3.png)

## Error codes and troubleshooting



??? info "1004: sign invalid"
    Incorrect Access ID or Access Secret. Please refer to the **Configuration** part above.

??? info "1106: permission deny"
    - App account not linked with cloud project: On the [Tuya IoT Platform](https://iot.tuya.com/cloud/), you have linked devices by using Tuya Smart or Smart Life app in your cloud project. For more information, see [Link devices by app account](https://developer.tuya.com/docs/iot/Platform_Configuration_smarthome?id=Kamcgamwoevrx#title-3-Link%20devices%20by%20app%20account){target="_blank"}.

    - Incorrect username or password: Enter the correct account and password of the Tuya Smart or Smart Life app in the **Account** and **Password** fields (social login, which the Tuya Smart app allows, may not work, and thus should be avoided for use with the Home Assistant integration). Note that the app account depends on which app (Tuya Smart or Smart Life) you used to link devices on the [Tuya IoT Platform](https://iot.tuya.com/cloud/).

    - Incorrect country. You must select the region of your account of the Tuya Smart app or Smart Life app.    

??? info "1100: param is empty"
    Empty parameter of username or app. Please fill the parameters refer to the **Configuration** part above.

??? info "2406: skill id invalid"
    - Make sure you use the **Tuya Smart** or **SmartLife** app account to log in. Also, choose the right data center endpoint related to your country region. For more details, please check [Country Regions and Data Center](https://github.com/tuya/tuya-home-assistant/blob/main/docs/regions_dataCenters.md). 
    
    - Your cloud project on the [Tuya IoT Development Platform](https://iot.tuya.com) should be created after May 25, 2021. Otherwise, you need to create a new project. 

    - This error can often be resolved by unlinking the app from the project (`Devices` tab > `Link Tuya App Account` > `Unlink`) and [relinking it again](#link-devices-by-app-account).

??? info "28841105: No permissions. This project is not authorized to call this API"
    Some APIs are not authorized, please [Subscribe](https://developer.tuya.com/docs/iot/applying-for-api-group-permissions?id=Ka6vf012u6q76#title-2-Subscribe%20to%20APIs){target="_blank"} then [Authorize](https://developer.tuya.com/docs/iot/applying-for-api-group-permissions?id=Ka6vf012u6q76#title-3-Grant%20a%20project%20access%20to%20API%20calls){target="_blank"}. The following APIs must be subscribed for this tutorial:

        - Device Status Notification

        - Industry Basic Service

        - Smart Home Basic Service
        
        - Authorization

        - IoT Core

        - Smart Home Scene Linkage

        - IoT Data Analytics

??? info "28841002: No permissions. Your subscription to cloud development plan has expired"
    Your subscription to Tuya cloud development **IoT Core Service** resources has expired, please [extend it](https://iot.tuya.com/cloud/products/detail?abilityId=1442730014117204014){target="_blank"} in `Cloud` > `Cloud Services` > `IoT Core` > `My Subscriptions` tab > `Subscribed Resources` > `IoT Core` > `Extend Trial Period`. 

## Document source
[Home Assistant Tuya](https://www.home-assistant.io/integrations/tuya/){target="_blank"}