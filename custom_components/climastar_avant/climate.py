"""Native climate entities for Climastar heaters."""

from __future__ import annotations

from homeassistant.components.climate import ClimateEntity, HVACAction, HVACMode
from homeassistant.components.climate.const import ClimateEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import device_registry as dr

from .entity import ClimastarHeaterEntity
from .runtime import ClimastarRuntime


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry[ClimastarRuntime], async_add_entities: AddEntitiesCallback) -> None:
    runtime = entry.runtime_data
    device_registry = dr.async_get(hass)
    entities: dict[tuple[str, int], ClimastarClimate] = {}
    def discover() -> None:
        new = []
        for gateway in runtime.gateways.values():
            device_registry.async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={("climastar_avant", gateway.device_id)},
                name=gateway.name,
                manufacturer="Climastar",
                model="Climastar Avant WiFi Gateway",
                sw_version=gateway.firmware,
            )
            for heater in gateway.heaters.values():
                key = (gateway.device_id, heater.address)
                if key not in entities:
                    entities[key] = ClimastarClimate(runtime, *key)
                    new.append(entities[key])
        if new: async_add_entities(new)
    runtime.add_listener(discover)
    discover()


class ClimastarClimate(ClimastarHeaterEntity, ClimateEntity):
    """A heater represented with the limited, verified climate API surface."""

    _key = "climate"
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    # The only observed cloud modes are auto and modified_auto. Both retain the
    # heater's automatic program, so they map to Home Assistant's Auto mode.
    _attr_hvac_modes = [HVACMode.AUTO]
    _attr_target_temperature_step = 0.5

    @property
    def name(self) -> str: return self.heater.name
    @property
    def hvac_mode(self) -> HVACMode | None:
        """Expose the verified automatic program mode without inventing controls."""
        if self.heater.status.get("mode") in {"auto", "modified_auto"}:
            return HVACMode.AUTO
        return None
    @property
    def temperature_unit(self) -> str:
        return UnitOfTemperature.FAHRENHEIT if self.heater.unit == "F" else UnitOfTemperature.CELSIUS
    @property
    def current_temperature(self) -> float | None: return self.heater.current_temperature
    @property
    def target_temperature(self) -> float | None: return self.heater.target_temperature
    @property
    def hvac_action(self) -> HVACAction | None:
        return HVACAction.HEATING if self.heater.status.get("active") else HVACAction.IDLE
    @property
    def extra_state_attributes(self) -> dict[str, str]:
        mode = self.heater.status.get("mode")
        return {"native_mode": str(mode)} if mode is not None else {}
    async def async_set_temperature(self, **kwargs: float) -> None:
        temperature = kwargs.get("temperature")
        if temperature is None: return
        await self._runtime.client.async_set_target_temperature(self._gateway_id, self._address, temperature, self.heater.unit)
