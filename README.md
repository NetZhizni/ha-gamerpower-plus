<img src="https://raw.githubusercontent.com/NetZhizni/ha-gamerpower-plus/main/custom_components/gamerpower_plus/brand/icon.png" alt="GamerPower Plus" width="96" align="right">

# GamerPower Plus

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![Validate](https://github.com/NetZhizni/ha-gamerpower-plus/actions/workflows/validate.yml/badge.svg)](https://github.com/NetZhizni/ha-gamerpower-plus/actions/workflows/validate.yml)
[![Tests](https://github.com/NetZhizni/ha-gamerpower-plus/actions/workflows/tests.yml/badge.svg)](https://github.com/NetZhizni/ha-gamerpower-plus/actions/workflows/tests.yml)

**English** | [Українська](https://github.com/NetZhizni/ha-gamerpower-plus/blob/main/doc/README_uk.md)

Home Assistant integration for free game giveaways (Steam, Epic Games Store, GOG and more) from [GamerPower.com](https://www.gamerpower.com).

> Data provided by [GamerPower.com](https://www.gamerpower.com). This project is not affiliated with GamerPower.

## What it is

The integration polls the [GamerPower API](https://www.gamerpower.com/api-read) every N minutes and creates a device per entry with sensors, a calendar and a "new giveaway" event. It is configured entirely in the UI, no YAML needed.

## How it differs

| | GamerPower Plus | [teefloo/HA-GameGiveAways](https://github.com/teefloo/HA-GameGiveAways) | [nuggetz/ha-gaming-hub](https://github.com/nuggetz/ha-gaming-hub) |
|---|---|---|---|
| Seen giveaways | kept in `Store`, survive restarts | memory only | — |
| "New" detection | by ID | — | by title |
| Bus event + `event` entity | ✅ | ❌ | — |
| Giveaways published while HA was down | reported after start | lost | — |
| Total worth | whole filtered list | first platform only | — |
| API error | entities `unavailable` | value `0` | — |
| Platforms | any of 18 | — | `pc` only |
| Calendar, expiring soon, 16 KB attribute limit | ✅ | — | ✅ |

The domain is `gamerpower_plus`, and it runs side by side with teefloo's `gamerpower`: no events, services or storage are shared.

## Installation

> Home Assistant version requirement:
>
> - Core $\geq$ 2025.8

### Method 1: [HACS](https://hacs.xyz/) (recommended)

One-click installation from HACS:

[![Open your Home Assistant instance and open the GamerPower Plus repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=NetZhizni&repository=ha-gamerpower-plus&category=integration)

Or add the repository by hand:

1. HACS → ⋮ → **Custom repositories** → add `https://github.com/NetZhizni/ha-gamerpower-plus` with type **Integration**.
2. In the HACS search box, type **GamerPower Plus** → open it → **Download**.
3. Restart Home Assistant.

HACS then offers new releases as updates.

### Method 2: Git clone from GitHub

You need shell access to Home Assistant, for example the [Terminal & SSH](https://github.com/home-assistant/addons/tree/master/ssh) add-on.

```bash
cd /config
git clone https://github.com/NetZhizni/ha-gamerpower-plus.git
mkdir -p custom_components
cp -r ha-gamerpower-plus/custom_components/gamerpower_plus custom_components/
```

Restart Home Assistant afterwards.

This method makes it easy to switch to a specific release. For example, to update to version 1.0.0:

```bash
cd /config/ha-gamerpower-plus
git fetch --tags
git checkout 1.0.0
rm -rf /config/custom_components/gamerpower_plus
cp -r custom_components/gamerpower_plus /config/custom_components/
```

Then restart Home Assistant again.

### Method 3: Manual installation via [Samba](https://github.com/home-assistant/addons/tree/master/samba) / [FTPS](https://github.com/hassio-addons/addon-ftp)

1. Download the archive of the latest release from [Releases](https://github.com/NetZhizni/ha-gamerpower-plus/releases).
2. Copy the `custom_components/gamerpower_plus` folder into the `config/custom_components` folder of your Home Assistant.
3. Restart Home Assistant.

## Configuration

### Add the integration

[Settings > Devices & services > ADD INTEGRATION](https://my.home-assistant.io/redirect/config_flow_start/?domain=gamerpower_plus) > search `GamerPower Plus` > choose platforms and giveaway types > SUBMIT

[![Open your Home Assistant instance and start setting up a new GamerPower Plus integration instance.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=gamerpower_plus)

### Options

| Option | Default | Description |
|---|---|---|
| Name | generated, e.g. `Steam, Epic — game` | Entry and device name |
| Platforms | Steam, Epic Games Store | Any of the 18 API platforms; a giveaway matches if it is on at least one of them |
| Giveaway types | game | `game` (games), `loot` (DLC, items), `beta` (beta, early access) |
| Sort by | Date | Date / Value / Popularity (sorted by the API, and the order is checked again locally after filtering) |
| Update interval | 60 min | At least 15 min (the API caches responses for 10 min) |
| Minimum worth | 0 USD | Hide cheaper giveaways; 0 shows everything |
| Include giveaways without worth (N/A) | on | Keep giveaways with unknown worth |
| Exclude keywords | — | Comma separated, case insensitive, e.g. `playtest, demo` |
| Expiring soon threshold | 24 h | When the `binary_sensor` turns on |

- **Platforms and types** are chosen when the entry is created and can be changed with **⋮ → Reconfigure**. They make the entry unique, so the same combination can't be added twice. After a change, giveaways that are already active are not reported as new.
- **Everything else** lives in **Configure** (options). The entry reloads by itself, no restart needed.
- You can create several entries, e.g. "Steam, Epic — game" and "PC — loot".

## Entities

Each entry creates one device with these entities:

| Entity | State |
|---|---|
| `sensor.…_active_giveaways` | Number of giveaways after all filters. The `giveaways` attribute lists `id, title, worth, end_date, url, image`, cut to keep attributes under 16 KB (`truncated: true` when items were dropped) |
| `sensor.…_total_worth` | Total worth in USD (`monetary`) of exactly the list you see |
| `sensor.…_latest_giveaway` | Title of the most recently published giveaway (by `published_date`); all its fields as attributes, the image as `entity_picture` |
| `binary_sensor.…_expiring_soon` | `on` while a giveaway ends within the threshold; the `giveaways` attribute lists them. Switches at the exact moment, not only on updates |
| `event.…_new_giveaway` | Fires for every new giveaway (`event_type: new_giveaway`) with the same data as the bus event |
| `calendar.…_giveaways` | Giveaways with a known end date as events from `published_date` to `end_date` |

When the API is unreachable or fails, entities become `unavailable`, not `0`. The API answer "no active giveaways" (HTTP 201) gives `0`.

## Event `gamerpower_plus_new_giveaway`

Fired on the event bus for every new giveaway. Fields: `id`, `title`, `worth` (`"$19.99"` / `"N/A"`), `worth_value` (number or `null`), `platforms` (list), `type`, `published_date`, `end_date` (ISO or `null`), `image`, `thumbnail`, `open_giveaway_url`, `gamerpower_url`, `description`, `instructions`, `config_entry_id`, `entry_title`.

How "new" is decided:
- Seen IDs are stored in `.storage/gamerpower_plus.<entry_id>` as `{id: first_seen}`. IDs older than 60 days that left the response are dropped.
- **First run**: everything current is recorded silently, no events.
- **After a restart**, giveaways published during the downtime are reported as new. Events wait until Home Assistant has fully started so automations receive them.
- An ID that disappears for a while and comes back is **not** new.
- Giveaways hidden by local filters are remembered but not announced.

## Services

| Service | Description |
|---|---|
| `gamerpower_plus.refresh` | Update now. `config_entry_id` is optional; without it every entry is refreshed |
| `gamerpower_plus.get_giveaways` | Returns `{entries: [{config_entry_id, title, count, total_worth, giveaways: [...]}]}` with all fields |
| `gamerpower_plus.reset_seen` | Forgets seen giveaways and refreshes right away, so every current giveaway is reported as new. Handy for testing notifications |

```yaml
action: gamerpower_plus.get_giveaways
response_variable: result
# {{ result.entries[0].giveaways | map(attribute='title') | list }}
```

## Example: phone notification with image and button

```yaml
alias: "New free game → phone"
triggers:
  - trigger: event
    event_type: gamerpower_plus_new_giveaway
actions:
  - action: notify.mobile_app_my_phone
    data:
      title: "🎁 {{ trigger.event.data.title }}"
      message: >-
        {{ trigger.event.data.worth }} · {{ trigger.event.data.platforms | join(', ') }}
        {%- if trigger.event.data.end_date %}
        · until {{ as_timestamp(trigger.event.data.end_date) | timestamp_custom('%d.%m %H:%M') }}
        {%- endif %}
      data:
        image: "{{ trigger.event.data.image }}"
        url: "{{ trigger.event.data.open_giveaway_url }}"          # iOS: tap action
        clickAction: "{{ trigger.event.data.open_giveaway_url }}"  # Android: tap action
        actions:
          - action: URI
            title: "Claim"
            uri: "{{ trigger.event.data.open_giveaway_url }}"
mode: queued
```

Instead of the bus event you can use the `event` entity; the data is then in `trigger.to_state.attributes`:

```yaml
triggers:
  - trigger: state
    entity_id: event.steam_epic_game_new_giveaway
    not_to: [unavailable, unknown]
```

## Example: Telegram

```yaml
alias: "New free game → Telegram"
triggers:
  - trigger: event
    event_type: gamerpower_plus_new_giveaway
actions:
  - action: telegram_bot.send_photo
    data:
      url: "{{ trigger.event.data.image }}"
      parse_mode: html
      caption: >-
        🎁 <b>{{ trigger.event.data.title }}</b>
        ({{ trigger.event.data.worth }}, {{ trigger.event.data.platforms | join(', ') }})

        {{ trigger.event.data.description[:500] }}

        <a href="{{ trigger.event.data.open_giveaway_url }}">Claim</a>
mode: queued
```

## Lovelace card

```yaml
type: markdown
title: 🎁 Free games
content: >-
  {% set items = state_attr('sensor.steam_epic_game_active_giveaways', 'giveaways') or [] %}
  {% for g in items %}
  <a href="{{ g.url }}"><img src="{{ g.image }}" width="100%"></a>

  **[{{ g.title }}]({{ g.url }})** — {{ g.worth }}
  {%- if g.end_date %}, until {{ as_timestamp(g.end_date) | timestamp_custom('%d.%m %H:%M') }}{% endif %}

  {% else %}
  No giveaways right now.
  {% endfor %}

  <sub>Data provided by [GamerPower.com](https://www.gamerpower.com)</sub>
```

For a calendar view, use the standard **Calendar** card with the `calendar.…_giveaways` entity.

### Detailed card with description and instructions

The `giveaways` attribute is compact (`id, title, worth, end_date, url, image`) to stay under 16 KB. If the card needs the poster, platforms, number of users who claimed it, description and instructions, create a trigger-based template sensor. It fetches the full list with `gamerpower_plus.get_giveaways` and updates together with the integration:

```yaml
# configuration.yaml
template:
  - triggers:
      - trigger: homeassistant
        event: start
      - trigger: state   # without to/from it also fires on attribute changes
        entity_id: sensor.steam_epic_game_active_giveaways
    actions:
      - action: gamerpower_plus.get_giveaways
        data: {}   # several entries? add config_entry_id: <entry ID>
        response_variable: result
    sensor:
      - name: "Steam giveaways data"   # → sensor.steam_giveaways_data
        unique_id: gamerpower_plus_giveaways_full
        state: "{{ result.entries[0].count }}"
        attributes:
          games: "{{ result.entries[0].giveaways }}"
```

Compared with the `command_line` script, only two fields differ: `platforms` is now a list (`| join(', ')`), and an unknown `end_date` is `null` instead of `'N/A'`. The card uses `regex_replace` instead of `striptags`, because `striptags` collapses line breaks and the instruction steps would run into one line.

```yaml
type: markdown
content: |
  {% set games = state_attr('sensor.steam_giveaways_data', 'games') %}
  {% if games and games | length > 0 %}
  {% for game in games %}
  ### [{{ game.title }}]({{ game.open_giveaway_url }})
  [![Game poster]({{ game.thumbnail }})]({{ game.open_giveaway_url }})
  **🖥 Platform:** {{ game.platforms | join(', ') }}
  **💰 Price:** {% if game.worth != 'N/A' %}~~{{ game.worth }}~~ ➡️ {% endif %}**FREE!**
  **⏳ Ends:** {{ (as_timestamp(game.end_date) | timestamp_custom('%d.%m.%Y %H:%M')) if game.end_date else 'Unknown' }}
  **👥 Claimed by:** {{ game.users }} users
  **📝 Description:** {{ game.description | regex_replace('<[^>]+>', '') | replace('\r\n', '\n') }}
  **🛠 Instructions:** {{ game.instructions | regex_replace('<[^>]+>', '') | replace('\r\n', '\n') }}

  ---
  {% endfor %}
  {% else %}
  *No active giveaways right now, or the sensor data is unavailable* 🤷‍♂️
  {% endif %}

  <sub>Data provided by [GamerPower.com](https://www.gamerpower.com)</sub>
```

For large selections (for example PC + loot) the `games` attribute can exceed 16 KB. The recorder then won't store it in history and logs a warning, but the card still works.

## Migrating from the `steam_giveaways.py` command_line script

1. Install the integration and add an entry with platforms **Steam** and **Epic Games Store** and type **game**. That is exactly the query the script made (`/filter?platform=epic-games-store.steam&type=game`).
2. Data mapping:

   | Script | GamerPower Plus |
   |---|---|
   | `total_count` | state of `sensor.…_active_giveaways` |
   | `games` | the `giveaways` attribute of the same sensor, the `get_giveaways` service, or the template sensor from the [detailed card](#detailed-card-with-description-and-instructions) |
   | `new_games` | event `gamerpower_plus_new_giveaway` / `event.…_new_giveaway` |

3. Rewrite the automations that watched `new_games` to use the trigger from the examples above.
4. Remove the `command_line` sensor from `configuration.yaml`, delete `steam_giveaways.py` and `/config/steam_giveaways_cache.json`, and restart Home Assistant.

The script cache is not imported. The first run of the integration records current giveaways silently, so you won't get duplicate notifications for games you already know about.

## Diagnostics

**Devices & services → GamerPower Plus → ⋮ → Download diagnostics**. The file contains the entry settings and public giveaway data; there is nothing sensitive in it.

## Known limitations

- API dates carry no timezone; they are treated as UTC.
- `/worth` can't combine several platforms, so total worth is summed locally from the `worth` fields; `N/A` giveaways are not counted.
- The API doesn't publish its popularity metric, so popularity sorting keeps the order returned by the API.

## Attribution

Giveaway data is provided by [GamerPower.com](https://www.gamerpower.com). Every entity carries the attribution `Data provided by GamerPower.com`, as the API terms require.

## Releases

The `Tag & Release` workflow runs on every push to `main` that changes `custom_components/gamerpower_plus/manifest.json`. When the tag for its `version` doesn't exist yet, the workflow creates the tag and a GitHub release with generated notes, and HACS offers that release as an update. To publish a release:

1. Bump `version` in `manifest.json` and `VERSION` in `const.py` (the workflow and a test check they match).
2. Add the changes to `CHANGELOG.md`.
3. Push to `main`.

The icon in `custom_components/gamerpower_plus/brand/` is served by Home Assistant itself (verified on 2026.10), so no home-assistant/brands entry is needed. Versions without local brand support show a placeholder icon.

## License

[MIT](LICENSE)
