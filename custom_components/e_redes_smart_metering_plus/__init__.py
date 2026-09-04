"""The E-Redes Smart Metering Plus integration."""

from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity_platform import async_calculate_suggested_object_id

from .const import CONF_CPES, DOMAIN
from .models import ERedesConfigEntry, ERedesRuntimeData
from .webhook import (
    async_remove_cloudhook,
    async_setup_webhook,
    async_unload_webhook,
)

_LOGGER = logging.getLogger(__name__)

_CONFIG_ENTRY_VERSION = 6
_PENDING_RESET_WATERMARKS = f"{DOMAIN}_pending_reset_watermarks"
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
    preserved_watermarks = dict(
        hass.data.get(_PENDING_RESET_WATERMARKS, {}).get(entry.entry_id, {})
    )
    entry.runtime_data = ERedesRuntimeData(
        allowed_cpes=frozenset(entry.data.get(CONF_CPES, ())),
        last_source_timestamps=preserved_watermarks,
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


async def async_remove_config_entry_device(
    hass: HomeAssistant,
    entry: ERedesConfigEntry,
    device_entry: dr.DeviceEntry,
) -> bool:
    """Clear a meter and let Home Assistant remove its registry device."""
    return await async_reset_meter(
        hass,
        entry,
        device_entry,
        remove_device=False,
    )


async def async_reset_meter(
    hass: HomeAssistant,
    entry: ERedesConfigEntry,
    device_entry: dr.DeviceEntry,
    *,
    reset_entity_names: bool = False,
    remove_device: bool = True,
) -> bool:
    """Delete a meter's discovered data so its next payload recreates it."""
    cpes = {
        identifier
        for domain, identifier in device_entry.identifiers
        if domain == DOMAIN and identifier in entry.runtime_data.allowed_cpes
    }
    if entry.entry_id not in device_entry.config_entries or len(cpes) != 1:
        return False

    cpe = cpes.pop()
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    if reset_entity_names:
        device_entry = (
            device_registry.async_update_device(device_entry.id, name_by_user=None)
            or device_entry
        )

    runtime_entities = {
        entity.unique_id: entity
        for entities in (
            entry.runtime_data.sensor_entities,
            entry.runtime_data.select_entities,
            entry.runtime_data.binary_sensor_entities,
        )
        for entity in entities.values()
        if entity.unique_id is not None
    }
    for entity_entry in er.async_entries_for_device(
        entity_registry, device_entry.id, include_disabled_entities=True
    ):
        if entity_entry.config_entry_id == entry.entry_id:
            if reset_entity_names and (
                runtime_entity := runtime_entities.get(entity_entry.unique_id)
            ):
                suggested_object_id = async_calculate_suggested_object_id(
                    runtime_entity, device_entry
                )
                new_entity_id = (
                    entity_registry.async_generate_entity_id(
                        entity_entry.domain,
                        suggested_object_id,
                        current_entity_id=entity_entry.entity_id,
                    )
                    if suggested_object_id
                    else entity_entry.entity_id
                )
                entity_entry = entity_registry.async_update_entity(
                    entity_entry.entity_id,
                    name=None,
                    new_entity_id=new_entity_id,
                )
            entity_registry.async_remove(entity_entry.entity_id)

    if remove_device and device_registry.async_get(device_entry.id) is not None:
        device_registry.async_remove_device(device_entry.id)

    runtime_data = entry.runtime_data
    for entities in (
        runtime_data.sensor_entities,
        runtime_data.select_entities,
        runtime_data.binary_sensor_entities,
    ):
        for key in tuple(entities):
            if key == cpe or key.startswith(f"{cpe}_"):
                entities.pop(key)

    for values in (
        runtime_data.latest_measurement_sensor_keys,
        runtime_data.webhook_locks,
        runtime_data.payload_fields,
    ):
        values.pop(cpe, None)

    await _async_reload_entry(hass, entry)
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
    """Reload the integration without reopening the webhook without watermarks."""
    pending_watermarks = hass.data.setdefault(_PENDING_RESET_WATERMARKS, {})
    watermarks = entry.runtime_data.last_source_timestamps
    pending_watermarks[entry.entry_id] = watermarks
    try:
        await hass.config_entries.async_reload(entry.entry_id)
    finally:
        if pending_watermarks.get(entry.entry_id) is watermarks:
            pending_watermarks.pop(entry.entry_id, None)
        if not pending_watermarks:
            hass.data.pop(_PENDING_RESET_WATERMARKS, None)
