# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [1.0.1] - 2026-10-10

### Added
- GamerPower icon in `brand/`, served locally by Home Assistant.
- `Tag & Release` workflow: a version bump in `manifest.json` on `main` creates the tag and GitHub release.
- Test that the `manifest.json` and `const.py` versions match.

### Changed
- README split into English (`README.md`, default) and Ukrainian (`doc/README_uk.md`).

### Fixed
- `VERSION` in `const.py` now matches `manifest.json`, so the release workflow no longer fails.
- `Tag & Release` workflow runs on every push to `main` and creates a missing tag or release, so a failed run is retried by the next push.

## [1.0.0] - 2026-10-10

### Added
- Config flow with platform, type, sort, interval, worth, N/A, keyword and expiring-soon settings; options flow with automatic reload; reconfigure flow for platforms and types.
- Sensors: active giveaways (size-limited list attribute), total worth (USD, monetary), latest giveaway.
- Binary sensor "Expiring soon" that switches exactly when giveaways enter the window or expire.
- Event entity and bus event `gamerpower_plus_new_giveaway`; seen IDs persisted in `Store`, events deferred until Home Assistant has started.
- Calendar with giveaways that have a known end date.
- Services `refresh`, `get_giveaways` (response) and `reset_seen`.
- Diagnostics, English and Ukrainian translations.
