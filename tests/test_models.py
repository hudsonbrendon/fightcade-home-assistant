"""Tests for the pure data transforms in models.py."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from custom_components.fightcade.models import (
    build_replay_url,
    extract_favorite_gameids,
    extract_last_match,
    is_online,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text())


def test_is_online_true_when_last_online_missing() -> None:
    user = load("user_online.json")["user"]
    assert is_online(user) is True


def test_is_online_false_when_last_online_present() -> None:
    user = load("user_offline.json")["user"]
    assert is_online(user) is False


def test_extract_favorite_gameids_sorted_by_time_played_desc() -> None:
    user = load("user_online.json")["user"]
    favs = extract_favorite_gameids(user, limit=2)
    assert favs == ["umk3", "garou"]


def test_extract_favorite_gameids_empty_when_no_gameinfo() -> None:
    assert extract_favorite_gameids({"name": "x"}, limit=3) == []


def test_extract_last_match_picks_first_replay_and_marks_opponent() -> None:
    replays = load("user_replays.json")["results"]["results"]
    match = extract_last_match("biggs", replays)
    assert match is not None
    assert match["quarkid"] == "1700000000000-1234"
    assert match["gameid"] == "umk3"
    assert match["opponent"] == "rival"
    assert match["you_score"] == 5  # noqa: PLR2004
    assert match["opponent_score"] == 3  # noqa: PLR2004
    assert match["won"] is True
    assert match["replay_url"] == "https://replay.fightcade.com/fbneo/umk3/1700000000000-1234"


def test_extract_last_match_handles_swapped_player_order() -> None:
    replays = load("user_replays.json")["results"]["results"]
    # second replay has biggs at index 1, no scores
    match = extract_last_match("biggs", [replays[1]])
    assert match is not None
    assert match["opponent"] == "rival"
    assert match["won"] is None  # no scores → result unknown


def test_extract_last_match_none_when_no_replays() -> None:
    assert extract_last_match("biggs", []) is None


def test_build_replay_url() -> None:
    url = build_replay_url({"emulator": "fbneo", "gameid": "umk3", "quarkid": "x-1"})
    assert url == "https://replay.fightcade.com/fbneo/umk3/x-1"
