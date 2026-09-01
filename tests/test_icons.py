"""Tests for E-Redes icon translations."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.icon import async_get_icons

from custom_components.e_redes_smart_metering_plus.const import DOMAIN


async def test_breaker_icons_load_from_icon_translations(hass: HomeAssistant) -> None:
    """Breaker entities expose friendly state and range icons."""
    resources = await async_get_icons(hass, "entity", [DOMAIN])
    icons = resources[DOMAIN]

    assert icons["select"]["contracted_power"]["default"] == ("mdi:transmission-tower")
    assert icons["sensor"]["breaker_load"]["range"]["100"] == ("mdi:alert-octagon")
    assert icons["sensor"]["breaker_load_status"]["state"] == {
        "normal": "mdi:check-circle-outline",
        "warning": "mdi:alert-outline",
        "critical": "mdi:alert-circle",
        "overload": "mdi:alert-octagon",
    }
    assert icons["binary_sensor"]["breaker_overload"]["state"]["on"] == (
        "mdi:alert-octagon"
    )
