"""Tests for the Fightcade entity base."""

from __future__ import annotations

from custom_components.fightcade.const import DOMAIN, MANUFACTURER
from custom_components.fightcade.entity import build_device_info


def test_build_device_info_uses_username_as_identifier() -> None:
    info = build_device_info("biggs")
    assert info["identifiers"] == {(DOMAIN, "biggs")}
    assert info["name"] == "Fightcade — biggs"
    assert info["manufacturer"] == MANUFACTURER
    assert info["entry_type"] == "service"
