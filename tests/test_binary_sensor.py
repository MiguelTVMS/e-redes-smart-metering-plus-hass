"""Tests for the binary sensor platform of E-Redes Smart Metering Plus integration."""

from __future__ import annotations

import pytest

from custom_components.e_redes_smart_metering_plus.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

pytestmark = pytest.mark.asyncio


async def _select_contracted_power(
    hass: HomeAssistant, cpe: str, option: str = "4.60 kVA"
) -> None:
    """Select contracted power for a test meter."""
    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id(
        "select", DOMAIN, f"{DOMAIN}_{cpe}_contracted_power"
    )
    assert entity_id is not None
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": entity_id, "option": option},
        blocking=True,
    )
    await hass.async_block_till_done()


async def test_breaker_overload_sensor_off_when_under_100(
    hass: HomeAssistant, hass_client, config_entry
) -> None:
    """Test that breaker overload sensor is OFF when load is under 100%."""

    client = await hass_client()
    cpe = "CPE_OVERLOAD_TEST_1"

    # Send webhook data with load under 100% (2300W / 230V = 10A, with 20A limit = 50%)
    payload = {
        "cpe": cpe,
        "instantaneousActivePowerImport": 2300.0,
        "voltageL1": 230.0,
    }
    resp = await client.post(
        f"/api/webhook/{config_entry.data['webhook_id']}",
        json=payload,
    )
    assert resp.status == 200
    await hass.async_block_till_done()
    await _select_contracted_power(hass, cpe)

    entity_registry = er.async_get(hass)

    # Check that breaker overload sensor was created
    unique_id = f"{DOMAIN}_{cpe}_breaker_overload"
    ent_id = entity_registry.async_get_entity_id("binary_sensor", DOMAIN, unique_id)
    assert ent_id is not None

    # Get the state
    state = hass.states.get(ent_id)
    assert state is not None

    # Should be OFF (no overload) when load is 50%
    assert state.state == "off"
    assert state.attributes.get("device_class") == "problem"


async def test_load_entities_unavailable_until_contracted_power_selected(
    hass: HomeAssistant, hass_client, config_entry
) -> None:
    """Load entities must not claim a state before explicit configuration."""
    client = await hass_client()
    cpe = "CPE_OVERLOAD_TEST_1"
    response = await client.post(
        f"/api/webhook/{config_entry.data['webhook_id']}",
        json={
            "cpe": cpe,
            "instantaneousActivePowerImport": 2300.0,
            "voltageL1": 230.0,
        },
    )
    assert response.status == 200
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    entity_ids = [
        registry.async_get_entity_id("sensor", DOMAIN, f"{DOMAIN}_{cpe}_breaker_load"),
        registry.async_get_entity_id(
            "sensor", DOMAIN, f"{DOMAIN}_{cpe}_breaker_load_status"
        ),
        registry.async_get_entity_id(
            "binary_sensor", DOMAIN, f"{DOMAIN}_{cpe}_breaker_load_warning"
        ),
        registry.async_get_entity_id(
            "binary_sensor", DOMAIN, f"{DOMAIN}_{cpe}_breaker_load_critical"
        ),
        registry.async_get_entity_id(
            "binary_sensor", DOMAIN, f"{DOMAIN}_{cpe}_breaker_overload"
        ),
    ]
    assert all(entity_ids)
    for entity_id in entity_ids:
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == "unavailable"


async def test_breaker_overload_sensor_on_when_over_100(
    hass: HomeAssistant, hass_client, config_entry
) -> None:
    """Test that breaker overload sensor is ON when load exceeds 100%."""

    client = await hass_client()
    cpe = "CPE_OVERLOAD_TEST_2"

    # Send webhook data with load over 100% (5750W / 230V = 25A, with 20A limit = 125%)
    payload = {
        "cpe": cpe,
        "instantaneousActivePowerImport": 5750.0,
        "voltageL1": 230.0,
    }
    resp = await client.post(
        f"/api/webhook/{config_entry.data['webhook_id']}",
        json=payload,
    )
    assert resp.status == 200
    await hass.async_block_till_done()
    await hass.async_block_till_done()  # Second wait for async signal
    await _select_contracted_power(hass, cpe)

    entity_registry = er.async_get(hass)

    # Check that breaker overload sensor exists
    unique_id = f"{DOMAIN}_{cpe}_breaker_overload"
    ent_id = entity_registry.async_get_entity_id("binary_sensor", DOMAIN, unique_id)
    assert ent_id is not None

    # Get the state
    state = hass.states.get(ent_id)
    assert state is not None

    # Should be ON (overload) when load is 125%
    assert state.state == "on"


