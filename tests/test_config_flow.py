"""Tests for the config flow of the E-Redes Smart Metering Plus integration."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from custom_components.e_redes_smart_metering_plus.const import (
    CONF_CPES,
    CONF_WEBHOOK_AUTH_ENABLED,
    CONF_WEBHOOK_AUTH_TOKEN,
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


async def test_options_separate_webhook_information_and_cpe_management(
    hass: HomeAssistant, config_entry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Webhook information and CPE management use separate options steps."""
    active_url = "https://hooks.nabu.casa/test"

    async def mock_active_url(hass_instance, entry):
        return active_url

    monkeypatch.setattr(
        "custom_components.e_redes_smart_metering_plus.config_flow.async_get_active_webhook_url",
        mock_active_url,
    )
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] == "menu"
    assert result["menu_options"] == [
        "webhook_settings",
        "manage_cpes",
        "reset_meter",
    ]

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "webhook_settings"}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "webhook_settings"
    assert result["description_placeholders"]["webhook_url"] == active_url

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "manage_cpes"}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "manage_cpes"
    assert not result.get("description_placeholders")

    updated_cpes = [TEST_CPE, "PT000000000000000001"]
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_CPES: updated_cpes}
    )

    assert result["type"] == "create_entry"
    assert config_entry.data[CONF_CPES] == sorted(updated_cpes)


async def test_options_configure_webhook_authentication(
    hass: HomeAssistant, config_entry
) -> None:
    """Webhook authentication can be enabled with a visible token."""
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "webhook_settings"}
    )

    defaults = result["data_schema"]({})
    assert defaults[CONF_WEBHOOK_AUTH_ENABLED] is False
    assert defaults[CONF_WEBHOOK_AUTH_TOKEN] == ""
    cpe = next(iter(config_entry.runtime_data.allowed_cpes))
    watermark = datetime(2026, 9, 4, 10, 0, tzinfo=UTC)
    measurement_keys = frozenset({"active_power", "voltage"})
    config_entry.runtime_data.last_source_timestamps[cpe] = watermark
    config_entry.runtime_data.latest_measurement_sensor_keys[cpe] = measurement_keys

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_WEBHOOK_AUTH_ENABLED: True,
            CONF_WEBHOOK_AUTH_TOKEN: "configured-token",
            "generate_auth_token": False,
        },
    )

    assert result["type"] == "create_entry"
    await hass.async_block_till_done()
    assert config_entry.data[CONF_WEBHOOK_AUTH_ENABLED] is True
    assert config_entry.data[CONF_WEBHOOK_AUTH_TOKEN] == "configured-token"
    assert config_entry.runtime_data.last_source_timestamps[cpe] == watermark
    assert (
        config_entry.runtime_data.latest_measurement_sensor_keys[cpe]
        == measurement_keys
    )


async def test_options_generate_webhook_authentication_token(
    hass: HomeAssistant, config_entry
) -> None:
    """A random token is shown before the user saves it."""
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "webhook_settings"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_WEBHOOK_AUTH_ENABLED: False,
            CONF_WEBHOOK_AUTH_TOKEN: "",
            "generate_auth_token": True,
        },
    )

    assert result["type"] == "form"
    generated = result["data_schema"]({})
    assert generated[CONF_WEBHOOK_AUTH_ENABLED] is True
    assert len(generated[CONF_WEBHOOK_AUTH_TOKEN]) >= 32
    assert generated["generate_auth_token"] is False
    assert CONF_WEBHOOK_AUTH_ENABLED not in config_entry.data


async def test_options_requires_token_when_authentication_is_enabled(
    hass: HomeAssistant, config_entry
) -> None:
    """Authentication cannot be enabled without a token."""
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "webhook_settings"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_WEBHOOK_AUTH_ENABLED: True,
            CONF_WEBHOOK_AUTH_TOKEN: "",
            "generate_auth_token": False,
        },
    )

    assert result["type"] == "form"
    assert result["errors"] == {CONF_WEBHOOK_AUTH_TOKEN: "auth_token_required"}


async def test_options_rejects_non_ascii_authentication_token(
    hass: HomeAssistant, config_entry
) -> None:
    """Authorization tokens are restricted to HTTP-safe ASCII text."""
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "webhook_settings"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_WEBHOOK_AUTH_ENABLED: True,
            CONF_WEBHOOK_AUTH_TOKEN: "inválido",
            "generate_auth_token": False,
        },
    )

    assert result["type"] == "form"
    assert result["errors"] == {CONF_WEBHOOK_AUTH_TOKEN: "auth_token_invalid"}


async def test_options_reset_meter_excludes_unconfigured_devices(
    hass: HomeAssistant, config_entry
) -> None:
    """Only devices whose CPE remains allowed are offered for reset."""
    configured_cpe = config_entry.data[CONF_CPES][0]
    unconfigured_cpe = "PT000000000000000099"
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, configured_cpe)},
    )
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, unconfigured_cpe)},
    )

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "reset_meter"}
    )

    schema = result["data_schema"].schema
    selector = next(iter(schema.values()))
    option_values = {option["value"] for option in selector.config["options"]}
    assert configured_cpe in option_values
    assert unconfigured_cpe not in option_values


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
