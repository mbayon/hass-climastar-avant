"""Small, useful diagnostic sensors for Climastar heaters."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import ClimastarHeaterEntity
from .runtime import ClimastarRuntime

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(hours=1)

DESCRIPTIONS = (
    SensorEntityDescription(
        key="energy_consumption",
        translation_key="energy_consumption",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
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
        self._energy_kwh: float | None = None
        super().__init__(runtime, gateway_id, address)

    @property
    def should_poll(self) -> bool:
        """Only the cloud energy-history endpoint needs periodic polling."""
        return self._key == "energy_consumption"

    async def async_added_to_hass(self) -> None:
        """Request the first energy reading immediately rather than after an hour."""
        await super().async_added_to_hass()
        if self._key == "energy_consumption":
            self.async_schedule_update_ha_state(force_refresh=True)

    async def async_update(self) -> None:
        """Refresh the vendor's cumulative energy measurement."""
        if self._key != "energy_consumption":
            return
        try:
            counter = await self._runtime.client.async_get_heater_energy_counter(
                self._gateway_id, self._address
            )
        except Exception as err:  # Keep the last valid total during a cloud outage.
            _LOGGER.debug("Could not refresh energy for Climastar heater %s: %s", self._address, err)
            return
        if counter is not None:
            # Verified against the official app: one counter step is 0.1 Wh.
            self._energy_kwh = counter / 10_000

    @property
    def native_value(self):
        if self._key == "energy_consumption":
            return self._energy_kwh
        value = {"pcb_temperature": self.heater.status.get("pcb_temp"), "rated_power": self.heater.setup.get("power", self.heater.status.get("power")), "duty": self.heater.status.get("duty"), "error_code": self.heater.status.get("error_code")}[self._key]
        try: return float(value) if self._key != "error_code" else int(value)
        except (TypeError, ValueError): return None
