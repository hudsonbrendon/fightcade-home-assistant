"""Config flow placeholder for the Fightcade integration (filled in Task 5)."""

from __future__ import annotations

from homeassistant.config_entries import ConfigFlow

from .const import DOMAIN


class FightcadeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fightcade (implementation in Task 5)."""

    VERSION = 1
