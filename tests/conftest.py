"""Common fixtures for fightcade tests."""
from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.fightcade.const import (
    CONF_FRIENDS,
    CONF_POLL_INTERVAL,
    CONF_USERNAME,
    DOMAIN,
)


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="biggs",
        data={CONF_USERNAME: "biggs"},
        options={CONF_POLL_INTERVAL: 60, CONF_FRIENDS: []},
        entry_id="01HZZZZ",
        unique_id="biggs",
    )


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom_components in every test."""
    yield
