"""Sensor platform for E-Redes Smart Metering Plus."""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import (
    CALCULATED_SENSORS,
    CONTRACTED_POWER_USAGE_CRITICAL_PERCENT,
    CONTRACTED_POWER_USAGE_EXCEEDED_PERCENT,
    CONTRACTED_POWER_USAGE_WARNING_PERCENT,
    DIAGNOSTIC_SENSORS,
    DOMAIN,
    SENSOR_DESCRIPTIONS_BY_KEY,
    SENSOR_MAPPING,
    ERedesCalculatedSensorEntityDescription,
    ERedesSensorEntityDescription,
)
from .models import ERedesConfigEntry, device_info_for_cpe
from .select import contracted_power_limit_amps, is_three_phase

_LOGGER = logging.getLogger(__name__)

_PHASES = (1, 2, 3)
_SINGLE_PHASE_CURRENT_KEY = "instantaneous_active_current_import"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ERedesConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    config_entry.runtime_data.sensor_add_entities = async_add_entities
    await async_restore_existing_entities(hass, config_entry, async_add_entities)


async def async_restore_existing_entities(
    hass: HomeAssistant,
    config_entry: ERedesConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Restore sensors which are already present in the entity registry."""
    entity_registry = er.async_get(hass)
    entities_to_restore: list[SensorEntity] = []

    for entity_entry in er.async_entries_for_config_entry(
        entity_registry, config_entry.entry_id
    ):
        if entity_entry.domain != "sensor" or entity_entry.platform != DOMAIN:
            continue

        parsed = _description_from_unique_id(entity_entry.unique_id)
        if parsed is None:
            continue
        cpe, description = parsed

        if isinstance(description, ERedesCalculatedSensorEntityDescription):
            sensor: SensorEntity = ERedesCalculatedSensor(
                cpe, description, config_entry
            )
        elif isinstance(description, ERedesSensorEntityDescription):
            sensor = ERedesSensor(cpe, description, config_entry)
        else:
            sensor = ERedesDiagnosticSensor(cpe, description, config_entry)

        config_entry.runtime_data.sensor_entities[f"{cpe}_{description.key}"] = sensor
        entities_to_restore.append(sensor)

    if entities_to_restore:
        async_add_entities(entities_to_restore)
        _LOGGER.debug("Restored %d sensor entities", len(entities_to_restore))


def _description_from_unique_id(
    unique_id: str,
) -> tuple[str, SensorEntityDescription] | None:
    """Extract the CPE and entity description from an existing unique ID."""
    prefix = f"{DOMAIN}_"
    if not unique_id.startswith(prefix):
        return None

    remainder = unique_id[len(prefix) :]
    descriptions = (
        *SENSOR_DESCRIPTIONS_BY_KEY.values(),
        *CALCULATED_SENSORS.values(),
        *DIAGNOSTIC_SENSORS.values(),
    )
    for description in descriptions:
        suffix = f"_{description.key}"
        if remainder.endswith(suffix):
            cpe = remainder[: -len(suffix)]
            if cpe:
                return cpe, description
    return None


def _timestamp_value(timestamp: str | None) -> datetime:
    """Parse an E-REDES timestamp as an aware UTC datetime."""
    if timestamp:
        try:
            parsed = datetime.fromisoformat(timestamp.replace(" ", "T"))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
        except (TypeError, ValueError):
            pass
    return dt_util.utcnow()


class ERedesSensor(RestoreSensor):
    """Represent a measurement supplied directly by E-REDES."""

    entity_description: ERedesSensorEntityDescription
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        cpe: str,
        description: ERedesSensorEntityDescription,
        config_entry: ERedesConfigEntry,
        initial_value: float | None = None,
        initial_timestamp: str | None = None,
    ) -> None:
        """Initialize the sensor."""
        self.entity_description = description
        self._cpe = cpe
        self._config_entry = config_entry
        self._attr_unique_id = f"{DOMAIN}_{cpe}_{description.key}"
        self._attr_native_value = initial_value
        self._last_update = (
            _timestamp_value(initial_timestamp) if initial_value is not None else None
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return device_info_for_cpe(self._cpe)

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return stable meter metadata."""
        return {"cpe": self._cpe}

    async def async_added_to_hass(self) -> None:
        """Restore state and subscribe to webhook updates."""
        await super().async_added_to_hass()
        if self._attr_native_value is None and (
            restored := await self.async_get_last_sensor_data()
        ):
            self._attr_native_value = restored.native_value

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_{self._cpe}_{self.entity_description.key}_update",
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self, value: float, timestamp: str | None = None) -> None:
        """Handle a validated webhook measurement."""
        self._attr_native_value = value
        self._last_update = _timestamp_value(timestamp)
        self.async_write_ha_state()


