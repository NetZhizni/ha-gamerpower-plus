<img src="https://raw.githubusercontent.com/NetZhizni/ha-gamerpower-plus/main/custom_components/gamerpower_plus/brand/icon.png" alt="GamerPower Plus" width="96" align="right">

# GamerPower Plus

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![Validate](https://github.com/NetZhizni/ha-gamerpower-plus/actions/workflows/validate.yml/badge.svg)](https://github.com/NetZhizni/ha-gamerpower-plus/actions/workflows/validate.yml)
[![Tests](https://github.com/NetZhizni/ha-gamerpower-plus/actions/workflows/tests.yml/badge.svg)](https://github.com/NetZhizni/ha-gamerpower-plus/actions/workflows/tests.yml)

[English](../README.md) | **Українська**

Інтеграція Home Assistant для безкоштовних роздач ігор (Steam, Epic Games Store, GOG та інші) з [GamerPower.com](https://www.gamerpower.com).

> Data provided by [GamerPower.com](https://www.gamerpower.com). Проєкт не пов'язаний з GamerPower.

## Що це

Інтеграція раз на N хвилин запитує [GamerPower API](https://www.gamerpower.com/api-read) і створює для кожного запису пристрій з сенсорами, календарем і подією «нова роздача». Налаштовується тільки через UI, YAML не потрібен.

## Чим відрізняється від інших

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

## Встановлення

> Вимоги до версії Home Assistant:
>
> - Core $\geq$ 2025.8

### Спосіб 1: [HACS](https://hacs.xyz/) (рекомендовано)

Встановлення з HACS в один клік:

[![Відкрити репозиторій GamerPower Plus у HACS вашого Home Assistant.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=NetZhizni&repository=ha-gamerpower-plus&category=integration)

Або додайте репозиторій вручну:

1. HACS → ⋮ → **Custom repositories** → додайте `https://github.com/NetZhizni/ha-gamerpower-plus` з типом **Integration**.
2. У пошуку HACS введіть **GamerPower Plus** → відкрийте → **Download**.
3. Перезапустіть Home Assistant.

Далі HACS сам пропонуватиме нові релізи як оновлення.

### Спосіб 2: Git clone з GitHub

Потрібен доступ до командного рядка Home Assistant, наприклад через доповнення [Terminal & SSH](https://github.com/home-assistant/addons/tree/master/ssh).

```bash
cd /config
git clone https://github.com/NetZhizni/ha-gamerpower-plus.git
mkdir -p custom_components
cp -r ha-gamerpower-plus/custom_components/gamerpower_plus custom_components/
```

Після цього перезапустіть Home Assistant.

Так зручно перемикатися на конкретний реліз. Наприклад, оновлення до версії 1.0.0:

```bash
cd /config/ha-gamerpower-plus
git fetch --tags
git checkout 1.0.0
rm -rf /config/custom_components/gamerpower_plus
cp -r custom_components/gamerpower_plus /config/custom_components/
```

І знову перезапустіть Home Assistant.

### Спосіб 3: Вручну через [Samba](https://github.com/home-assistant/addons/tree/master/samba) / [FTPS](https://github.com/hassio-addons/addon-ftp)

1. Завантажте архів останнього релізу зі сторінки [Releases](https://github.com/NetZhizni/ha-gamerpower-plus/releases).
2. Скопіюйте теку `custom_components/gamerpower_plus` у теку `config/custom_components` вашого Home Assistant.
3. Перезапустіть Home Assistant.

## Налаштування

### Додавання інтеграції

[Налаштування > Пристрої та служби > ДОДАТИ ІНТЕГРАЦІЮ](https://my.home-assistant.io/redirect/config_flow_start/?domain=gamerpower_plus) > знайдіть `GamerPower Plus` > оберіть платформи й типи роздач > НАДІСЛАТИ

[![Почати налаштування GamerPower Plus у вашому Home Assistant.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=gamerpower_plus)

### Параметри

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

## Сутності

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

## Подія `gamerpower_plus_new_giveaway`

Надсилається на шину подій для кожної нової роздачі. Поля: `id`, `title`, `worth` (`"$19.99"` / `"N/A"`), `worth_value` (число або `null`), `platforms` (список), `type`, `published_date`, `end_date` (ISO або `null`), `image`, `thumbnail`, `open_giveaway_url`, `gamerpower_url`, `description`, `instructions`, `config_entry_id`, `entry_title`.

Як визначається «нова»:
- ID бачених роздач зберігаються в `.storage/gamerpower_plus.<entry_id>` (`{id: first_seen}`). Записи, старші за 60 днів і відсутні у відповіді, видаляються.
- **Перший запуск**: усе поточне просто запам'ятовується, події не надсилаються.
- **Після перезапуску HA** роздачі, що з'явились під час простою, надсилаються як нові. Події відкладаються до повного старту HA, щоб автоматизації встигли їх отримати.
- ID, що тимчасово зник і повернувся, новим **не** вважається.
- Роздачі, приховані локальними фільтрами, запам'ятовуються, але подія для них не надсилається.

## Сервіси

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

## Приклад: сповіщення на телефон з картинкою і кнопкою

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

## Приклад: Telegram

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

## Картка Lovelace

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

### Детальна картка з описом та інструкцією

Атрибут `giveaways` компактний (`id, title, worth, end_date, url, image`), щоб вкластися в 16 KB. Якщо в картці потрібні постер, платформи, кількість тих, хто вже забрав, опис та інструкція, створіть trigger-template-сенсор. Він бере повний список через `gamerpower_plus.get_giveaways` і оновлюється разом з інтеграцією:

```yaml
# configuration.yaml
template:
  - triggers:
      - trigger: homeassistant
        event: start
      - trigger: state   # без to/from спрацьовує і на зміну атрибутів
        entity_id: sensor.steam_epic_game_active_giveaways
    actions:
      - action: gamerpower_plus.get_giveaways
        data: {}   # кілька записів? додайте config_entry_id: <ID запису>
        response_variable: result
    sensor:
      - name: "Дані про роздачі Steam"   # → sensor.dani_pro_rozdachi_steam
        unique_id: gamerpower_plus_giveaways_full
        state: "{{ result.entries[0].count }}"
        attributes:
          games: "{{ result.entries[0].giveaways }}"
```

Порівняно з `command_line`-скриптом відрізняються лише два поля: `platforms` тепер список (`| join(', ')`), а невідома `end_date` дорівнює `null`, а не `'N/A'`. Замість `striptags` використано `regex_replace`: `striptags` схлопує переноси рядків, і кроки інструкції злипалися б в один рядок.

```yaml
type: markdown
content: |
  {% set games = state_attr('sensor.dani_pro_rozdachi_steam', 'games') %}
  {% if games and games | length > 0 %}
  {% for game in games %}
  ### [{{ game.title }}]({{ game.open_giveaway_url }})
  [![Постер гри]({{ game.thumbnail }})]({{ game.open_giveaway_url }})
  **🖥 Платформа:** {{ game.platforms | join(', ') }}
  **💰 Ціна:** {% if game.worth != 'N/A' %}~~{{ game.worth }}~~ ➡️ {% endif %}**БЕЗКОШТОВНО!**
  **⏳ Діє до:** {{ (as_timestamp(game.end_date) | timestamp_custom('%d.%m.%Y %H:%M')) if game.end_date else 'Невідомо' }}
  **👥 Вже забрали:** {{ game.users }} чол.
  **📝 Опис:** {{ game.description | regex_replace('<[^>]+>', '') | replace('\r\n', '\n') }}
  **🛠 Інструкція:** {{ game.instructions | regex_replace('<[^>]+>', '') | replace('\r\n', '\n') }}

  ---
  {% endfor %}
  {% else %}
  *Наразі немає активних роздач або дані сенсора недоступні* 🤷‍♂️
  {% endif %}

  <sub>Data provided by [GamerPower.com](https://www.gamerpower.com)</sub>
```

Для великих вибірок (наприклад, PC + loot) атрибут `games` може перевищити 16 KB. Тоді recorder не збереже його в історію й запише попередження в лог, але картка все одно працюватиме.

## Міграція з `command_line`-скрипта `steam_giveaways.py`

1. Встановіть інтеграцію й додайте запис: платформи **Steam** і **Epic Games Store**, тип **game**. Саме такий запит робив скрипт (`/filter?platform=epic-games-store.steam&type=game`).
2. Відповідність даних:

   | Скрипт | GamerPower Plus |
   |---|---|
   | `total_count` | стан `sensor.…_active_giveaways` |
   | `games` | атрибут `giveaways` того ж сенсора, сервіс `get_giveaways` або template-сенсор з [детальної картки](#детальна-картка-з-описом-та-інструкцією) (той самий `sensor.dani_pro_rozdachi_steam`) |
   | `new_games` | подія `gamerpower_plus_new_giveaway` / `event.…_new_giveaway` |

3. Перепишіть автоматизації, які стежили за `new_games`, на тригер з прикладів вище.
4. Видаліть `command_line`-сенсор із `configuration.yaml`, а також `steam_giveaways.py` і `/config/steam_giveaways_cache.json`, і перезапустіть HA.

Кеш скрипта не переноситься. Перший запуск інтеграції лише запам'ятовує поточні роздачі, тож повторних сповіщень про вже відомі ігри не буде.

## Діагностика

**Пристрої та служби → GamerPower Plus → ⋮ → Завантажити діагностику**. Файл містить налаштування запису й публічні дані роздач, чутливих даних там немає.

## Відомі обмеження

- API не вказує часовий пояс дат, тому вони трактуються як UTC.
- `/worth` не вміє рахувати кілька платформ разом, тому сумарна вартість рахується локально з полів `worth`. Роздачі з `N/A` до суми не входять.
- Метрика «популярності» в API не публікується, тому для цього сортування зберігається порядок, який повернув API.

## Атрибуція

Дані про роздачі надає [GamerPower.com](https://www.gamerpower.com). Кожна сутність має атрибуцію `Data provided by GamerPower.com`, як того вимагають умови API.

## Релізи

Workflow `Tag & Release` запускається на кожен push у `main`, який змінює `custom_components/gamerpower_plus/manifest.json`. Якщо тега з такою `version` ще немає, він створює тег і GitHub Release з автоматичними нотатками, і HACS пропонує цей реліз як оновлення. Щоб випустити реліз:

1. Підніміть `version` у `manifest.json` і `VERSION` у `const.py` (workflow і тест перевіряють, що вони однакові).
2. Допишіть зміни в `CHANGELOG.md`.
3. Зробіть push у `main`.

Іконку з `custom_components/gamerpower_plus/brand/` Home Assistant роздає сам (перевірено на 2026.10), тож запис у home-assistant/brands не потрібен. Версії без підтримки локальних брендів показують іконку-заглушку.

## Ліцензія

[MIT](../LICENSE)
