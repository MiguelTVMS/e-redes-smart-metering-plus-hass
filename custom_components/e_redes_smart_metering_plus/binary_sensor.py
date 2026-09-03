"""Binary sensor platform for E-Redes Smart Metering Plus."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONTRACTED_POWER_USAGE_CRITICAL_PERCENT,
    CONTRACTED_POWER_USAGE_EXCEEDED_PERCENT,
    CONTRACTED_POWER_USAGE_WARNING_PERCENT,
    DOMAIN,
)
from .models import ERedesConfigEntry, device_info_for_cpe

_LOGGER = logging.getLogger(__name__)

_PROBLEM_THRESHOLDS = {
    "contracted_power_usage_warning": CONTRACTED_POWER_USAGE_WARNING_PERCENT,
    "contracted_power_usage_critical": CONTRACTED_POWER_USAGE_CRITICAL_PERCENT,
    "contracted_power_exceeded": CONTRACTED_POWER_USAGE_EXCEEDED_PERCENT,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ERedesConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up contracted-power problem binary sensors."""
    config_entry.runtime_data.binary_sensor_add_entities = async_add_entities
    await async_restore_existing_binary_sensors(hass, config_entry, async_add_entities)


async def async_restore_existing_binary_sensors(
    hass: HomeAssistant,
    config_entry: ERedesConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Restore contracted-power problem entities from the entity registry."""
    registry = er.async_get(hass)
    entities: list[ERedesContractedPowerProblemSensor] = []
    prefix = f"{DOMAIN}_"

    for entity_entry in er.async_entries_for_config_entry(
        registry, config_entry.entry_id
    ):
        if entity_entry.domain != "binary_sensor" or entity_entry.platform != DOMAIN:
            continue
        if not entity_entry.unique_id.startswith(prefix):
            continue
        remainder = entity_entry.unique_id[len(prefix) :]
        for sensor_key, threshold in _PROBLEM_THRESHOLDS.items():
            suffix = f"_{sensor_key}"
            if not remainder.endswith(suffix):
                continue
            cpe = remainder[: -len(suffix)]
            if not cpe:
                break
            entity = ERedesContractedPowerProblemSensor(
                cpe, config_entry, sensor_key, threshold
            )
            config_entry.runtime_data.binary_sensor_entities[f"{cpe}_{sensor_key}"] = (
                entity
            )
            entities.append(entity)
            break

    if entities:
        async_add_entities(entities)
        _LOGGER.debug("Restored %d contracted-power problem sensors", len(entities))


@callback
def async_create_contracted_power_problem_sensors(
    config_entry: ERedesConfigEntry, cpe: str
) -> None:
    """Create warning, critical, and exceeded sensors for a CPE."""
    if not (add_entities := config_entry.runtime_data.binary_sensor_add_entities):
        _LOGGER.warning(
            "Cannot create contracted-power problem sensors for %s: add_entities unavailable",
            cpe,
        )
        return

    entities: list[ERedesContractedPowerProblemSensor] = []
    for sensor_key, threshold in _PROBLEM_THRESHOLDS.items():
        entity_key = f"{cpe}_{sensor_key}"
        if entity_key in config_entry.runtime_data.binary_sensor_entities:
            continue
        entity = ERedesContractedPowerProblemSensor(
            cpe, config_entry, sensor_key, threshold
        )
        config_entry.runtime_data.binary_sensor_entities[entity_key] = entity
        entities.append(entity)

    if entities:
        add_entities(entities)


class ERedesContractedPowerProblemSensor(BinarySensorEntity):
    """Represent one contracted-power usage severity threshold."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_should_poll = False

    def __init__(
        self,
        cpe: str,
        config_entry: ERedesConfigEntry,
        sensor_key: str,
        threshold: float,
    ) -> None:
        """Initialize a contracted-power problem sensor."""
        self._cpe = cpe
        self._config_entry = config_entry
        self._threshold = threshold
        self._attr_translation_key = sensor_key
        self._attr_unique_id = f"{DOMAIN}_{cpe}_{sensor_key}"
        self._attr_is_on = False

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return device_info_for_cpe(self._cpe)

    @property
    def extra_state_attributes(self) -> dict[str, float | str]:
        """Return threshold metadata."""
        return {"cpe": self._cpe, "threshold": self._threshold}

    @property
    def available(self) -> bool:
        """Return whether contracted-power usage is available."""
        usage_sensor = self._config_entry.runtime_data.sensor_entities.get(
            f"{self._cpe}_contracted_power_usage"
        )
        return usage_sensor is not None and usage_sensor.native_value is not None

    async def async_added_to_hass(self) -> None:
        """Subscribe to contracted-power usage updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_{self._cpe}_contracted_power_usage_update",
                self._handle_contracted_power_usage_update,
            )
        )
        self._update_problem_state()

    @callback
    def _handle_contracted_power_usage_update(self) -> None:
        """Update after contracted-power usage changes."""
        self._update_problem_state()
        self.async_write_ha_state()

    def _update_problem_state(self) -> None:
        """Set the problem state from the configured load threshold."""
        usage_sensor = self._config_entry.runtime_data.sensor_entities.get(
            f"{self._cpe}_contracted_power_usage"
        )
        if usage_sensor is None or usage_sensor.native_value is None:
            self._attr_is_on = False
            return
        try:
            self._attr_is_on = float(str(usage_sensor.native_value)) >= self._threshold
        except (TypeError, ValueError):
            self._attr_is_on = False
