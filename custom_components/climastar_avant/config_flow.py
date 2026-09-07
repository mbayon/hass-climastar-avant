"""Config and reauthentication flows for Climastar Avant WiFi."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client

from .api import ClimastarApiClient, ClimastarAuthError, ClimastarConnectionError
from .const import CONF_EMAIL, CONF_PASSWORD, DOMAIN, NAME

STEP_SCHEMA = vol.Schema({vol.Required(CONF_EMAIL): str, vol.Required(CONF_PASSWORD): str})


class ClimastarAvantConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle UI credential entry."""

    VERSION = 1

    async def _validate(self, user_input: dict[str, str]) -> str | None:
        client = ClimastarApiClient(aiohttp_client.async_get_clientsession(self.hass))
        try:
            await client.async_login(user_input[CONF_EMAIL], user_input[CONF_PASSWORD])
            return None
        except ClimastarAuthError:
            return "invalid_auth"
        except ClimastarConnectionError:
            return "cannot_connect"

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input:
            email = user_input[CONF_EMAIL].strip().lower()
            errors["base"] = await self._validate({**user_input, CONF_EMAIL: email}) or ""
            if not errors["base"]:
                await self.async_set_unique_id(email)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=NAME, data={**user_input, CONF_EMAIL: email})
            errors = {key: value for key, value in errors.items() if value}
        return self.async_show_form(step_id="user", data_schema=STEP_SCHEMA, errors=errors)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        self._reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input:
            email = user_input[CONF_EMAIL].strip().lower()
            errors["base"] = await self._validate({**user_input, CONF_EMAIL: email}) or ""
            if not errors["base"] and self._reauth_entry:
                self.hass.config_entries.async_update_entry(self._reauth_entry, data={**user_input, CONF_EMAIL: email})
                await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")
            errors = {key: value for key, value in errors.items() if value}
        return self.async_show_form(step_id="reauth_confirm", data_schema=STEP_SCHEMA, errors=errors)
