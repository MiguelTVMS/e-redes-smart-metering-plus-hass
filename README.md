# E-REDES Smart Metering Plus

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=MiguelTVMS&repository=e-redes-smart-metering-plus-hass&category=integration)

Monitor compatible E-REDES Smart Metering Plus meters in Home Assistant. The integration receives meter data by webhook, creates one device for each configured CPE, and needs no YAML or automations.

> [!IMPORTANT]
> Smart Metering Plus must already be active for your E-REDES meter. This integration cannot request access to the service or retrieve your meter data itself.

> [!NOTE]
> This project is not affiliated with, sponsored by, or endorsed by E-REDES - Distribuição de Eletricidade, S.A. Read the full [disclaimer](DISCLAIMER.md).

## Before you install

- Home Assistant 2026.1.0 or newer.
- An active E-REDES Smart Metering Plus service.
- The complete CPE for every meter you want to connect. A valid CPE starts with `PT` and has 20 characters.
- A URL that E-REDES can reach. Home Assistant Cloud works automatically. Otherwise, configure an external Home Assistant URL or securely expose your instance.

## Installation

### HACS

1. Open the button above in your Home Assistant instance. If the repository is not already available in HACS, add `https://github.com/MiguelTVMS/e-redes-smart-metering-plus-hass` as a custom repository in the **Integration** category.
2. Download **E-REDES Smart Metering Plus** from HACS.
3. Restart Home Assistant.
4. Go to **Settings > Devices & services > Add integration**, then search for **E-REDES Smart Metering Plus**.

### Manual installation

1. Copy `custom_components/e_redes_smart_metering_plus` from this repository to your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Add the integration from **Settings > Devices & services > Add integration**.

## Set up your meter

1. During setup, enter every CPE that may send data to this Home Assistant instance.
2. Open **Settings > Devices & services**, select the integration, choose **Configure**, then open **Webhook URL and Authentication**.
3. Copy the active URL into E-REDES Smart Metering Plus. Authentication is disabled by default. To enable it, generate or enter a token, save it in Home Assistant, and provide the same token to E-REDES as the HTTP Header Authentication value.
4. When the first payload arrives, Home Assistant creates a device for that CPE.
5. On each meter device, select the **Contracted power** from your electricity contract. Power usage entities remain unavailable until you choose a tier.

The webhook path is always `/api/webhook/e_redes_smart_metering_plus`.

### Choosing the webhook URL

- If **Home Assistant Cloud** is connected and no external URL is configured, the integration creates a Cloudhook URL.
- If an external Home Assistant URL is configured in **Settings > System > Network**, the integration uses it.
- Otherwise, it shows the local Home Assistant URL. E-REDES must be able to reach that URL for updates to arrive.

Reloading or restarting the integration preserves the existing Cloudhook. It is deleted only when you remove the integration entry.

> [!CAUTION]
> The CPE list is an allowlist, not sender authentication. Optional authentication checks the `Authorization` header and accepts the configured token either verbatim or as `Bearer <token>`. E-REDES publicly requests an HTTP Header Authentication value but does not document its exact header format, so confirm the setting with E-REDES if delivery fails. Keep the webhook URL and token private, and do not include CPE values or complete payloads in public support requests.

## What Home Assistant creates

For each CPE, Home Assistant creates a separate meter device. Available entities depend on the values that E-REDES sends.

| Type | Entities |
| --- | --- |
| Energy | Imported energy and Exported energy |
| Power | Import power, Export power, Peak import power, Peak export power, and per-phase power when available |
| Electrical estimates | Voltage L1/L2/L3 and estimated active import current L1/L2/L3 when the matching data is available |
| Contract usage | Contracted power, Estimated power usage, and Estimated power usage status |
| Diagnostics | Last update and Update interval, disabled by default |

The following diagnostic problem entities are also disabled by default: **Estimated power usage warning**, **Estimated critical power usage**, and **Estimated power usage exceeded**. Enable them from the device page only if you need separate alert entities.

To rediscover a meter's available fields, delete its device from Home Assistant. The integration keeps the CPE authorized and preserves the webhook URL. The next payload for that CPE recreates the device using only newly received fields while preserving existing entity IDs when those fields return. To also restore generated device and entity names and entity IDs, open the integration's **Configure** dialog and choose **Reset a meter**. Neither operation deletes recorder history or long-term statistics.

Estimated power usage compares the active-current component derived from active power and voltage with the nominal current for the selected contracted-power tier. For three-phase data, it uses the most-loaded reported phase. The Smart Metering Plus webhook does not provide current, apparent power, or power factor, so this is a lower-bound estimate whenever the power factor is below 1. It must not be used to predict the behavior of a physical breaker, the meter's control function, or other protection hardware.

The three-phase list includes the 3.45 kVA tier used by eligible non-residential installations. New residential three-phase installations normally start at 6.90 kVA.

## Webhook data

The integration supports current E-REDES single-phase and three-phase payloads. It processes the following measurements when present:

- cumulative imported and exported energy
- instantaneous and peak imported and exported power
- voltage and per-phase power
- timestamps used to reject older out-of-order measurements

Unknown fields and missing optional values do not stop supported values from being processed. The official service documentation is available from [E-REDES Smart Metering Plus](https://www.e-redes.pt/en/smart-metering-plus).

## Troubleshooting

### No meter device or updates

1. Confirm that the CPE is complete and listed in the integration's **Configure** dialog.
2. Confirm that the exact active webhook URL was provided to E-REDES.
3. Ensure E-REDES can reach the URL. A local URL requires appropriate network exposure.
4. Check **Settings > System > Logs** for integration messages.

Requests for a CPE that is not in the configured list are rejected with HTTP 403. Add all of your meters in **Configure**. Each CPE gets its own device once data arrives.

To capture the first accepted payload after a restart, temporarily enable debug logging:

```yaml
logger:
  logs:
    custom_components.e_redes_smart_metering_plus: debug
```

The logged payload can contain your CPE and energy data. Disable debug logging after checking it, and remove sensitive values before sharing logs.

## Support and development

For a bug report or feature request, use the [issue tracker](https://github.com/MiguelTVMS/e-redes-smart-metering-plus-hass/issues). Do not publish CPE values, webhook URLs, or unredacted payloads.

Developers should use the [development guide](docs/DEVELOPMENT.md) and [contribution guidelines](CONTRIBUTING.md).

## Legal

[Disclaimer](DISCLAIMER.md)  
[License](LICENSE)
