"""Tests focused on sensor behavior for the E-Redes Smart Metering Plus integration."""

from __future__ import annotations

import pytest

from custom_components.e_redes_smart_metering_plus.const import DOMAIN, SENSOR_MAPPING
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize(
    "field_name,value",
    [
        ("instantaneousActivePowerImport", 987),
        ("activeEnergyImport", 12340),
        ("activeEnergyExport", 5450),
        ("voltageL1", 230.5),
    ],
)
async def test_sensor_state_and_unique_id(
    hass: HomeAssistant, hass_client, config_entry, field_name: str, value: float
) -> None:
    """Verify entity unique_id scheme and state updates via dispatcher from webhook."""

    client = await hass_client()

    payload = {"cpe": "CPE001", field_name: value}
    resp = await client.post(
        f"/api/webhook/{config_entry.data['webhook_id']}",
        json=payload,
    )
    assert resp.status == 200
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)

    sensor_key = SENSOR_MAPPING[field_name]["key"]
    unique_id = f"{DOMAIN}_{payload['cpe']}_{sensor_key}"

    ent_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
    assert ent_id is not None

    state = hass.states.get(ent_id)
    assert state is not None
    assert pytest.approx(float(state.state)) == float(value)

    # Ensure device info attributes are exposed
    assert state.attributes.get("cpe") == payload["cpe"]


async def test_total_increasing_prevents_decreasing_values(
    hass: HomeAssistant, hass_client, config_entry
) -> None:
    """Test that total_increasing sensors reject decreasing values."""

    client = await hass_client()
    cpe = "CPE_TEST_001"

    # Send initial value
    initial_value = 10000.0
    payload = {"cpe": cpe, "activeEnergyImport": initial_value}
    resp = await client.post(
        f"/api/webhook/{config_entry.data['webhook_id']}",
        json=payload,
    )
    assert resp.status == 200
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    sensor_key = SENSOR_MAPPING["activeEnergyImport"]["key"]
    unique_id = f"{DOMAIN}_{cpe}_{sensor_key}"
    ent_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
    assert ent_id is not None

    # Verify initial state
    state = hass.states.get(ent_id)
    assert state is not None
    assert float(state.state) == initial_value

    # Send increasing value - should update
    increasing_value = 10500.0
    payload = {"cpe": cpe, "activeEnergyImport": increasing_value}
    resp = await client.post(
        f"/api/webhook/{config_entry.data['webhook_id']}",
        json=payload,
    )
    assert resp.status == 200
    await hass.async_block_till_done()

    state = hass.states.get(ent_id)
    assert state is not None
    assert float(state.state) == increasing_value

    # Send decreasing value - should be rejected and state should remain unchanged
    decreasing_value = 9500.0
    payload = {"cpe": cpe, "activeEnergyImport": decreasing_value}
    resp = await client.post(
        f"/api/webhook/{config_entry.data['webhook_id']}",
        json=payload,
    )
    assert resp.status == 200
    await hass.async_block_till_done()

    # State should still be the previous increasing value
    state = hass.states.get(ent_id)
    assert state is not None
    assert float(state.state) == increasing_value  # Should not have changed

    # Send another increasing value - should update again
    next_increasing_value = 11000.0
    payload = {"cpe": cpe, "activeEnergyImport": next_increasing_value}
    resp = await client.post(
        f"/api/webhook/{config_entry.data['webhook_id']}",
        json=payload,
    )
    assert resp.status == 200
    await hass.async_block_till_done()

    state = hass.states.get(ent_id)
    assert state is not None
    assert float(state.state) == next_increasing_value


async def test_measurement_sensors_allow_any_values(
    hass: HomeAssistant, hass_client, config_entry
) -> None:
    """Test that measurement sensors (not total_increasing) accept any value changes."""

    client = await hass_client()
    cpe = "CPE_TEST_002"

    # Send initial value for power sensor (state_class: measurement)
    initial_value = 5000.0
    payload = {"cpe": cpe, "instantaneousActivePowerImport": initial_value}
    resp = await client.post(
        f"/api/webhook/{config_entry.data['webhook_id']}",
        json=payload,
    )
    assert resp.status == 200
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    sensor_key = SENSOR_MAPPING["instantaneousActivePowerImport"]["key"]
    unique_id = f"{DOMAIN}_{cpe}_{sensor_key}"
    ent_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
    assert ent_id is not None

    state = hass.states.get(ent_id)
    assert state is not None
    assert float(state.state) == initial_value

    # Send decreasing value - should be accepted for measurement sensors
    decreasing_value = 2000.0
    payload = {"cpe": cpe, "instantaneousActivePowerImport": decreasing_value}
    resp = await client.post(
        f"/api/webhook/{config_entry.data['webhook_id']}",
        json=payload,
    )
    assert resp.status == 200
    await hass.async_block_till_done()

    state = hass.states.get(ent_id)
    assert state is not None
    assert float(state.state) == decreasing_value  # Should have updated


