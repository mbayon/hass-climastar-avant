"""Shared entity helpers."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .models import Heater
from .runtime import ClimastarRuntime


class ClimastarHeaterEntity(Entity):
    """Base class tied to a single normalized heater."""

    _attr_has_entity_name = True

    def __init__(self, runtime: ClimastarRuntime, gateway_id: str, address: int) -> None:
        self._runtime, self._gateway_id, self._address = runtime, gateway_id, address
        heater = self.heater
        self._attr_unique_id = f"{heater.stable_id}-{self._key}"

    @property
    def heater(self) -> Heater:
        heater = self._runtime.get_heater(self._gateway_id, self._address)
        if heater is None: raise RuntimeError("Heater disappeared from normalized state")
        return heater

    @property
    def available(self) -> bool:
        heater = self.heater
        gateway = self._runtime.gateways[self._gateway_id]
        return bool(self._runtime.connected and gateway.connected and heater.installed and not heater.lost and heater.status.get("sync_status") != "lost")

    @property
    def device_info(self) -> DeviceInfo:
        heater, gateway = self.heater, self._runtime.gateways[self._gateway_id]
        return DeviceInfo(
            identifiers={(DOMAIN, f"heater-{heater.stable_id}")},
            name=heater.name,
            manufacturer="Climastar",
            model="Climastar Avant WiFi Heater",
            hw_version=str(heater.version.get("hw_version")) if heater.version.get("hw_version") else None,
            sw_version=str(heater.version.get("fw_version")) if heater.version.get("fw_version") else None,
            via_device=(DOMAIN, gateway.device_id),
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._runtime.add_listener(self.async_write_ha_state))
