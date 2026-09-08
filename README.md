# Climastar Avant WiFi for Home Assistant

Control Climastar Avant WiFi electric heaters from Home Assistant. The integration connects to the same cloud service as the official Climastar Avant WiFi app, discovers the account's gateways and heaters automatically, and exposes each installed heater as a native climate entity.

No API key, gateway ID, serial number, or developer credentials are required.

> [!WARNING]
> This is an independent community integration. It is not affiliated with or endorsed by Climastar.

## What it provides

- A `climate` entity for every installed heater, with current temperature, target temperature, 0.5 °C setpoint steps, and live **Heating** / **Idle** state.
- Automatic discovery of multiple gateways and heaters in one account.
- Cloud-push updates with reconnect handling; it does not continuously poll the service.
- Sensible availability: a disconnected gateway or a lost/uninstalled heater becomes unavailable without deleting its entity history.
- Read-only diagnostic sensors for PCB temperature, rated power, duty, and error code.
- Window-open and presence binary sensors when the heater reports those values.
- Home Assistant UI configuration and reauthentication.

## Important behavior

Changing the target temperature uses the verified native `modified_auto` behavior of the official app. The cloud's next push update is treated as the source of truth, so the interface may briefly show the prior target after a change.

The integration deliberately does **not** run a thermostat or heating strategy of its own. Use Home Assistant automations, schedules, window sensors, occupancy sensors, weather, or an external thermostat to decide when and how to change a heater's target temperature.

## Energy Dashboard

The verified cloud API reports configured/rated heater power, not cumulative energy use or live electrical draw. For that reason, this integration does not provide an Energy Dashboard source: deriving kWh from rated power would be inaccurate. Use an energy-capable plug or electrical meter if you need consumption reporting.

## Not supported yet

The following controls are intentionally absent because their cloud write behavior has not been verified:

- Schedules, away mode, comfort/eco/frost modes, and program editing
- Boost, lock, True Radiant, and window-detection configuration
- Power-limit configuration
- A manual on/off or HVAC-mode control

Reliability takes priority over presenting controls that may not operate safely or as expected.

## Installation

### HACS

1. In Home Assistant, open **HACS → Integrations**.
2. Select the **⋮** menu, then **Custom repositories**.
3. Add `https://github.com/mbayon/hass-climastar-avant` and choose **Integration** as the category.
4. Find **Climastar Avant WiFi** in HACS and select **Download**.
5. Restart Home Assistant.

### Manual installation

1. Copy the `custom_components/climastar_avant` directory from this repository to your Home Assistant configuration directory:

   ```text
   <config>/custom_components/climastar_avant
   ```

2. Restart Home Assistant.

## Initial setup

1. Go to **Settings → Devices & services → Add integration**.
2. Search for **Climastar Avant WiFi**.
3. Enter the email address and password used in the official Avant WiFi app.
4. Home Assistant discovers the gateways and heaters in the account.

Each gateway is added as a Home Assistant device. Each heater is a separate device associated with its gateway. Renaming a heater in the official app does not change its stable Home Assistant identity.

## Updating with HACS

After a new version is merged to the repository's default branch:

1. Open **HACS → Integrations → Climastar Avant WiFi**.
2. Open the **⋮** menu and choose **Update information** to force a GitHub refresh.
3. If an update is offered, select **Redownload**.
4. Restart Home Assistant.

## Reauthentication

If the cloud rejects the saved session or account credentials, Home Assistant creates a reauthentication repair. Open the repair and enter the current Avant WiFi account credentials. You do not need to remove the integration or edit files.

## Troubleshooting

- **Entity unavailable:** Verify the gateway is connected in the official app and that the heater is installed and not marked as lost. A temporary cloud outage also makes entities unavailable while retaining their last known data.
- **Integration is not listed after installation:** Restart Home Assistant. If needed, clear the browser cache before using **Add integration**.
- **Temperature change does not appear immediately:** The REST response is only an acknowledgement; wait for the cloud push update from the heater.

### Debug logging

Add the following to `configuration.yaml`, then restart Home Assistant:

```yaml
logger:
  default: info
  logs:
    custom_components.climastar_avant: debug
```

Debug logging and downloaded diagnostics intentionally omit passwords, access tokens, refresh tokens, authorization headers, and location information. When opening an issue, include the Home Assistant version, integration version, sanitized diagnostics, and relevant debug log lines.

## Support

Please report reproducible problems in the [GitHub issue tracker](https://github.com/mbayon/hass-climastar-avant/issues). Do not include credentials, tokens, HAR files, or private location information in an issue.
