"""Tests for E-Redes Smart Metering Plus setup."""

from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.e_redes_smart_metering_plus import async_setup_entry
from custom_components.e_redes_smart_metering_plus.const import DOMAIN
from custom_components.e_redes_smart_metering_plus.sensor import (
    async_ensure_sensors_for_data,
)
from homeassistant.core import HomeAssistant


async def test_platforms_ready_before_webhook_registration(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Webhook setup must not run before dynamic entity callbacks are ready."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="E-Redes Smart Metering Plus",
        data={},
    )
    entry.add_to_hass(hass)

    setup_order: list[str] = []
    added_entities: list[object] = []

    async def mock_forward_entry_setups(config_entry, platforms) -> None:
        setup_order.append("platforms")
        hass.data[DOMAIN][config_entry.entry_id]["add_entities"] = (
            added_entities.extend
        )

    async def mock_setup_webhook(hass_instance, config_entry) -> str:
        setup_order.append("webhook")
        await async_ensure_sensors_for_data(
            hass_instance,
            config_entry.entry_id,
            "STARTUP_CPE",
            {"activeEnergyImport": 12345},
        )
        return DOMAIN

    monkeypatch.setattr(
        hass.config_entries,
        "async_forward_entry_setups",
        mock_forward_entry_setups,
    )
    monkeypatch.setattr(
        "custom_components.e_redes_smart_metering_plus.async_setup_webhook",
        mock_setup_webhook,
    )

    assert await async_setup_entry(hass, entry)
    assert setup_order == ["platforms", "webhook"]
    assert len(added_entities) == 1
