"""Number platform for E-Redes Smart Metering Plus integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, MANUFACTURER, MODEL

_LOGGER = logging.getLogger(__name__)

DEFAULT_BREAKER_LIMIT = 20  # Default breaker limit in amps


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up E-Redes Smart Metering Plus number entities from config entry."""
    # Store the add_entities callback for later use when devices are discovered
    if "number_add_entities" not in hass.data[DOMAIN][config_entry.entry_id]:
        hass.data[DOMAIN][config_entry.entry_id][
            "number_add_entities"
        ] = async_add_entities
        hass.data[DOMAIN][config_entry.entry_id]["number_entities"] = {}

    # Restore existing entities from entity registry
    await async_restore_existing_number_entities(hass, config_entry, async_add_entities)


async def async_restore_existing_number_entities(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Restore existing number entities from entity registry."""
    entity_registry = er.async_get(hass)
    entities_to_restore = []

    # Find all number entities for this integration
    for entity_entry in entity_registry.entities.values():
        if not (
            entity_entry.config_entry_id == config_entry.entry_id
            and entity_entry.domain == "number"
            and entity_entry.platform == DOMAIN
        ):
            continue

        # Parse the unique_id to extract CPE
        unique_id = entity_entry.unique_id
        if not unique_id.startswith(f"{DOMAIN}_"):
            continue

        # Format: e_redes_smart_metering_plus_CPE_breaker_limit
        # Remove the domain prefix and _breaker_limit suffix
        remainder = unique_id[len(f"{DOMAIN}_"):]
        if not remainder.endswith("_breaker_limit"):
            continue

        cpe = remainder[: -len("_breaker_limit")]

        _LOGGER.debug(
            "Restoring breaker limit number entity: %s for CPE: %s",
            entity_entry.entity_id,
            cpe,
        )

        # Create number entity
        entity = ERedisBreakerLimitNumber(cpe, config_entry.entry_id)
        entities_to_restore.append(entity)

        # Store reference
        hass.data[DOMAIN][config_entry.entry_id]["number_entities"][cpe] = entity

    if entities_to_restore:
        async_add_entities(entities_to_restore)
        _LOGGER.info(
            "Restored %d breaker limit number entities", len(
                entities_to_restore)
        )
    else:
        _LOGGER.debug(
            "No existing breaker limit number entities found to restore")


@callback
def async_create_breaker_limit_entity(
    hass: HomeAssistant,
    config_entry_id: str,
    cpe: str,
) -> None:
    """Create a breaker limit number entity for a CPE device."""
    # Check if entity already exists
    if cpe in hass.data[DOMAIN][config_entry_id].get("number_entities", {}):
        return

    # Get the add_entities callback
    add_entities = hass.data[DOMAIN][config_entry_id].get(
        "number_add_entities")
    if not add_entities:
        _LOGGER.warning(
            "Cannot create breaker limit entity for %s: add_entities not available", cpe
        )
        return

    # Create the entity
    entity = ERedisBreakerLimitNumber(cpe, config_entry_id)

    # Add it to Home Assistant
    add_entities([entity])

    # Store reference
    hass.data[DOMAIN][config_entry_id]["number_entities"][cpe] = entity

    _LOGGER.info("Created breaker limit number entity for CPE: %s", cpe)


# type: ignore[misc]
class ERedisBreakerLimitNumber(NumberEntity, RestoreEntity):
    """Representation of the E-Redes Breaker Limit number entity."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 1
    _attr_native_max_value = 200
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:current-ac"
    _attr_native_unit_of_measurement = "A"

    def __init__(
        self,
        cpe: str,
        config_entry_id: str,
    ) -> None:
        """Initialize the breaker limit number entity."""
        self._cpe = cpe
        self._config_entry_id = config_entry_id
        self._attr_unique_id = f"{DOMAIN}_{cpe}_breaker_limit"
        self._attr_name = "Breaker limit"
        self._attr_should_poll = False
        self._native_value: float = DEFAULT_BREAKER_LIMIT

    @property  # type: ignore[misc]
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._cpe)},
            name=f"E-Redes Smart Meter ({self._cpe})",
            manufacturer=MANUFACTURER,
            model=MODEL,
            serial_number=self._cpe,
            suggested_area="Energy",
        )

    @property  # type: ignore[override]
    def native_value(self) -> float:
        """Return the current value."""
        return self._native_value

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()

        # Restore previous state
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (
            None,
            "unknown",
            "unavailable",
        ):
            try:
                restored_value = float(last_state.state)
                self._native_value = restored_value
                _LOGGER.info(
                    "Restored breaker limit for %s: %s A",
                    self._cpe,
                    restored_value,
                )
            except (ValueError, TypeError) as err:
                _LOGGER.warning(
                    "Could not restore breaker limit for %s: %s, using default",
                    self._cpe,
                    err,
                )
                self._native_value = DEFAULT_BREAKER_LIMIT
        else:
            _LOGGER.info(
                "No previous state found for breaker limit %s, using default: %s A",
                self._cpe,
                DEFAULT_BREAKER_LIMIT,
            )

        # Write the state immediately to ensure it's persisted
        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        self._native_value = value
        self.async_write_ha_state()
        _LOGGER.info("Breaker limit for %s set to: %s A", self._cpe, value)

    @property
    # type: ignore[override]
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        return {
            "cpe": self._cpe,
            "description": "Maximum current capacity of your electrical breaker",
        }
