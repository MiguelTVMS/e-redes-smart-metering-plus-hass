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

### Updating

Update the integration from HACS, restart Home Assistant, and confirm the installed version in HACS. Manual installations must replace the complete integration directory before restarting Home Assistant.

## Configure the integration

1. During setup, enter every CPE that may send data to this Home Assistant instance.
2. Open **Settings > Devices & services**, select the integration, and choose **Configure**.
3. Open **Webhook URL and Authentication**, then copy the active URL into E-REDES Smart Metering Plus.
4. When the first accepted payload arrives, Home Assistant creates a device for that CPE.
5. On each meter device, select the **Contracted power** from your electricity contract. Power usage entities remain unavailable until you choose a tier.

The **Configure** menu has three sections:

| Section | Purpose |
| --- | --- |
| Webhook URL and Authentication | View the active URL and configure optional `Authorization` header validation |
| Manage allowed CPEs | Add or remove CPEs from the payload allowlist |
| Reset a meter | Delete a discovered meter and restore its generated device name, entity names, and entity IDs when it is recreated |

The webhook path is always `/api/webhook/e_redes_smart_metering_plus`.

### Choosing the webhook URL

- If **Home Assistant Cloud** is connected and no external URL is configured, the integration creates a Cloudhook URL.
- If an external Home Assistant URL is configured in **Settings > System > Network**, the integration uses it.
- Otherwise, it shows the local Home Assistant URL. E-REDES must be able to reach that URL for updates to arrive.

Reloading or restarting the integration preserves the existing Cloudhook. It is deleted only when you remove the integration entry.

### Authentication

Authentication is disabled by default. To enable it:

1. Open **Webhook URL and Authentication**.
2. Enable **Require Authorization header**.
3. Choose one token path:
   - To use your own token, enter an ASCII value and submit once to save it.
   - To generate a token, select **Generate a new random token** and submit once. Copy the generated value shown in the refreshed form, then submit again to save it.
4. Provide the saved token to E-REDES as the HTTP Header Authentication value.

The token is intentionally displayed as plain text so it can be copied. Home Assistant does not provide a separate copy button for this selector. The integration accepts either the exact token or `Bearer <token>` in the HTTP `Authorization` header. Disabling **Require Authorization header** stops checking the header after the form is saved, even if a token remains in the token field. Changing or disabling authentication does not change the webhook URL.

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

### Delete or reset one meter

Both operations keep the integration, webhook URL, authentication settings, and CPE allowlist. The next accepted payload for the CPE recreates the meter.

| Operation | Use it when | Names and entity IDs after recreation |
| --- | --- | --- |
| Delete the device from its Home Assistant device page | You want to rediscover the fields currently sent by E-REDES | Existing entity registry IDs are reused when the same fields return |
| **Configure > Reset a meter** | You also want to discard custom device and entity names and regenerate entity IDs | Generated names and IDs are restored from the recreated meter |

Before a full reset, update dashboards, automations, scripts, and external consumers that refer to the old entity IDs. Neither operation deletes recorder history or long-term statistics. Home Assistant may associate retained statistics with their previous statistic IDs, so a reset is not a recorder purge.

Removing a CPE under **Manage allowed CPEs** is different. It rejects future payloads for that CPE, but it does not delete the existing device. If you want to remove the device as well, delete or reset the meter first, then remove its CPE from the allowlist. If the CPE was already removed, add it back, wait for the integration to reload, delete or reset the device, and then remove the CPE again.

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

Common webhook responses are:

| Status | Meaning |
| --- | --- |
| 200 | Payload accepted, or an older out-of-order measurement safely ignored |
| 400 | Invalid JSON, a non-object JSON body, or no `cpe` field |
| 401 | Authentication is enabled and the `Authorization` value does not match |
| 403 | The CPE is not in the configured allowlist |
| 422 | The payload contains no valid supported measurement |

If E-REDES receives HTTP 200 but entities do not change, check the payload timestamp. Measurements older than the latest accepted timestamp for that CPE are intentionally ignored.

### Integration fails after a Home Assistant update

Install the latest integration release from HACS and restart Home Assistant before reporting the failure. Version 1.8.1 and newer support the Home Assistant 2026.9 entity and device registry APIs while retaining the declared Home Assistant 2026.1 minimum.

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

Release changes are listed in the [changelog](CHANGELOG.md).

## Legal

[Disclaimer](DISCLAIMER.md)  
[License](LICENSE)
