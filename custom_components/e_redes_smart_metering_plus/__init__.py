"""The E-Redes Smart Metering Plus integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .webhook import async_setup_webhook, async_unload_webhook

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the E-Redes Smart Metering Plus component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up E-Redes Smart Metering Plus from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}

    # Set up webhook
    webhook_id = await async_setup_webhook(hass, entry)
    hass.data[DOMAIN][entry.entry_id]["webhook_id"] = webhook_id

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    await async_setup_services(hass)

    return True


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for the integration."""
    
    async def get_webhook_url_service(call) -> None:
        """Service to get webhook URL."""
        config_entry_id = call.data.get("config_entry_id")
        
        # If no config entry ID provided, use the first one found
        if not config_entry_id:
            if DOMAIN in hass.data and hass.data[DOMAIN]:
                config_entry_id = next(iter(hass.data[DOMAIN].keys()))
            else:
                _LOGGER.error("No E-Redes config entries found")
                return
        
        # Get webhook URL
        if (config_entry_id in hass.data.get(DOMAIN, {}) 
            and "webhook_url" in hass.data[DOMAIN][config_entry_id]):
            webhook_url = hass.data[DOMAIN][config_entry_id]["webhook_url"]
            _LOGGER.info("E-Redes Webhook URL: %s", webhook_url)
            
            # Also fire an event with the webhook URL
            hass.bus.async_fire(
                f"{DOMAIN}_webhook_url",
                {"webhook_url": webhook_url, "config_entry_id": config_entry_id}
            )
        else:
            _LOGGER.error("Webhook URL not found for config entry %s", config_entry_id)
    
    # Register the service
    hass.services.async_register(
        DOMAIN,
        "get_webhook_url",
        get_webhook_url_service,
    )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload webhook
    webhook_id = hass.data[DOMAIN][entry.entry_id].get("webhook_id")
    if webhook_id:
        await async_unload_webhook(hass, webhook_id)

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
