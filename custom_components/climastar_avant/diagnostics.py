"""Safe diagnostics for support requests."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import API_BASE
from .runtime import ClimastarRuntime

TO_REDACT = {
    "token", "access_token", "refresh_token", "authorization", "password", "email", "geodata",
}

def _safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "**REDACTED**" if key.lower() in TO_REDACT else _safe(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_safe(item) for item in value]
    return value

async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry[ClimastarRuntime]) -> dict[str, Any]:
    """Return operational metadata without credentials, tokens, or location data."""
    runtime = entry.runtime_data
    gateways = []
    for gateway in runtime.gateways.values():
        gateways.append({
            "device_id": gateway.device_id,
            "name": gateway.name,
            "product_id": gateway.product_id,
            "firmware": gateway.firmware,
            "connected": gateway.connected,
            "heaters": [
                {
                    "address": heater.address,
                    "uid": heater.uid,
                    "name": heater.name,
                    "installed": heater.installed,
                    "lost": heater.lost,
                    "status": _safe(heater.status),
                    "setup": _safe(heater.setup),
                    "version": _safe(heater.version),
                }
                for heater in gateway.heaters.values()
            ],
        })
    return {"api_host": API_BASE, "websocket_connected": runtime.connected, "gateways": gateways}
