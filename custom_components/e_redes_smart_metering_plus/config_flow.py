"""Config flow for E-Redes Smart Metering Plus integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import DOMAIN


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
        try:
            if "cloud" in self.hass.config.components:
                from homeassistant.components import cloud
                if cloud.async_is_logged_in(self.hass):
                    cloud_status = "Connected - webhook will use secure Nabu Casa cloud URL"
                else:
                    cloud_status = "Available but not logged in - will use local webhook URL"
            else:
                cloud_status = "Not available - will use local webhook URL"
        except Exception:
            cloud_status = "Unknown - will attempt local webhook URL"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
            errors={"base": f"CLOUD STATUS: {cloud_status} | Click Submit to continue with integration setup."},
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Create the options flow."""
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """E-Redes Smart Metering Plus config flow options handler."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        
        # If user submitted the form, just close it
        if user_input is not None:
            return self.async_create_entry(title="", data={})
        
        # Get the real webhook URL
        webhook_url = "Not yet generated"
        
        # First try to get webhook URL from config entry data
        if "webhook_url" in self.config_entry.data:
            webhook_url = self.config_entry.data["webhook_url"]
        
        # If not found, try to get from runtime data
        elif (DOMAIN in self.hass.data 
              and self.config_entry.entry_id in self.hass.data[DOMAIN]
              and "webhook_url" in self.hass.data[DOMAIN][self.config_entry.entry_id]):
            webhook_url = self.hass.data[DOMAIN][self.config_entry.entry_id]["webhook_url"]
        
        # If still not found, try to generate it
        elif webhook_url == "Not yet generated":
            webhook_id = self.config_entry.entry_id
            try:
                # Check if cloud is available for cloudhook
                if "cloud" in self.hass.config.components:
                    from homeassistant.components import cloud
                    if cloud.async_is_logged_in(self.hass):
                        webhook_url = f"https://hooks.nabu.casa/... (Cloud webhook - restart integration to see full URL)"
                    else:
                        from homeassistant.components import webhook
                        webhook_url = webhook.async_generate_url(self.hass, webhook_id)
                else:
                    from homeassistant.components import webhook
                    webhook_url = webhook.async_generate_url(self.hass, webhook_id)
            except Exception as err:
                webhook_url = f"Error generating URL: {err}"
        
        # Show a copyable, prefilled text field (we ignore edits) and describe via placeholders
        schema = vol.Schema({
            vol.Optional("webhook_url", default=webhook_url): selector.TextSelector(
                selector.TextSelectorConfig(multiline=False)
            )
        })

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            description_placeholders={"webhook_url": webhook_url},
        )
