# Setup and Configuration Guide

## Prerequisites

- Home Assistant Core 2024.6.0 or newer
- Access to your E-Redes energy provider dashboard to configure webhooks
- (Optional) Nabu Casa subscription for automatic cloud webhook URLs

## Installation

### Method 1: HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add `https://github.com/migueltvms/e-redes-smart-metering-plus-hass` as an Integration
6. Install "E-Redes Smart Metering Plus"
7. Restart Home Assistant

### Method 2: Manual Installation

1. Download the latest release from GitHub
2. Extract the `custom_components/e_redes_smart_metering_plus` directory to your Home Assistant `custom_components` folder
3. Restart Home Assistant

## Configuration

### Step 1: Add the Integration

1. Go to **Settings** → **Devices & Services**
2. Click **+ ADD INTEGRATION**
3. Search for "E-Redes Smart Metering Plus"
4. Click on the integration to add it

### Step 2: Webhook URL

After adding the integration, you'll get a webhook URL:

- **With Nabu Casa**: Secure cloud URL (recommended)

  ```text
  https://hooks.nabu.casa/your-unique-id
  ```

- **Without Nabu Casa**: Local URL (requires port forwarding)

  ```text
  https://your-home-assistant-url:8123/api/webhook/your-integration-id
  ```

### Step 3: Configure E-Redes Provider

1. Log into your E-Redes energy provider dashboard
2. Navigate to smart meter settings or webhook configuration
3. Enter the webhook URL provided by Home Assistant
4. Save the configuration

## Usage Examples

### Basic Energy Monitoring Dashboard

Create a dashboard card to monitor your energy consumption:

```yaml
type: entities
title: Energy Monitoring
entities:
  - entity: sensor.e_redes_pt000xxxxxxxxxxxxxxx_instantaneous_active_power_import
    name: Current Power Usage
  - entity: sensor.e_redes_pt000xxxxxxxxxxxxxxx_active_energy_import  
    name: Total Energy Import
  - entity: sensor.e_redes_pt000xxxxxxxxxxxxxxx_instantaneous_active_power_export
    name: Current Power Export
  - entity: sensor.e_redes_pt000xxxxxxxxxxxxxxx_active_energy_export
    name: Total Energy Export
```

### Power vs Time Chart

```yaml
type: history-graph
title: Power Usage History
entities:
  - sensor.e_redes_pt000xxxxxxxxxxxxxxx_instantaneous_active_power_import
  - sensor.e_redes_pt000xxxxxxxxxxxxxxx_instantaneous_active_power_export
hours_to_show: 24
refresh_interval: 60
```

### Energy Statistics Card

```yaml
type: statistics-graph
title: Energy Statistics
entities:
  - sensor.e_redes_pt000xxxxxxxxxxxxxxx_active_energy_import
  - sensor.e_redes_pt000xxxxxxxxxxxxxxx_active_energy_export
period: day
stat_types:
  - change
```

### Automation Examples

#### High Power Usage Alert

```yaml
automation:
  - alias: "High Power Usage Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.e_redes_pt000xxxxxxxxxxxxxxx_instantaneous_active_power_import
        above: 3000  # 3kW
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "High Power Usage"
          message: "Current power usage is {{ states('sensor.e_redes_pt000xxxxxxxxxxxxxxx_instantaneous_active_power_import') }}W"
```

#### Daily Energy Report

```yaml
automation:
  - alias: "Daily Energy Report"
    trigger:
      - platform: time
        at: "23:00:00"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "Daily Energy Report"
          message: |
            Today's energy usage:
            Import: {{ states('sensor.e_redes_pt000xxxxxxxxxxxxxxx_active_energy_import') }} kWh
            Export: {{ states('sensor.e_redes_pt000xxxxxxxxxxxxxxx_active_energy_export') }} kWh
```

## Troubleshooting

### Common Issues

#### Webhook Not Receiving Data

**Symptoms**: No sensor data updates, entities show "unavailable"

**Solutions**:

1. Check webhook URL configuration in E-Redes dashboard
2. Verify Home Assistant is accessible from the internet
3. Check Home Assistant logs for webhook errors:

   ```text
   Settings → System → Logs
   Search for: e_redes_smart_metering_plus
   ```

#### Multiple Meters Not Showing

**Symptoms**: Only one meter appears despite having multiple CPEs

**Solutions**:

1. Verify each meter is sending data with unique CPE identifiers
2. Check logs for webhook data reception
3. Ensure each meter is properly configured in E-Redes dashboard

#### Sensor Values Not Updating

**Symptoms**: Sensors exist but values don't change

**Solutions**:

1. Enable debug logging (see below)
2. Check webhook data format matches expected structure
3. Verify meter is actively sending data

### Debug Logging

Add to your `configuration.yaml`:

```yaml
logger:
  default: warn
  logs:
    custom_components.e_redes_smart_metering_plus: debug
```

Then restart Home Assistant and check logs for detailed information.

### Webhook Testing

You can test your webhook manually using curl:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "clock": "2025-08-01 12:41:10",
    "cpe": "PT000TESTXXXXXXXXXX",
    "instantaneousActivePowerImport": 1500.5,
    "activeEnergyImport": 12345.67
  }' \
  "YOUR_WEBHOOK_URL_HERE"
```

## Advanced Configuration

### Custom Sensor Names

Sensors are automatically named based on the CPE identifier. If you want custom names, you can rename them in:

**Settings** → **Devices & Services** → **E-Redes Smart Metering Plus** → Click on device → Rename entities

### Integration with Energy Dashboard

1. Go to **Settings** → **Dashboards** → **Energy**
2. Add your energy sensors:
   - **Grid consumption**: `sensor.e_redes_pt000xxxxxxxxxxxxxxx_active_energy_import`
   - **Return to grid**: `sensor.e_redes_pt000xxxxxxxxxxxxxxx_active_energy_export`

### Multiple Homes/Locations

If you have meters in multiple locations, each will appear as a separate device with its own CPE identifier.

## Support

For issues and questions:

- Check the [GitHub Issues](https://github.com/migueltvms/e-redes-smart-metering-plus-hass/issues)
- Join the discussion in [Home Assistant Community](https://community.home-assistant.io/)
- Read the [Contributing Guide](../CONTRIBUTING.md) if you want to help improve the integration
