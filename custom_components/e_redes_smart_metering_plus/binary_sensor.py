"""Binary sensor platform for E-Redes Smart Metering Plus integration."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .models import ERedesConfigEntry, device_info_for_cpe

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ERedesConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up E-Redes Smart Metering Plus binary sensors from config entry."""
    config_entry.runtime_data.binary_sensor_add_entities = async_add_entities

    # Restore existing entities from entity registry
    await async_restore_existing_binary_sensors(hass, config_entry, async_add_entities)


async def async_restore_existing_binary_sensors(
    hass: HomeAssistant,
    config_entry: ERedesConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Restore existing binary sensor entities from entity registry."""
    entity_registry = er.async_get(hass)
    entities_to_restore = []

    # Find all binary sensor entities for this integration
    for entity_entry in er.async_entries_for_config_entry(
        entity_registry, config_entry.entry_id
    ):
        if not (
            entity_entry.config_entry_id == config_entry.entry_id
            and entity_entry.domain == "binary_sensor"
            and entity_entry.platform == DOMAIN
        ):
            continue

        # Parse the unique_id to extract CPE
        unique_id = entity_entry.unique_id
        if not unique_id.startswith(f"{DOMAIN}_"):
            continue

        # Format: e_redes_smart_metering_plus_CPE_breaker_overload
        # Remove the domain prefix and _breaker_overload suffix
        remainder = unique_id[len(f"{DOMAIN}_") :]
        if not remainder.endswith("_breaker_overload"):
            continue

        cpe = remainder[: -len("_breaker_overload")]

        _LOGGER.debug(
            "Restoring breaker overload binary sensor: %s for CPE: %s",
            entity_entry.entity_id,
            cpe,
        )

        # Create binary sensor entity
        entity = ERedesBreakerOverloadSensor(cpe, config_entry)
        entities_to_restore.append(entity)

        # Store reference
        config_entry.runtime_data.binary_sensor_entities[cpe] = entity

    if entities_to_restore:
        async_add_entities(entities_to_restore)
        _LOGGER.info(
            "Restored %d breaker overload binary sensors", len(entities_to_restore)
        )
    else:
        _LOGGER.debug("No existing breaker overload binary sensors found to restore")


@callback
def async_create_breaker_overload_sensor(
    config_entry: ERedesConfigEntry,
    cpe: str,
) -> None:
    """Create a breaker overload binary sensor for a CPE device."""
    # Check if entity already exists
    if cpe in config_entry.runtime_data.binary_sensor_entities:
        return

    # Get the add_entities callback
    add_entities = config_entry.runtime_data.binary_sensor_add_entities
    if not add_entities:
        _LOGGER.warning(
            "Cannot create breaker overload sensor for %s: add_entities not available",
            cpe,
        )
        return

    # Create the entity
    entity = ERedesBreakerOverloadSensor(cpe, config_entry)

    # Add it to Home Assistant
    config_entry.runtime_data.binary_sensor_entities[cpe] = entity
    add_entities([entity])

    _LOGGER.info("Created breaker overload binary sensor for CPE: %s", cpe)


class ERedesBreakerOverloadSensor(BinarySensorEntity):
    """Representation of the E-Redes Breaker Overload binary sensor."""

    _attr_has_entity_name = True
    _attr_translation_key = "breaker_overload"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:alert-circle"

    def __init__(
        self,
        cpe: str,
        config_entry: ERedesConfigEntry,
    ) -> None:
        """Initialize the breaker overload binary sensor."""
        self._cpe = cpe
        self._config_entry = config_entry
        self._attr_unique_id = f"{DOMAIN}_{cpe}_breaker_overload"
        self._attr_should_poll = False
        self._attr_is_on = False

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return device_info_for_cpe(self._cpe)

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()

        # Listen to breaker load sensor updates
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_{self._cpe}_breaker_load_update",
                self._handle_breaker_load_update,
            )
        )

        self._check_overload()

    @callback
    def _handle_breaker_load_update(self) -> None:
        """Handle updates from breaker load sensor."""
        self._check_overload()
        self.async_write_ha_state()

    def _check_overload(self) -> None:
        """Check if breaker is overloaded (load > 100%)."""
        try:
            # Get the breaker load sensor
            entities = self._config_entry.runtime_data.sensor_entities
            breaker_load_key = f"{self._cpe}_breaker_load"
            breaker_load_sensor = entities.get(breaker_load_key)

            if not breaker_load_sensor or breaker_load_sensor.native_value is None:
                _LOGGER.debug(
                    "Breaker load sensor not available or has no value for %s",
                    self._cpe,
                )
                self._attr_is_on = False
                return

            # Get the load percentage
            load_percentage = float(str(breaker_load_sensor.native_value))

            # Check if overloaded (> 100%)
            self._attr_is_on = load_percentage > 100

            _LOGGER.debug(
                "Breaker overload check for %s: load=%.0f%%, overload=%s",
                self._cpe,
                load_percentage,
                self._attr_is_on,
            )

        except (ValueError, TypeError, KeyError) as err:
            _LOGGER.debug("Error checking breaker overload for %s: %s", self._cpe, err)
            self._attr_is_on = False
