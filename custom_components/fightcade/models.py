"""Pure data transforms over Fightcade API payloads.

Kept free of Home Assistant imports so they are trivially unit-testable.
"""

from __future__ import annotations

from typing import Any

from .const import REPLAY_URL_TEMPLATE


def is_online(user: dict[str, Any]) -> bool:
    """A user is online when the API omits last_online (no logout recorded)."""
    return user.get("last_online") is None


def extract_favorite_gameids(user: dict[str, Any], *, limit: int) -> list[str]:
    """Top-N gameids by time_played from the user's gameinfo."""
    gameinfo = user.get("gameinfo") or {}
    ranked = sorted(
        gameinfo.items(),
        key=lambda kv: kv[1].get("time_played", 0),
        reverse=True,
    )
    return [gid for gid, _ in ranked[:limit]]


def build_replay_url(replay: dict[str, Any]) -> str:
    """Build a Fightcade replay URL from replay metadata."""
    return REPLAY_URL_TEMPLATE.format(
        emulator=replay["emulator"],
        gameid=replay["gameid"],
        quarkid=replay["quarkid"],
    )


def extract_last_match(username: str, replays: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Normalize the most recent replay into a flat dict centered on `username`.

    Returns None if there are no replays. `won` is True/False/None — None when
    scores aren't recorded (casual matches).
    """
    if not replays:
        return None
    replay = replays[0]
    players = replay.get("players", [])
    you = next((p for p in players if p.get("name") == username), None)
    opponent = next((p for p in players if p.get("name") != username), None)
    you_score = you.get("score") if you else None
    opp_score = opponent.get("score") if opponent else None
    won: bool | None
    if you_score is None or opp_score is None:
        won = None
    else:
        won = you_score > opp_score
    return {
        "quarkid": replay["quarkid"],
        "gameid": replay["gameid"],
        "channelname": replay.get("channelname"),
        "date": replay["date"],
        "duration": replay.get("duration"),
        "ranked": replay.get("ranked"),
        "opponent": opponent["name"] if opponent else None,
        "opponent_country": (opponent or {}).get("country"),
        "you_score": you_score,
        "opponent_score": opp_score,
        "won": won,
        "replay_url": build_replay_url(replay),
    }
