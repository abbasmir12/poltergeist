"""Platform capability helpers (the ONLY place that touches sys.platform)."""

from __future__ import annotations

import sys

IS_WINDOWS = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")


def is_windows() -> bool:
    return IS_WINDOWS


def is_mac() -> bool:
    return IS_MAC


def is_linux() -> bool:
    return IS_LINUX


def default_unicode() -> bool:
    """Best-effort Unicode support detection for the spooky prompt."""
    if IS_WINDOWS:
        try:
            return True  # Windows Terminal/PowerShell 5+ handle UTF-8 via rich
        except Exception:  # noqa: BLE001
            return False
    return sys.stdout.encoding.lower().startswith("utf") if sys.stdout.encoding else False
