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

    sensor_key = SENSOR_MAPPING[field_name].key
    unique_id = f"{DOMAIN}_{payload['cpe']}_{sensor_key}"

    ent_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
    assert ent_id is not None

    state = hass.states.get(ent_id)
    assert state is not None
    assert pytest.approx(float(state.state)) == float(value)

    # Ensure device info attributes are exposed
    assert state.attributes.get("cpe") == payload["cpe"]


async def test_total_sensor_accepts_corrections_and_ignores_older_payloads(
    hass: HomeAssistant, hass_client, config_entry
) -> None:
    """Test that total sensors accept newer corrections but ignore stale payloads."""

    client = await hass_client()
    cpe = "CPE_TEST_001"

    # Send initial value
    initial_value = 10000.0
    payload = {
        "cpe": cpe,
        "SourceTimestamp": "2026-08-30 12:00:00",
        "activeEnergyImport": initial_value,
    }
    resp = await client.post(
        f"/api/webhook/{config_entry.data['webhook_id']}",
        json=payload,
    )
    assert resp.status == 200
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    sensor_key = SENSOR_MAPPING["activeEnergyImport"].key
    unique_id = f"{DOMAIN}_{cpe}_{sensor_key}"
    ent_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
    assert ent_id is not None

    # Verify initial state
    state = hass.states.get(ent_id)
    assert state is not None
    assert float(state.state) == initial_value
    assert state.attributes["state_class"] == "total"

    # Send increasing value - should update
    increasing_value = 10500.0
    payload = {
        "cpe": cpe,
        "SourceTimestamp": "2026-08-30 12:02:00",
        "activeEnergyImport": increasing_value,
    }
    resp = await client.post(
        f"/api/webhook/{config_entry.data['webhook_id']}",
        json=payload,
    )
    assert resp.status == 200
    await hass.async_block_till_done()

    state = hass.states.get(ent_id)
    assert state is not None
    assert float(state.state) == increasing_value

    # An older payload should be ignored, regardless of its value.
    stale_value = 9500.0
    payload = {
        "cpe": cpe,
        "SourceTimestamp": "2026-08-30 12:01:00",
        "activeEnergyImport": stale_value,
    }
    resp = await client.post(
        f"/api/webhook/{config_entry.data['webhook_id']}",
        json=payload,
    )
    assert resp.status == 200
    await hass.async_block_till_done()

    state = hass.states.get(ent_id)
    assert state is not None
    assert float(state.state) == increasing_value

    # A newer downward correction should be accepted.
    corrected_value = 10450.0
    payload = {
        "cpe": cpe,
        "SourceTimestamp": "2026-08-30 12:03:00",
        "activeEnergyImport": corrected_value,
    }
    resp = await client.post(
        f"/api/webhook/{config_entry.data['webhook_id']}",
        json=payload,
    )
    assert resp.status == 200
    await hass.async_block_till_done()

    state = hass.states.get(ent_id)
    assert state is not None
    assert float(state.state) == corrected_value


async def test_measurement_sensors_allow_any_values(
    hass: HomeAssistant, hass_client, config_entry
) -> None:
    """Test that measurement sensors accept any value changes."""

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
    sensor_key = SENSOR_MAPPING["instantaneousActivePowerImport"].key
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
    # Expected active-current estimate: 2300 / 230 = 10.0 A

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

    # Check that the calculated current estimate was created.
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
    # Expected active-current estimate: 4600 / 230 = 20.0 A

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
    assert state.attributes["estimated"] is True
    assert state.attributes["estimate_basis"] == "active_power_divided_by_voltage"


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


