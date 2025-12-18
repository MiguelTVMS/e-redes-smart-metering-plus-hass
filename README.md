# E-REDES Smart Metering Plus Home Assistant Integration

_Home Assistant integration for E-REDES Smart Metering Plus energy meters in Portugal._

> [!IMPORTANT]  
> Not affiliated with, sponsored by, or endorsed by **E-REDES – Distribuição de Eletricidade, S.A.** See the full [Disclaimer](DISCLAIMER.md).

> [!WARNING]  
> **Smart Metering Plus is required**. The meter is provided by E-REDES and, for now, access is limited to a pilot program. Enrollment appears to be closed as E-REDES moves into final testing. Setup details are being tracked in [issue](https://github.com/MiguelTVMS/e-redes-smart-metering-plus-hass/issues/3). If you don't have a Smart Metering Plus meter or pilot access, this integration will not receive data.

> [!NOTE]  
> **Version 1.2.0+ Breaking Change**: Starting from version 1.2.0, the webhook URL is now **fixed** and uses a predictable path: `/api/webhook/e_redes_smart_metering_plus`. If you're upgrading from an earlier version, you'll need to update the webhook URL configured in your E-REDES account. The new URL will be displayed in the integration configuration panel.

**This integration will set up the following platforms.**

Platform | Description
-- | --
`sensor` | Show info from E-REDES Smart Metering Plus webhook data.
`number` | Configure breaker limit for monitoring.
`binary_sensor` | Alert when breaker is overloaded.

## Features

- 🔄 **Real-time Energy Monitoring** - Receive live data from your E-REDES smart meters
- 🌐 **Cloud Webhook Support** - Automatic secure webhook URL generation with Nabu Casa
- 📊 **Multiple Meter Support** - Handle multiple meters (CPEs) automatically
- ⚡ **Zero Configuration** - No YAML configuration or automation setup required
- 🏠 **Automatic Device Creation** - Devices and sensors created dynamically as data arrives
- ⚙️ **Breaker Limit Configuration** - Set your breaker capacity per device
- 🔋 **Breaker Load Monitoring** - Real-time monitoring of breaker load percentage
- ⚠️ **Overload Alerts** - Automatic problem sensor when breaker load exceeds 100%

## Installation

### HACS (Recommended)

1. Ensure that [HACS](https://hacs.xyz/) is installed.
2. Search for and install the "E-Redes Smart Metering Plus" integration.
3. Restart Home Assistant.
4. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "E-Redes Smart Metering Plus".

### Manual Installation

1. Using the tool of choice, open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder), create a new folder called `e_redes_smart_metering_plus`.
4. Download _all_ the files from the `custom_components/e_redes_smart_metering_plus/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. In the HA UI, go to "Configuration" -> "Integrations", click "+", and search for "E-Redes Smart Metering Plus"

## Configuration

1. Add the integration through the Home Assistant UI
2. The integration will automatically create a **fixed webhook URL**: `/api/webhook/e_redes_smart_metering_plus`
3. If you have Nabu Casa, a secure cloud URL will be generated automatically using the same fixed webhook ID.
4. Configure your E-REDES account with the webhook URL (self-service configuration is not yet available for general users).
5. Start receiving real-time energy data!

### Webhook URL Format

- **Local URL**: `http://your-home-assistant:8123/api/webhook/e_redes_smart_metering_plus`
- **Nabu Casa URL**: `https://your-instance.ui.nabu.casa/api/webhook/e_redes_smart_metering_plus` (generated automatically if you have Home Assistant Cloud)

The webhook URL uses a **fixed path** that doesn't change between restarts, making it easier to configure with E-REDES.

## Webhook Data Format

The integration expects webhook data in the following JSON format:

```json
{
    "clock": "2025-08-01 12:41:10",
    "cpe": "PT000XXXXXXXXXXXXXXX",
    "instantaneousActivePowerImport": 85.85,
    "maxActivePowerImport": 85.75,
    "maxActivePowerImportTime": "2024-04-29 12:41:10",
    "activeEnergyImport": 198114.34,
    "instantaneousActivePowerExport": 64.93,
    "maxActivePowerExport": 96.86,
    "maxActivePowerExportTime": "2024-04-29 12:41:10",
    "activeEnergyExport": 612865.24,
    "voltageL1": 231.58
}
```

## Entities Created

For each unique CPE (meter), the following entities are automatically created:

### Sensors

- **Instantaneous Active Power Import** (W) - Real-time power consumption
- **Max Active Power Import** (W) - Maximum power imported
- **Active Energy Import** (Wh) - Total energy consumed (Home Assistant converts to kWh automatically)
- **Instantaneous Active Power Export** (W) - Real-time power generation
- **Max Active Power Export** (W) - Maximum power exported  
- **Active Energy Export** (Wh) - Total energy produced (Home Assistant converts to kWh automatically)
- **Voltage L1** (V) - Line voltage
- **Instantaneous Active Current Import** (A) - Calculated current (Power / Voltage)
- **Breaker Load** (%) - Current load relative to breaker limit
- **Breaker Overload** - Problem sensor that alerts when breaker load exceeds 100%

### Configuration

- **Breaker Limit** (A) - Configurable breaker capacity (default: 20A, range: 1-200A)

### Diagnostic Sensors

> [!NOTE]
> Diagnostic sensors are **disabled by default**. Enable them in the device page if you need to monitor webhook activity.

- **Last Update** - Timestamp of the last webhook received (displays as "X seconds/minutes/hours ago")
- **Update Interval** (s) - Time between consecutive webhook updates in seconds

These sensors help you monitor the health of your webhook connection and identify any issues with data delivery.

## Troubleshooting

### Webhook Not Receiving Data

1. Check that your webhook URL is correctly configured with E-REDES
2. Verify your Home Assistant is accessible from the internet (if using local webhook)
3. Check Home Assistant logs for webhook-related errors

### Multiple Meters

The integration automatically handles multiple meters. Each meter (identified by its unique CPE) will create a separate device with its own set of sensors.

## Contributions are welcome

If you want to contribute, please read the [Contribution Guidelines](CONTRIBUTING.md)

### Development Tools

- 🪝 **Pre-commit Hook** - Automatic code quality checks before each commit. See [Pre-commit Hook Documentation](docs/PRE_COMMIT_HOOK.md) for details.

## Legal

[Disclaimer](DISCLAIMER.md)  
[License](LICENSE)
