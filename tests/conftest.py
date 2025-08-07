"""Pytest configuration for E-Redes Smart Metering Plus tests."""
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from custom_components.e_redes_smart_metering_plus.const import DOMAIN


@pytest.fixture
def hass(hass_storage):
    """Fixture for Home Assistant instance."""
    return hass_storage


@pytest.fixture
async def setup_integration(hass: HomeAssistant):
    """Set up the integration for testing."""
    hass.data.setdefault(DOMAIN, {})
    return hass
