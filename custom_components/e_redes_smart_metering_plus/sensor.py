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
from homeassistant.util import dt as dt_util

from .const import (
    CALCULATED_SENSORS,
    DIAGNOSTIC_SENSORS,
    DOMAIN,
    MANUFACTURER,
    MODEL,
    SENSOR_MAPPING,
)

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
        sensor_config = None
        is_calculated = False

        # First check regular sensors
        for config in SENSOR_MAPPING.values():
            key = config["key"]
            if remainder.endswith(f"_{key}"):
                sensor_key = key
                cpe = remainder[: -len(f"_{key}")]
                sensor_config = config
                break

        # If not found, check calculated sensors
        if not sensor_key:
            for key, config in CALCULATED_SENSORS.items():
                if remainder.endswith(f"_{key}"):
                    sensor_key = key
                    cpe = remainder[: -len(f"_{key}")]
                    sensor_config = config
                    is_calculated = True
                    break

        if not (sensor_key and cpe and sensor_config):
            continue

        _LOGGER.debug(
            "Restoring entity: %s for CPE: %s, sensor: %s (calculated: %s)",
            entity_entry.entity_id,
            cpe,
            sensor_key,
            is_calculated,
        )

        # Create sensor entity
        if is_calculated:
            sensor = ERedesCalculatedSensor(
                cpe, sensor_key, sensor_config, config_entry.entry_id, hass
            )
        else:
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


