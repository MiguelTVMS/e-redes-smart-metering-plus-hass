"""Information entities for E-Redes Smart Metering Plus integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MANUFACTURER, MODEL

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up E-Redes info entities from config entry."""
    entities = []
    
    # Create webhook URL info entity
    entities.append(ERedesWebhookInfoEntity(config_entry))
    
    async_add_entities(entities)


class ERedesWebhookInfoEntity(TextEntity):
    """Entity to display webhook URL information."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the webhook info entity."""
        self._config_entry = config_entry
        self._attr_name = "E-Redes Webhook URL"
        self._attr_unique_id = f"{DOMAIN}_{config_entry.entry_id}_webhook_info"
        self._attr_icon = "mdi:webhook"
        self._attr_entity_registry_enabled_default = True

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, "integration")},
            name="E-Redes Smart Metering Plus Integration",
            manufacturer=MANUFACTURER,
            model="Integration Controller",
            configuration_url=self._get_webhook_url(),
        )

    @property
    def native_value(self) -> str:
        """Return the webhook URL."""
        return self._get_webhook_url()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        webhook_url = self._get_webhook_url()
        return {
            "webhook_url": webhook_url,
            "instructions": "Copy this URL and configure it in your E-Redes provider dashboard",
            "configuration_steps": [
                "1. Copy the webhook URL",
                "2. Log into your E-Redes energy provider dashboard",
                "3. Navigate to Smart Metering Plus settings",
                "4. Configure the webhook endpoint with the copied URL",
                "5. Enable data transmission"
            ]
        }

    def _get_webhook_url(self) -> str:
        """Get webhook URL from config or runtime data."""
        # Try config entry data first
        if "webhook_url" in self._config_entry.data:
            return self._config_entry.data["webhook_url"]
        
        # Try runtime data
        if (DOMAIN in self.hass.data 
            and self._config_entry.entry_id in self.hass.data[DOMAIN]
            and "webhook_url" in self.hass.data[DOMAIN][self._config_entry.entry_id]):
            return self.hass.data[DOMAIN][self._config_entry.entry_id]["webhook_url"]
        
        return "Not yet generated"

    async def async_update(self) -> None:
        """Update the entity."""
        # Force update of the value
        self._attr_native_value = self._get_webhook_url()
