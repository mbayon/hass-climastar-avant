"""Async transport client for the Climastar Avant WiFi cloud API."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import aiohttp

from .const import API_BASE, CLIENT_ID, CLIENT_SECRET, HTTP_TIMEOUT, SERIAL_ID, WS_URL

_LOGGER = logging.getLogger(__name__)


class ClimastarError(Exception):
    """Base API exception."""


class ClimastarAuthError(ClimastarError):
    """Credentials or refresh token are no longer accepted."""


class ClimastarConnectionError(ClimastarError):
    """Cloud service is unavailable."""


class ClimastarApiClient:
    """One shared authenticated API client per Home Assistant config entry."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._token_expires_at: datetime | None = None
        self._token_lock = asyncio.Lock()

    @staticmethod
    def user_id_from_token(token: str) -> str:
        """Extract the user id from the JWT payload without validating its signature."""
        try:
            payload = token.split(".")[1]
            decoded = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
            user_id = json.loads(decoded).get("userId")
        except (IndexError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as err:
            raise ClimastarAuthError("Malformed access token") from err
        if not isinstance(user_id, str) or not user_id:
            raise ClimastarAuthError("Access token has no user id")
        return user_id

    async def async_login(self, email: str, password: str) -> None:
        """Obtain a fresh token pair using the account credentials."""
        await self._async_token({"username": email, "password": password, "grant_type": "password"})

    async def async_refresh(self) -> None:
        """Refresh the access token without submitting account credentials."""
        if not self._refresh_token:
            raise ClimastarAuthError("No refresh token")
        await self._async_token({"refresh_token": self._refresh_token, "grant_type": "refresh_token"})

    async def _async_token(self, data: dict[str, str]) -> None:
        headers = {"X-SerialId": SERIAL_ID, "Content-Type": "application/x-www-form-urlencoded"}
        try:
            async with self._session.post(
                f"{API_BASE}/client/token", data=data, headers=headers,
                auth=aiohttp.BasicAuth(CLIENT_ID, CLIENT_SECRET), timeout=HTTP_TIMEOUT,
            ) as response:
                if response.status in (400, 401, 403):
                    raise ClimastarAuthError("Authentication rejected")
                if response.status >= 400:
                    raise ClimastarConnectionError(f"Token endpoint returned HTTP {response.status}")
                payload = await response.json()
        except aiohttp.ClientError as err:
            raise ClimastarConnectionError("Could not reach Climastar cloud") from err
        token = payload.get("access_token")
        refresh = payload.get("refresh_token")
        if not isinstance(token, str) or not isinstance(refresh, str):
            raise ClimastarAuthError("Token response was incomplete")
        self._access_token, self._refresh_token = token, refresh
        expires_in = payload.get("expires_in", 14400)
        try:
            seconds = max(int(expires_in), 60)
        except (TypeError, ValueError):
            seconds = 14400
        self._token_expires_at = datetime.now(UTC) + timedelta(seconds=seconds)

    async def async_access_token(self) -> str:
        """Return a usable access token, refreshing it shortly before expiry."""
        async with self._token_lock:
            if not self._access_token:
                raise ClimastarAuthError("Not authenticated")
            if self._token_expires_at and datetime.now(UTC) >= self._token_expires_at - timedelta(minutes=5):
                _LOGGER.debug("Refreshing Climastar access token")
                await self.async_refresh()
            return self._access_token

    async def _async_update_heater_status(
        self, gateway_id: str, address: int, body: dict[str, str]
    ) -> None:
        """Send a verified status update; the subsequent push update is authoritative."""
        token = await self.async_access_token()
        headers = {"Authorization": f"Bearer {token}", "X-SerialId": SERIAL_ID}
        url = f"{API_BASE}/api/v2/devs/{gateway_id}/htr/{address}/status"
        try:
            async with self._session.post(url, json=body, headers=headers, timeout=HTTP_TIMEOUT) as response:
                if response.status in (401, 403):
                    raise ClimastarAuthError("Authorization rejected")
                if response.status not in (200, 201, 202, 204):
                    raise ClimastarConnectionError(f"Temperature write returned HTTP {response.status}")
        except aiohttp.ClientError as err:
            raise ClimastarConnectionError("Could not update Climastar heater status") from err

    async def async_set_target_temperature(
        self, gateway_id: str, address: int, temperature: float, unit: str
    ) -> None:
        """Set a manual target temperature using the official app's payload."""
        await self._async_update_heater_status(
            gateway_id,
            address,
            {"mode": "manual", "stemp": str(temperature), "units": unit},
        )
        _LOGGER.debug(
            "Manual target temperature request accepted for gateway %s heater %s",
            gateway_id,
            address,
        )

    async def async_set_heater_mode(
        self,
        gateway_id: str,
        address: int,
        mode: str,
        temperature: float | None = None,
        unit: str | None = None,
    ) -> None:
        """Select the verified automatic schedule or manual mode."""
        if mode == "auto":
            body = {"mode": "auto"}
        elif mode == "manual" and temperature is not None and unit is not None:
            body = {"mode": "manual", "stemp": str(temperature), "units": unit}
        else:
            raise ValueError("Manual mode requires a target temperature and unit")
        await self._async_update_heater_status(gateway_id, address, body)
        _LOGGER.debug("Mode request accepted for gateway %s heater %s", gateway_id, address)

    async def async_update_heater_setup(
        self, gateway_id: str, address: int, setup: dict[str, Any]
    ) -> None:
        """Apply a verified heater setup payload; push state remains authoritative."""
        token = await self.async_access_token()
        headers = {"Authorization": f"Bearer {token}", "X-SerialId": SERIAL_ID}
        url = f"{API_BASE}/api/v2/devs/{gateway_id}/htr/{address}/setup"
        try:
            async with self._session.post(
                url, json=setup, headers=headers, timeout=HTTP_TIMEOUT
            ) as response:
                if response.status in (401, 403):
                    raise ClimastarAuthError("Authorization rejected")
                if response.status not in (200, 201, 202, 204):
                    raise ClimastarConnectionError(
                        f"Heater setup write returned HTTP {response.status}"
                    )
        except aiohttp.ClientError as err:
            raise ClimastarConnectionError("Could not update Climastar heater setup") from err
        _LOGGER.debug("Setup request accepted for gateway %s heater %s", gateway_id, address)

    async def async_connect_websocket(self) -> aiohttp.ClientWebSocketResponse:
        """Open an authenticated user WebSocket."""
        token = await self.async_access_token()
        user_id = self.user_id_from_token(token)
        try:
            return await self._session.ws_connect(f"{WS_URL}?{urlencode({'token': token, 'user_id': user_id})}", heartbeat=30)
        except aiohttp.ClientError as err:
            raise ClimastarConnectionError("Could not connect Climastar updates") from err
