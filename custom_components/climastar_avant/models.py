"""Typed, defensive state models for Climastar cloud messages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@dataclass(slots=True)
class Heater:
    gateway_id: str
    address: int
    name: str
    uid: str | None = None
    installed: bool = False
    lost: bool = False
    status: dict[str, Any] = field(default_factory=dict)
    setup: dict[str, Any] = field(default_factory=dict)
    version: dict[str, Any] = field(default_factory=dict)

    @property
    def stable_id(self) -> str:
        """Return a stable identifier; UID is supplied by heater firmware."""
        return self.uid or f"{self.gateway_id}-{self.address}"

    @property
    def current_temperature(self) -> float | None:
        return _float(self.status.get("mtemp"))

    @property
    def target_temperature(self) -> float | None:
        return _float(self.status.get("stemp"))

    @property
    def unit(self) -> str:
        return str(self.status.get("units", self.setup.get("units", "C"))).upper()

    def update_resource(self, resource: str, body: dict[str, Any]) -> None:
        """Merge one resource update received from the push service."""
        target = getattr(self, resource, None)
        if isinstance(target, dict):
            target.update(body)


@dataclass(slots=True)
class Gateway:
    device_id: str
    name: str
    product_id: str | None = None
    firmware: str | None = None
    connected: bool = False
    heaters: dict[int, Heater] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)


def gateway_from_raw(raw: dict[str, Any]) -> Gateway | None:
    """Convert the known gateway shape to a model, tolerating incomplete data."""
    device_id = raw.get("dev_id")
    if not isinstance(device_id, str) or not device_id:
        return None
    dev_data = raw.get("devData") if isinstance(raw.get("devData"), dict) else {}
    gateway = Gateway(
        device_id=device_id,
        name=str(raw.get("name") or "Climastar Avant WiFi Gateway"),
        product_id=str(raw["product_id"]) if raw.get("product_id") is not None else None,
        firmware=str(raw["fw_version"]) if raw.get("fw_version") is not None else None,
        connected=bool(dev_data.get("connected", False)),
        data=dev_data,
    )
    nodes = dev_data.get("nodes", [])
    if not isinstance(nodes, list):
        return gateway
    for node in nodes:
        if not isinstance(node, dict) or node.get("type") != "htr":
            continue
        try:
            address = int(node["addr"])
        except (KeyError, TypeError, ValueError):
            continue
        heater = Heater(
            gateway_id=device_id,
            address=address,
            name=str(node.get("name") or f"Heater {address}"),
            uid=str(node["uid"]) if node.get("uid") else None,
            installed=bool(node.get("installed", False)),
            lost=bool(node.get("lost", False)),
            status=dict(node.get("status") or {}),
            setup=dict(node.get("setup") or {}),
            version=dict(node.get("version") or {}),
        )
        gateway.heaters[address] = heater
    return gateway
