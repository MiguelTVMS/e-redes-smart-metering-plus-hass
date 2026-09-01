"""Tests for E-Redes icon translations."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.icon import async_get_icons

from custom_components.e_redes_smart_metering_plus.const import DOMAIN


async def test_contracted_power_icons_load_from_icon_translations(
    hass: HomeAssistant,
) -> None:
    """Contracted-power entities expose friendly state and range icons."""
    resources = await async_get_icons(hass, "entity", [DOMAIN])
    icons = resources[DOMAIN]

    assert icons["select"]["contracted_power"]["default"] == ("mdi:transmission-tower")
    assert icons["sensor"]["contracted_power_usage"]["range"]["100"] == (
        "mdi:alert-octagon"
    )
    assert icons["sensor"]["contracted_power_usage_status"]["state"] == {
        "normal": "mdi:check-circle-outline",
        "warning": "mdi:alert-outline",
        "critical": "mdi:alert-circle",
        "exceeded": "mdi:alert-octagon",
    }
    assert icons["binary_sensor"]["contracted_power_exceeded"]["state"]["on"] == (
        "mdi:alert-octagon"
    )
