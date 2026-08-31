# E-REDES Smart Metering Plus Home Assistant Integration

_Home Assistant integration for E-REDES Smart Metering Plus energy meters in Portugal._

> [!IMPORTANT]  
> Not affiliated with, sponsored by, or endorsed by **E-REDES – Distribuição de Eletricidade, S.A.** See the full [Disclaimer](DISCLAIMER.md).

> [!WARNING]  
> **Smart Metering Plus is required**. The meter is provided by E-REDES and, for now, access is limited to a pilot program. Enrollment appears to be closed as E-REDES moves into final testing. Setup details are being tracked in [issue](https://github.com/MiguelTVMS/e-redes-smart-metering-plus-hass/issues/3). If you don't have a Smart Metering Plus meter or pilot access, this integration will not receive data.

> [!NOTE]  
> The webhook uses the fixed path `/api/webhook/e_redes_smart_metering_plus`. Configure every CPE that is allowed to use it. During upgrade, CPEs from existing integration devices are added automatically so their updates continue.

**This integration will set up the following platforms.**

Platform | Description
-- | --
`sensor` | Show info from E-REDES Smart Metering Plus webhook data.
`number` | Configure breaker limit for monitoring.
`binary_sensor` | Alert when breaker is overloaded.

## Features

- 🔄 **Real-time Energy Monitoring** - Receive live data from your E-REDES smart meters
- 🌐 **Cloud Webhook Support** - Automatic secure webhook URL generation with Nabu Casa
- 📊 **Multiple Meter Support** - Allow one or more known meters by CPE
- ⚡ **UI Configuration** - No YAML configuration or automation setup required
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
2. Add every complete CPE that should be accepted. You can edit this list later without removing existing CPEs.
3. The integration creates the fixed webhook path `/api/webhook/e_redes_smart_metering_plus`.
4. Open **Settings > Devices & services**, select the integration, then **Configure** to copy the active URL. With Home Assistant Cloud connected, this shows the Cloudhook URL.
5. Configure E-REDES with that URL and start receiving data.

### Webhook URL Format

- **Local URL**: `http://your-home-assistant:8123/api/webhook/e_redes_smart_metering_plus`
- **Home Assistant Cloud URL**: `https://hooks.nabu.casa/...` (generated automatically when Home Assistant Cloud is connected)

Reloading or restarting the integration reuses the existing Cloudhook. The Cloudhook is deleted only when the integration entry is removed.

> [!CAUTION]
> The CPE allowlist prevents other meter identifiers from creating or updating entities, but it is not sender authentication. The public E-REDES page mentions HTTP header authentication without publishing the header format. This integration does not guess or enforce an undocumented header.

## Webhook Data Format

The integration supports the current E-REDES single-phase and three-phase payloads. The current single-phase example is:

```json
{
    "LocalTimestamp": "2026-08-01 12:41:10",
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

Legacy timestamps (`SourceTimestamp` and `clock`) and the legacy `maxActivePowerImportTotalLastAverage` field remain supported. Three-phase payloads can also create voltage L2/L3 and per-phase import/export power sensors. See the [official E-REDES Smart Metering Plus documentation](https://www.e-redes.pt/en/smart-metering-plus).

Supported values are processed even when optional fields are missing or new unsupported fields appear. The integration warns when the payload field set changes.

## Entities Created

For each unique CPE (meter), the following entities are automatically created:

### Sensors

- **Instantaneous Active Power Import** (W) - Real-time power consumption
- **Max Active Power Import** (W) - Maximum power imported
- **Active Energy Import** (Wh) - Total energy consumed (Home Assistant converts to kWh automatically)
- **Instantaneous Active Power Export** (W) - Real-time power generation
- **Max Active Power Export** (W) - Maximum power exported  
- **Active Energy Export** (Wh) - Total energy produced (Home Assistant converts to kWh automatically)
- **Voltage L1/L2/L3** (V) - Available phase voltages
- **Per-phase Instantaneous Active Power Import/Export** (W) - Created when supplied by a three-phase meter
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

To capture the first accepted payload after each restart and validate its fields, temporarily enable debug logging:

```yaml
logger:
  logs:
    custom_components.e_redes_smart_metering_plus: debug
```

The complete first payload for each configured CPE is written at debug level. It may contain meter identifiers and energy data, so disable debug logging after validation and remove sensitive values before sharing logs.

### Multiple Meters

Add every meter in the integration's **Configure** dialog. Each allowed CPE creates a separate device and set of entities when data arrives. Requests for CPEs outside this list receive HTTP 403.

## Contributions are welcome

If you want to contribute, please read the [Contribution Guidelines](CONTRIBUTING.md)

### Development Tools

- 🪝 **Pre-commit Hook** - Automatic code quality checks before each commit. See [Pre-commit Hook Documentation](docs/PRE_COMMIT_HOOK.md) for details.
- 🐍 **Native Python 3.13** - Reproducible local tooling managed by `uv`.
- 🐳 **Local Home Assistant** - Run Home Assistant 2026.1.0 with `make ha-up` and validate the integration at `http://localhost:8123`.

Run `make bootstrap` once, then use `make validate` for formatting, linting, and tests. `make ha-up` and `make ha-restart` sync the current integration source into the development configuration before starting Home Assistant. See [Contributing](CONTRIBUTING.md) for the complete local workflow.

## Legal

[Disclaimer](DISCLAIMER.md)  
[License](LICENSE)