async def test_calculated_current_sensor(
    hass: HomeAssistant, hass_client, config_entry
) -> None:
    """Test that calculated current sensor is created and calculates correctly."""

    client = await hass_client()
    cpe = "CPE_TEST_CALC"

    # Send power and voltage data
    power = 2300.0  # W
    voltage = 230.0  # V
    # Expected current: 2300 / 230 = 10.0 A

    payload = {
        "cpe": cpe,
        "instantaneousActivePowerImport": power,
        "voltageL1": voltage,
    }
    resp = await client.post(
        f"/api/webhook/{config_entry.data['webhook_id']}",
        json=payload,
    )
    assert resp.status == 200
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)

    # Check that calculated current sensor was created
    calculated_sensor_key = "instantaneous_active_current_import"
    unique_id = f"{DOMAIN}_{cpe}_{calculated_sensor_key}"
    ent_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
    assert ent_id is not None

    # Verify calculated value
    state = hass.states.get(ent_id)
    assert state is not None
    assert float(state.state) == pytest.approx(10.0, rel=0.01)  # 2300W / 230V = 10A

    # Test with different values
    power = 4600.0  # W
    voltage = 230.0  # V
    # Expected current: 4600 / 230 = 20.0 A

    payload = {
        "cpe": cpe,
        "instantaneousActivePowerImport": power,
        "voltageL1": voltage,
    }
    resp = await client.post(
        f"/api/webhook/{config_entry.data['webhook_id']}",
        json=payload,
    )
    assert resp.status == 200
    await hass.async_block_till_done()

    # Verify updated calculated value
    state = hass.states.get(ent_id)
    assert state is not None
    assert float(state.state) == pytest.approx(20.0, rel=0.01)  # 4600W / 230V = 20A

    # Check attributes
    assert state.attributes.get("unit_of_measurement") == "A"
    assert state.attributes.get("device_class") == "current"
    assert state.attributes.get("cpe") == cpe


async def test_calculated_current_sensor_unknown_when_missing_data(
    hass: HomeAssistant, hass_client, config_entry
) -> None:
    """Test that calculated current sensor shows unknown when source data is missing."""

    client = await hass_client()
    cpe = "CPE_TEST_UNKNOWN"

    # Send only power data (no voltage)
    payload = {
        "cpe": cpe,
        "instantaneousActivePowerImport": 2300.0,
    }
    resp = await client.post(
        f"/api/webhook/{config_entry.data['webhook_id']}",
        json=payload,
    )
    assert resp.status == 200
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)

    # Calculated sensor should not be created if voltage is missing
    calculated_sensor_key = "instantaneous_active_current_import"
    unique_id = f"{DOMAIN}_{cpe}_{calculated_sensor_key}"
    ent_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)

    # Should be None because voltage sensor doesn't exist yet
    assert ent_id is None

    # Now send voltage data
    payload = {
        "cpe": cpe,
        "voltageL1": 230.0,
    }
    resp = await client.post(
        f"/api/webhook/{config_entry.data['webhook_id']}",
        json=payload,
    )
    assert resp.status == 200
    await hass.async_block_till_done()

    # Now calculated sensor should be created
    ent_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
    assert ent_id is not None

    # Verify calculated value
    state = hass.states.get(ent_id)
    assert state is not None
    # Should be calculated now: 2300W / 230V = 10A
    assert float(state.state) == pytest.approx(10.0, rel=0.01)


async def test_breaker_load_sensor(
    hass: HomeAssistant, hass_client, config_entry
) -> None:
    """Test that breaker load sensor calculates percentage correctly."""

    client = await hass_client()
    cpe = "CPE_BREAKER_TEST"

    # Send complete webhook data (power and voltage)
    payload = {
        "cpe": cpe,
        "instantaneousActivePowerImport": 4600.0,  # 4600W
        "voltageL1": 230.0,  # 230V -> 20A current
    }
    resp = await client.post(
        f"/api/webhook/{config_entry.data['webhook_id']}",
        json=payload,
    )
    assert resp.status == 200
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)

    # Check that breaker load sensor was created
    breaker_load_sensor_key = "breaker_load"
    unique_id = f"{DOMAIN}_{cpe}_{breaker_load_sensor_key}"
    ent_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
    assert ent_id is not None

    # Get the state
    state = hass.states.get(ent_id)
    assert state is not None

    # With default breaker limit of 20A and current of 20A (4600W / 230V)
    # Load should be 100% (no decimals)
    expected_load = 100
    assert int(float(state.state)) == expected_load

    # Check attributes
    assert state.attributes.get("unit_of_measurement") == "%"
    assert state.attributes.get("cpe") == cpe
    assert state.attributes.get("calculation_type") == "current_breaker_limit"

    # Now update breaker limit to 40A
    breaker_limit_entity_id = f"number.e_redes_smart_meter_{cpe.lower()}_breaker_limit"
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": breaker_limit_entity_id, "value": 40.0},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Check that breaker load updated to 50% (20A / 40A * 100, no decimals)
    state = hass.states.get(ent_id)
    assert state is not None
    expected_load = 50
    assert int(float(state.state)) == expected_load

    # Send new power data: 2300W -> 10A current
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

    # Check that breaker load updated to 25% (10A / 40A * 100, no decimals)
    state = hass.states.get(ent_id)
    assert state is not None
    expected_load = 25
    assert int(float(state.state)) == expected_load
