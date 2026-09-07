"""Read-only useful state binary sensors."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import ClimastarHeaterEntity
from .runtime import ClimastarRuntime

DESCRIPTIONS = (
    BinarySensorEntityDescription(key="window_open", translation_key="window_open", device_class=BinarySensorDeviceClass.WINDOW),
    BinarySensorEntityDescription(key="presence", translation_key="presence", device_class=BinarySensorDeviceClass.OCCUPANCY),
)
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry[ClimastarRuntime], async_add_entities: AddEntitiesCallback) -> None:
    runtime = entry.runtime_data; added: set[tuple[str, int, str]] = set()
    def discover() -> None:
        new = []
        for gateway in runtime.gateways.values():
            for heater in gateway.heaters.values():
                for description in DESCRIPTIONS:
                    key = (gateway.device_id, heater.address, description.key)
                    if key not in added: added.add(key); new.append(ClimastarBinarySensor(runtime, gateway.device_id, heater.address, description))
        if new: async_add_entities(new)
    runtime.add_listener(discover); discover()

class ClimastarBinarySensor(ClimastarHeaterEntity, BinarySensorEntity):
    def __init__(self, runtime: ClimastarRuntime, gateway_id: str, address: int, description: BinarySensorEntityDescription) -> None:
        self.entity_description = description; self._key = description.key
        super().__init__(runtime, gateway_id, address)
    @property
    def is_on(self) -> bool | None:
        return self.heater.status.get(self._key)
