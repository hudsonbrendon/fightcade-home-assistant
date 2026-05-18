"""Constants for the Fightcade integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "fightcade"
MANUFACTURER: Final = "Fightcade"

CONF_USERNAME: Final = "username"
CONF_POLL_INTERVAL: Final = "poll_interval"
CONF_FRIENDS: Final = "friends"

DEFAULT_POLL_INTERVAL: Final = 60
MIN_POLL_INTERVAL: Final = 30
MAX_POLL_INTERVAL: Final = 600

API_URL: Final = "https://www.fightcade.com/api/"
REPLAY_URL_TEMPLATE: Final = "https://replay.fightcade.com/{emulator}/{gameid}/{quarkid}"

RANK_MAP: Final = {0: "Unranked", 1: "E", 2: "D", 3: "C", 4: "B", 5: "A", 6: "S"}

EVENT_NEW_TOURNAMENT: Final = "fightcade_event"
EVENT_FRIEND_ONLINE: Final = "fightcade_friend_online"

FAVORITE_GAMES_LIMIT: Final = 3
