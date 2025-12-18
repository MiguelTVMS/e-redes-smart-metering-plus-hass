"""Constants for the E-Redes Smart Metering Plus integration."""

from homeassistant.helpers.entity import EntityCategory

DOMAIN = "e_redes_smart_metering_plus"

# Fixed webhook ID - creates a predictable URL path
WEBHOOK_ID = DOMAIN

# Webhook constants
WEBHOOK_PATH = f"/api/webhook/{WEBHOOK_ID}"

# Device info
MANUFACTURER = "E-Redes"
MODEL = "Smart Metering Plus"

# Sensor mapping
SENSOR_MAPPING = {
    "instantaneousActivePowerImport": {
        "name": "Instantaneous Active Power Import",
        "key": "instantaneous_active_power_import",
        "unit": "W",
        "device_class": "power",
        "state_class": "measurement",
        "icon": "mdi:transmission-tower-import",
    },
    "maxActivePowerImport": {
        "name": "Max Active Power Import",
        "key": "max_active_power_import",
        "unit": "W",
        "device_class": "power",
        "state_class": "measurement",
        "icon": "mdi:transmission-tower-import",
    },
    "activeEnergyImport": {
        "name": "Active Energy Import",
        "key": "active_energy_import",
        "unit": "Wh",
        "device_class": "energy",
        "state_class": "total_increasing",
        "icon": "mdi:counter",
    },
    "instantaneousActivePowerExport": {
        "name": "Instantaneous Active Power Export",
        "key": "instantaneous_active_power_export",
        "unit": "W",
        "device_class": "power",
        "state_class": "measurement",
        "icon": "mdi:transmission-tower-export",
    },
    "maxActivePowerExport": {
        "name": "Max Active Power Export",
        "key": "max_active_power_export",
        "unit": "W",
        "device_class": "power",
        "state_class": "measurement",
        "icon": "mdi:transmission-tower-export",
    },
    "activeEnergyExport": {
        "name": "Active Energy Export",
        "key": "active_energy_export",
        "unit": "Wh",
        "device_class": "energy",
        "state_class": "total_increasing",
        "icon": "mdi:counter",
    },
    "voltageL1": {
        "name": "Voltage L1",
        "key": "voltage_l1",
        "unit": "V",
        "device_class": "voltage",
        "state_class": "measurement",
        "icon": "mdi:sine-wave",
    },
}

# Calculated sensors (not directly from webhook data)
CALCULATED_SENSORS = {
    "instantaneous_active_current_import": {
        "name": "Instantaneous Active Current Import",
        "key": "instantaneous_active_current_import",
        "unit": "A",
        "device_class": "current",
        "state_class": "measurement",
        "icon": "mdi:current-ac",
        "calculation": "power_voltage",  # Indicates calculation type
        "source_sensors": ["instantaneous_active_power_import", "voltage_l1"],
    },
    "breaker_load": {
        "name": "Breaker Load",
        "key": "breaker_load",
        "unit": "%",
        "device_class": "power_factor",
        "state_class": "measurement",
        "icon": "mdi:gauge",
        "calculation": "current_breaker_limit",  # Indicates calculation type
        "source_sensors": ["instantaneous_active_power_import", "voltage_l1"],
        # Requires breaker limit number entity
        "requires_number_entity": "breaker_limit",
    },
}

# Diagnostic sensors
DIAGNOSTIC_SENSORS = {
    "last_update": {
        "name": "Last Update",
        "key": "last_update",
        "device_class": "timestamp",
        "icon": "mdi:clock-outline",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "enabled_by_default": False,
    },
    "update_interval": {
        "name": "Update Interval",
        "key": "update_interval",
        "unit": "s",
        "device_class": "duration",
        "state_class": "measurement",
        "icon": "mdi:timer-outline",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "enabled_by_default": False,
    },
}
