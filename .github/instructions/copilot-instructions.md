---
applyTo: '**'
---

# E-Redes Smart Metering Plus Home Assistant Integration

## Project Description

This is a Home Assistant integration for the E-Redes Smart Metering Plus energy meters in Portugal. It allows users to monitor and manage their energy consumption through the Home Assistant platform. The Smart Metering Plus system provides real-time data on energy usage, enabling users to make informed decisions about their energy consumption. This data is delivered via a webhook that should be received by Home Assistant using a public URL. If the user has an active Nabu Casa subscription, the integration should make use of the public webhook URL provided automatically by Home Assistant Cloud.

This integration is fully automatic. When the user installs it, it creates a webhook URL and begins listening for data without requiring any manual YAML configuration or automation setup. Webhook data is processed in real time, and a new device is created for each unique CPE (meter) detected.

## Webhook Format

```json
{
  "cpe": "PT000XXXXXXXXXXXXXXX",
  "SourceTimestamp": "2025-09-24 18:33:20",
  "activeEnergyExport": 0,
  "activeEnergyImport": 14817930,
  "instantaneousActivePowerExport": 0,
  "instantaneousActivePowerImport": 2518,
  "maxActivePowerExport": 0,
  "maxActivePowerExportTime": "0000-00-00 00:00:00",
  "maxActivePowerImportTotalLastAverage": 3680,
  "maxActivePowerImportTotalTime": "2025-09-09 11:45:00",
  "voltageL1": 237.1,
  "clock": "2025-09-24 19:33:20"
}
```

### Attention:
The fields activeEnergyImport and activeEnergyExport are cumulative values in Wh (Watt-hour). The instantaneousActivePowerImport and instantaneousActivePowerExport fields represent the current power in W (Watt). The voltageL1 field represents the voltage in V (Volts).

**Note:**
The user may have **multiple meters**, each uniquely identified by the `cpe` field.
All webhook requests will be sent to the **same endpoint**, but the integration must dynamically create and update **separate devices and entities** for each unique `cpe` value.

## Copilot Instructions

Copilot should help the developer build the following features for this custom Home Assistant integration:

### 1. Component Structure

Create a custom integration under `custom_components/e_redes_smart_metering_plus/`.
Implement the following files:

* `__init__.py`: Setup logic
* `manifest.json`: Integration metadata
* `sensor.py`: Dynamic sensor entities
* `webhook.py`: Webhook registration and data processing
* `config_flow.py`: Optional UI configuration for Nabu Casa detection

### 2. Webhook Handling

* Automatically register a webhook using `webhook.async_register()` with a **fixed webhook ID** (`e_redes_smart_metering_plus`).
* The webhook URL should be **predictable and consistent** across restarts: `/api/webhook/e_redes_smart_metering_plus`
* If the `cloud` integration is active, generate a public webhook URL with `cloud.async_create_cloudhook()` using the same fixed webhook ID.
* If not, fall back to a local URL and optionally display instructions to expose it.
* Each incoming request should:

  * Identify the `cpe` from the payload
  * If no matching device exists, create one dynamically
  * Register sensor entities (one per metric)
  * Update the states of those entities with the incoming values
* No user automation or YAML configuration should be required.
* Use `WEBHOOK_ID = DOMAIN` constant from `const.py` to ensure consistency.

### 3. Sensors to Create

Create sensor entities for each CPE:

* `instantaneous_active_power_import` (W)
* `max_active_power_import` (W)
* `active_energy_import` (kWh)
* `instantaneous_active_power_export` (W)
* `max_active_power_export` (W)
* `active_energy_export` (kWh)
* `voltage_l1` (V)

Each sensor should:

* Belong to a device associated with its `cpe`
* Have a unique entity ID (e.g., `sensor.e_redes_PT000XYZ_power_import`)
* Use correct `device_class`, `state_class`, and `unit_of_measurement`
* Be updated live via the webhook handler

### 4. Cloud Support (Nabu Casa)

* Detect whether the `cloud` integration is loaded
* Use `cloud.async_create_cloudhook()` to generate a secure public webhook URL
* Display this URL in the integration configuration panel
* Allow users to copy it or configure their energy provider with it

### 5. Options Flow (Optional)

Allow the user to:

* View the webhook URL
* Force regeneration (e.g., reset if compromised)
* Choose Nabu Casa vs local fallback

### 6. HACS Compatibility

Ensure HACS compatibility:

* Include and keep `./hacs.json` updated based on the specifications in the [HACS documentation](https://www.hacs.xyz/docs/publish/start/#hacsjson).

### 7. Testing

Copilot should assist in writing tests for:

* Webhook handler logic
* Sensor creation and updates
* Multi-CPE device management
* Cloudhook registration logic

Use `pytest` with mocks for webhook events.
All the tests should be in the `tests` directory.

### 8. Dev Tools

Support modern Python tooling:
* All development will be done based on Home Assistant version 2025.6.1.
* Devcontainers using `.devcontainer/devcontainer.json` for VSCode with python 3.13 and without virtual environments.
* All the development requirements should be in `requirements_dev.txt`
* GitHub Actions workflow for HACS lint + Tests

## Documentation to help Copilot

[Home Assistant Developer Documentation](https://developers.home-assistant.io/docs)
[HACS Documentation](https://www.hacs.xyz/docs/publish/start).