"""Push-driven state runtime shared by all entities in one account."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

import aiohttp

from .api import ClimastarApiClient, ClimastarAuthError, ClimastarConnectionError
from .const import RECONNECT_MAX_DELAY
from .models import Gateway, Heater, gateway_from_raw

_LOGGER = logging.getLogger(__name__)
Listener = Callable[[], None]


class ClimastarRuntime:
    """Owns WebSocket lifecycle and normalized account state."""

    def __init__(self, client: ClimastarApiClient, on_auth_failure: Callable[[], None]) -> None:
        self.client = client
        self._on_auth_failure = on_auth_failure
        self.gateways: dict[str, Gateway] = {}
        self.connected = False
        self._listeners: set[Listener] = set()
        self._task: asyncio.Task[None] | None = None
        self._stopping = False

    async def async_start(self) -> None:
        self._stopping = False
        self._task = asyncio.create_task(self._async_run(), name="climastar_avant_websocket")

    async def async_stop(self) -> None:
        self._stopping = True
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self.connected = False
        self._notify()

    def add_listener(self, listener: Listener) -> Callable[[], None]:
        self._listeners.add(listener)
        def remove() -> None:
            self._listeners.discard(listener)
        return remove

    def get_heater(self, gateway_id: str, address: int) -> Heater | None:
        gateway = self.gateways.get(gateway_id)
        return gateway.heaters.get(address) if gateway else None

    def async_apply_all_data(self, data: Any) -> None:
        """Apply snapshot recursively, accepting homes or a direct device list."""
        found: dict[str, Gateway] = {}
        def walk(value: Any) -> None:
            if isinstance(value, dict):
                if "dev_id" in value and "devData" in value:
                    gateway = gateway_from_raw(value)
                    if gateway:
                        found[gateway.device_id] = gateway
                else:
                    for child in value.values(): walk(child)
            elif isinstance(value, list):
                for child in value: walk(child)
        walk(data)
        self.gateways = found
        self._notify()

    def async_apply_update(self, gateway_id: str, path: str, body: Any) -> None:
        if not isinstance(body, dict): return
        parts = path.strip("/").split("/")
        if len(parts) != 3 or parts[0] != "htr": return
        try: address = int(parts[1])
        except ValueError: return
        heater = self.get_heater(gateway_id, address)
        if heater and parts[2] in {"status", "setup", "prog"}:
            heater.update_resource(parts[2], body)
            _LOGGER.debug("Applied Climastar update %s for gateway %s", path, gateway_id)
            self._notify()

    async def _async_run(self) -> None:
        delay = 1
        while not self._stopping:
            try:
                ws = await self.client.async_connect_websocket()
                self.connected = True; delay = 1; self._notify()
                _LOGGER.debug("Connected to Climastar push service")
                await ws.send_json({"event": "all_data"})
                async for message in ws:
                    if message.type is aiohttp.WSMsgType.TEXT:
                        self._handle_message(message.data)
                    elif message.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                        break
                await ws.close()
            except ClimastarAuthError:
                self.connected = False; self._notify()
                if not self._stopping: self._on_auth_failure()
                return
            except (ClimastarConnectionError, asyncio.TimeoutError) as err:
                _LOGGER.debug("Climastar push connection interrupted: %s", err)
            finally:
                if self.connected:
                    self.connected = False; self._notify()
            if not self._stopping:
                await asyncio.sleep(delay)
                delay = min(delay * 2, RECONNECT_MAX_DELAY)

    def _handle_message(self, raw: str) -> None:
        try: message = json.loads(raw)
        except json.JSONDecodeError: return
        if message.get("event") == "all_data": self.async_apply_all_data(message.get("data", []))
        elif message.get("event") == "update":
            update = message.get("data", {})
            if isinstance(update, dict): self.async_apply_update(str(message.get("devid", "")), str(update.get("path", "")), update.get("body"))

    def _notify(self) -> None:
        for listener in list(self._listeners): listener()
