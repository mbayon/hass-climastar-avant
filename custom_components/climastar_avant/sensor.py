"""Small, useful diagnostic sensors for Climastar heaters."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfPower, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import ClimastarHeaterEntity
from .runtime import ClimastarRuntime

DESCRIPTIONS = (
    SensorEntityDescription(key="pcb_temperature", translation_key="pcb_temperature", device_class=SensorDeviceClass.TEMPERATURE, native_unit_of_measurement=UnitOfTemperature.CELSIUS, entity_category=EntityCategory.DIAGNOSTIC),
    SensorEntityDescription(key="rated_power", translation_key="rated_power", device_class=SensorDeviceClass.POWER, native_unit_of_measurement=UnitOfPower.WATT, entity_category=EntityCategory.DIAGNOSTIC),
    SensorEntityDescription(key="duty", translation_key="duty", native_unit_of_measurement="%", entity_category=EntityCategory.DIAGNOSTIC),
    SensorEntityDescription(key="error_code", translation_key="error_code", entity_category=EntityCategory.DIAGNOSTIC),
)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry[ClimastarRuntime], async_add_entities: AddEntitiesCallback) -> None:
    runtime = entry.runtime_data
    added: set[tuple[str, int, str]] = set()
    def discover() -> None:
        new = []
        for gateway in runtime.gateways.values():
            for heater in gateway.heaters.values():
                for description in DESCRIPTIONS:
                    key = (gateway.device_id, heater.address, description.key)
                    if key not in added: added.add(key); new.append(ClimastarSensor(runtime, gateway.device_id, heater.address, description))
        if new: async_add_entities(new)
    runtime.add_listener(discover); discover()

class ClimastarSensor(ClimastarHeaterEntity, SensorEntity):
    def __init__(self, runtime: ClimastarRuntime, gateway_id: str, address: int, description: SensorEntityDescription) -> None:
        self.entity_description = description; self._key = description.key
        super().__init__(runtime, gateway_id, address)
    @property
    def native_value(self):
        value = {"pcb_temperature": self.heater.status.get("pcb_temp"), "rated_power": self.heater.setup.get("power", self.heater.status.get("power")), "duty": self.heater.status.get("duty"), "error_code": self.heater.status.get("error_code")}[self._key]
        try: return float(value) if self._key != "error_code" else int(value)
        except (TypeError, ValueError): return None
