"""Tests for the config flow of the E-Redes Smart Metering Plus integration."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant

from custom_components.e_redes_smart_metering_plus.const import DOMAIN, WEBHOOK_ID


pytestmark = pytest.mark.asyncio


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
        result["flow_id"], user_input={}
    )

    assert result2["type"] == "create_entry"
    assert result2["title"] == "E-Redes Smart Metering Plus"
    data = result2["data"]
    assert "webhook_id" in data
    assert data["webhook_id"] == WEBHOOK_ID
