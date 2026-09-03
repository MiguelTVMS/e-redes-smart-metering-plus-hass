"""Tests for the config flow of the E-Redes Smart Metering Plus integration."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from custom_components.e_redes_smart_metering_plus.const import (
    CONF_CPES,
    DOMAIN,
    WEBHOOK_ID,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

pytestmark = pytest.mark.asyncio

TEST_CPE = "PT000000000000000000"


async def test_show_form(hass: HomeAssistant) -> None:
    """Test that the first step shows a form with webhook preview URL."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    # Ensure description placeholders includes webhook_url
    placeholders = result.get("description_placeholders") or {}
    assert "webhook_url" in placeholders
    assert placeholders["webhook_url"].startswith("http")


async def test_create_entry(hass: HomeAssistant) -> None:
    """Test creating the entry from the user step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == "form"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_CPES: [TEST_CPE]}
    )

    assert result2["type"] == "create_entry"
    assert result2["title"] == "E-Redes Smart Metering Plus"
    data = result2["data"]
    assert "webhook_id" in data
    assert data["webhook_id"] == WEBHOOK_ID
    assert data[CONF_CPES] == [TEST_CPE]


async def test_options_show_active_url_and_update_cpes(
    hass: HomeAssistant, config_entry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Options expose the active URL and replace the allowed CPE list."""
    active_url = "https://hooks.nabu.casa/test"

    async def mock_active_url(hass_instance, entry):
        return active_url

    monkeypatch.setattr(
        "custom_components.e_redes_smart_metering_plus.config_flow.async_get_active_webhook_url",
        mock_active_url,
    )
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] == "menu"
    assert result["menu_options"] == ["manage_cpes", "reset_meter"]

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "manage_cpes"}
    )
    assert result["type"] == "form"
    assert result["description_placeholders"]["webhook_url"] == active_url

    updated_cpes = [TEST_CPE, "PT000000000000000001"]
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_CPES: updated_cpes}
    )

    assert result["type"] == "create_entry"
    assert config_entry.data[CONF_CPES] == sorted(updated_cpes)


async def test_options_reset_meter_requires_confirmation(
    hass: HomeAssistant, config_entry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Resetting a meter requires selection and an explicit confirmation step."""
    cpe = config_entry.data[CONF_CPES][0]
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, cpe)},
        name=f"E-Redes Smart Meter {cpe}",
    )
    reset_meter = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "custom_components.e_redes_smart_metering_plus.async_reset_meter",
        reset_meter,
    )

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "reset_meter"}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "reset_meter"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"meter": cpe}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "confirm_reset_meter"
    assert result["description_placeholders"]["meter"] == device.name
    reset_meter.assert_not_awaited()

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={}
    )
    assert result["type"] == "create_entry"
    reset_meter.assert_awaited_once_with(
        hass,
        config_entry,
        device,
        reset_entity_names=True,
    )
