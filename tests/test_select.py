"""Tests for contracted-power selection."""

from __future__ import annotations

import pytest

from custom_components.e_redes_smart_metering_plus.const import DOMAIN
from custom_components.e_redes_smart_metering_plus.select import (
    async_create_contracted_power_entity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

pytestmark = pytest.mark.asyncio

TEST_CPE = "PT0002000012345678900"


def _select_entity_id(hass: HomeAssistant, cpe: str) -> str:
    """Return the contracted-power select entity ID."""
    entity_id = er.async_get(hass).async_get_entity_id(
        "select", DOMAIN, f"{DOMAIN}_{cpe}_contracted_power"
    )
    assert entity_id is not None
    return entity_id


async def test_select_has_no_invented_default(
    hass: HomeAssistant, config_entry
) -> None:
    """A new meter requires an explicit contracted-power choice."""
    async_create_contracted_power_entity(config_entry, TEST_CPE)
    await hass.async_block_till_done()

    state = hass.states.get(_select_entity_id(hass, TEST_CPE))
    assert state is not None
    assert state.state == "unknown"
    assert state.attributes["options"] == [
        "1.15 kVA",
        "2.30 kVA",
        "3.45 kVA",
        "4.60 kVA",
        "5.75 kVA",
        "6.90 kVA",
        "10.35 kVA",
        "13.80 kVA",
    ]


async def test_select_restores_selected_option(
    hass: HomeAssistant, config_entry
) -> None:
    """The selected contracted power persists across reloads."""
    async_create_contracted_power_entity(config_entry, TEST_CPE)
    await hass.async_block_till_done()
    entity_id = _select_entity_id(hass, TEST_CPE)

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": entity_id, "option": "6.90 kVA"},
        blocking=True,
    )
    await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "6.90 kVA"


async def test_three_phase_payload_uses_three_phase_options(
    hass: HomeAssistant, hass_client, config_entry
) -> None:
    """Phase-discriminated data changes the select to official three-phase tiers."""
    client = await hass_client()
    response = await client.post(
        f"/api/webhook/{config_entry.data['webhook_id']}",
        json={
            "cpe": "TEST123",
            "voltageL1": 230,
            "voltageL2": 231,
            "voltageL3": 229,
            "instantaneousActivePowerImportL1": 100,
            "instantaneousActivePowerImportL2": 200,
            "instantaneousActivePowerImportL3": 300,
        },
    )
    assert response.status == 200
    await hass.async_block_till_done()

    state = hass.states.get(_select_entity_id(hass, "TEST123"))
    assert state is not None
    assert state.attributes["installation_type"] == "three_phase"
    assert state.attributes["options"] == [
        "6.90 kVA",
        "10.35 kVA",
        "13.80 kVA",
        "17.25 kVA",
        "20.70 kVA",
        "27.60 kVA",
        "34.50 kVA",
        "41.40 kVA",
    ]


async def test_standard_legacy_breaker_limit_is_migrated(
    hass: HomeAssistant, config_entry
) -> None:
    """A standard legacy amp value becomes its matching contracted-power tier."""
    registry = er.async_get(hass)
    legacy = registry.async_get_or_create(
        domain="number",
        platform=DOMAIN,
        config_entry=config_entry,
        unique_id=f"{DOMAIN}_{TEST_CPE}_breaker_limit",
    )
    hass.states.async_set(legacy.entity_id, "20")

    async_create_contracted_power_entity(config_entry, TEST_CPE)
    await hass.async_block_till_done()

    state = hass.states.get(_select_entity_id(hass, TEST_CPE))
    assert state is not None
    assert state.state == "4.60 kVA"
