"""Webhook handling for E-Redes Smart Metering Plus integration."""
from __future__ import annotations

import json
import logging
from typing import Any

from aiohttp.web import Request, Response

from homeassistant.components import cloud, webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, MANUFACTURER, MODEL, SENSOR_MAPPING

_LOGGER = logging.getLogger(__name__)


async def async_setup_webhook(hass: HomeAssistant, entry: ConfigEntry) -> str:
    """Set up webhook for receiving E-Redes data."""
    webhook_id = entry.entry_id
    
    # Register the webhook handler
    webhook.async_register(
        hass,
        DOMAIN,
        f"E-Redes Smart Metering Plus ({entry.title})",
        webhook_id,
        handle_webhook,
    )
    
    # Try to create a cloud webhook if available
    webhook_url = None
    if cloud.async_is_logged_in(hass):
        try:
            webhook_url = await cloud.async_create_cloudhook(hass, webhook_id)
            _LOGGER.info("Created cloud webhook: %s", webhook_url)
        except Exception as err:
            _LOGGER.warning("Failed to create cloud webhook: %s", err)
    
    if not webhook_url:
        # Fall back to local webhook
        webhook_url = webhook.async_generate_url(hass, webhook_id)
        _LOGGER.info("Using local webhook: %s", webhook_url)
    
    # Store webhook URL in config entry data
    hass.config_entries.async_update_entry(
        entry,
        data={**entry.data, "webhook_url": webhook_url}
    )
    
    # Also store webhook URL in integration data for easy access
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    if entry.entry_id not in hass.data[DOMAIN]:
        hass.data[DOMAIN][entry.entry_id] = {}
    hass.data[DOMAIN][entry.entry_id]["webhook_url"] = webhook_url
    
    return webhook_id


async def async_unload_webhook(hass: HomeAssistant, webhook_id: str) -> None:
    """Unload webhook."""
    webhook.async_unregister(hass, webhook_id)
    
    # Remove cloud webhook if it exists
    if cloud.async_is_logged_in(hass):
        try:
            await cloud.async_delete_cloudhook(hass, webhook_id)
        except Exception as err:
            _LOGGER.warning("Failed to delete cloud webhook: %s", err)


async def handle_webhook(
    hass: HomeAssistant, webhook_id: str, request: Request
) -> Response:
    """Handle incoming webhook data."""
    try:
        data = await request.json()
        _LOGGER.debug("Received webhook data: %s", data)
        
        # Validate required fields
        if "cpe" not in data:
            _LOGGER.error("Missing 'cpe' field in webhook data")
            return Response(status=400, text="Missing 'cpe' field")
        
        cpe = data["cpe"]
        
        # Ensure device exists
        await async_ensure_device(hass, cpe)
        
        # Process sensor data
        await async_process_sensor_data(hass, cpe, data)
        
        return Response(status=200, text="OK")
        
    except json.JSONDecodeError:
        _LOGGER.error("Invalid JSON in webhook request")
        return Response(status=400, text="Invalid JSON")
    except Exception as err:
        _LOGGER.error("Error processing webhook: %s", err)
        return Response(status=500, text="Internal Server Error")


async def async_ensure_device(hass: HomeAssistant, cpe: str) -> None:
    """Ensure device exists for the given CPE."""
    device_registry = dr.async_get(hass)
    
    # Check if device already exists
    device = device_registry.async_get_device(
        identifiers={(DOMAIN, cpe)}
    )
    
    if not device:
        # Create new device
        device = device_registry.async_get_or_create(
            config_entry_id=None,  # Will be set by sensor registration
            identifiers={(DOMAIN, cpe)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=f"E-Redes Smart Meter {cpe}",
            sw_version=None,
        )
        _LOGGER.info("Created new device for CPE: %s", cpe)


async def async_process_sensor_data(
    hass: HomeAssistant, cpe: str, data: dict[str, Any]
) -> None:
    """Process sensor data and update entities."""
    # Find the config entry for this integration
    config_entry = None
    for entry in hass.config_entries.async_entries(DOMAIN):
        config_entry = entry
        break
    
    if not config_entry:
        _LOGGER.error("No config entry found for processing sensor data")
        return
    
    # Ensure sensors exist for this data
    from .sensor import async_ensure_sensors_for_data
    await async_ensure_sensors_for_data(hass, config_entry.entry_id, cpe, data)
    
    # Send update signal for each sensor type
    for field_name, field_value in data.items():
        if field_name == "cpe":
            continue
            
        if field_name in SENSOR_MAPPING:
            sensor_key = SENSOR_MAPPING[field_name]["key"]
            entity_id = f"sensor.e_redes_{cpe}_{sensor_key}"
            
            # Dispatch update to sensor entity
            async_dispatcher_send(
                hass,
                f"{DOMAIN}_{cpe}_{sensor_key}_update",
                field_value,
                data.get("clock")  # Include timestamp if available
            )
            
            _LOGGER.debug("Updated sensor %s with value %s", entity_id, field_value)
        else:
            _LOGGER.debug("Unknown field in webhook data: %s", field_name)
