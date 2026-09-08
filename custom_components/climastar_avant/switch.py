"""Verified configuration switches for Climastar heaters."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import ClimastarHeaterEntity
from .runtime import ClimastarRuntime

_SETUP_FIELDS = frozenset(
    {
        "revision",
        "sync_status",
        "control_mode",
        "units",
        "power",
        "offset",
        "priority",
        "away_mode",
        "away_offset",
        "modified_auto_span",
        "window_mode_enabled",
        "true_radiant_enabled",
        "max_stemp_limit",
    }
)

DESCRIPTIONS = (
    SwitchEntityDescription(
        key="window_mode_enabled",
        translation_key="window_mode",
        entity_category=EntityCategory.CONFIG,
    ),
    SwitchEntityDescription(
        key="true_radiant_enabled",
        translation_key="true_radiant",
        entity_category=EntityCategory.CONFIG,
    ),
)

_CAPABILITY_FIELDS = {
    "window_mode_enabled": "window_mode_available",
    "true_radiant_enabled": "true_radiant_available",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[ClimastarRuntime],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one switch for every verified writable setup capability."""
    runtime = entry.runtime_data
    added: set[tuple[str, int, str]] = set()

    def discover() -> None:
        new_entities = []
        for gateway in runtime.gateways.values():
            for heater in gateway.heaters.values():
                for description in DESCRIPTIONS:
                    if description.key not in heater.setup:
                        continue
                    capability = _CAPABILITY_FIELDS[description.key]
                    factory_options = heater.setup.get("factory_options", {})
                    if isinstance(factory_options, dict) and not factory_options.get(
                        capability, False
                    ):
                        continue
                    key = (gateway.device_id, heater.address, description.key)
                    if key not in added:
                        added.add(key)
                        new_entities.append(
                            ClimastarSetupSwitch(
                                runtime, gateway.device_id, heater.address, description
                            )
                        )
        if new_entities:
            async_add_entities(new_entities)

    runtime.add_listener(discover)
    discover()


class ClimastarSetupSwitch(ClimastarHeaterEntity, SwitchEntity):
    """A setup flag with a confirmed REST write payload."""

    def __init__(
        self,
        runtime: ClimastarRuntime,
        gateway_id: str,
        address: int,
        description: SwitchEntityDescription,
    ) -> None:
        self.entity_description = description
        self._key = description.key
        super().__init__(runtime, gateway_id, address)

    @property
    def is_on(self) -> bool | None:
        value = self.heater.setup.get(self._key)
        return bool(value) if value is not None else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set_enabled(False)

    async def _async_set_enabled(self, enabled: bool) -> None:
        setup = self.heater.setup
        payload = {key: setup[key] for key in _SETUP_FIELDS if key in setup}
        missing = _SETUP_FIELDS - payload.keys()
        if missing:
            raise HomeAssistantError("Heater setup is incomplete; try again after it syncs")
        payload[self._key] = enabled
        await self._runtime.client.async_update_heater_setup(
            self._gateway_id, self._address, payload
        )
