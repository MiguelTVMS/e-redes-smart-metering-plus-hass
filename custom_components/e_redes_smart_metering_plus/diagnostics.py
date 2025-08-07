"""Diagnostics support for E-Redes Smart Metering Plus."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = {}
    
    # Get webhook URL from config entry data
    webhook_url = entry.data.get("webhook_url", "Not configured")
    
    # Also try to get from runtime data
    if (DOMAIN in hass.data 
        and entry.entry_id in hass.data[DOMAIN] 
        and "webhook_url" in hass.data[DOMAIN][entry.entry_id]):
        runtime_webhook_url = hass.data[DOMAIN][entry.entry_id]["webhook_url"]
    else:
        runtime_webhook_url = "Not available"
    
    data["webhook_info"] = {
        "webhook_url_from_config": webhook_url,
        "webhook_url_from_runtime": runtime_webhook_url,
        "webhook_configured": webhook_url != "Not configured",
    }
    
    data["config_entry_info"] = {
        "entry_id": entry.entry_id,
        "title": entry.title,
        "version": entry.version,
        "minor_version": entry.minor_version,
        "data": entry.data,
        "options": entry.options,
    }
    
    # Get device and entity count
    device_registry = hass.helpers.device_registry.async_get(hass)
    entity_registry = hass.helpers.entity_registry.async_get(hass)
    
    devices = [
        device for device in device_registry.devices.values()
        if entry.entry_id in device.config_entries
    ]
    
    entities = [
        entity for entity in entity_registry.entities.values()
        if entity.config_entry_id == entry.entry_id
    ]
    
    data["statistics"] = {
        "devices_count": len(devices),
        "entities_count": len(entities),
        "devices": [
            {
                "id": device.id,
                "name": device.name,
                "model": device.model,
                "manufacturer": device.manufacturer,
                "identifiers": list(device.identifiers),
            }
            for device in devices
        ],
        "entities": [
            {
                "entity_id": entity.entity_id,
                "name": entity.name,
                "device_id": entity.device_id,
                "platform": entity.platform,
            }
            for entity in entities
        ],
    }
    
    return data
