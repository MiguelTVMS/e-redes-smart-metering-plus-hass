"""Test fixtures for the E-Redes Smart Metering Plus integration."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.e_redes_smart_metering_plus.const import (
    CONF_CPES,
    DOMAIN,
    WEBHOOK_ID,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant


@pytest.fixture(autouse=True)
def _mock_cloud(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure tests don't hit Home Assistant Cloud.

    Force cloud to appear logged out so the integration falls back to local webhook URLs
    and avoids cloudhook API calls.
    """
    async def mock_refresh_cloudhook(hass, entry, webhook_id):
        return None

    monkeypatch.setattr(
        "custom_components.e_redes_smart_metering_plus.webhook._async_refresh_cloudhook",
        mock_refresh_cloudhook,
    )
    monkeypatch.setattr(
        "custom_components.e_redes_smart_metering_plus.webhook._listen_for_cloud_connection",
        lambda hass, target: lambda: None,
    )


@pytest.fixture(autouse=True)
# type: ignore[reportGeneralTypeIssues]
def _auto_enable_custom_integrations(enable_custom_integrations: bool) -> None:
    """Make sure HA can find our integration under custom_components/."""
    # The fixture does all the work; this wrapper just enables it globally.
    return None


@pytest.fixture
async def config_entry(hass: HomeAssistant) -> AsyncGenerator[MockConfigEntry]:
    """Create and set up a config entry for the integration."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="E-Redes Smart Metering Plus",
        data={
            "webhook_id": WEBHOOK_ID,
            CONF_CPES: [
                "1234567890",
                "ABCDEF",
                "TEST123",
                "XYZ",
                "CPE001",
                "CPE_TEST_001",
                "CPE_TEST_002",
                "CPE_TEST_CALC",
                "CPE_TEST_UNKNOWN",
                "CPE_USAGE_TEST",
                "CPE_USAGE_TEST_1",
                "CPE_USAGE_TEST_2",
                "CPE_USAGE_TEST_3",
                "CPE_USAGE_TEST_4",
                "PT0002000012345678900",
            ],
        },
        version=2,
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Loaded state indicates __init__.async_setup_entry completed and sensor platform forwarded
    assert entry.state is ConfigEntryState.LOADED

    yield entry

    # Teardown
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