async def test_breaker_overload_sensor_updates_with_load_changes(
    hass: HomeAssistant, hass_client, config_entry
) -> None:
    """Test that breaker overload sensor updates when load changes."""

    client = await hass_client()
    cpe = "CPE_OVERLOAD_TEST_3"

    # Start with normal load (under 100%)
    payload = {
        "cpe": cpe,
        "instantaneousActivePowerImport": 2300.0,  # 10A with 230V
        "voltageL1": 230.0,
    }
    resp = await client.post(
        f"/api/webhook/{config_entry.data['webhook_id']}",
        json=payload,
    )
    assert resp.status == 200
    await hass.async_block_till_done()
    await hass.async_block_till_done()  # Second wait for async signal
    await _select_contracted_power(hass, cpe)

    entity_registry = er.async_get(hass)
    unique_id = f"{DOMAIN}_{cpe}_breaker_overload"
    ent_id = entity_registry.async_get_entity_id("binary_sensor", DOMAIN, unique_id)
    assert ent_id is not None

    # Should be OFF
    state = hass.states.get(ent_id)
    assert state is not None
    assert state.state == "off"

    # Increase load to overload (125%)
    payload = {
        "cpe": cpe,
        "instantaneousActivePowerImport": 5750.0,
        "voltageL1": 230.0,
    }
    resp = await client.post(
        f"/api/webhook/{config_entry.data['webhook_id']}",
        json=payload,
    )
    assert resp.status == 200
    await hass.async_block_till_done()

    # Should now be ON
    state = hass.states.get(ent_id)
    assert state is not None
    assert state.state == "on"

    # Decrease load back to normal (50%)
    payload = {
        "cpe": cpe,
        "instantaneousActivePowerImport": 2300.0,
        "voltageL1": 230.0,
    }
    resp = await client.post(
        f"/api/webhook/{config_entry.data['webhook_id']}",
        json=payload,
    )
    assert resp.status == 200
    await hass.async_block_till_done()

    # Should be OFF again
    state = hass.states.get(ent_id)
    assert state is not None
    assert state.state == "off"


async def test_breaker_overload_sensor_updates_with_limit_changes(
    hass: HomeAssistant, hass_client, config_entry
) -> None:
    """Test that breaker overload sensor updates when breaker limit changes."""

    client = await hass_client()
    cpe = "CPE_OVERLOAD_TEST_4"

    # Send webhook data with normal load (5290W / 230V = 23A, with 20A limit = 115%)
    payload = {
        "cpe": cpe,
        "instantaneousActivePowerImport": 5290.0,
        "voltageL1": 230.0,
    }
    resp = await client.post(
        f"/api/webhook/{config_entry.data['webhook_id']}",
        json=payload,
    )
    assert resp.status == 200
    await hass.async_block_till_done()
    await hass.async_block_till_done()  # Second wait for async signal
    await _select_contracted_power(hass, cpe)

    entity_registry = er.async_get(hass)
    unique_id = f"{DOMAIN}_{cpe}_breaker_overload"
    ent_id = entity_registry.async_get_entity_id("binary_sensor", DOMAIN, unique_id)
    assert ent_id is not None

    # With default 20A limit, 23A = 115% -> should be ON
    state = hass.states.get(ent_id)
    assert state is not None
    assert state.state == "on"

    # Select 6.90 kVA, corresponding to 30A (23A / 30A = 76.67%).
    await _select_contracted_power(hass, cpe, "6.90 kVA")

    # Should now be OFF (no overload)
    state = hass.states.get(ent_id)
    assert state is not None
    assert state.state == "off"


async def test_breaker_problem_levels_and_status(
    hass: HomeAssistant, hass_client, config_entry
) -> None:
    """Warning, critical, overload, and enum status follow cumulative levels."""
    client = await hass_client()
    cpe = "CPE_OVERLOAD_TEST_1"
    entity_registry = er.async_get(hass)

    async def send_load(load_percent: float) -> None:
        response = await client.post(
            f"/api/webhook/{config_entry.data['webhook_id']}",
            json={
                "cpe": cpe,
                "instantaneousActivePowerImport": 4600 * load_percent / 100,
                "voltageL1": 230.0,
            },
        )
        assert response.status == 200
        await hass.async_block_till_done()

    await send_load(70)
    await _select_contracted_power(hass, cpe)

    expected_levels = (
        (70, ("off", "off", "off"), "normal"),
        (85, ("on", "off", "off"), "warning"),
        (97, ("on", "on", "off"), "critical"),
        (100, ("on", "on", "on"), "overload"),
    )
    sensor_keys = (
        "breaker_load_warning",
        "breaker_load_critical",
        "breaker_overload",
    )

    for load, expected_binary_states, expected_status in expected_levels:
        await send_load(load)
        for sensor_key, expected_state in zip(
            sensor_keys, expected_binary_states, strict=True
        ):
            entity_id = entity_registry.async_get_entity_id(
                "binary_sensor", DOMAIN, f"{DOMAIN}_{cpe}_{sensor_key}"
            )
            assert entity_id is not None
            state = hass.states.get(entity_id)
            assert state is not None
            assert state.state == expected_state

        status_id = entity_registry.async_get_entity_id(
            "sensor", DOMAIN, f"{DOMAIN}_{cpe}_breaker_load_status"
        )
        assert status_id is not None
        status = hass.states.get(status_id)
        assert status is not None
        assert status.state == expected_status
