"""Select platform for E-Redes Smart Metering Plus."""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import (
    RestoreEntity,
    async_get as async_get_restore,
)

from .const import (
    CONTRACTED_POWER_OPTIONS,
    DOMAIN,
    SINGLE_PHASE_CONTRACTED_POWER_AMPS,
    THREE_PHASE_CONTRACTED_POWER_AMPS,
)
from .models import ERedesConfigEntry, device_info_for_cpe

_LOGGER = logging.getLogger(__name__)


def is_three_phase(config_entry: ERedesConfigEntry, cpe: str) -> bool:
    """Return whether phase-specific E-REDES measurements identify three-phase."""
    entities = config_entry.runtime_data.sensor_entities
    return any(
        f"{cpe}_{sensor_key}" in entities
        for sensor_key in (
            "voltage_l2",
            "voltage_l3",
            "instantaneous_active_power_import_l1",
            "instantaneous_active_power_import_l2",
            "instantaneous_active_power_import_l3",
        )
    )


def contracted_power_options(
    config_entry: ERedesConfigEntry, cpe: str
) -> tuple[str, ...]:
    """Return official contracted-power choices for the detected installation."""
    if is_three_phase(config_entry, cpe):
        return tuple(THREE_PHASE_CONTRACTED_POWER_AMPS)
    return tuple(SINGLE_PHASE_CONTRACTED_POWER_AMPS)


def breaker_limit_amps(
    config_entry: ERedesConfigEntry, cpe: str, option: str | None
) -> float | None:
    """Return the official nominal current for a contracted-power option."""
    if option is None:
        return None
    mapping = (
        THREE_PHASE_CONTRACTED_POWER_AMPS
        if is_three_phase(config_entry, cpe)
        else SINGLE_PHASE_CONTRACTED_POWER_AMPS
    )
    return mapping.get(option)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ERedesConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up contracted-power select entities."""
    config_entry.runtime_data.select_add_entities = async_add_entities
    await async_restore_existing_select_entities(hass, config_entry, async_add_entities)


async def async_restore_existing_select_entities(
    hass: HomeAssistant,
    config_entry: ERedesConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Restore contracted-power selects present in the entity registry."""
    entity_registry = er.async_get(hass)
    entities: list[ERedesContractedPowerSelect] = []
    suffix = "_contracted_power"
    prefix = f"{DOMAIN}_"

    for entity_entry in er.async_entries_for_config_entry(
        entity_registry, config_entry.entry_id
    ):
        if entity_entry.domain != "select" or entity_entry.platform != DOMAIN:
            continue
        if not entity_entry.unique_id.startswith(
            prefix
        ) or not entity_entry.unique_id.endswith(suffix):
            continue
        cpe = entity_entry.unique_id[len(prefix) : -len(suffix)]
        if not cpe:
            continue
        entity = ERedesContractedPowerSelect(cpe, config_entry)
        config_entry.runtime_data.select_entities[cpe] = entity
        entities.append(entity)

    if entities:
        async_add_entities(entities)
        _LOGGER.debug("Restored %d contracted-power selects", len(entities))


@callback
def async_create_contracted_power_entity(
    config_entry: ERedesConfigEntry, cpe: str
) -> None:
    """Create a contracted-power select for a CPE."""
    if cpe in config_entry.runtime_data.select_entities:
        return
    if not (add_entities := config_entry.runtime_data.select_add_entities):
        _LOGGER.warning(
            "Cannot create contracted-power select for %s: add_entities unavailable",
            cpe,
        )
        return

    entity = ERedesContractedPowerSelect(cpe, config_entry)
    config_entry.runtime_data.select_entities[cpe] = entity
    add_entities([entity])


@callback
def async_refresh_contracted_power_entity(
    config_entry: ERedesConfigEntry, cpe: str
) -> None:
    """Refresh choices after payload fields identify the installation type."""
    entity = config_entry.runtime_data.select_entities.get(cpe)
    if isinstance(entity, ERedesContractedPowerSelect):
        entity.async_refresh_options()


