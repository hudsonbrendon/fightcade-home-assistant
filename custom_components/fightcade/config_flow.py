"""Config and options flow for the Fightcade integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .api import FightcadeApiError, FightcadeClient, FightcadeUserNotFound
from .const import (
    CONF_FRIENDS,
    CONF_POLL_INTERVAL,
    CONF_USERNAME,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    MAX_POLL_INTERVAL,
    MIN_POLL_INTERVAL,
)


def _parse_friends_csv(raw: str) -> list[str]:
    return [u.strip() for u in raw.split(",") if u.strip()]


class FightcadeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Initial user flow: ask for username, validate against the API."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            username = user_input[CONF_USERNAME].strip()
            await self.async_set_unique_id(username.lower())
            self._abort_if_unique_id_configured()

            client = FightcadeClient(async_get_clientsession(self.hass))
            try:
                await client.async_get_user(username)
            except FightcadeUserNotFound:
                errors["base"] = "user_not_found"
            except FightcadeApiError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title=username, data={CONF_USERNAME: username})

        schema = vol.Schema({vol.Required(CONF_USERNAME): str})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return FightcadeOptionsFlow(entry)


class FightcadeOptionsFlow(OptionsFlow):
    """Options flow: polling interval, friends list."""

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    CONF_POLL_INTERVAL: int(user_input[CONF_POLL_INTERVAL]),
                    CONF_FRIENDS: _parse_friends_csv(user_input[CONF_FRIENDS]),
                },
            )

        current_interval = self._entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
        current_friends = ", ".join(self._entry.options.get(CONF_FRIENDS, []))

        schema = vol.Schema(
            {
                vol.Required(CONF_POLL_INTERVAL, default=current_interval): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_POLL_INTERVAL,
                        max=MAX_POLL_INTERVAL,
                        step=10,
                        mode=NumberSelectorMode.BOX,
                        unit_of_measurement="s",
                    )
                ),
                vol.Optional(CONF_FRIENDS, default=current_friends): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
