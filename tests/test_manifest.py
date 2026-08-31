"""Tests for the integration manifest."""

from __future__ import annotations

import json
from pathlib import Path


def test_manifest_keys_follow_hassfest_order() -> None:
    """Ensure domain and name come first and remaining keys are alphabetical."""
    manifest_path = (
        Path(__file__).parents[1]
        / "custom_components"
        / "e_redes_smart_metering_plus"
        / "manifest.json"
    )
    manifest_keys = list(json.loads(manifest_path.read_text()).keys())

    assert manifest_keys[:2] == ["domain", "name"]
    assert manifest_keys[2:] == sorted(manifest_keys[2:])
