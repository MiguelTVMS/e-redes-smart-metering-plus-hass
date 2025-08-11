"""Test fixtures for the E-Redes Smart Metering Plus integration."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.e_redes_smart_metering_plus.const import DOMAIN


@pytest.fixture(autouse=True)
def _mock_cloud(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure tests don't hit Home Assistant Cloud.

    Force cloud to appear logged out so the integration falls back to local webhook URLs
    and avoids cloudhook API calls.
    """

    monkeypatch.setattr(
        "homeassistant.components.cloud.async_is_logged_in", lambda hass: False,
        raising=True,
    )


@pytest.fixture(autouse=True)
# type: ignore[reportGeneralTypeIssues]
def _auto_enable_custom_integrations(enable_custom_integrations) -> None:
    """Make sure HA can find our integration under custom_components/."""
    # The fixture does all the work; this wrapper just enables it globally.
    return None


@pytest.fixture
async def config_entry(hass: HomeAssistant) -> AsyncGenerator[MockConfigEntry, None]:
    """Create and set up a config entry for the integration."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="E-Redes Smart Metering Plus",
        data={"webhook_id": "test-webhook-id"},
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
