"""The E-Redes Smart Metering Plus integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, WEBHOOK_ID
from .webhook import async_setup_webhook, async_unload_webhook

# List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
_PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.NUMBER, Platform.BINARY_SENSOR]


# Create ConfigEntry type alias for webhook integration
type EredesSmartMeteringPlusConfigEntry = ConfigEntry[dict[str, str]]


async def async_setup_entry(
    hass: HomeAssistant, entry: EredesSmartMeteringPlusConfigEntry
) -> bool:
    """Set up E-Redes Smart Metering Plus from a config entry."""

    # Initialize domain data if not exists
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    # Initialize entry-specific data structure required by sensor platform
    hass.data[DOMAIN][entry.entry_id] = {
        "webhook_id": WEBHOOK_ID,
        "name": entry.data.get("name", "E-Redes Smart Meter"),
        "entities": {},  # Will store sensor entities
        "add_entities": None,  # Will be set by sensor platform
    }

    # Store configuration data for platforms to access
    # For webhook integrations, we typically store webhook configuration
    entry.runtime_data = {
        "webhook_id": WEBHOOK_ID,
        "name": entry.data.get("name", "E-Redes Smart Meter"),
    }

    # Set up the webhook
    await async_setup_webhook(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: EredesSmartMeteringPlusConfigEntry
) -> bool:
    """Unload a config entry."""
    # Unload the webhook - use fixed webhook ID
    await async_unload_webhook(hass, WEBHOOK_ID)

    # Clean up domain data
    if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
        del hass.data[DOMAIN][entry.entry_id]

    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
