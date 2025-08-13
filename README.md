# E-Redes Smart Metering Plus Home Assistant Integration

_Home Assistant integration for E-Redes Smart Metering Plus energy meters in Portugal._

> [!IMPORTANT]  
> This is an independent, community-developed project and is not affiliated with, endorsed by, or connected to E-Redes or any of its subsidiaries. This integration is developed and maintained by volunteers and is not an official E-Redes product or service.

> [!WARNING]  
> **Smart Metering Plus is required**. The meter is provided by E-Redes and, for now, access is limited to a pilot program. Enrollment appears to be closed as E-Redes moves into final testing. Setup details are being tracked in [issue](https://github.com/MiguelTVMS/e-redes-smart-metering-plus-hass/issues/3). If you don’t have a Smart Metering Plus meter or pilot access, this integration will not receive data.

**This integration will set up the following platforms.**

Platform | Description
-- | --
`sensor` | Show info from E-Redes Smart Metering Plus API.

## Features

- 🔄 **Real-time Energy Monitoring** - Receive live data from your E-Redes smart meters
- 🌐 **Cloud Webhook Support** - Automatic secure webhook URL generation with Nabu Casa
- 📊 **Multiple Meter Support** - Handle multiple meters (CPEs) automatically
- ⚡ **Zero Configuration** - No YAML configuration or automation setup required
- 🏠 **Automatic Device Creation** - Devices and sensors created dynamically as data arrives

## Installation

### HACS (Recommended)

1. Ensure that [HACS](https://hacs.xyz/) is installed.
2. Search for and install the "E-Redes Smart Metering Plus" integration.
3. Restart Home Assistant.
4. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "E-Redes Smart Metering Plus".

### Manual Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `e_redes_smart_metering_plus`.
4. Download _all_ the files from the `custom_components/e_redes_smart_metering_plus/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "E-Redes Smart Metering Plus"

## Configuration

1. Add the integration through the Home Assistant UI
2. The integration will automatically create a webhook URL
3. If you have Nabu Casa, a secure cloud URL will be generated automatically
4. Configure your E-Redes energy provider with the webhook URL
5. Start receiving real-time energy data!

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

## Sensors Created

For each unique CPE (meter), the following sensors are automatically created:

- **Instantaneous Active Power Import** (W) - Real-time power consumption
- **Max Active Power Import** (W) - Maximum power imported
- **Active Energy Import** (kWh) - Total energy consumed
- **Instantaneous Active Power Export** (W) - Real-time power generation
- **Max Active Power Export** (W) - Maximum power exported  
- **Active Energy Export** (kWh) - Total energy produced
- **Voltage L1** (V) - Line voltage

## Troubleshooting

### Webhook Not Receiving Data

1. Check that your webhook URL is correctly configured with E-Redes
2. Verify your Home Assistant is accessible from the internet (if using local webhook)
3. Check Home Assistant logs for webhook-related errors

### Multiple Meters

The integration automatically handles multiple meters. Each meter (identified by its unique CPE) will create a separate device with its own set of sensors.

## Contributions are welcome

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)
