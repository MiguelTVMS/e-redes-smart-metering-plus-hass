"""Config flow for E-Redes Smart Metering Plus integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.helpers import selector

from homeassistant import config_entries
from homeassistant.components import cloud, webhook
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for E-Redes Smart Metering Plus."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            # Check if already configured
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title="E-Redes Smart Metering Plus",
                data={},
            )

        # Check cloud status
        cloud_status = "Not connected"
        if cloud.async_is_logged_in(self.hass):
            cloud_status = "Connected (webhook will use secure cloud URL)"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
            description_placeholders={
                "cloud_status": cloud_status,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """E-Redes Smart Metering Plus config flow options handler."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        
        # If user submitted the form, just close it
        if user_input is not None:
            return self.async_create_entry(title="", data={})
        
        webhook_url = "Not yet generated"
        
        # Debug logging
        _LOGGER.debug("Config entry data keys: %s", list(self.config_entry.data.keys()))
        _LOGGER.debug("Runtime data available: %s", DOMAIN in self.hass.data)
        if DOMAIN in self.hass.data:
            _LOGGER.debug("Entry ID in runtime data: %s", self.config_entry.entry_id in self.hass.data[DOMAIN])
            if self.config_entry.entry_id in self.hass.data[DOMAIN]:
                _LOGGER.debug("Runtime data keys: %s", list(self.hass.data[DOMAIN][self.config_entry.entry_id].keys()))
        
        # First try to get webhook URL from config entry data
        if "webhook_url" in self.config_entry.data:
            webhook_url = self.config_entry.data["webhook_url"]
            _LOGGER.debug("Found webhook URL in config entry: %s", webhook_url)
        
        # If not found, try to get from runtime data
        elif (DOMAIN in self.hass.data 
              and self.config_entry.entry_id in self.hass.data[DOMAIN]
              and "webhook_url" in self.hass.data[DOMAIN][self.config_entry.entry_id]):
            webhook_url = self.hass.data[DOMAIN][self.config_entry.entry_id]["webhook_url"]
            _LOGGER.debug("Found webhook URL in runtime data: %s", webhook_url)
        
        # If still not found, try to generate it based on the webhook ID pattern
        elif webhook_url == "Not yet generated":
            # Try to generate the webhook URL using the entry ID as webhook ID
            webhook_id = self.config_entry.entry_id
            try:
                # Check if cloud is available for cloudhook
                if cloud.async_is_logged_in(self.hass):
                    # Don't create a new cloudhook, just indicate it would be cloud-based
                    webhook_url = f"https://hooks.nabu.casa/... (Cloud webhook - will be generated on next restart)"
                else:
                    # Generate local webhook URL
                    webhook_url = webhook.async_generate_url(self.hass, webhook_id)
                _LOGGER.debug("Generated webhook URL: %s", webhook_url)
            except Exception as err:
                _LOGGER.warning("Could not generate webhook URL: %s", err)
                webhook_url = f"Error generating URL - restart integration to initialize webhook"
        
        # Log final result
        _LOGGER.info("Options flow showing webhook URL: %s", webhook_url)
        
        # Show form with just information display
        return self.async_show_form(
            step_id="init",
            description_placeholders={
                "webhook_url": webhook_url,
            },
        )
