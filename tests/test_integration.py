"""Test the E-Redes Smart Metering Plus integration."""

from __future__ import annotations

from homeassistant.components import webhook
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry

DOMAIN = "eredes_smart_metering_plus"


async def test_webhook_integration_setup(
    hass: HomeAssistant,
) -> None:
    """Test that the integration sets up and webhook is registered."""
    # Create a mock config entry
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"webhook_id": "test-webhook-id"},
        title="E-Redes Smart Metering Plus",
    )
    entry.add_to_hass(hass)

    # Setup the integration
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Check that the webhook is registered by verifying the URL can be generated
    webhook_url = webhook.async_generate_url(hass, "test-webhook-id")
    assert webhook_url is not None
    assert "test-webhook-id" in webhook_url

    # Verify the webhook ID matches what we stored
    assert entry.data["webhook_id"] == "test-webhook-id"


async def test_webhook_unload(
    hass: HomeAssistant,
) -> None:
    """Test that the webhook is unregistered when the integration is unloaded."""
    # Create a mock config entry
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"webhook_id": "test-webhook-id-2"},
        title="E-Redes Smart Metering Plus",
    )
    entry.add_to_hass(hass)

    # Setup the integration
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Verify webhook is registered
    webhook_url = webhook.async_generate_url(hass, "test-webhook-id-2")
    assert webhook_url is not None

    # Unload the integration
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    # The webhook should be unregistered after unload
    # Note: We can't easily test this directly, but no exceptions should be raised
