"""Webhook handling for E-Redes Smart Metering Plus integration."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
import json
import logging
from typing import Any

from aiohttp.web import Request, Response

from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, MANUFACTURER, MODEL, SENSOR_MAPPING, WEBHOOK_ID
from .sensor import async_ensure_calculated_sensors, async_ensure_sensors_for_data

_LOGGER = logging.getLogger(__name__)


def _get_measurement_timestamp(
    data: dict[str, Any],
) -> tuple[str | None, datetime | None]:
    """Return the best available normalized measurement timestamp."""
    for field_name in ("SourceTimestamp", "clock"):
        raw_timestamp = data.get(field_name)
        if not isinstance(raw_timestamp, str):
            continue

        try:
            parsed_timestamp = datetime.fromisoformat(raw_timestamp.replace(" ", "T"))
        except ValueError:
            continue

        if parsed_timestamp.tzinfo is None:
            parsed_timestamp = parsed_timestamp.replace(tzinfo=UTC)
        else:
            parsed_timestamp = parsed_timestamp.astimezone(UTC)

        return raw_timestamp, parsed_timestamp

    return None, None


async def _async_create_cloudhook(hass: HomeAssistant, webhook_id: str) -> str | None:
    """Create a cloudhook when Home Assistant Cloud is available."""
    from homeassistant.components import cloud

    if not cloud.async_is_logged_in(hass) or not cloud.async_is_connected(hass):
        return None

    return await cloud.async_get_or_create_cloudhook(hass, webhook_id)


def _listen_for_cloud_connection(
    hass: HomeAssistant,
    target: Callable[[Any], Awaitable[None] | None],
) -> Callable[[], None]:
    """Listen for Home Assistant Cloud connection changes."""
    from homeassistant.components import cloud

    return cloud.async_listen_connection_change(hass, target)


def _store_webhook_url(
    hass: HomeAssistant, entry: ConfigEntry, webhook_id: str, webhook_url: str
) -> None:
    """Store the active webhook URL in the config entry and runtime data."""
    if entry.data.get("webhook_url") != webhook_url:
        hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                "webhook_id": webhook_id,
                "webhook_url": webhook_url,
            },
        )

    entry_data = hass.data[DOMAIN][entry.entry_id]
    entry_data["webhook_url"] = webhook_url
    entry_data["webhook_id"] = webhook_id


async def _async_refresh_cloudhook(
    hass: HomeAssistant, entry: ConfigEntry, webhook_id: str
) -> str | None:
    """Create or retrieve and store the cloudhook when Cloud is connected."""
    try:
        webhook_url = await _async_create_cloudhook(hass, webhook_id)
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning(
            "Failed to create cloud webhook (%s): %s",
            type(err).__name__,
            str(err) or "no details",
        )
        return None

    if webhook_url:
        _store_webhook_url(hass, entry, webhook_id, webhook_url)
        _LOGGER.info("Using cloud webhook: %s", webhook_url)

    return webhook_url


async def _async_delete_cloudhook(hass: HomeAssistant, webhook_id: str) -> None:
    """Delete a cloudhook when Home Assistant Cloud is available."""
    from homeassistant.components import cloud

    if cloud.async_is_logged_in(hass) and cloud.async_is_connected(hass):
        await cloud.async_delete_cloudhook(hass, webhook_id)


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

    # Use a cloudhook immediately when Cloud is already connected.
    webhook_url = await _async_refresh_cloudhook(hass, entry, webhook_id)

    if not webhook_url:
        # Fall back to local webhook
        webhook_url = webhook.async_generate_url(hass, webhook_id)
        _LOGGER.info("Using local webhook: %s", webhook_url)

    _store_webhook_url(hass, entry, webhook_id, webhook_url)

    async def async_handle_cloud_connection_change(_state: Any) -> None:
        """Create the cloudhook when Home Assistant Cloud connects."""
        await _async_refresh_cloudhook(hass, entry, webhook_id)

    unsubscribe = _listen_for_cloud_connection(
        hass, async_handle_cloud_connection_change
    )
    hass.data[DOMAIN][entry.entry_id]["cloud_connection_unsubscribe"] = unsubscribe

    return webhook_id


async def async_unload_webhook(
    hass: HomeAssistant, webhook_id: str, entry_id: str
) -> None:
    """Unload webhook."""
    webhook.async_unregister(hass, webhook_id)

    entry_data = hass.data.get(DOMAIN, {}).get(entry_id, {})
    if unsubscribe := entry_data.pop("cloud_connection_unsubscribe", None):
        unsubscribe()

    # Remove cloud webhook if it exists
    try:
        await _async_delete_cloudhook(hass, webhook_id)
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning(
            "Failed to delete cloud webhook (%s): %s",
            type(err).__name__,
            str(err) or "no details",
        )


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
    entry_data = hass.data[DOMAIN][entry.entry_id]
    webhook_locks: dict[str, asyncio.Lock] = entry_data.setdefault("webhook_locks", {})
    webhook_lock = webhook_locks.setdefault(cpe, asyncio.Lock())

    async with webhook_lock:
        await _async_process_ordered_sensor_data(hass, entry, cpe, data)


async def _async_process_ordered_sensor_data(
    hass: HomeAssistant, entry: ConfigEntry, cpe: str, data: dict[str, Any]
) -> None:
    """Process sensor data in measurement timestamp order for one CPE."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    raw_timestamp, source_timestamp = _get_measurement_timestamp(data)
    last_source_timestamps: dict[str, datetime] = entry_data.setdefault(
        "last_source_timestamps", {}
    )
    last_source_timestamp = last_source_timestamps.get(cpe)

    if (
        source_timestamp is not None
        and last_source_timestamp is not None
        and source_timestamp < last_source_timestamp
    ):
        _LOGGER.debug(
            "Ignored out-of-order webhook for CPE %s: measurement timestamp %s is older than %s",
            cpe,
            source_timestamp.isoformat(),
            last_source_timestamp.isoformat(),
        )
        return

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
                raw_timestamp,
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

    # Ensure diagnostic sensors exist
    from .sensor import async_ensure_diagnostic_sensors

    await async_ensure_diagnostic_sensors(hass, entry.entry_id, cpe)

    # Send webhook update signal for diagnostic sensors
    async_dispatcher_send(
        hass,
        f"{DOMAIN}_{cpe}_webhook_update",
        raw_timestamp,
    )

    if source_timestamp is not None:
        last_source_timestamps[cpe] = source_timestamp