async def test_three_phase_current_sensors_use_matching_phase_data(
    hass: HomeAssistant, hass_client, config_entry
) -> None:
    """Test that three-phase currents use only matching phase measurements."""
    client = await hass_client()
    cpe = "TEST123"
    payload = {
        "cpe": cpe,
        "instantaneousActivePowerImport": 8050.0,
        "voltageL1": 230.0,
        "voltageL2": 220.0,
        "voltageL3": 240.0,
        "instantaneousActivePowerImportL1": 2300.0,
        "instantaneousActivePowerImportL2": 1100.0,
        "instantaneousActivePowerImportL3": 4800.0,
    }

    response = await client.post(
        f"/api/webhook/{config_entry.data['webhook_id']}", json=payload
    )
    assert response.status == 200
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    for phase, expected_current in ((1, 10.0), (2, 5.0), (3, 20.0)):
        unique_id = f"{DOMAIN}_{cpe}_instantaneous_active_current_import_l{phase}"
        entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
        assert entity_id is not None
        state = hass.states.get(entity_id)
        assert state is not None
        assert float(state.state) == pytest.approx(expected_current)

    aggregate_unique_id = f"{DOMAIN}_{cpe}_instantaneous_active_current_import"
    assert (
        entity_registry.async_get_entity_id("sensor", DOMAIN, aggregate_unique_id)
        is None
    )

    contracted_power_id = entity_registry.async_get_entity_id(
        "select", DOMAIN, f"{DOMAIN}_{cpe}_contracted_power"
    )
    assert contracted_power_id is not None
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": contracted_power_id, "option": "13.80 kVA"},
        blocking=True,
    )
    await hass.async_block_till_done()

    usage_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{DOMAIN}_{cpe}_contracted_power_usage"
    )
    assert usage_id is not None
    usage = hass.states.get(usage_id)
    assert usage is not None
    assert float(usage.state) == pytest.approx(100.0)


async def test_three_phase_usage_requires_phase_power_measurements(
    hass: HomeAssistant, hass_client, config_entry
) -> None:
    """Three-phase usage must not derive a phase current from aggregate power."""
    client = await hass_client()
    cpe = "TEST123"
    response = await client.post(
        f"/api/webhook/{config_entry.data['webhook_id']}",
        json={
            "cpe": cpe,
            "instantaneousActivePowerImport": 13800.0,
            "voltageL1": 230.0,
            "voltageL2": 230.0,
            "voltageL3": 230.0,
        },
    )
    assert response.status == 200
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    contracted_power_id = entity_registry.async_get_entity_id(
        "select", DOMAIN, f"{DOMAIN}_{cpe}_contracted_power"
    )
    assert contracted_power_id is not None
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": contracted_power_id, "option": "13.80 kVA"},
        blocking=True,
    )
    await hass.async_block_till_done()

    usage_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{DOMAIN}_{cpe}_contracted_power_usage"
    )
    assert usage_id is not None
    usage = hass.states.get(usage_id)
    assert usage is not None
    assert usage.state == "unavailable"


async def test_contracted_power_usage_sensor(
    hass: HomeAssistant, hass_client, config_entry
) -> None:
    """Test that contracted-power usage is calculated correctly."""

    client = await hass_client()
    cpe = "CPE_USAGE_TEST"

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

    contracted_power_id = entity_registry.async_get_entity_id(
        "select", DOMAIN, f"{DOMAIN}_{cpe}_contracted_power"
    )
    assert contracted_power_id is not None
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": contracted_power_id, "option": "4.60 kVA"},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Check that the contracted-power usage sensor was created.
    usage_sensor_key = "contracted_power_usage"
    unique_id = f"{DOMAIN}_{cpe}_{usage_sensor_key}"
    ent_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
    assert ent_id is not None

    # Get the state
    state = hass.states.get(ent_id)
    assert state is not None

    # With 4.60 kVA (20A) selected, the 20A active current is 100% load.
    expected_load = 100
    assert int(float(state.state)) == expected_load

    # Check attributes
    assert state.attributes.get("unit_of_measurement") == "%"
    assert state.attributes.get("cpe") == cpe
    assert state.attributes.get("calculation_type") == "contracted_power_usage"
    assert state.attributes["estimated"] is True
    assert state.attributes["estimate_basis"] == "active_power_and_voltage"
    assert state.attributes["power_factor_assumption"] == 1.0

    # Select 6.90 kVA, corresponding to 30A for a single-phase installation.
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": contracted_power_id, "option": "6.90 kVA"},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Check that contracted-power usage updated to 66.67% (20A / 30A).
    state = hass.states.get(ent_id)
    assert state is not None
    assert float(state.state) == pytest.approx(66.67, rel=0.01)

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

    # Check that contracted-power usage updated to 33.33% (10A / 30A).
    state = hass.states.get(ent_id)
    assert state is not None
    assert float(state.state) == pytest.approx(33.33, rel=0.01)
