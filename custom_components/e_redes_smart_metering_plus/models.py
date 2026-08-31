"""Data models for the E-Redes Smart Metering Plus integration."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.number import NumberEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, MANUFACTURER, MODEL, WEBHOOK_ID


@dataclass
class ERedesRuntimeData:
    """Runtime data associated with one config entry."""

    allowed_cpes: frozenset[str]
    webhook_id: str = WEBHOOK_ID
    webhook_url: str | None = None
    sensor_entities: dict[str, SensorEntity] = field(default_factory=dict)
    number_entities: dict[str, NumberEntity] = field(default_factory=dict)
    binary_sensor_entities: dict[str, BinarySensorEntity] = field(default_factory=dict)
    sensor_add_entities: AddConfigEntryEntitiesCallback | None = None
    number_add_entities: AddConfigEntryEntitiesCallback | None = None
    binary_sensor_add_entities: AddConfigEntryEntitiesCallback | None = None
    last_source_timestamps: dict[str, datetime] = field(default_factory=dict)
    webhook_locks: dict[str, asyncio.Lock] = field(default_factory=dict)
    payload_fields: dict[str, frozenset[str]] = field(default_factory=dict)
    rejected_cpe_warning_logged: bool = False


type ERedesConfigEntry = ConfigEntry[ERedesRuntimeData]


def device_info_for_cpe(cpe: str) -> DeviceInfo:
    """Return consistent device information for a CPE."""
    return DeviceInfo(
        identifiers={(DOMAIN, cpe)},
        name=f"E-Redes Smart Meter {cpe}",
        manufacturer=MANUFACTURER,
        model=MODEL,
        serial_number=cpe,
    )
