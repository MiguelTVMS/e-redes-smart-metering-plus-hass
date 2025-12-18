"""Tests for the number platform of the E-Redes Smart Metering Plus integration."""

from __future__ import annotations

import pytest

from custom_components.e_redes_smart_metering_plus.const import DOMAIN
from custom_components.e_redes_smart_metering_plus.number import (
    DEFAULT_BREAKER_LIMIT,
    async_create_breaker_limit_entity,
)
from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

pytestmark = pytest.mark.asyncio

TEST_CPE = "PT0002000012345678900"


async def test_number_entity_created_for_device(
    hass: HomeAssistant, config_entry
) -> None:
    """Test that a number entity is created when a device is discovered."""
    cpe = TEST_CPE

    # Create the breaker limit entity
    async_create_breaker_limit_entity(hass, config_entry.entry_id, cpe)
    await hass.async_block_till_done()

    # Check that the number entity exists
    entity_registry = er.async_get(hass)
    # Entity ID is lowercase by Home Assistant
    entity_id = f"number.e_redes_smart_meter_{cpe.lower()}_breaker_limit"

    # Find the entity in the registry
    entity_entry = entity_registry.async_get(entity_id)
    assert entity_entry is not None
    assert entity_entry.domain == NUMBER_DOMAIN
    assert entity_entry.unique_id == f"{DOMAIN}_{cpe}_breaker_limit"


async def test_number_entity_default_value(hass: HomeAssistant, config_entry) -> None:
    """Test that the number entity has the correct default value."""
    cpe = TEST_CPE

    # Create the breaker limit entity
    async_create_breaker_limit_entity(hass, config_entry.entry_id, cpe)
    await hass.async_block_till_done()

    # Get the state
    entity_id = f"number.e_redes_smart_meter_{cpe.lower()}_breaker_limit"
    state = hass.states.get(entity_id)

    assert state is not None
    assert float(state.state) == DEFAULT_BREAKER_LIMIT


async def test_number_entity_set_value(hass: HomeAssistant, config_entry) -> None:
    """Test that the number entity value can be set."""
    cpe = TEST_CPE

    # Create the breaker limit entity
    async_create_breaker_limit_entity(hass, config_entry.entry_id, cpe)
    await hass.async_block_till_done()

    # Set a new value
    entity_id = f"number.e_redes_smart_meter_{cpe.lower()}_breaker_limit"
    await hass.services.async_call(
        NUMBER_DOMAIN,
        "set_value",
        {"entity_id": entity_id, "value": 32},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Check the new value
    state = hass.states.get(entity_id)
    assert state is not None
    assert float(state.state) == 32


async def test_number_entity_restore_state(hass: HomeAssistant, config_entry) -> None:
    """Test that the number entity restores its previous state."""
    cpe = TEST_CPE

    # Create the breaker limit entity
    async_create_breaker_limit_entity(hass, config_entry.entry_id, cpe)
    await hass.async_block_till_done()

    # Set a custom value
    entity_id = f"number.e_redes_smart_meter_{cpe.lower()}_breaker_limit"
    await hass.services.async_call(
        NUMBER_DOMAIN,
        "set_value",
        {"entity_id": entity_id, "value": 40},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Verify the value
    state = hass.states.get(entity_id)
    assert state is not None
    assert float(state.state) == 40

    # Unload the integration
    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    # Reload the integration
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Recreate the entity (simulating device discovery)
    async_create_breaker_limit_entity(hass, config_entry.entry_id, cpe)
    await hass.async_block_till_done()

    # Check that the value was restored
    state = hass.states.get(entity_id)
    assert state is not None
    assert float(state.state) == 40


async def test_number_entity_attributes(hass: HomeAssistant, config_entry) -> None:
    """Test that the number entity has the correct attributes."""
    cpe = TEST_CPE

    # Create the breaker limit entity
    async_create_breaker_limit_entity(hass, config_entry.entry_id, cpe)
    await hass.async_block_till_done()

    # Get the state
    entity_id = f"number.e_redes_smart_meter_{cpe.lower()}_breaker_limit"
    state = hass.states.get(entity_id)

    assert state is not None
    assert state.attributes.get("unit_of_measurement") == "A"
    assert state.attributes.get("cpe") == cpe
    assert state.attributes.get("min") == 1
    assert state.attributes.get("max") == 200
    assert state.attributes.get("step") == 1


async def test_number_entity_restored_from_registry(
    hass: HomeAssistant, config_entry
) -> None:
    """Test that number entities are restored from entity registry on restart."""
    cpe = TEST_CPE

    # Create the breaker limit entity
    async_create_breaker_limit_entity(hass, config_entry.entry_id, cpe)
    await hass.async_block_till_done()

    # Verify it was created
    entity_id = f"number.e_redes_smart_meter_{cpe.lower()}_breaker_limit"
    state = hass.states.get(entity_id)
    assert state is not None
    assert float(state.state) == DEFAULT_BREAKER_LIMIT

    # Get entity registry to verify it's registered
    entity_registry = er.async_get(hass)
    entity_entry = entity_registry.async_get(entity_id)
    assert entity_entry is not None
    assert entity_entry.unique_id == f"{DOMAIN}_{cpe}_breaker_limit"

    # Now simulate a restart by unloading and reloading the config entry
    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    # Reload the integration
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Verify the entity was restored (should exist even without webhook data)
    state = hass.states.get(entity_id)
    assert state is not None
    # The state should be restored from the entity registry
    assert state.state is not None


async def test_number_entity_custom_value_persists(
    hass: HomeAssistant, config_entry
) -> None:
    """Test that custom breaker limit value persists across restarts."""
    cpe = TEST_CPE

    # Create the breaker limit entity
    async_create_breaker_limit_entity(hass, config_entry.entry_id, cpe)
    await hass.async_block_till_done()

    entity_id = f"number.e_redes_smart_meter_{cpe.lower()}_breaker_limit"

    # Verify initial default value
    state = hass.states.get(entity_id)
    assert state is not None
    assert float(state.state) == DEFAULT_BREAKER_LIMIT

    # Set a custom value
    custom_value = 32.0
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": entity_id, "value": custom_value},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Verify the custom value was set
    state = hass.states.get(entity_id)
    assert state is not None
    assert float(state.state) == custom_value

    # Simulate a restart by unloading and reloading the config entry
    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    # Reload the integration
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Verify the custom value persisted after restart
    state = hass.states.get(entity_id)
    assert state is not None
    assert float(state.state) == custom_value, (
        f"Custom value {custom_value} was not persisted. " f"Got {state.state} instead."
    )