class ERedesContractedPowerSelect(SelectEntity, RestoreEntity):
    """Select the contracted power shown on the electricity contract."""

    _attr_has_entity_name = True
    _attr_translation_key = "contracted_power"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_should_poll = False

    def __init__(self, cpe: str, config_entry: ERedesConfigEntry) -> None:
        """Initialize the contracted-power select."""
        self._cpe = cpe
        self._config_entry = config_entry
        self._attr_unique_id = f"{DOMAIN}_{cpe}_contracted_power"
        self._attr_options = list(CONTRACTED_POWER_OPTIONS)
        self._attr_current_option = None
        self._legacy_breaker_limit: float | None = None
        self._legacy_migration_warning_logged = False

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return device_info_for_cpe(self._cpe)

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return stable configuration metadata."""
        return {
            "cpe": self._cpe,
            "installation_type": (
                "three_phase"
                if is_three_phase(self._config_entry, self._cpe)
                else "single_phase"
            ),
        }

    async def async_added_to_hass(self) -> None:
        """Restore the selection or migrate the legacy breaker limit."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) and (
            last_state.state in CONTRACTED_POWER_OPTIONS
        ):
            self._attr_current_option = last_state.state
        else:
            self._legacy_breaker_limit = self._legacy_breaker_limit_from_state()
        self.async_refresh_options()

    def _legacy_breaker_limit_from_state(self) -> float | None:
        """Return the previous number entity value when available."""
        registry = er.async_get(self.hass)
        entity_id = registry.async_get_entity_id(
            "number", DOMAIN, f"{DOMAIN}_{self._cpe}_breaker_limit"
        )
        if entity_id is None:
            return None
        state = self.hass.states.get(entity_id)
        if state is None:
            stored = async_get_restore(self.hass).last_states.get(entity_id)
            state = stored.state if stored else None
        if state is None:
            return None
        try:
            return float(state.state)
        except (TypeError, ValueError):
            return None

    @callback
    def async_refresh_options(self) -> None:
        """Update phase-appropriate options and migrate a matching legacy value."""
        self._attr_options = list(
            contracted_power_options(self._config_entry, self._cpe)
        )
        if self._attr_current_option not in self._attr_options:
            if self._attr_current_option is not None:
                _LOGGER.warning(
                    "Cleared contracted power for %s because it is not valid for the detected installation type",
                    self._cpe,
                )
            self._attr_current_option = None

        if self._attr_current_option is None and self._legacy_breaker_limit is not None:
            mapping = (
                THREE_PHASE_CONTRACTED_POWER_AMPS
                if is_three_phase(self._config_entry, self._cpe)
                else SINGLE_PHASE_CONTRACTED_POWER_AMPS
            )
            self._attr_current_option = next(
                (
                    option
                    for option, amps in mapping.items()
                    if amps == self._legacy_breaker_limit
                ),
                None,
            )
            if self._attr_current_option is not None:
                _LOGGER.info(
                    "Migrated legacy breaker limit for %s to contracted power %s",
                    self._cpe,
                    self._attr_current_option,
                )
                self._legacy_breaker_limit = None
            elif not self._legacy_migration_warning_logged:
                _LOGGER.warning(
                    "Legacy breaker limit %.2f A for %s does not match an official contracted-power tier; select the value shown on the electricity contract",
                    self._legacy_breaker_limit,
                    self._cpe,
                )
                self._legacy_migration_warning_logged = True

        if self.hass is not None:
            self.async_write_ha_state()
            self._notify_dependants()

    async def async_select_option(self, option: str) -> None:
        """Select a contracted-power option."""
        self._attr_current_option = option
        self.async_write_ha_state()
        self._notify_dependants()

    @callback
    def _notify_dependants(self) -> None:
        """Notify calculated entities that the configured limit changed."""
        async_dispatcher_send(
            self.hass,
            f"{DOMAIN}_{self._cpe}_contracted_power_update",
            self._attr_current_option,
        )
