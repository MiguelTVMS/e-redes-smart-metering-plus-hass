"""Tests for the manual webhook helper scripts."""

from __future__ import annotations

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[1]


def test_webhook_scripts_generate_current_source_timestamp() -> None:
    """Manual webhook helpers must not send a permanently stale timestamp."""
    shell_script = (REPOSITORY_ROOT / "scripts/send-test-webhook").read_text()
    powershell_script = (REPOSITORY_ROOT / "scripts/send-test-webhook.ps1").read_text()

    assert 'date -u +"%Y-%m-%d %H:%M:%S"' in shell_script
    assert "${SOURCE_TIMESTAMP}" in shell_script
    assert '[DateTime]::UtcNow.ToString("yyyy-MM-dd HH:mm:ss")' in powershell_script
    assert (
        "SourceTimestamp                      = $sourceTimestamp" in powershell_script
    )
    assert 'SourceTimestamp                      = "2025-' not in powershell_script
