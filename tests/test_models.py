"""Tests for pure normalized state parsing."""

from __future__ import annotations

import json
from pathlib import Path

from custom_components.climastar_avant.models import gateway_from_raw


def test_parses_heater_and_uid() -> None:
    data = json.loads((Path(__file__).parent / "fixtures" / "all_data.json").read_text())
    gateway = gateway_from_raw(data["data"][0]["devs"][0])
    assert gateway is not None
    office = gateway.heaters[2]
    assert office.stable_id == "003A00361347313436373230"
    assert office.current_temperature == 26.3
    assert office.target_temperature == 21.0


def test_rename_does_not_change_stable_uid() -> None:
    raw = {"dev_id": "gateway", "devData": {"nodes": [{"type": "htr", "addr": 1, "name": "Before", "uid": "fixed", "installed": True}]}}
    first = gateway_from_raw(raw)
    raw["devData"]["nodes"][0]["name"] = "After"
    second = gateway_from_raw(raw)
    assert first and second and first.heaters[1].stable_id == second.heaters[1].stable_id == "fixed"
