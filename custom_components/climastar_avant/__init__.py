"""Climastar Avant WiFi integration setup."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

from .api import ClimastarApiClient, ClimastarAuthError
from .const import CONF_EMAIL, CONF_PASSWORD, DOMAIN, PLATFORMS
from .runtime import ClimastarRuntime

_LOGGER = logging.getLogger(__name__)
type ClimastarConfigEntry = ConfigEntry[ClimastarRuntime]


async def async_setup_entry(hass: HomeAssistant, entry: ClimastarConfigEntry) -> bool:
    """Set up one account and start its shared push runtime."""
    if not hass.data.setdefault(DOMAIN, {}).get("static_assets_registered"):
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    f"/{DOMAIN}",
                    str(Path(__file__).parent / "images"),
                    cache_headers=True,
                )
            ]
        )
        hass.data[DOMAIN]["static_assets_registered"] = True
    client = ClimastarApiClient(aiohttp_client.async_get_clientsession(hass))
    try:
        await client.async_login(entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])
    except ClimastarAuthError:
        _LOGGER.warning("Climastar account requires reauthentication")
        hass.async_create_task(hass.config_entries.async_start_reauth(entry))
        return False
    except Exception as err:  # Setup must not leak auth details to logs/UI.
        _LOGGER.warning("Could not authenticate Climastar account: %s", type(err).__name__)
        return False

    def start_reauth() -> None:
        hass.async_create_task(hass.config_entries.async_start_reauth(entry))

    runtime = ClimastarRuntime(client, start_reauth)
    entry.runtime_data = runtime
    await runtime.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ClimastarConfigEntry) -> bool:
    """Stop the WebSocket task before unloading platforms."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_stop()
    return unloaded
