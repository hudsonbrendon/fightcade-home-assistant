# Fightcade for Home Assistant

Unofficial Home Assistant integration that surfaces your Fightcade profile inside HA: online presence, per-game rank and stats, last match, upcoming tournaments, and friend-online notifications.

> Built on the public Fightcade API at `https://www.fightcade.com/api/`. Not affiliated with Fightcade.

## Install (HACS)

1. Add this repository as a custom HACS integration.
2. Install "Fightcade".
3. Restart Home Assistant.
4. Settings → Devices & Services → Add Integration → "Fightcade".
5. Enter your Fightcade username.

## Configuration

Optional, via Configure on the integration card:
- **Polling interval** (default 60 s, range 30–600 s).
- **Friends to watch** — comma-separated Fightcade usernames whose online status you want as binary sensors.

## Entities

| Entity | Type | Notes |
|---|---|---|
| `binary_sensor.fightcade_<user>_online` | binary_sensor | `on` when no logout timestamp is recorded. |
| `binary_sensor.fightcade_friend_<friend>_online` | binary_sensor | One per configured friend. |
| `sensor.fightcade_<user>_last_match` | sensor | Most recent replay; attributes hold opponent, result, replay URL. |
| `sensor.fightcade_<user>_<gameid>_rank` | sensor | One per game in your `gameinfo`. State is the rank letter. |
| `sensor.fightcade_<user>_<gameid>_matches` | sensor | Ranked match count. |
| `sensor.fightcade_<user>_<gameid>_time_played` | sensor | Hours played. |
| `sensor.fightcade_events_<gameid>` | sensor | Count of upcoming events for your top-3 most-played games. |

## Events

| Event | Payload | When |
|---|---|---|
| `fightcade_event` | `{gameid, name, date, link, region, stream?}` | A new tournament appears for one of your favorite games. |
| `fightcade_friend_online` | `{username}` | A configured friend transitions from offline to online. |
