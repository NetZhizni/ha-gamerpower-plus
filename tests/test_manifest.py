"""Consistency checks for release metadata."""

from __future__ import annotations

import json
from pathlib import Path

from custom_components.gamerpower_plus.const import DOMAIN, VERSION

INTEGRATION_DIR = Path(__file__).parents[1] / "custom_components" / DOMAIN


def test_version_matches_manifest() -> None:
    """The release workflow tags manifest.json's version; const.py must agree."""
    manifest = json.loads((INTEGRATION_DIR / "manifest.json").read_text("utf-8"))
    assert manifest["version"] == VERSION


def test_brand_icons_present() -> None:
    """Home Assistant serves these from the integration's brand folder."""
    for name in ("icon.png", "icon@2x.png"):
        assert (INTEGRATION_DIR / "brand" / name).is_file()
