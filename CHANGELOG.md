# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-10-10

### Added
- Config flow with platform, type, sort, interval, worth, N/A, keyword and expiring-soon settings; options flow with automatic reload; reconfigure flow for platforms and types.
- Sensors: active giveaways (size-limited list attribute), total worth (USD, monetary), latest giveaway.
- Binary sensor "Expiring soon" that switches exactly when giveaways enter the window or expire.
- Event entity and bus event `gamerpower_plus_new_giveaway`; seen IDs persisted in `Store`, events deferred until Home Assistant has started.
- Calendar with giveaways that have a known end date.
- Services `refresh`, `get_giveaways` (response) and `reset_seen`.
- Diagnostics, English and Ukrainian translations.
