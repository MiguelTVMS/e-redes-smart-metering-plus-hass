"""Example configuration for logger component in configuration.yaml.

Add the following to your configuration.yaml to enable debug logging:

logger:
  default: warn
  logs:
    custom_components.e_redes_smart_metering_plus: debug

Or add to your configuration.yaml for the full integration logging:

logger:
  default: warn
  logs:
    custom_components.e_redes_smart_metering_plus: debug
    custom_components.e_redes_smart_metering_plus.webhook: debug
    custom_components.e_redes_smart_metering_plus.sensor: debug
    custom_components.e_redes_smart_metering_plus.config_flow: debug
"""
