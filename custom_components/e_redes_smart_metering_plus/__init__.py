"""The E-Redes Smart Metering Plus integration."""

from __future__ import annotations

import logging
import re
from typing import Any

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

_LOGGER = logging.getLogger(__name__)

_CONFIG_ENTRY_VERSION = 6
_PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SELECT, Platform.BINARY_SENSOR]
_CPE_UNIQUE_ID_PATTERN = re.compile(rf"^{DOMAIN}_(PT[A-Z0-9]{{18}})_")
_CONTRACTED_POWER_ENTITY_KEY_MIGRATIONS = {
    "breaker_load_warning": "contracted_power_usage_warning",
    "breaker_load_critical": "contracted_power_usage_critical",
    "breaker_overload": "contracted_power_exceeded",
    "breaker_load": "contracted_power_usage",
    "breaker_load_status": "contracted_power_usage_status",
}


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
    if entry.version > _CONFIG_ENTRY_VERSION:
        _LOGGER.error(
            "Cannot migrate config entry from version %d because this integration only supports version %d",
            entry.version,
            _CONFIG_ENTRY_VERSION,
        )
        return False

    data = dict(entry.data)
    if entry.version < 2:
        configured_cpes = set(entry.data.get(CONF_CPES, ()))
        device_registry = dr.async_get(hass)
        for device in dr.async_entries_for_config_entry(
            device_registry, entry.entry_id
        ):
            configured_cpes.update(
                identifier
                for domain, identifier in device.identifiers
                if domain == DOMAIN
            )

        entity_registry = er.async_get(hass)
        for entity in er.async_entries_for_config_entry(
            entity_registry, entry.entry_id
        ):
            if match := _CPE_UNIQUE_ID_PATTERN.match(entity.unique_id):
                configured_cpes.add(match.group(1))

        data[CONF_CPES] = sorted(configured_cpes)

    if entry.version < 3:
        entity_registry = er.async_get(hass)
        for entity in er.async_entries_for_config_entry(
            entity_registry, entry.entry_id
        ):
            if entity.domain == Platform.NUMBER and entity.unique_id.endswith(
                "_breaker_limit"
            ):
                entity_registry.async_update_entity(
                    entity.entity_id,
                    disabled_by=er.RegistryEntryDisabler.INTEGRATION,
                )

    if entry.version < 6:
        entity_registry = er.async_get(hass)
        migrated_keys = 0
        migrated_entity_ids = 0
        for entity in er.async_entries_for_config_entry(
            entity_registry, entry.entry_id
        ):
            for old_key, new_key in _CONTRACTED_POWER_ENTITY_KEY_MIGRATIONS.items():
                suffix = f"_{old_key}"
                update_kwargs: dict[str, Any] = {}
                if entity.unique_id.endswith(suffix):
                    new_unique_id = f"{entity.unique_id[: -len(suffix)]}_{new_key}"
                    if (
                        entity_registry.async_get_entity_id(
                            entity.domain,
                            entity.platform,
                            new_unique_id,
                        )
                        is None
                    ):
                        update_kwargs["new_unique_id"] = new_unique_id
                        migrated_keys += 1
                    else:
                        _LOGGER.warning(
                            "Could not migrate unique ID %s to %s because the target already exists",
                            entity.unique_id,
                            new_unique_id,
                        )
                        break
                if entity.entity_id.endswith(suffix):
                    new_entity_id = f"{entity.entity_id[: -len(suffix)]}_{new_key}"
                    if entity_registry.async_get(new_entity_id) is None:
                        update_kwargs["new_entity_id"] = new_entity_id
                        migrated_entity_ids += 1
                    else:
                        _LOGGER.warning(
                            "Could not migrate entity ID %s to %s because the target already exists",
                            entity.entity_id,
                            new_entity_id,
                        )
                if not update_kwargs:
                    continue
                entity_registry.async_update_entity(
                    entity.entity_id,
                    **update_kwargs,
                )
                break
        if migrated_keys or migrated_entity_ids:
            _LOGGER.info(
                "Migrated %d contracted-power unique IDs and %d entity IDs",
                migrated_keys,
                migrated_entity_ids,
            )

    hass.config_entries.async_update_entry(
        entry,
        data=data,
        version=_CONFIG_ENTRY_VERSION,
    )
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ERedesConfigEntry) -> None:
    """Reload the integration after its configuration changes."""
    await hass.config_entries.async_reload(entry.entry_id)
