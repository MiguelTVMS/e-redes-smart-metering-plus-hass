"""Sensor platform for E-Redes Smart Metering Plus integration."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MANUFACTURER, MODEL, SENSOR_MAPPING

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up E-Redes Smart Metering Plus sensors from config entry."""
    # We'll create entities dynamically as data comes in
    # Store the add_entities callback for later use
    hass.data[DOMAIN][config_entry.entry_id]["add_entities"] = async_add_entities
    hass.data[DOMAIN][config_entry.entry_id]["entities"] = {}


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
        
        self._attr_name = f"E-Redes {cpe} {sensor_config['name']}"
        self._attr_unique_id = f"{DOMAIN}_{cpe}_{sensor_key}"
        self._attr_device_class = sensor_config.get("device_class")
        self._attr_state_class = sensor_config.get("state_class")
        self._attr_native_unit_of_measurement = sensor_config.get("unit")
        self._attr_icon = sensor_config.get("icon")
        
        self._attr_native_value = None
        self._last_update = None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._cpe)},
            name=f"E-Redes Smart Meter {self._cpe}",
            manufacturer=MANUFACTURER,
            model=MODEL,
            configuration_url=None,
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        attrs = {}
        if self._last_update:
            attrs["last_update"] = self._last_update
        attrs["cpe"] = self._cpe
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
    def _handle_update(self, value: float | int, timestamp: str | None = None) -> None:
        """Handle sensor update."""
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
    if field_name not in SENSOR_MAPPING:
        return
    
    sensor_config = SENSOR_MAPPING[field_name]
    sensor_key = sensor_config["key"]
    
    # Check if entity already exists
    entities = hass.data[DOMAIN][config_entry_id]["entities"]
    entity_key = f"{cpe}_{sensor_key}"
    
    if entity_key in entities:
        return  # Entity already exists
    
    # Create new sensor entity
    sensor = ERedisSensor(cpe, sensor_key, sensor_config, config_entry_id)
    
    # Add to Home Assistant
    add_entities = hass.data[DOMAIN][config_entry_id]["add_entities"]
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
    for field_name in data:
        if field_name != "cpe" and field_name in SENSOR_MAPPING:
            await async_create_sensor_for_cpe(hass, config_entry_id, cpe, field_name)
