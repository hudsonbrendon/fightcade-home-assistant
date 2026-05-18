"""Shared entity helpers for the Fightcade integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, MANUFACTURER


def build_device_info(username: str) -> DeviceInfo:
    """Build the DeviceInfo for a Fightcade account.

    One device per config entry, keyed by username, so every entity for a given
    user is grouped under the same device card in the UI.
    """
    return DeviceInfo(
        identifiers={(DOMAIN, username)},
        name=f"Fightcade — {username}",
        manufacturer=MANUFACTURER,
        entry_type=DeviceEntryType.SERVICE,
        configuration_url="https://www.fightcade.com/",
    )
