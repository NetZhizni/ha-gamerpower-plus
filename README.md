# GamerPower Plus

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![Validate](https://github.com/NetZhizni/ha-gamerpower-plus/actions/workflows/validate.yml/badge.svg)](https://github.com/NetZhizni/ha-gamerpower-plus/actions/workflows/validate.yml)
[![Tests](https://github.com/NetZhizni/ha-gamerpower-plus/actions/workflows/tests.yml/badge.svg)](https://github.com/NetZhizni/ha-gamerpower-plus/actions/workflows/tests.yml)

**[Українська](#українська) · [English](#english)**

Home Assistant integration for free game giveaways (Steam, Epic Games Store, GOG and more) from [GamerPower.com](https://www.gamerpower.com).

> Data provided by [GamerPower.com](https://www.gamerpower.com). This project is not affiliated with GamerPower.

---

## Українська

### Що це

Інтеграція раз на N хвилин запитує [GamerPower API](https://www.gamerpower.com/api-read) і створює для кожного запису пристрій з сенсорами, календарем і подією «нова роздача». Налаштовується тільки через UI, YAML не потрібен.

### Чим відрізняється від інших

| | GamerPower Plus | [teefloo/HA-GameGiveAways](https://github.com/teefloo/HA-GameGiveAways) | [nuggetz/ha-gaming-hub](https://github.com/nuggetz/ha-gaming-hub) |
|---|---|---|---|
| Бачені роздачі | у `Store`, переживають перезапуск HA | лише в пам'яті | — |
| Визначення «нової» | за ID | — | за назвою |
| Подія на шині + `event`-сутність | ✅ | ❌ | — |
| Роздачі, що з'явилися під час простою HA | ловляться після запуску | губляться | — |
| Сумарна вартість | з усього відфільтрованого списку | лише з першої платформи | — |
| Помилка API | сутності `unavailable` | значення `0` | — |
| Платформи | будь-які з 18 | — | лише `pc` |
| Календар, «скоро закінчиться», ліміт атрибутів 16 KB | ✅ | — | ✅ |

Інтеграція має domain `gamerpower_plus` і може працювати поруч із `gamerpower` від teefloo: у них немає спільних подій, сервісів чи сховища.

### Встановлення через HACS

1. HACS → ⋮ → **Custom repositories** → додайте `https://github.com/NetZhizni/ha-gamerpower-plus` з типом **Integration**.
2. Знайдіть **GamerPower Plus** у HACS і встановіть.
3. Перезапустіть Home Assistant.
4. **Налаштування → Пристрої та служби → Додати інтеграцію → GamerPower Plus**.

Вручну: скопіюйте `custom_components/gamerpower_plus` у `/config/custom_components/` і перезапустіть HA.

Мінімальна версія Home Assistant: 2025.8.

### Налаштування

| Параметр | За замовчуванням | Опис |
|---|---|---|
| Назва | генерується, напр. `Steam, Epic — game` | Назва запису й пристрою |
| Платформи | Steam, Epic Games Store | Будь-які з 18 платформ API. Роздача підходить, якщо вона є хоча б на одній |
| Типи роздач | game | `game` (ігри), `loot` (DLC, предмети), `beta` (бета, ранній доступ) |
| Сортування | Дата | Дата / Вартість / Популярність (сортує API, а після фільтрів порядок перевіряється локально) |
| Інтервал оновлення | 60 хв | Мінімум 15 хв (API кешує відповіді на 10 хв) |
| Мінімальна вартість | 0 USD | Роздачі, дешевші за неї, приховуються. 0 означає показувати все |
| Включати роздачі без вартості (N/A) | так | Чи показувати роздачі з невідомою вартістю |
| Ключові слова для виключення | — | Через кому, без урахування регістру, напр. `playtest, demo` |
| Поріг «Скоро закінчиться» | 24 год | Коли вмикається `binary_sensor` |

- **Платформи й типи** задаються при створенні запису, а змінити їх можна через **⋮ → Змінити конфігурацію** (Reconfigure). Від них залежить унікальність запису: два записи з однаковою комбінацією створити не вийде. Після зміни вибору роздачі, які вже активні, не надсилаються як нові.
- **Усе інше** змінюється в **Параметрах** (Configure). Запис перезавантажується автоматично, без перезапуску HA.
- Записів можна створити кілька, наприклад окремо «Steam, Epic — game» і «PC — loot».

### Сутності

Для кожного запису створюється один пристрій із такими сутностями:

| Сутність | Що показує |
|---|---|
| `sensor.…_active_giveaways` | Кількість роздач після всіх фільтрів. Атрибут `giveaways` містить список `id, title, worth, end_date, url, image`, обрізаний так, щоб атрибути були < 16 KB (`truncated: true`, якщо щось не влізло) |
| `sensor.…_total_worth` | Сумарна вартість у USD (`monetary`) саме того списку, який ви бачите |
| `sensor.…_latest_giveaway` | Назва найновішої роздачі за `published_date`. В атрибутах усі її поля, картинка показується як `entity_picture` |
| `binary_sensor.…_expiring_soon` | `on`, якщо якась роздача закінчується раніше за поріг. Атрибут `giveaways` містить такі роздачі. Стан змінюється точно в момент, а не лише під час оновлення |
| `event.…_new_giveaway` | Спрацьовує на кожну нову роздачу (`event_type: new_giveaway`), атрибути як у події на шині |
| `calendar.…_giveaways` | Роздачі з відомою датою завершення у вигляді подій від `published_date` до `end_date` |

Якщо API недоступний або повертає помилку, сутності стають `unavailable`, а не `0`. Відповідь API «немає активних роздач» (HTTP 201) дає `0`.

### Подія `gamerpower_plus_new_giveaway`

Надсилається на шину подій для кожної нової роздачі. Поля: `id`, `title`, `worth` (`"$19.99"` / `"N/A"`), `worth_value` (число або `null`), `platforms` (список), `type`, `published_date`, `end_date` (ISO або `null`), `image`, `thumbnail`, `open_giveaway_url`, `gamerpower_url`, `description`, `instructions`, `config_entry_id`, `entry_title`.

Як визначається «нова»:
- ID бачених роздач зберігаються в `.storage/gamerpower_plus.<entry_id>` (`{id: first_seen}`). Записи, старші за 60 днів і відсутні у відповіді, видаляються.
- **Перший запуск**: усе поточне просто запам'ятовується, події не надсилаються.
- **Після перезапуску HA** роздачі, що з'явились під час простою, надсилаються як нові. Події відкладаються до повного старту HA, щоб автоматизації встигли їх отримати.
- ID, що тимчасово зник і повернувся, новим **не** вважається.
- Роздачі, приховані локальними фільтрами, запам'ятовуються, але подія для них не надсилається.

### Сервіси

| Сервіс | Опис |
|---|---|
| `gamerpower_plus.refresh` | Оновити зараз. `config_entry_id` необов'язковий: без нього оновлюються всі записи |
| `gamerpower_plus.get_giveaways` | Повертає відповідь `{entries: [{config_entry_id, title, count, total_worth, giveaways: [...]}]}` з усіма полями |
| `gamerpower_plus.reset_seen` | Забуває бачені роздачі й одразу оновлює дані, тож усі поточні роздачі прийдуть як нові. Зручно для перевірки сповіщень |

```yaml
action: gamerpower_plus.get_giveaways
response_variable: result
# {{ result.entries[0].giveaways | map(attribute='title') | list }}
```

### Приклад: сповіщення на телефон з картинкою і кнопкою

```yaml
alias: "Нова безкоштовна гра → телефон"
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
        · до {{ as_timestamp(trigger.event.data.end_date) | timestamp_custom('%d.%m %H:%M') }}
        {%- endif %}
      data:
        image: "{{ trigger.event.data.image }}"
        url: "{{ trigger.event.data.open_giveaway_url }}"          # iOS: дія при натисканні
        clickAction: "{{ trigger.event.data.open_giveaway_url }}"  # Android: дія при натисканні
        actions:
          - action: URI
            title: "Забрати"
            uri: "{{ trigger.event.data.open_giveaway_url }}"
mode: queued
```

Замість події на шині можна використати `event`-сутність, тоді дані будуть у `trigger.to_state.attributes`:

```yaml
triggers:
  - trigger: state
    entity_id: event.steam_epic_game_new_giveaway
    not_to: [unavailable, unknown]
```

### Приклад: Telegram

```yaml
alias: "Нова безкоштовна гра → Telegram"
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

        <a href="{{ trigger.event.data.open_giveaway_url }}">Забрати</a>
mode: queued
```

### Картка Lovelace

```yaml
type: markdown
title: 🎁 Безкоштовні ігри
content: >-
  {% set items = state_attr('sensor.steam_epic_game_active_giveaways', 'giveaways') or [] %}
  {% for g in items %}
  <a href="{{ g.url }}"><img src="{{ g.image }}" width="100%"></a>

  **[{{ g.title }}]({{ g.url }})** — {{ g.worth }}
  {%- if g.end_date %}, до {{ as_timestamp(g.end_date) | timestamp_custom('%d.%m %H:%M') }}{% endif %}

  {% else %}
  Зараз роздач немає.
  {% endfor %}

  <sub>Data provided by [GamerPower.com](https://www.gamerpower.com)</sub>
```

Для календаря підійде стандартна картка **Calendar** із сутністю `calendar.…_giveaways`.

### Міграція з `command_line`-скрипта `steam_giveaways.py`

1. Встановіть інтеграцію й додайте запис: платформи **Steam** і **Epic Games Store**, тип **game**. Саме такий запит робив скрипт (`/filter?platform=epic-games-store.steam&type=game`).
2. Відповідність даних:

   | Скрипт | GamerPower Plus |
   |---|---|
   | `total_count` | стан `sensor.…_active_giveaways` |
   | `games` | атрибут `giveaways` того ж сенсора або сервіс `get_giveaways` |
   | `new_games` | подія `gamerpower_plus_new_giveaway` / `event.…_new_giveaway` |

3. Перепишіть автоматизації, які стежили за `new_games`, на тригер з прикладів вище.
4. Видаліть `command_line`-сенсор із `configuration.yaml`, а також `steam_giveaways.py` і `/config/steam_giveaways_cache.json`, і перезапустіть HA.

Кеш скрипта не переноситься. Перший запуск інтеграції лише запам'ятовує поточні роздачі, тож повторних сповіщень про вже відомі ігри не буде.

### Діагностика

**Пристрої та служби → GamerPower Plus → ⋮ → Завантажити діагностику**. Файл містить налаштування запису й публічні дані роздач, чутливих даних там немає.

### Відомі обмеження

- API не вказує часовий пояс дат, тому вони трактуються як UTC.
- `/worth` не вміє рахувати кілька платформ разом, тому сумарна вартість рахується локально з полів `worth`. Роздачі з `N/A` до суми не входять.
- Метрика «популярності» в API не публікується, тому для цього сортування зберігається порядок, який повернув API.

---

## English

### What it is

The integration polls the [GamerPower API](https://www.gamerpower.com/api-read) and creates a device per entry with sensors, a calendar and a "new giveaway" event. It is configured entirely in the UI, no YAML needed.

### How it differs

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

### Installation with HACS

1. HACS → ⋮ → **Custom repositories** → add `https://github.com/NetZhizni/ha-gamerpower-plus` as **Integration**.
2. Find **GamerPower Plus** in HACS and install it.
3. Restart Home Assistant.
4. **Settings → Devices & services → Add integration → GamerPower Plus**.

Manual: copy `custom_components/gamerpower_plus` to `/config/custom_components/` and restart.

Requires Home Assistant 2025.8 or newer.

### Options

| Option | Default | Description |
|---|---|---|
| Name | generated, e.g. `Steam, Epic — game` | Entry and device name |
| Platforms | Steam, Epic Games Store | Any of the 18 API platforms; a giveaway matches if it is on any of them |
| Giveaway types | game | `game`, `loot` (DLC, items), `beta` (beta, early access) |
| Sort by | Date | Date / Value / Popularity (sorted by the API, and the order is checked again locally after filtering) |
| Update interval | 60 min | At least 15 min (the API caches responses for 10 min) |
| Minimum worth | 0 USD | Hide cheaper giveaways; 0 shows everything |
| Include giveaways without worth (N/A) | on | Keep giveaways with unknown worth |
| Exclude keywords | — | Comma separated, case insensitive, e.g. `playtest, demo` |
| Expiring soon threshold | 24 h | When the binary sensor turns on |

- **Platforms and types** are chosen when the entry is created and can be changed with **⋮ → Reconfigure**. They make the entry unique, so the same combination can't be added twice. After a change, giveaways that are already active are not reported as new.
- **Everything else** lives in **Configure** (options). The entry reloads by itself, no restart needed.
- You can create several entries, e.g. "Steam, Epic — game" and "PC — loot".

### Entities

| Entity | State |
|---|---|
| `sensor.…_active_giveaways` | Number of giveaways after all filters. The `giveaways` attribute lists `id, title, worth, end_date, url, image`, cut to keep attributes under 16 KB (`truncated: true` when items were dropped) |
| `sensor.…_total_worth` | Total worth in USD (`monetary`) of exactly the list you see |
| `sensor.…_latest_giveaway` | Title of the most recently published giveaway; all its fields as attributes, thumbnail as `entity_picture` |
| `binary_sensor.…_expiring_soon` | `on` while a giveaway ends within the threshold; the `giveaways` attribute lists them. Switches at the exact moment, not only on updates |
| `event.…_new_giveaway` | Fires for every new giveaway (`event_type: new_giveaway`) with the same data as the bus event |
| `calendar.…_giveaways` | Giveaways with a known end date as events from `published_date` to `end_date` |

When the API is unreachable or fails, entities become `unavailable`, not `0`. HTTP 201 ("no active giveaways") gives `0`.

### Event `gamerpower_plus_new_giveaway`

Fired on the event bus for every new giveaway. Fields: `id`, `title`, `worth` (`"$19.99"` / `"N/A"`), `worth_value` (number or `null`), `platforms` (list), `type`, `published_date`, `end_date` (ISO or `null`), `image`, `thumbnail`, `open_giveaway_url`, `gamerpower_url`, `description`, `instructions`, `config_entry_id`, `entry_title`.

How "new" is decided:
- Seen IDs are stored in `.storage/gamerpower_plus.<entry_id>` as `{id: first_seen}`. IDs older than 60 days that left the response are dropped.
- **First run**: everything current is recorded silently, no events.
- **After a restart**, giveaways published during the downtime are reported. Events wait until Home Assistant has fully started so automations receive them.
- An ID that disappears for a while and comes back is **not** new.
- Giveaways hidden by local filters are remembered but not announced.

### Services

| Service | Description |
|---|---|
| `gamerpower_plus.refresh` | Update now. `config_entry_id` is optional; without it every entry is refreshed |
| `gamerpower_plus.get_giveaways` | Returns `{entries: [{config_entry_id, title, count, total_worth, giveaways: [...]}]}` with all fields |
| `gamerpower_plus.reset_seen` | Forgets seen giveaways and refreshes, so every current giveaway is reported as new. Handy for testing notifications |

### Automation examples

The Ukrainian section above has complete examples, and the YAML works as is in any language:
- mobile notification with image and a "Claim" button (`notify.mobile_app_*`, `image`, `actions: URI`);
- Telegram photo with caption and link (`telegram_bot.send_photo`);
- a Lovelace markdown card listing giveaways with images.

Minimal mobile notification:

```yaml
triggers:
  - trigger: event
    event_type: gamerpower_plus_new_giveaway
actions:
  - action: notify.mobile_app_my_phone
    data:
      title: "🎁 {{ trigger.event.data.title }}"
      message: "{{ trigger.event.data.worth }} · {{ trigger.event.data.platforms | join(', ') }}"
      data:
        image: "{{ trigger.event.data.image }}"
        actions:
          - action: URI
            title: "Claim"
            uri: "{{ trigger.event.data.open_giveaway_url }}"
```

### Migrating from the `steam_giveaways.py` command_line sensor

1. Add an entry with **Steam** + **Epic Games Store** and type **game**, the same query the script made.
2. `total_count` → state of `sensor.…_active_giveaways`; `games` → its `giveaways` attribute or `get_giveaways`; `new_games` → event `gamerpower_plus_new_giveaway` / `event.…_new_giveaway`.
3. Point automations at the new trigger, then remove the `command_line` sensor, the script and `/config/steam_giveaways_cache.json`, and restart.

The script cache is not imported. The first run records current giveaways silently, so you won't get duplicate notifications.

### Known limitations

- API dates carry no timezone; they are treated as UTC.
- `/worth` can't combine platforms, so total worth is summed locally from `worth`; `N/A` giveaways are not counted.
- The API doesn't expose its popularity metric, so popularity keeps the API order.

### Attribution

Giveaway data is provided by [GamerPower.com](https://www.gamerpower.com). Every entity carries the attribution `Data provided by GamerPower.com`, as the API terms require.

### License

[MIT](LICENSE)
