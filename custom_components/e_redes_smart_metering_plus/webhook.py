"""Webhook handling for E-Redes Smart Metering Plus integration."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from http import HTTPStatus
import json
import logging
import math
from typing import Any

from aiohttp.hdrs import METH_POST
from aiohttp.web import Request, Response

from homeassistant.components import webhook
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    DOMAIN,
    KNOWN_PAYLOAD_FIELDS,
    MANUFACTURER,
    MODEL,
    SENSOR_MAPPING,
    TIMESTAMP_FIELDS,
    WEBHOOK_ID,
)
from .models import ERedesConfigEntry
from .sensor import async_ensure_calculated_sensors, async_ensure_sensors_for_data

_LOGGER = logging.getLogger(__name__)


def _get_measurement_timestamp(
    data: dict[str, Any],
) -> tuple[str | None, datetime | None]:
    """Return the best available normalized measurement timestamp."""
    for field_name in TIMESTAMP_FIELDS:
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

    if not cloud.async_active_subscription(hass) or not cloud.async_is_connected(hass):
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
    entry: ERedesConfigEntry, webhook_id: str, webhook_url: str
) -> None:
    """Store the active webhook URL in runtime data."""
    entry.runtime_data.webhook_url = webhook_url
    entry.runtime_data.webhook_id = webhook_id


async def _async_refresh_cloudhook(
    hass: HomeAssistant, entry: ERedesConfigEntry, webhook_id: str
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
        _store_webhook_url(entry, webhook_id, webhook_url)
        _LOGGER.info("Using the Home Assistant Cloud webhook")

    return webhook_url


async def async_get_active_webhook_url(
    hass: HomeAssistant, entry: ERedesConfigEntry
) -> str:
    """Return the active webhook URL for display in integration settings."""
    if hasattr(entry, "runtime_data") and entry.runtime_data.webhook_url:
        return entry.runtime_data.webhook_url

    cloudhook_url = await _async_refresh_cloudhook(hass, entry, WEBHOOK_ID)
    if cloudhook_url:
        return cloudhook_url
    return webhook.async_generate_url(hass, WEBHOOK_ID)


async def async_setup_webhook(hass: HomeAssistant, entry: ERedesConfigEntry) -> str:
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
        allowed_methods={METH_POST},
    )

    # Use a cloudhook immediately when Cloud is already connected.
    webhook_url = await _async_refresh_cloudhook(hass, entry, webhook_id)

    if not webhook_url:
        # Fall back to local webhook
        webhook_url = webhook.async_generate_url(hass, webhook_id)
        _LOGGER.info("Using the local E-Redes webhook")

    _store_webhook_url(entry, webhook_id, webhook_url)

    async def async_handle_cloud_connection_change(_state: Any) -> None:
        """Refresh the displayed URL when Home Assistant Cloud changes."""
        if not await _async_refresh_cloudhook(hass, entry, webhook_id):
            _store_webhook_url(
                entry, webhook_id, webhook.async_generate_url(hass, webhook_id)
            )

    unsubscribe = _listen_for_cloud_connection(
        hass, async_handle_cloud_connection_change
    )
    entry.async_on_unload(unsubscribe)

    return webhook_id


def async_unload_webhook(hass: HomeAssistant, webhook_id: str) -> None:
    """Unload webhook."""
    webhook.async_unregister(hass, webhook_id)


async def async_remove_cloudhook(hass: HomeAssistant, webhook_id: str) -> None:
    """Delete a cloudhook only when the config entry is permanently removed."""
    try:
        from homeassistant.components import cloud

        await cloud.async_delete_cloudhook(hass, webhook_id)
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug(
            "Cloud webhook did not require removal (%s): %s",
            type(err).__name__,
            str(err) or "no details",
        )


async def handle_webhook(
    hass: HomeAssistant, webhook_id: str, request: Request, entry: ERedesConfigEntry
) -> Response:
    """Handle incoming webhook data."""
    try:
        data = await request.json()

        if not isinstance(data, dict):
            return Response(
                status=HTTPStatus.BAD_REQUEST, text="JSON body must be an object"
            )

        # Validate required fields
        raw_cpe = data.get("cpe")
        if not isinstance(raw_cpe, str) or not raw_cpe.strip():
            return Response(status=HTTPStatus.BAD_REQUEST, text="Missing 'cpe' field")

        cpe = raw_cpe.strip().upper()
        if cpe not in entry.runtime_data.allowed_cpes:
            if not entry.runtime_data.rejected_cpe_warning_logged:
                _LOGGER.warning(
                    "Rejected webhook data for an unconfigured CPE; add the CPE in the integration options if it belongs to this Home Assistant instance"
                )
                entry.runtime_data.rejected_cpe_warning_logged = True
            return Response(status=HTTPStatus.FORBIDDEN, text="CPE not configured")

        data["cpe"] = cpe
        _log_payload_shape(entry, cpe, data)
        validated_data = _validated_sensor_data(data)
        if not any(field in SENSOR_MAPPING for field in validated_data):
            return Response(
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
                text="No valid supported measurements",
            )

        # Ensure device exists
        _LOGGER.debug("Creating/ensuring device for CPE: %s", cpe)
        await async_ensure_device(hass, entry, cpe)
        _LOGGER.debug("Device ensured for CPE: %s", cpe)

        # Process sensor data
        _LOGGER.debug("Processing sensor data for CPE: %s", cpe)
        await async_process_sensor_data(hass, entry, cpe, validated_data)
        _LOGGER.debug("Sensor data processed for CPE: %s", cpe)

        return Response(status=HTTPStatus.OK, text="OK")

    except json.JSONDecodeError as err:
        _LOGGER.error("Invalid JSON in webhook request: %s", err)
        return Response(status=HTTPStatus.BAD_REQUEST, text="Invalid JSON")
    except Exception:
        _LOGGER.exception("Error processing webhook")
        return Response(
            status=HTTPStatus.INTERNAL_SERVER_ERROR, text="Internal Server Error"
        )


def _validated_sensor_data(data: dict[str, Any]) -> dict[str, Any]:
    """Return known valid measurements while preserving supported metadata."""
    validated = {
        field_name: field_value
        for field_name, field_value in data.items()
        if field_name in KNOWN_PAYLOAD_FIELDS and field_name not in SENSOR_MAPPING
    }

    for field_name, field_value in data.items():
        if field_name not in SENSOR_MAPPING:
            continue
        if isinstance(field_value, bool):
            _LOGGER.warning("Ignored invalid value for payload field %s", field_name)
            continue
        try:
            numeric_value = float(field_value)
            if not math.isfinite(numeric_value):
                raise ValueError
        except (TypeError, ValueError):
            _LOGGER.warning("Ignored invalid value for payload field %s", field_name)
            continue
        validated[field_name] = numeric_value

    return validated


def _log_payload_shape(
    entry: ERedesConfigEntry, cpe: str, data: dict[str, Any]
) -> None:
    """Log first payloads and warn when their set of fields changes."""
    current_fields = frozenset(data)
    previous_fields = entry.runtime_data.payload_fields.get(cpe)

    if previous_fields is None:
        _LOGGER.debug("First webhook payload after startup for CPE %s: %s", cpe, data)
        unsupported_fields = current_fields - KNOWN_PAYLOAD_FIELDS
        if unsupported_fields:
            _LOGGER.warning(
                "Webhook payload for CPE %s contains unsupported fields: %s; supported values will still be processed",
                cpe,
                ", ".join(sorted(unsupported_fields)),
            )
    elif current_fields != previous_fields:
        _LOGGER.warning(
            "Webhook payload fields changed for CPE %s; added: %s; removed: %s. Available supported values will still be processed",
            cpe,
            ", ".join(sorted(current_fields - previous_fields)) or "none",
            ", ".join(sorted(previous_fields - current_fields)) or "none",
        )

    entry.runtime_data.payload_fields[cpe] = current_fields


async def async_ensure_device(
    hass: HomeAssistant, entry: ERedesConfigEntry, cpe: str
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
            serial_number=cpe,
        )
        _LOGGER.info("Created new device for CPE: %s", cpe)

    # Ensure companion entities even when the device predates those platforms.
    from .number import async_create_breaker_limit_entity

    async_create_breaker_limit_entity(entry, cpe)

    from .binary_sensor import async_create_breaker_overload_sensor

    async_create_breaker_overload_sensor(entry, cpe)


async def async_process_sensor_data(
    hass: HomeAssistant, entry: ERedesConfigEntry, cpe: str, data: dict[str, Any]
) -> None:
    """Process sensor data and update entities."""
    webhook_lock = entry.runtime_data.webhook_locks.setdefault(cpe, asyncio.Lock())

    async with webhook_lock:
        await _async_process_ordered_sensor_data(hass, entry, cpe, data)


async def _async_process_ordered_sensor_data(
    hass: HomeAssistant, entry: ERedesConfigEntry, cpe: str, data: dict[str, Any]
) -> None:
    """Process sensor data in measurement timestamp order for one CPE."""
    raw_timestamp, source_timestamp = _get_measurement_timestamp(data)
    last_source_timestamps = entry.runtime_data.last_source_timestamps
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
    await async_ensure_sensors_for_data(entry, cpe, data, raw_timestamp)

    # Send update signal for each sensor type
    for field_name, field_value in data.items():
        if field_name == "cpe":
            continue

        if field_name in SENSOR_MAPPING:
            sensor_key = SENSOR_MAPPING[field_name].key

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
    await async_ensure_calculated_sensors(entry, cpe)

    # Ensure diagnostic sensors exist
    from .sensor import async_ensure_diagnostic_sensors

    await async_ensure_diagnostic_sensors(entry, cpe)

    # Send webhook update signal for diagnostic sensors
    async_dispatcher_send(
        hass,
        f"{DOMAIN}_{cpe}_webhook_update",
        raw_timestamp,
    )

    if source_timestamp is not None:
        last_source_timestamps[cpe] = source_timestamp