class ERedesCalculatedSensor(SensorEntity):
    """Representation of a calculated E-Redes sensor."""

    def __init__(
        self,
        cpe: str,
        sensor_key: str,
        sensor_config: dict[str, Any],
        config_entry_id: str,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the calculated sensor."""
        self._cpe = cpe
        self._sensor_key = sensor_key
        self._config = sensor_config
        self._config_entry_id = config_entry_id
        self._hass = hass

        self._attr_name = f"{sensor_config['name']}"
        self._attr_unique_id = f"{DOMAIN}_{cpe}_{sensor_key}"
        self._attr_device_class = sensor_config.get("device_class")
        self._attr_state_class = sensor_config.get("state_class")
        self._attr_native_unit_of_measurement = sensor_config.get("unit")
        self._attr_icon = sensor_config.get("icon")

        # Initialize state
        self._attr_native_value = None
        self._last_update: datetime | None = None

        # Enable state restoration
        self._attr_should_poll = False

        # Store source sensor keys
        self._source_sensors = sensor_config.get("source_sensors", [])

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
        attrs["calculation_type"] = self._config.get("calculation", "unknown")
        attrs["source_sensors"] = self._source_sensors
        return attrs

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()

        # Connect to dispatcher for updates from source sensors
        for source_sensor in self._source_sensors:
            self.async_on_remove(
                async_dispatcher_connect(
                    self.hass,
                    f"{DOMAIN}_{self._cpe}_{source_sensor}_update",
                    self._handle_source_update,
                )
            )

        # If this sensor requires a number entity (like breaker_limit), listen to it
        if self._config.get("requires_number_entity"):
            number_entity_key = self._config["requires_number_entity"]
            self.async_on_remove(
                async_dispatcher_connect(
                    self.hass,
                    f"{DOMAIN}_{self._cpe}_{number_entity_key}_update",
                    self._handle_number_entity_update,
                )
            )

        # Perform initial calculation
        self._calculate_value()

        # If this is the breaker load sensor, notify binary sensor after initial calculation
        if self._sensor_key == "breaker_load":
            from homeassistant.helpers.dispatcher import async_dispatcher_send

            signal_name = f"{DOMAIN}_{self._cpe}_breaker_load_update"
            _LOGGER.info("Sending initial dispatcher signal: %s", signal_name)
            async_dispatcher_send(
                self.hass,
                signal_name,
            )

    @callback
    def _handle_source_update(self, value: float, timestamp: str | None = None) -> None:
        """Handle updates from source sensors."""
        # Recalculate when any source sensor updates
        self._calculate_value()

        if timestamp:
            try:
                self._last_update = datetime.fromisoformat(timestamp.replace(" ", "T"))
            except (ValueError, TypeError):
                self._last_update = datetime.now()
        else:
            self._last_update = datetime.now()

        self.async_write_ha_state()

        # If this is the breaker load sensor, notify binary sensor
        if self._sensor_key == "breaker_load":
            from homeassistant.helpers.dispatcher import async_dispatcher_send

            async_dispatcher_send(
                self.hass,
                f"{DOMAIN}_{self._cpe}_breaker_load_update",
            )

    @callback
    def _handle_number_entity_update(self, value: float) -> None:
        """Handle updates from number entities (like breaker limit)."""
        # Recalculate when number entity updates
        self._calculate_value()
        self.async_write_ha_state()

        # If this is the breaker load sensor, notify binary sensor
        if self._sensor_key == "breaker_load":
            from homeassistant.helpers.dispatcher import async_dispatcher_send

            async_dispatcher_send(
                self.hass,
                f"{DOMAIN}_{self._cpe}_breaker_load_update",
            )

    def _calculate_value(self) -> None:
        """Calculate the sensor value based on source sensors."""
        calculation_type = self._config.get("calculation")

        if calculation_type == "power_voltage":
            # Current (A) = Power (W) / Voltage (V)
            self._calculate_current_from_power_voltage()
        elif calculation_type == "current_breaker_limit":
            # Breaker Load (%) = (Current / Breaker Limit) * 100
            self._calculate_breaker_load()
        else:
            _LOGGER.warning("Unknown calculation type: %s", calculation_type)
            self._attr_native_value = None

    def _calculate_current_from_power_voltage(self) -> None:
        """Calculate current from power and voltage."""
        try:
            # Get the source sensor entities
            entities = self._hass.data[DOMAIN][self._config_entry_id]["entities"]

            power_key = f"{self._cpe}_instantaneous_active_power_import"
            voltage_key = f"{self._cpe}_voltage_l1"

            # Get power sensor
            power_sensor = entities.get(power_key)
            if not power_sensor or power_sensor.native_value is None:
                _LOGGER.debug(
                    "Power sensor not available or has no value for %s", self._cpe
                )
                self._attr_native_value = None
                return

            # Get voltage sensor
            voltage_sensor = entities.get(voltage_key)
            if not voltage_sensor or voltage_sensor.native_value is None:
                _LOGGER.debug(
                    "Voltage sensor not available or has no value for %s", self._cpe
                )
                self._attr_native_value = None
                return

            # Get values
            power = float(power_sensor.native_value)
            voltage = float(voltage_sensor.native_value)

            # Check for zero voltage to avoid division by zero
            if voltage == 0:
                _LOGGER.warning(
                    "Voltage is zero for %s, cannot calculate current", self._cpe
                )
                self._attr_native_value = None
                return

            # Calculate current: I = P / V
            current = power / voltage

            # Round to 2 decimal places
            self._attr_native_value = round(current, 2)

            _LOGGER.debug(
                "Calculated current for %s: %.2f A (P=%.2f W, V=%.2f V)",
                self._cpe,
                current,
                power,
                voltage,
            )

        except (ValueError, TypeError, KeyError) as err:
            _LOGGER.debug("Error calculating current for %s: %s", self._cpe, err)
            self._attr_native_value = None

    def _calculate_breaker_load(self) -> None:
        """Calculate breaker load percentage from current and breaker limit."""
        try:
            # Get the source sensor entities
            entities = self._hass.data[DOMAIN][self._config_entry_id]["entities"]

            power_key = f"{self._cpe}_instantaneous_active_power_import"
            voltage_key = f"{self._cpe}_voltage_l1"

            # Get power sensor
            power_sensor = entities.get(power_key)
            if not power_sensor or power_sensor.native_value is None:
                _LOGGER.debug(
                    "Power sensor not available or has no value for %s", self._cpe
                )
                self._attr_native_value = None
                return

            # Get voltage sensor
            voltage_sensor = entities.get(voltage_key)
            if not voltage_sensor or voltage_sensor.native_value is None:
                _LOGGER.debug(
                    "Voltage sensor not available or has no value for %s", self._cpe
                )
                self._attr_native_value = None
                return

            # Get values
            power = float(power_sensor.native_value)
            voltage = float(voltage_sensor.native_value)

            # Check for zero voltage to avoid division by zero
            if voltage == 0:
                _LOGGER.warning(
                    "Voltage is zero for %s, cannot calculate breaker load", self._cpe
                )
                self._attr_native_value = None
                return

            # Calculate current: I = P / V
            current = power / voltage

            # Get breaker limit from number entity
            number_entities = self._hass.data[DOMAIN][self._config_entry_id].get(
                "number_entities", {}
            )
            breaker_limit_entity = number_entities.get(self._cpe)

            if not breaker_limit_entity:
                _LOGGER.debug("Breaker limit entity not available for %s", self._cpe)
                self._attr_native_value = None
                return

            breaker_limit = float(breaker_limit_entity.native_value)

            # Check for zero breaker limit to avoid division by zero
            if breaker_limit == 0:
                _LOGGER.warning(
                    "Breaker limit is zero for %s, cannot calculate load", self._cpe
                )
                self._attr_native_value = None
                return

            # Calculate load percentage: Load (%) = (Current / Breaker Limit) * 100
            load_percentage = (current / breaker_limit) * 100

            # Round to integer (no decimals)
            self._attr_native_value = int(round(load_percentage))

            _LOGGER.debug(
                "Calculated breaker load for %s: %d%% (I=%.2f A, Limit=%.1f A)",
                self._cpe,
                int(load_percentage),
                current,
                breaker_limit,
            )

        except (ValueError, TypeError, KeyError) as err:
            _LOGGER.debug("Error calculating breaker load for %s: %s", self._cpe, err)
            self._attr_native_value = None


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


async def async_ensure_calculated_sensors(
    hass: HomeAssistant,
    config_entry_id: str,
    cpe: str,
) -> None:
    """Ensure all calculated sensors exist for a CPE."""
    _LOGGER.debug("Ensuring calculated sensors for CPE %s", cpe)

    entities = hass.data[DOMAIN][config_entry_id]["entities"]

    for sensor_key, sensor_config in CALCULATED_SENSORS.items():
        entity_key = f"{cpe}_{sensor_key}"

        if entity_key in entities:
            _LOGGER.debug("Calculated sensor %s already exists", entity_key)
            continue

        # Check if all source sensors exist before creating calculated sensor
        source_sensors = sensor_config.get("source_sensors", [])
        all_sources_exist = True

        for source_sensor in source_sensors:
            source_key = f"{cpe}_{source_sensor}"
            if source_key not in entities:
                all_sources_exist = False
                _LOGGER.debug(
                    "Source sensor %s not available for calculated sensor %s",
                    source_sensor,
                    sensor_key,
                )
                break

        if not all_sources_exist:
            _LOGGER.debug(
                "Not creating calculated sensor %s - source sensors not available",
                sensor_key,
            )
            continue

        # Check if required number entity exists (e.g., breaker_limit)
        if sensor_config.get("requires_number_entity"):
            number_entity_key = sensor_config["requires_number_entity"]
            number_entities = hass.data[DOMAIN][config_entry_id].get(
                "number_entities", {}
            )
            if cpe not in number_entities:
                _LOGGER.debug(
                    "Required number entity %s not available for calculated sensor %s",
                    number_entity_key,
                    sensor_key,
                )
                continue

        _LOGGER.debug("Creating calculated sensor %s for CPE %s", sensor_key, cpe)

        # Create calculated sensor entity
        sensor = ERedesCalculatedSensor(
            cpe, sensor_key, sensor_config, config_entry_id, hass
        )

        # Add to Home Assistant
        add_entities = hass.data[DOMAIN][config_entry_id]["add_entities"]
        add_entities([sensor])

        # Store reference
        entities[entity_key] = sensor

        _LOGGER.info("Created calculated sensor %s for CPE %s", sensor_key, cpe)


class ERedesDiagnosticSensor(SensorEntity):
    """Representation of an E-Redes diagnostic sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        cpe: str,
        sensor_key: str,
        sensor_config: dict[str, Any],
        config_entry_id: str,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the diagnostic sensor."""
        self._cpe = cpe
        self._sensor_key = sensor_key
        self._config = sensor_config
        self._config_entry_id = config_entry_id
        self._hass = hass
        self._attr_unique_id = f"{DOMAIN}_{cpe}_{sensor_key}"
        self._attr_name = sensor_config["name"]
        self._attr_icon = sensor_config.get("icon")
        self._attr_native_unit_of_measurement = sensor_config.get("unit")
        self._attr_device_class = sensor_config.get("device_class")
        self._attr_state_class = sensor_config.get("state_class")
        self._attr_entity_category = sensor_config.get("entity_category")
        self._attr_entity_registry_enabled_default = sensor_config.get(
            "enabled_by_default", True
        )
        self._attr_native_value = None
        self._last_update_time: datetime | None = None

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

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()

        # Subscribe to webhook updates for this CPE
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_{self._cpe}_webhook_update",
                self._handle_webhook_update,
            )
        )

    @callback
    def _handle_webhook_update(self, timestamp: str | None = None) -> None:
        """Handle webhook update for diagnostic tracking."""
        now = dt_util.utcnow()

        if self._sensor_key == "last_update":
            # Store the actual datetime - Home Assistant will format it
            self._attr_native_value = now

        elif self._sensor_key == "update_interval":
            # Calculate interval between updates in seconds
            if self._last_update_time:
                interval = (now - self._last_update_time).total_seconds()
                self._attr_native_value = round(interval, 1)
            else:
                self._attr_native_value = None

        self._last_update_time = now
        self.async_write_ha_state()


async def async_ensure_diagnostic_sensors(
    hass: HomeAssistant,
    config_entry_id: str,
    cpe: str,
) -> None:
    """Ensure all diagnostic sensors exist for a CPE."""
    _LOGGER.debug("Ensuring diagnostic sensors for CPE %s", cpe)

    entities = hass.data[DOMAIN][config_entry_id]["entities"]

    for sensor_key, sensor_config in DIAGNOSTIC_SENSORS.items():
        entity_key = f"{cpe}_{sensor_key}"

        if entity_key in entities:
            _LOGGER.debug("Diagnostic sensor %s already exists", entity_key)
            continue

        _LOGGER.debug("Creating diagnostic sensor %s for CPE %s", sensor_key, cpe)

        # Create diagnostic sensor entity
        sensor = ERedesDiagnosticSensor(
            cpe, sensor_key, sensor_config, config_entry_id, hass
        )

        # Add to Home Assistant
        add_entities = hass.data[DOMAIN][config_entry_id]["add_entities"]
        add_entities([sensor])

        # Store reference
        entities[entity_key] = sensor

        _LOGGER.info("Created diagnostic sensor %s for CPE %s", sensor_key, cpe)
