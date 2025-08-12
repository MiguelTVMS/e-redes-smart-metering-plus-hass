"""Tests focused on sensor behavior for the E-Redes Smart Metering Plus integration."""

from __future__ import annotations

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.e_redes_smart_metering_plus.const import DOMAIN, SENSOR_MAPPING


pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize(
    "field_name,value",
    [
        ("instantaneousActivePowerImport", 987),
        ("activeEnergyImport", 12.34),
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
