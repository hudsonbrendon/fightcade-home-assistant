"""Diagnostics for the Fightcade integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

REDACTIONS = {"gravatar"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    coordinator = entry.runtime_data
    data = coordinator.data
    return {
        "entry": {
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "user": async_redact_data(data.user, REDACTIONS),
        "online": data.online,
        "last_match": data.last_match,
        "events_counts": {gid: len(evs) for gid, evs in data.events.items()},
        "friends": {
            friend: {
                "online": info["online"],
                "error": info.get("error"),
            }
            for friend, info in data.friends.items()
        },
    }
