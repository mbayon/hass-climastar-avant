"""Transport behavior tests using aiohttp's test server."""

from __future__ import annotations

import base64
import json

import pytest
from aiohttp import web

from custom_components.climastar_avant.api import ClimastarApiClient, ClimastarAuthError


def test_extracts_user_id() -> None:
    payload = base64.urlsafe_b64encode(json.dumps({"userId": "user-1"}).encode()).decode().rstrip("=")
    assert ClimastarApiClient.user_id_from_token(f"header.{payload}.signature") == "user-1"


def test_rejects_bad_token() -> None:
    with pytest.raises(ClimastarAuthError):
        ClimastarApiClient.user_id_from_token("bad")
