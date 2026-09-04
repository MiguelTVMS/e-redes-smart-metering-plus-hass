"""Tests for repository documentation consistency."""

from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTATION = tuple(
    sorted(
        (
            *ROOT.glob("*.md"),
            *(ROOT / "docs").rglob("*.md"),
            *(ROOT / "tests").rglob("*.md"),
        )
    )
)
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^]]+]\(([^)]+)\)")


def test_local_documentation_links_exist() -> None:
    """Every relative file link in repository documentation must resolve."""
    for document in DOCUMENTATION:
        for target in MARKDOWN_LINK.findall(document.read_text(encoding="utf-8")):
            path = target.split("#", 1)[0]
            if not path or "://" in path or path.startswith(("/", "mailto:")):
                continue
            assert (
                (document.parent / path).resolve().exists()
            ), f"Broken link in {document.relative_to(ROOT)}: {target}"


def test_changelog_starts_with_manifest_version() -> None:
    """The newest changelog entry must match the integration manifest."""
    manifest = json.loads(
        (
            ROOT / "custom_components" / "e_redes_smart_metering_plus" / "manifest.json"
        ).read_text(encoding="utf-8")
    )
    headings = re.findall(
        r"^## ([^\n]+)$", (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), re.M
    )
    assert headings[0] == manifest["version"]


def test_documentation_changes_trigger_tests() -> None:
    """Documentation-only pull requests must run consistency tests."""
    workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text(
        encoding="utf-8"
    )
    assert "- '*.md'" in workflow
    assert "- 'docs/**'" in workflow
