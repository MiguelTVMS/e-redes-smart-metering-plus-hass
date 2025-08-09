"""Test webhook data processing for E-Redes Smart Metering Plus."""

from __future__ import annotations

from homeassistant.components.eredes_smart_metering_plus.webhook import handle_webhook
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry

DOMAIN = "eredes_smart_metering_plus"


async def test_webhook_data_processing(
    hass: HomeAssistant,
) -> None:
    """Test that webhook can process incoming data correctly."""
    # Create a mock config entry
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"webhook_id": "test-webhook-data"},
        title="E-Redes Smart Metering Plus",
    )
    entry.add_to_hass(hass)

    # Setup the integration
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Simulate webhook data from E-Redes
    webhook_data = {
        "cpe": "PT0012345678901234567890AB",  # Required field
        "deviceId": "1234567890",
        "timestamp": "2025-01-09T00:00:00Z",
        "readings": [
            {"type": "active_energy_import", "value": 1234.5, "unit": "kWh"},
            {"type": "active_energy_export", "value": 567.8, "unit": "kWh"},
        ],
    }

    # Create a mock request object
    class MockRequest:
        def __init__(self, json_data) -> None:
            self._json_data = json_data

        async def json(self):
            return self._json_data

        @property
        def headers(self):
            return {"content-type": "application/json"}

    mock_request = MockRequest(webhook_data)

    # Call the webhook handler directly (this shouldn't timeout)
    response = await handle_webhook(hass, "test-webhook-data", mock_request, entry)
    # The webhook should accept data and return success
    assert response.status == 200
