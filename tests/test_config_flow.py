"""Test the E-Redes Smart Metering Plus config flow."""

from unittest.mock import AsyncMock

from homeassistant import config_entries
from homeassistant.components.eredes_smart_metering_plus.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_form(hass: HomeAssistant, mock_setup_entry: AsyncMock) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None  # No errors on initial form
    assert result["step_id"] == "user"

    # Check that the schema is empty (no input fields needed)
    assert result["data_schema"].schema == {}

    # Check that the webhook URL is available in placeholders
    assert "webhook_url" in result["description_placeholders"]

    # Complete the flow by submitting empty form (no input data needed)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {},  # Empty dict for empty schema
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "E-Redes Smart Metering Plus"
    assert "webhook_id" in result["data"]
    assert len(mock_setup_entry.mock_calls) == 1


async def test_options_flow_webhook_url_display(hass: HomeAssistant) -> None:
    """Test that options flow displays the webhook URL correctly."""
    # Create a mock config entry with webhook data
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "webhook_id": "test-webhook-id-123",
            "webhook_url": "https://example.com/api/webhook/test-webhook-id-123",
        },
        entry_id="test-entry-id",
        title="E-Redes Smart Metering Plus",
    )
    config_entry.add_to_hass(hass)

    # Start the options flow
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"

    # Check that the menu options are empty (only close button)
    assert result["menu_options"] == []

    # Check that the webhook URL is available in placeholders
    assert "webhook_url" in result["description_placeholders"]

    # With empty menu options, the flow shows only a close button
    # No further configuration is possible or needed
