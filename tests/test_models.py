"""Tests for the pure data transforms in models.py."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from custom_components.fightcade.models import (
    build_replay_url,
    epoch_ms_to_iso,
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


def test_epoch_ms_to_iso_returns_utc_isoformat() -> None:
    assert epoch_ms_to_iso(0) == "1970-01-01T00:00:00+00:00"
    assert epoch_ms_to_iso(1716100000000).startswith("2024-")


def test_extract_favorite_gameids_limit_truncates_above_count() -> None:
    user = load("user_online.json")["user"]
    favs = extract_favorite_gameids(user, limit=10)
    assert len(favs) == 3  # only 3 games in fixture  # noqa: PLR2004


def test_extract_favorite_gameids_treats_missing_time_played_as_zero() -> None:
    user = {"gameinfo": {"a": {}, "b": {"time_played": 10}}}
    favs = extract_favorite_gameids(user, limit=2)
    assert favs[0] == "b"


def test_extract_favorite_gameids_empty_dict_gameinfo() -> None:
    assert extract_favorite_gameids({"gameinfo": {}}, limit=3) == []


def test_extract_last_match_handles_no_players() -> None:
    replay = {
        "quarkid": "x",
        "gameid": "g",
        "emulator": "fbneo",
        "date": 0,
        "players": [],
    }
    match = extract_last_match("biggs", [replay])
    assert match is not None
    assert match["opponent"] is None
    assert match["won"] is None


def test_extract_last_match_username_missing_from_players() -> None:
    """If the configured user isn't in the replay, we still pick an opponent."""
    replay = {
        "quarkid": "x",
        "gameid": "g",
        "emulator": "fbneo",
        "date": 0,
        "players": [
            {"name": "alice", "score": 1},
            {"name": "bob", "score": 2},
        ],
    }
    match = extract_last_match("biggs", [replay])
    assert match is not None
    # neither matches → 'you' is None, opponent is first non-match (alice)
    assert match["opponent"] == "alice"
    assert match["won"] is None  # no 'you' score


def test_extract_last_match_one_score_missing_returns_won_none() -> None:
    replay = {
        "quarkid": "x",
        "gameid": "g",
        "emulator": "fbneo",
        "date": 0,
        "players": [
            {"name": "biggs", "score": 3},
            {"name": "rival"},
        ],
    }
    match = extract_last_match("biggs", [replay])
    assert match is not None
    assert match["won"] is None
    assert match["you_score"] == 3  # noqa: PLR2004
    assert match["opponent_score"] is None


def test_extract_last_match_loss_when_opp_score_higher() -> None:
    replay = {
        "quarkid": "x",
        "gameid": "g",
        "emulator": "fbneo",
        "date": 0,
        "players": [
            {"name": "biggs", "score": 1},
            {"name": "rival", "score": 4},
        ],
    }
    match = extract_last_match("biggs", [replay])
    assert match is not None
    assert match["won"] is False


def test_is_online_false_when_last_online_is_zero() -> None:
    """last_online=0 is still a logout timestamp; user is offline."""
    assert is_online({"last_online": 0}) is False
