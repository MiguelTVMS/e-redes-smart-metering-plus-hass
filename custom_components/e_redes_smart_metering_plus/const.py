"""Constants for the E-Redes Smart Metering Plus integration."""

DOMAIN = "e_redes_smart_metering_plus"

# Webhook constants
WEBHOOK_PATH = f"/api/webhook/{DOMAIN}"

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
        "unit": "kWh",
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
        "unit": "kWh",
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
