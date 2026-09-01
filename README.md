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
`select` | Choose the contracted-power tier used for load monitoring.
`binary_sensor` | Show warning, critical, and overload problem states.

## Features

- 🔄 **Real-time Energy Monitoring** - Receive live data from your E-REDES smart meters
- 🌐 **Cloud Webhook Support** - Automatic secure webhook URL generation with Nabu Casa
- 📊 **Multiple Meter Support** - Allow one or more known meters by CPE
- ⚡ **UI Configuration** - No YAML configuration or automation setup required
- 🏠 **Automatic Device Creation** - Devices and sensors created dynamically as data arrives
- ⚙️ **Contracted Power Configuration** - Select the market tier shown on your electricity contract
- 🔋 **Breaker Load Monitoring** - Monitor active load against the official nominal-current limit
- ⚠️ **Load Alerts** - Warning, critical, and overload problem sensors

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
4. Open **Settings > Devices & services**, select the integration, then **Configure** to copy the active URL. The integration respects **Settings > System > Network > Home Assistant URL**: a configured external URL is used when Home Assistant Cloud is disabled there, otherwise the Cloudhook URL is shown.
5. Configure E-REDES with that URL and start receiving data.
6. On each meter device, select the contracted power shown on your electricity bill. Breaker-load entities remain unavailable until this is configured.

### Webhook URL Format

- **Local URL**: `http://your-home-assistant:8123/api/webhook/e_redes_smart_metering_plus`
- **Configured external URL**: `https://your-home-assistant.example/api/webhook/e_redes_smart_metering_plus`
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
- **Instantaneous Active Current Import** (A) - Created for single-phase payloads from total power and L1 voltage
- **Instantaneous Active Current Import L1/L2/L3** (A) - Created for three-phase payloads from matching per-phase power and voltage
- **Breaker Load** (%) - Active current relative to the nominal limit; three-phase payloads use the most-loaded measured phase
- **Breaker Load Status** - Normal, Warning, Critical, or Overload
- **Breaker Load Warning** - Problem sensor active at 80% and above
- **Breaker Load Critical** - Problem sensor active at 95% and above
- **Breaker Overload** - Problem sensor active at 100% and above

The problem sensors are cumulative: Critical also keeps Warning active, and Overload keeps all three active. They represent active load from the available E-REDES measurements and configured contracted-power tier. They do not simulate a physical breaker's trip curve.

The integration does not derive an aggregate current for three-phase payloads. It only calculates currents when E-REDES supplies matching power and voltage measurements for the installation or phase.

### Configuration

- **Contracted Power** (kVA) - Official single-phase or three-phase market tiers. There is no default, so select the value from the electricity contract.

During upgrade, a standard value from the previous free-form Breaker Limit entity is mapped to the corresponding contracted-power tier when possible. The old number entity is disabled, and non-standard values are not rounded or silently changed.

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

Run `make bootstrap` once, then use `make validate` for formatting, linting, and tests. Docker Compose mounts the current integration source directly, so `make ha-restart` is enough after Python changes. See the [cross-platform development guide](docs/DEVELOPMENT.md) and [Contributing](CONTRIBUTING.md) for the complete local workflow.

The development Compose stack seeds a safe `configuration.yaml`, completes Home Assistant onboarding, and enables passwordless local browser access automatically. A generated recovery password stays in ignored local configuration and is available through `make ha-credentials`. Adding the integration remains an explicit UI step because it requires real CPE identifiers.

## Legal

[Disclaimer](DISCLAIMER.md)  
[License](LICENSE)
