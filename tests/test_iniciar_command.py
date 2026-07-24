"""Regression tests for the Marcelo double-click launcher."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INICIAR = REPO_ROOT / "INICIAR.command"


def test_iniciar_command_exists_with_bash_shebang() -> None:
    raw = INICIAR.read_bytes()
    assert raw.startswith(b"#!/bin/bash\n"), (
        "INICIAR.command must be a bash script with LF shebang"
    )
    assert b"\r\n" not in raw, "CRLF line endings break .command on macOS"


def test_iniciar_command_is_executable_in_git() -> None:
    """ZIP/share often drops +x; git must still record mode 100755 for clean archives."""
    mode = subprocess.check_output(
        ["git", "ls-files", "-s", "--", "INICIAR.command"],
        cwd=REPO_ROOT,
        text=True,
    ).split()[0]
    assert mode == "100755", f"expected git mode 100755, got {mode}"


def test_iniciar_command_self_heals_quarantine_and_permissions() -> None:
    """
    When Marcelo receives the tool via WhatsApp/Drive/email, macOS adds
    com.apple.quarantine and often strips +x. Gatekeeper then says the file is
    'damaged'/'broken'. Once Terminal can start the script, it must repair itself.
    """
    text = INICIAR.read_text(encoding="utf-8")
    assert "chmod" in text and "$0" in text
    assert "com.apple.quarantine" in text
    assert "xattr" in text
