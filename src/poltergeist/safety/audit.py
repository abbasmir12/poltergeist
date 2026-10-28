"""Append-only local audit log for every ghost-executed command.

Format: JSON Lines in the platform data dir. No network access ever.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

from .redact import redact_output

_MAX_OUTPUT_PREVIEW = 2000


class AuditLog:
    """Thread-safe JSONL writer. `enabled=False` short-circuits (for tests)."""

    def __init__(self, path: Path, *, enabled: bool = True) -> None:
        self.path = path
        self.enabled = enabled
        self._lock = threading.Lock()

    def record(
        self,
        *,
        command: str,
        verdict: str,
        approved_by: str,  # "user" | "ghost-auto" | "system"
        exit_code: int | None = None,
        output: str = "",
        shell: str = "",
        cwd: str = "",
        ghost_comment: str = "",
    ) -> dict[str, Any] | None:
        """Append one redacted entry; returns what was written."""
        if not self.enabled:
            return None
        entry: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "command": redact_output(command),
            "verdict": verdict,
            "approved_by": approved_by,
            "shell": shell,
            "cwd": cwd,
        }
        if exit_code is not None:
            entry["exit_code"] = exit_code
        if output:
            entry["output_preview"] = redact_output(output)[-_MAX_OUTPUT_PREVIEW:]
        if ghost_comment:
            entry["ghost_comment"] = ghost_comment
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def tail(self, n: int = 20) -> list[dict[str, Any]]:
        """Last n entries (oldest first); used by the ghost's memory."""
        if not self.enabled or not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8", errors="replace").splitlines()
        out = []
        for line in lines[-n:]:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def wipe(self) -> bool:
        """Delete the audit file (`haunt forget`). Returns True if removed."""
        with self._lock:
            if self.path.exists():
                self.path.unlink(missing_ok=True)
                return True
        return False
