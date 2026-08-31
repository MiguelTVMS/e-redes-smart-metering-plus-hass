"""The E-Redes Smart Metering Plus integration."""

from __future__ import annotations

import re

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import CONF_CPES, DOMAIN
from .models import ERedesConfigEntry, ERedesRuntimeData
from .webhook import (
    async_remove_cloudhook,
    async_setup_webhook,
    async_unload_webhook,
)

_PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.NUMBER, Platform.BINARY_SENSOR]
_CPE_UNIQUE_ID_PATTERN = re.compile(rf"^{DOMAIN}_(PT[A-Z0-9]{{18}})_")


async def async_setup_entry(hass: HomeAssistant, entry: ERedesConfigEntry) -> bool:
    """Set up E-Redes Smart Metering Plus from a config entry."""
    entry.runtime_data = ERedesRuntimeData(
        allowed_cpes=frozenset(entry.data.get(CONF_CPES, ()))
    )

    # Platforms must provide their entity callbacks before the webhook can receive data.
    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    try:
        # Register the webhook only after dynamic entity creation is ready.
        await async_setup_webhook(hass, entry)
    except Exception:
        await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
        raise

    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ERedesConfigEntry) -> bool:
    """Unload a config entry."""
    if not await hass.config_entries.async_unload_platforms(entry, _PLATFORMS):
        return False

    async_unload_webhook(hass, entry.runtime_data.webhook_id)
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ERedesConfigEntry) -> None:
    """Remove cloud resources when a config entry is permanently deleted."""
    await async_remove_cloudhook(hass, entry.data.get("webhook_id", DOMAIN))


async def async_migrate_entry(hass: HomeAssistant, entry: ERedesConfigEntry) -> bool:
    """Migrate existing config entries to the current schema."""
    if entry.version >= 2:
        return True

    configured_cpes = set(entry.data.get(CONF_CPES, ()))
    device_registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(device_registry, entry.entry_id):
        configured_cpes.update(
            identifier for domain, identifier in device.identifiers if domain == DOMAIN
        )

    entity_registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        if match := _CPE_UNIQUE_ID_PATTERN.match(entity.unique_id):
            configured_cpes.add(match.group(1))

    hass.config_entries.async_update_entry(
        entry,
        data={**entry.data, CONF_CPES: sorted(configured_cpes)},
        version=2,
    )
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ERedesConfigEntry) -> None:
    """Reload the integration after its configuration changes."""
    await hass.config_entries.async_reload(entry.entry_id)
