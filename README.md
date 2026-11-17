<p align="center">
  <img src="custom_components/fightcade/brand/logo@2x.png" alt="Fightcade" height="128">
</p>

# Fightcade for Home Assistant

[![Tests](https://github.com/hudsonbrendon/fightcade-home-assistant/actions/workflows/tests.yml/badge.svg)](https://github.com/hudsonbrendon/fightcade-home-assistant/actions/workflows/tests.yml)
[![Hassfest](https://github.com/hudsonbrendon/fightcade-home-assistant/actions/workflows/hassfest.yml/badge.svg)](https://github.com/hudsonbrendon/fightcade-home-assistant/actions/workflows/hassfest.yml)
[![HACS](https://github.com/hudsonbrendon/fightcade-home-assistant/actions/workflows/validate.yml/badge.svg)](https://github.com/hudsonbrendon/fightcade-home-assistant/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/hudsonbrendon/fightcade-home-assistant?sort=semver)](https://github.com/hudsonbrendon/fightcade-home-assistant/releases)
[![Downloads](https://img.shields.io/github/downloads/hudsonbrendon/fightcade-home-assistant/total)](https://github.com/hudsonbrendon/fightcade-home-assistant/releases)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.4.0%2B-18BCF2?logo=homeassistant&logoColor=white)](https://www.home-assistant.io/)
[![License](https://img.shields.io/github/license/hudsonbrendon/fightcade-home-assistant)](LICENSE)

Unofficial Home Assistant integration that surfaces your Fightcade profile inside HA: online presence, per-game rank and stats, last match, upcoming tournaments, and friend-online notifications.

> Built on the public Fightcade API at `https://www.fightcade.com/api/`. Not affiliated with Fightcade.

## Install (HACS)

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=hudsonbrendon&repository=fightcade-home-assistant&category=integration)
[![Add integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=fightcade)

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
| `sensor.fightcade_<user>_events_<gameid>` | sensor | Count of upcoming events for your top-3 most-played games. |

## Events

| Event | Payload | When |
|---|---|---|
| `fightcade_event` | `{gameid, name, date, link, region, stream?}` | A new tournament appears for one of your favorite games. |
| `fightcade_friend_online` | `{username}` | A configured friend transitions from offline to online. |

## Automation examples

### Notify when a new tournament is announced

```yaml
automation:
  - alias: Notify new Fightcade tournament
    trigger:
      - platform: event
        event_type: fightcade_event
    action:
      - service: notify.mobile_app_my_phone
        data:
          title: "New {{ trigger.event.data.gameid }} tournament"
          message: "{{ trigger.event.data.name }} — {{ trigger.event.data.link }}"
```

### Light up the room when a friend comes online

```yaml
automation:
  - alias: Friend online → arcade light
    trigger:
      - platform: event
        event_type: fightcade_friend_online
    action:
      - service: light.turn_on
        target: {entity_id: light.arcade}
        data: {color_name: "magenta"}
```

## Adding via HACS (manual repo until accepted)

1. HACS → ⋮ → Custom repositories
2. URL: `https://github.com/hudsonbrendon/fightcade-home-assistant`
3. Category: Integration
4. Install, then restart Home Assistant.

## Troubleshooting

- **`user_not_found` during setup** — usernames are case-sensitive on Fightcade. Try the exact capitalization shown in the in-app profile.
- **Sensors not updating** — open Settings → Devices & Services → Fightcade → Diagnostics. Check the `friends[*].error` and the integration log under Logs.
- **Tournament events fire on first refresh** — they shouldn't. If they do, delete `<config>/.storage/fightcade.seen_events.*` and reload the entry.
