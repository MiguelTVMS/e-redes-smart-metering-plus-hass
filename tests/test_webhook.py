"""Webhook tests for the E-Redes Smart Metering Plus integration."""

from __future__ import annotations

import json
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.e_redes_smart_metering_plus.const import DOMAIN, SENSOR_MAPPING
from custom_components.e_redes_smart_metering_plus.webhook import handle_webhook


pytestmark = pytest.mark.asyncio


class DummyRequest:
    """A minimal request object exposing only an async json() method."""

    def __init__(self, payload):
        self._payload = payload

    async def json(self):  # noqa: D401 - simple passthrough
        return self._payload


@pytest.mark.parametrize(
    "payload",
    [
        {
            "cpe": "1234567890",
            "instantaneousActivePowerImport": 1200,
            "clock": "2025-08-11T12:00:00",
        },
        {
            "cpe": "ABCDEF",
            "activeEnergyImport": 5.25,
        },
    ],
)
async def test_webhook_creates_and_updates_sensors(
    hass: HomeAssistant, config_entry, payload: dict
) -> None:
    """Posting webhook data should create entities and update their state."""

    resp = await handle_webhook(
        hass, config_entry.data["webhook_id"], DummyRequest(
            payload), config_entry
    )
    assert resp.status == 200
    assert resp.text == "OK"

    await hass.async_block_till_done()

    # Validate that the corresponding entity exists and has expected state
    entity_registry = er.async_get(hass)

    # Determine which field maps to a sensor key
    first_field = next(k for k in payload if k !=
                       "cpe" and k in SENSOR_MAPPING)
    sensor_key = SENSOR_MAPPING[first_field]["key"]

    unique_id = f"{DOMAIN}_{payload['cpe']}_{sensor_key}"
    entity_entry = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, unique_id)
    assert entity_entry is not None, "Sensor entity should be created in registry"

    state = hass.states.get(entity_entry)
    assert state is not None
    assert state.state not in (None, "unknown", "unavailable")

    # Numeric conversion in HA stores as string state; compare as float
    expected = payload[first_field]
    assert pytest.approx(float(state.state)) == float(expected)

    # Attributes
    assert state.attributes.get("cpe") == payload["cpe"]
    # For the specific import power sensor, webhook URL attributes are exposed
    if sensor_key == "instantaneous_active_power_import":
        assert "integration_webhook_url" in state.attributes
        assert state.attributes.get("webhook_info")
        assert state.attributes.get("configuration_note")


async def test_webhook_missing_cpe_returns_400(
    hass: HomeAssistant, config_entry
) -> None:
    """Webhook should respond 400 when 'cpe' is missing."""

    resp = await handle_webhook(
        hass,
        config_entry.data["webhook_id"],
        DummyRequest({"instantaneousActivePowerImport": 100}),
        config_entry,
    )
    assert resp.status == 400
    assert resp.text == "Missing 'cpe' field"


async def test_webhook_invalid_json_returns_400(
    hass: HomeAssistant, config_entry
) -> None:
    """Webhook should respond 400 on invalid JSON body."""

    class BadRequest:
        async def json(self):  # noqa: D401
            raise json.JSONDecodeError("bad", "{}", 0)

    resp = await handle_webhook(
        hass, config_entry.data["webhook_id"], BadRequest(), config_entry
    )
    assert resp.status == 400
    assert resp.text == "Invalid JSON"


async def test_webhook_ignores_unknown_fields(
    hass: HomeAssistant, config_entry
) -> None:
    """Unknown fields in payload should be ignored and not create entities."""

    payload = {"cpe": "XYZ", "foo": 1, "bar": 2}

    resp = await handle_webhook(
        hass, config_entry.data["webhook_id"], DummyRequest(
            payload), config_entry
    )
    assert resp.status == 200

    # Ensure no entities were created for unknown fields
    entity_registry = er.async_get(hass)
    for key in ("foo", "bar"):
        unique_id = f"{DOMAIN}_{payload['cpe']}_{key}"
        ent_id = entity_registry.async_get_entity_id(
            "sensor", DOMAIN, unique_id)
        assert ent_id is None
