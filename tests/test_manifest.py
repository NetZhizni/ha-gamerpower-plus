"""Consistency checks for release metadata."""

from __future__ import annotations

import json
from pathlib import Path

from custom_components.gamerpower_plus.const import DOMAIN

ROOT = Path(__file__).parents[1]
INTEGRATION_DIR = ROOT / "custom_components" / DOMAIN


def test_changelog_has_manifest_version() -> None:
    """The release workflow takes its notes from this version's CHANGELOG section."""
    manifest = json.loads((INTEGRATION_DIR / "manifest.json").read_text("utf-8"))
    heading = f"## [{manifest['version']}] - "
    lines = (ROOT / "CHANGELOG.md").read_text("utf-8").splitlines()
    assert any(line.startswith(heading) for line in lines)


def test_brand_icons_present() -> None:
    """Home Assistant serves these from the integration's brand folder."""
    for name in ("icon.png", "icon@2x.png"):
        assert (INTEGRATION_DIR / "brand" / name).is_file()
