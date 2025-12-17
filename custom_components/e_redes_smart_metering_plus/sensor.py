"""Sensor platform for E-Redes Smart Metering Plus integration."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, MANUFACTURER, MODEL, SENSOR_MAPPING

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up E-Redes Smart Metering Plus sensors from config entry."""
    # Store the add_entities callback for later use
    hass.data[DOMAIN][config_entry.entry_id]["add_entities"] = async_add_entities
    hass.data[DOMAIN][config_entry.entry_id]["entities"] = {}

    # Restore existing entities from entity registry
    await async_restore_existing_entities(hass, config_entry, async_add_entities)


async def async_restore_existing_entities(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Restore existing entities from entity registry."""
    entity_registry = er.async_get(hass)
    entities_to_restore = []

    # Find all entities for this integration
    for entity_entry in entity_registry.entities.values():
        if not (
            entity_entry.config_entry_id == config_entry.entry_id
            and entity_entry.domain == "sensor"
            and entity_entry.platform == DOMAIN
        ):
            continue

        # Parse the unique_id to extract CPE and sensor_key
        unique_id = entity_entry.unique_id
        if not unique_id.startswith(f"{DOMAIN}_"):
            continue

        # Format: e_redes_smart_metering_plus_CPE_sensor_key
        # Remove the domain prefix
        remainder = unique_id[len(f"{DOMAIN}_") :]

        # Find the sensor_key by matching against known sensor keys
        sensor_key = None
        cpe = None

        for config in SENSOR_MAPPING.values():
            key = config["key"]
            if remainder.endswith(f"_{key}"):
                sensor_key = key
                cpe = remainder[: -len(f"_{key}")]
                break

        if not (sensor_key and cpe):
            continue

        # Find sensor config for this sensor_key
        sensor_config = None
        for config in SENSOR_MAPPING.values():
            if config["key"] == sensor_key:
                sensor_config = config
                break

        if not sensor_config:
            continue

        _LOGGER.debug(
            "Restoring entity: %s for CPE: %s, sensor: %s",
            entity_entry.entity_id,
            cpe,
            sensor_key,
        )

        # Create sensor entity
        sensor = ERedisSensor(cpe, sensor_key, sensor_config, config_entry.entry_id)
        entities_to_restore.append(sensor)

        # Store in entities dict
        entity_key = f"{cpe}_{sensor_key}"
        hass.data[DOMAIN][config_entry.entry_id]["entities"][entity_key] = sensor

    if entities_to_restore:
        _LOGGER.info("Restored %d existing sensor entities", len(entities_to_restore))
        async_add_entities(entities_to_restore)
    else:
        _LOGGER.debug("No existing entities found to restore")


class ERedisSensor(SensorEntity):
    """Representation of an E-Redes Smart Metering Plus sensor."""

    def __init__(
        self,
        cpe: str,
        sensor_key: str,
        sensor_config: dict[str, Any],
        config_entry_id: str,
    ) -> None:
        """Initialize the sensor."""
        self._cpe = cpe
        self._sensor_key = sensor_key
        self._config = sensor_config
        self._config_entry_id = config_entry_id

        self._attr_name = f"{sensor_config['name']}"
        self._attr_unique_id = (
            # Keep CPE in unique_id for uniqueness
            f"{DOMAIN}_{cpe}_{sensor_key}"
        )
        self._attr_device_class = sensor_config.get("device_class")
        self._attr_state_class = sensor_config.get("state_class")
        self._attr_native_unit_of_measurement = sensor_config.get("unit")
        self._attr_icon = sensor_config.get("icon")

        # Initialize state - will be restored from Home Assistant's state machine
        self._attr_native_value = None
        self._last_update: datetime | None = None

        # Enable state restoration
        self._attr_should_poll = False

    @property
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

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        attrs: dict[str, Any] = {}
        if self._last_update:
            attrs["last_update"] = self._last_update
        attrs["cpe"] = self._cpe

        # Add webhook URL info to the first sensor of each device for easy access
        if self._sensor_key == "instantaneous_active_power_import":
            webhook_url = None
            if (
                DOMAIN in self.hass.data
                and self._config_entry_id in self.hass.data[DOMAIN]
                and "webhook_url" in self.hass.data[DOMAIN][self._config_entry_id]
            ):
                webhook_url = self.hass.data[DOMAIN][self._config_entry_id][
                    "webhook_url"
                ]

            if webhook_url:
                attrs["integration_webhook_url"] = webhook_url
                attrs["webhook_info"] = "This URL receives data for ALL E-Redes meters"
                attrs["configuration_note"] = (
                    "Configure this URL once in your E-Redes provider dashboard - it will handle all your meters"
                )

        return attrs

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()

        # Connect to dispatcher for updates
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_{self._cpe}_{self._sensor_key}_update",
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self, value: float, timestamp: str | None = None) -> None:
        """Handle sensor update."""
        # For total_increasing sensors, ensure values never decrease
        if self._attr_state_class == "total_increasing":
            if self._attr_native_value is not None:
                try:
                    # Convert current value to float for comparison
                    # Energy sensors are always numeric, so this is safe
                    # type: ignore[arg-type]
                    current_value = float(self._attr_native_value)
                    if value < current_value:
                        _LOGGER.warning(
                            "Rejected decreasing value for %s: %s -> %s (state_class: total_increasing). "
                            "This may be due to out-of-order webhook delivery or meter reset.",
                            self.entity_id,
                            current_value,
                            value,
                        )
                        return  # Discard the update to prevent state class violation
                except (ValueError, TypeError):
                    # If conversion fails, proceed with update
                    pass

        self._attr_native_value = value

        if timestamp:
            try:
                self._last_update = datetime.fromisoformat(timestamp.replace(" ", "T"))
            except (ValueError, TypeError):
                self._last_update = datetime.now()
        else:
            self._last_update = datetime.now()

        self.async_write_ha_state()
        _LOGGER.debug("Updated sensor %s with value %s", self.entity_id, value)


async def async_create_sensor_for_cpe(
    hass: HomeAssistant,
    config_entry_id: str,
    cpe: str,
    field_name: str,
) -> None:
    """Create a sensor entity for a specific CPE and field."""
    _LOGGER.debug("Creating sensor for CPE %s, field %s", cpe, field_name)

    if field_name not in SENSOR_MAPPING:
        _LOGGER.debug("Field %s not in sensor mapping, skipping", field_name)
        return

    sensor_config = SENSOR_MAPPING[field_name]
    sensor_key = sensor_config["key"]

    _LOGGER.debug("Sensor config for %s: %s", field_name, sensor_config)

    # Check if entity already exists
    entities = hass.data[DOMAIN][config_entry_id]["entities"]
    entity_key = f"{cpe}_{sensor_key}"

    if entity_key in entities:
        _LOGGER.debug("Entity %s already exists, skipping creation", entity_key)
        return  # Entity already exists

    _LOGGER.debug("Creating new sensor entity for %s", entity_key)

    # Create new sensor entity
    sensor = ERedisSensor(cpe, sensor_key, sensor_config, config_entry_id)

    # Add to Home Assistant
    add_entities = hass.data[DOMAIN][config_entry_id]["add_entities"]
    _LOGGER.debug("Adding entities using callback: %s", add_entities)
    add_entities([sensor])

    # Store reference
    entities[entity_key] = sensor

    _LOGGER.info("Created sensor %s for CPE %s", sensor_key, cpe)


# Function to be called from webhook handler to ensure sensors exist
async def async_ensure_sensors_for_data(
    hass: HomeAssistant,
    config_entry_id: str,
    cpe: str,
    data: dict[str, Any],
) -> None:
    """Ensure all required sensors exist for the incoming data."""
    _LOGGER.debug(
        "Ensuring sensors for CPE %s with data keys: %s", cpe, list(data.keys())
    )

    for field_name in data:
        if field_name != "cpe" and field_name in SENSOR_MAPPING:
            _LOGGER.debug("Creating sensor for field: %s", field_name)
            await async_create_sensor_for_cpe(hass, config_entry_id, cpe, field_name)
        else:
            _LOGGER.debug("Skipping field %s (cpe field or not in mapping)", field_name)
