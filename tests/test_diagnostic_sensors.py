"""Tests for E-Redes Smart Metering Plus diagnostic sensors."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.e_redes_smart_metering_plus.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory


@pytest.fixture
async def config_entry(hass: HomeAssistant):
    """Create a config entry fixture."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "webhook_id": DOMAIN,
        },
        entry_id="test_entry_diagnostic",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_diagnostic_sensors_disabled_by_default(
    hass: HomeAssistant, hass_client, config_entry
) -> None:
    """Test that diagnostic sensors are disabled by default."""

    client = await hass_client()
    cpe = "CPE_DIAGNOSTIC_TEST_1"

    # Send webhook data to create device and sensors
    payload = {
        "cpe": cpe,
        "instantaneousActivePowerImport": 1000.0,
        "voltageL1": 230.0,
    }
    resp = await client.post(
        f"/api/webhook/{config_entry.data['webhook_id']}",
        json=payload,
    )
    assert resp.status == 200
    await hass.async_block_till_done()
    await hass.async_block_till_done()
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)

    # Check that last_update sensor exists but is disabled by default
    last_update_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{DOMAIN}_{cpe}_last_update"
    )
    assert last_update_id is not None
    last_update_entry = entity_registry.async_get(last_update_id)
    assert last_update_entry is not None
    assert last_update_entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION

    # Check that update_interval sensor exists but is disabled by default
    interval_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{DOMAIN}_{cpe}_update_interval"
    )
    assert interval_id is not None
    interval_entry = entity_registry.async_get(interval_id)
    assert interval_entry is not None
    assert interval_entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION


async def test_last_update_sensor_created(
    hass: HomeAssistant, hass_client, config_entry
) -> None:
    """Test that last update diagnostic sensor is created."""

    client = await hass_client()
    cpe = "CPE_DIAGNOSTIC_TEST_2"

    entity_registry = er.async_get(hass)

    # Send webhook to create sensors
    payload = {
        "cpe": cpe,
        "instantaneousActivePowerImport": 1000.0,
        "voltageL1": 230.0,
    }
    resp = await client.post(
        f"/api/webhook/{config_entry.data['webhook_id']}",
        json=payload,
    )
    assert resp.status == 200
    await hass.async_block_till_done()
    await hass.async_block_till_done()
    await hass.async_block_till_done()

    # Check that last_update sensor exists
    last_update_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{DOMAIN}_{cpe}_last_update"
    )
    assert last_update_id is not None

    # Verify sensor has correct attributes
    last_update_entry = entity_registry.async_get(last_update_id)
    assert last_update_entry is not None
    assert last_update_entry.entity_category == EntityCategory.DIAGNOSTIC
    assert last_update_entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION


async def test_update_interval_sensor_created(
    hass: HomeAssistant, hass_client, config_entry
) -> None:
    """Test that update interval diagnostic sensor is created."""

    client = await hass_client()
    cpe = "CPE_DIAGNOSTIC_TEST_3"

    entity_registry = er.async_get(hass)

    # Send webhook to create sensors
    payload = {
        "cpe": cpe,
        "instantaneousActivePowerImport": 1000.0,
        "voltageL1": 230.0,
    }
    resp = await client.post(
        f"/api/webhook/{config_entry.data['webhook_id']}",
        json=payload,
    )
    assert resp.status == 200
    await hass.async_block_till_done()
    await hass.async_block_till_done()
    await hass.async_block_till_done()

    # Check that update_interval sensor exists
    interval_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{DOMAIN}_{cpe}_update_interval"
    )
    assert interval_id is not None

    # Verify sensor has correct attributes
    interval_entry = entity_registry.async_get(interval_id)
    assert interval_entry is not None
    assert interval_entry.entity_category == EntityCategory.DIAGNOSTIC
    assert interval_entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION


async def test_diagnostic_sensors_are_diagnostic_category(
    hass: HomeAssistant, hass_client, config_entry
) -> None:
    """Test that diagnostic sensors have diagnostic entity category."""

    client = await hass_client()
    cpe = "CPE_DIAGNOSTIC_TEST_4"

    # Send webhook data
    payload = {
        "cpe": cpe,
        "instantaneousActivePowerImport": 1000.0,
        "voltageL1": 230.0,
    }
    resp = await client.post(
        f"/api/webhook/{config_entry.data['webhook_id']}",
        json=payload,
    )
    assert resp.status == 200
    await hass.async_block_till_done()
    await hass.async_block_till_done()
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)

    # Check last_update sensor category
    last_update_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{DOMAIN}_{cpe}_last_update"
    )
    assert last_update_id is not None
    last_update_entry = entity_registry.async_get(last_update_id)
    assert last_update_entry is not None
    assert last_update_entry.entity_category == EntityCategory.DIAGNOSTIC

    # Check update_interval sensor category
    interval_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{DOMAIN}_{cpe}_update_interval"
    )
    assert interval_id is not None
    interval_entry = entity_registry.async_get(interval_id)
    assert interval_entry is not None
    assert interval_entry.entity_category == EntityCategory.DIAGNOSTIC
