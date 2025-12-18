"""Webhook handling for E-Redes Smart Metering Plus integration."""

from __future__ import annotations

import json
import logging
from typing import Any

from aiohttp.web import Request, Response

from homeassistant.components import cloud, webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, MANUFACTURER, MODEL, SENSOR_MAPPING, WEBHOOK_ID
from .sensor import async_ensure_calculated_sensors, async_ensure_sensors_for_data

_LOGGER = logging.getLogger(__name__)


async def async_setup_webhook(hass: HomeAssistant, entry: ConfigEntry) -> str:
    """Set up webhook for receiving E-Redes data."""
    # Use fixed webhook ID
    webhook_id = WEBHOOK_ID

    # Create a handler with the config entry bound to it
    async def webhook_handler(
        hass: HomeAssistant, webhook_id: str, request: Request
    ) -> Response:
        """Handle webhook with config entry context."""
        return await handle_webhook(hass, webhook_id, request, entry)

    # Register the webhook handler
    webhook.async_register(
        hass,
        DOMAIN,
        "E-Redes Smart Metering Plus",
        webhook_id,
        webhook_handler,
    )

    # Try to create a cloud webhook if available
    webhook_url = None
    if cloud.async_is_logged_in(hass):
        try:
            webhook_url = await cloud.async_create_cloudhook(hass, webhook_id)
            _LOGGER.info("Created cloud webhook: %s", webhook_url)
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Failed to create cloud webhook: %s", err)

    if not webhook_url:
        # Fall back to local webhook
        webhook_url = webhook.async_generate_url(hass, webhook_id)
        _LOGGER.info("Using local webhook: %s", webhook_url)

    # Store webhook URL in config entry data
    hass.config_entries.async_update_entry(
        entry, data={**entry.data, "webhook_id": webhook_id, "webhook_url": webhook_url}
    )

    # Also store webhook URL in integration data for easy access
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    if entry.entry_id not in hass.data[DOMAIN]:
        hass.data[DOMAIN][entry.entry_id] = {}
    hass.data[DOMAIN][entry.entry_id]["webhook_url"] = webhook_url
    hass.data[DOMAIN][entry.entry_id]["webhook_id"] = webhook_id

    return webhook_id


async def async_unload_webhook(hass: HomeAssistant, webhook_id: str) -> None:
    """Unload webhook."""
    webhook.async_unregister(hass, webhook_id)

    # Remove cloud webhook if it exists
    if cloud.async_is_logged_in(hass):
        try:
            await cloud.async_delete_cloudhook(hass, webhook_id)
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Failed to delete cloud webhook: %s", err)


async def handle_webhook(
    hass: HomeAssistant, webhook_id: str, request: Request, entry: ConfigEntry
) -> Response:
    """Handle incoming webhook data."""
    try:
        _LOGGER.info("Webhook handler called with webhook_id: %s", webhook_id)

        data = await request.json()
        _LOGGER.info("Received webhook data: %s", data)

        # Validate required fields
        if "cpe" not in data:
            _LOGGER.error("Missing 'cpe' field in webhook data")
            return Response(status=400, text="Missing 'cpe' field")

        cpe = data["cpe"]
        _LOGGER.info("Processing data for CPE: %s", cpe)

        # Ensure device exists
        _LOGGER.debug("Creating/ensuring device for CPE: %s", cpe)
        await async_ensure_device(hass, entry, cpe)
        _LOGGER.debug("Device ensured for CPE: %s", cpe)

        # Process sensor data
        _LOGGER.debug("Processing sensor data for CPE: %s", cpe)
        await async_process_sensor_data(hass, entry, cpe, data)
        _LOGGER.debug("Sensor data processed for CPE: %s", cpe)

        _LOGGER.info("Webhook processing completed successfully for CPE: %s", cpe)
        return Response(status=200, text="OK")

    except json.JSONDecodeError as err:
        _LOGGER.error("Invalid JSON in webhook request: %s", err)
        return Response(status=400, text="Invalid JSON")
    except Exception as err:
        _LOGGER.exception("Error processing webhook")
        return Response(status=500, text=f"Internal Server Error: {err}")


async def async_ensure_device(
    hass: HomeAssistant, entry: ConfigEntry, cpe: str
) -> None:
    """Ensure device exists for the given CPE."""
    device_registry = dr.async_get(hass)

    # Check if device already exists
    device = device_registry.async_get_device(identifiers={(DOMAIN, cpe)})

    if not device:
        # Create new device
        device = device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,  # Use the actual config entry ID
            identifiers={(DOMAIN, cpe)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=f"E-Redes Smart Meter {cpe}",
            sw_version=None,
        )
        _LOGGER.info("Created new device for CPE: %s", cpe)

        # Create breaker limit number entity for this device
        from .number import async_create_breaker_limit_entity

        async_create_breaker_limit_entity(hass, entry.entry_id, cpe)

        # Create breaker overload binary sensor for this device
        from .binary_sensor import async_create_breaker_overload_sensor

        async_create_breaker_overload_sensor(hass, entry.entry_id, cpe)


async def async_process_sensor_data(
    hass: HomeAssistant, entry: ConfigEntry, cpe: str, data: dict[str, Any]
) -> None:
    """Process sensor data and update entities."""
    # Ensure sensors exist for this data
    await async_ensure_sensors_for_data(hass, entry.entry_id, cpe, data)

    # Send update signal for each sensor type
    for field_name, field_value in data.items():
        if field_name == "cpe":
            continue

        if field_name in SENSOR_MAPPING:
            sensor_key = SENSOR_MAPPING[field_name]["key"]

            # Dispatch update to sensor entity
            async_dispatcher_send(
                hass,
                f"{DOMAIN}_{cpe}_{sensor_key}_update",
                field_value,
                data.get("clock"),  # Include timestamp if available
            )

            _LOGGER.debug(
                "Dispatched update for sensor %s_%s with value %s",
                cpe,
                sensor_key,
                field_value,
            )
        else:
            _LOGGER.debug("Unknown field in webhook data: %s", field_name)

    # Ensure calculated sensors exist after processing source sensors
    await async_ensure_calculated_sensors(hass, entry.entry_id, cpe)
