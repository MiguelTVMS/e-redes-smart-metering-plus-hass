"""Tests for the binary sensor platform of E-Redes Smart Metering Plus integration."""

from __future__ import annotations

import pytest

from custom_components.e_redes_smart_metering_plus.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

pytestmark = pytest.mark.asyncio


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

    entity_registry = er.async_get(hass)
    unique_id = f"{DOMAIN}_{cpe}_breaker_overload"
    ent_id = entity_registry.async_get_entity_id("binary_sensor", DOMAIN, unique_id)
    assert ent_id is not None

    # With default 20A limit, 23A = 115% -> should be ON
    state = hass.states.get(ent_id)
    assert state is not None
    assert state.state == "on"

    # Increase breaker limit to 32A (23A / 32A = 71.875%)
    breaker_limit_entity_id = f"number.e_redes_smart_meter_{cpe.lower()}_breaker_limit"
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": breaker_limit_entity_id, "value": 32.0},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Should now be OFF (no overload)
    state = hass.states.get(ent_id)
    assert state is not None
    assert state.state == "off"