class ERedesCalculatedSensor(RestoreSensor):
    """Represent a value calculated from E-REDES measurements."""

    entity_description: ERedesCalculatedSensorEntityDescription
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        cpe: str,
        description: ERedesCalculatedSensorEntityDescription,
        config_entry: ERedesConfigEntry,
    ) -> None:
        """Initialize the calculated sensor."""
        self.entity_description = description
        self._cpe = cpe
        self._config_entry = config_entry
        self._attr_unique_id = f"{DOMAIN}_{cpe}_{description.key}"
        self._attr_native_value = None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return device_info_for_cpe(self._cpe)

    @property
    def available(self) -> bool:
        """Return whether load entities have valid configured inputs."""
        if self.entity_description.key in {
            "contracted_power_usage",
            "contracted_power_usage_status",
        }:
            return self.native_value is not None
        return True

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return stable calculation metadata."""
        attributes: dict[str, Any] = {
            "cpe": self._cpe,
            "calculation_type": self.entity_description.calculation,
            "source_sensors": self.entity_description.source_sensors,
        }
        if self.entity_description.calculation == "power_voltage":
            attributes.update(
                {
                    "estimated": True,
                    "estimate_basis": "active_power_divided_by_voltage",
                }
            )
        if self.entity_description.key in {
            "contracted_power_usage",
            "contracted_power_usage_status",
        }:
            select_entity = self._config_entry.runtime_data.select_entities.get(
                self._cpe
            )
            selected_option = (
                select_entity.current_option if select_entity is not None else None
            )
            attributes.update(
                {
                    "contracted_power": selected_option,
                    "contracted_power_current_limit_amps": contracted_power_limit_amps(
                        self._config_entry, self._cpe, selected_option
                    ),
                    "installation_type": (
                        "three_phase"
                        if is_three_phase(self._config_entry, self._cpe)
                        else "single_phase"
                    ),
                    "estimated": True,
                    "estimate_basis": "active_power_and_voltage",
                    "power_factor_assumption": 1.0,
                }
            )
            if current_and_phase := self._usage_current_and_phase():
                attributes["limiting_phase"] = current_and_phase[1]
        return attributes

    async def async_added_to_hass(self) -> None:
        """Restore state and subscribe to source updates."""
        await super().async_added_to_hass()
        if restored := await self.async_get_last_sensor_data():
            self._attr_native_value = restored.native_value

        source_sensors = set(self.entity_description.source_sensors)
        if self.entity_description.key in {
            _SINGLE_PHASE_CURRENT_KEY,
            "contracted_power_usage",
        }:
            for phase in _PHASES:
                source_sensors.update(
                    {
                        f"instantaneous_active_power_import_l{phase}",
                        f"voltage_l{phase}",
                    }
                )

        for source_sensor in source_sensors:
            self.async_on_remove(
                async_dispatcher_connect(
                    self.hass,
                    f"{DOMAIN}_{self._cpe}_{source_sensor}_update",
                    self._handle_source_update,
                )
            )

        if select_key := self.entity_description.requires_select_entity:
            self.async_on_remove(
                async_dispatcher_connect(
                    self.hass,
                    f"{DOMAIN}_{self._cpe}_{select_key}_update",
                    self._handle_config_entity_update,
                )
            )

        calculated = self._calculate_value()
        if calculated is not None or self.entity_description.key in {
            "contracted_power_usage",
            "contracted_power_usage_status",
        }:
            self._attr_native_value = calculated
        self._notify_contracted_power_usage_update()

    @callback
    def _handle_source_update(self, *_args: Any) -> None:
        """Recalculate after a source sensor update."""
        self._attr_native_value = self._calculate_value()
        self.async_write_ha_state()
        self._notify_contracted_power_usage_update()

    @callback
    def _handle_config_entity_update(self, *_args: Any) -> None:
        """Recalculate after the contracted-power selection changes."""
        self._attr_native_value = self._calculate_value()
        self.async_write_ha_state()
        self._notify_contracted_power_usage_update()

    def _notify_contracted_power_usage_update(self) -> None:
        """Notify problem sensors when contracted-power usage changes."""
        if self.entity_description.key == "contracted_power_usage":
            async_dispatcher_send(
                self.hass, f"{DOMAIN}_{self._cpe}_contracted_power_usage_update"
            )

    def _calculate_value(self) -> float | str | None:
        """Calculate the current value from runtime entities."""
        if self.entity_description.calculation == "power_voltage":
            return self._calculate_current_from_power_voltage()
        if self.entity_description.calculation == "contracted_power_usage":
            return self._calculate_contracted_power_usage()
        if self.entity_description.calculation == "contracted_power_usage_status":
            return self._calculate_contracted_power_usage_status()
        _LOGGER.warning(
            "Unknown calculation type: %s", self.entity_description.calculation
        )
        return None

    def _power_and_voltage(self) -> tuple[float, float] | None:
        """Return current power and voltage source values."""
        power_key, voltage_key = self.entity_description.source_sensors[:2]
        return self._sensor_values(power_key, voltage_key)

    def _sensor_values(
        self, power_key: str, voltage_key: str
    ) -> tuple[float, float] | None:
        """Return numeric values for matching power and voltage sensors."""
        entities = self._config_entry.runtime_data.sensor_entities
        power_sensor = entities.get(f"{self._cpe}_{power_key}")
        voltage_sensor = entities.get(f"{self._cpe}_{voltage_key}")
        if (
            power_sensor is None
            or power_sensor.native_value is None
            or voltage_sensor is None
            or voltage_sensor.native_value is None
        ):
            return None
        try:
            power = float(str(power_sensor.native_value))
            voltage = float(str(voltage_sensor.native_value))
        except (TypeError, ValueError):
            return None
        if voltage == 0:
            return None
        return power, voltage

    def _calculate_current_from_power_voltage(self) -> float | None:
        """Estimate the active component of current from power and voltage."""
        if (
            self.entity_description.key == _SINGLE_PHASE_CURRENT_KEY
            and self._has_phase_power()
        ):
            return None
        if (values := self._power_and_voltage()) is None:
            return None
        power, voltage = values
        return power / voltage

    def _has_phase_power(self) -> bool:
        """Return whether E-REDES supplied any phase-specific import power."""
        entities = self._config_entry.runtime_data.sensor_entities
        return any(
            f"{self._cpe}_instantaneous_active_power_import_l{phase}" in entities
            for phase in _PHASES
        )

    def _phase_currents(self) -> list[tuple[float, str]]:
        """Return estimated active currents for phases with matching values."""
        entities = self._config_entry.runtime_data.sensor_entities
        currents: list[tuple[float, str]] = []
        for phase in _PHASES:
            power_sensor = entities.get(
                f"{self._cpe}_instantaneous_active_power_import_l{phase}"
            )
            voltage_sensor = entities.get(f"{self._cpe}_voltage_l{phase}")
            if (
                power_sensor is None
                or power_sensor.native_value is None
                or voltage_sensor is None
                or voltage_sensor.native_value is None
            ):
                continue
            try:
                power = float(str(power_sensor.native_value))
                voltage = float(str(voltage_sensor.native_value))
            except (TypeError, ValueError):
                continue
            if voltage != 0:
                currents.append((power / voltage, f"L{phase}"))
        return currents

    def _usage_current_and_phase(self) -> tuple[float, str] | None:
        """Return the highest estimated active current and its phase."""
        if is_three_phase(self._config_entry, self._cpe):
            if not (currents := self._phase_currents()):
                return None
            return max(currents, key=lambda value: value[0])
        if (
            values := self._sensor_values(
                "instantaneous_active_power_import", "voltage_l1"
            )
        ) is None:
            return None
        power, voltage = values
        return power / voltage, "single_phase"

    def _calculate_contracted_power_usage(self) -> float | None:
        """Estimate contracted-power usage from active power and voltage."""
        if (current_and_phase := self._usage_current_and_phase()) is None:
            return None
        current, _phase = current_and_phase
        select_entity = self._config_entry.runtime_data.select_entities.get(self._cpe)
        selected_option = (
            select_entity.current_option if select_entity is not None else None
        )
        current_limit = contracted_power_limit_amps(
            self._config_entry, self._cpe, selected_option
        )
        if current_limit is None or current_limit <= 0:
            return None
        return current / current_limit * 100

    def _calculate_contracted_power_usage_status(self) -> str | None:
        """Return the severity corresponding to contracted-power usage."""
        usage_sensor = self._config_entry.runtime_data.sensor_entities.get(
            f"{self._cpe}_contracted_power_usage"
        )
        if usage_sensor is None or usage_sensor.native_value is None:
            return None
        try:
            usage = float(str(usage_sensor.native_value))
        except (TypeError, ValueError):
            return None
        if usage >= CONTRACTED_POWER_USAGE_EXCEEDED_PERCENT:
            return "exceeded"
        if usage >= CONTRACTED_POWER_USAGE_CRITICAL_PERCENT:
            return "critical"
        if usage >= CONTRACTED_POWER_USAGE_WARNING_PERCENT:
            return "warning"
        return "normal"


async def async_create_sensor_for_cpe(
    config_entry: ERedesConfigEntry,
    cpe: str,
    field_name: str,
    value: float,
    timestamp: str | None,
) -> None:
    """Create a sensor entity for a specific CPE and payload field."""
    if (description := SENSOR_MAPPING.get(field_name)) is None:
        return

    entity_key = f"{cpe}_{description.key}"
    if entity_key in config_entry.runtime_data.sensor_entities:
        return

    sensor = ERedesSensor(cpe, description, config_entry, value, timestamp)
    config_entry.runtime_data.sensor_entities[entity_key] = sensor
    if add_entities := config_entry.runtime_data.sensor_add_entities:
        add_entities([sensor])


async def async_ensure_sensors_for_data(
    config_entry: ERedesConfigEntry,
    cpe: str,
    data: dict[str, Any],
    timestamp: str | None = None,
) -> None:
    """Ensure sensors exist for all supported measurements in a payload."""
    for field_name, value in data.items():
        if field_name in SENSOR_MAPPING:
            await async_create_sensor_for_cpe(
                config_entry, cpe, field_name, float(value), timestamp
            )


async def async_ensure_calculated_sensors(
    config_entry: ERedesConfigEntry,
    cpe: str,
) -> None:
    """Ensure calculated sensors exist when all their dependencies are present."""
    entities = config_entry.runtime_data.sensor_entities
    has_phase_power = any(
        f"{cpe}_instantaneous_active_power_import_l{phase}" in entities
        for phase in _PHASES
    )

    for sensor_key, description in CALCULATED_SENSORS.items():
        entity_key = f"{cpe}_{sensor_key}"
        if entity_key in entities:
            continue
        if sensor_key == _SINGLE_PHASE_CURRENT_KEY and has_phase_power:
            continue
        has_description_sources = all(
            f"{cpe}_{source_sensor}" in entities
            for source_sensor in description.source_sensors
        )
        has_complete_phase = any(
            f"{cpe}_instantaneous_active_power_import_l{phase}" in entities
            and f"{cpe}_voltage_l{phase}" in entities
            for phase in _PHASES
        )
        if not has_description_sources and not (
            sensor_key == "contracted_power_usage" and has_complete_phase
        ):
            continue
        if description.requires_select_entity and (
            cpe not in config_entry.runtime_data.select_entities
        ):
            continue

        sensor = ERedesCalculatedSensor(cpe, description, config_entry)
        entities[entity_key] = sensor
        if add_entities := config_entry.runtime_data.sensor_add_entities:
            add_entities([sensor])


class ERedesDiagnosticSensor(SensorEntity):
    """Represent webhook diagnostics for one meter."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        cpe: str,
        description: SensorEntityDescription,
        config_entry: ERedesConfigEntry,
    ) -> None:
        """Initialize the diagnostic sensor."""
        self.entity_description = description
        self._cpe = cpe
        self._attr_unique_id = f"{DOMAIN}_{cpe}_{description.key}"
        self._attr_native_value = None
        self._last_update_time: datetime | None = None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return device_info_for_cpe(self._cpe)

    async def async_added_to_hass(self) -> None:
        """Subscribe to webhook receipt events."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_{self._cpe}_webhook_update",
                self._handle_webhook_update,
            )
        )

    @callback
    def _handle_webhook_update(self, _timestamp: str | None = None) -> None:
        """Update receipt time diagnostics."""
        now = dt_util.utcnow()
        if self.entity_description.key == "last_update":
            self._attr_native_value = now
        elif self.entity_description.key == "update_interval":
            self._attr_native_value = (
                (now - self._last_update_time).total_seconds()
                if self._last_update_time
                else None
            )
        self._last_update_time = now
        self.async_write_ha_state()


async def async_ensure_diagnostic_sensors(
    config_entry: ERedesConfigEntry,
    cpe: str,
) -> None:
    """Ensure diagnostic sensors exist for a CPE."""
    entities = config_entry.runtime_data.sensor_entities
    for sensor_key, description in DIAGNOSTIC_SENSORS.items():
        entity_key = f"{cpe}_{sensor_key}"
        if entity_key in entities:
            continue
        sensor = ERedesDiagnosticSensor(cpe, description, config_entry)
        entities[entity_key] = sensor
        if add_entities := config_entry.runtime_data.sensor_add_entities:
            add_entities([sensor])
