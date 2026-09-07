"""Push snapshot and incremental update tests."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

from custom_components.climastar_avant.runtime import ClimastarRuntime


def test_snapshot_and_incremental_update() -> None:
    runtime = ClimastarRuntime(Mock(), Mock())
    snapshot = json.loads((Path(__file__).parent / "fixtures" / "all_data.json").read_text())["data"]
    runtime.async_apply_all_data(snapshot)
    assert set(runtime.gateways) == {"e106b5d318f0819bef", "second-gateway"}
    runtime.async_apply_update("e106b5d318f0819bef", "/htr/2/status", {"stemp": "20.5", "active": True})
    heater = runtime.get_heater("e106b5d318f0819bef", 2)
    assert heater and heater.target_temperature == 20.5 and heater.status["active"] is True
