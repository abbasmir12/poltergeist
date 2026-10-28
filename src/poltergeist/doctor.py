"""`haunt doctor` — check the séance conditions and print fix instructions."""

from __future__ import annotations

import sys
from dataclasses import dataclass

import httpx
from rich.console import Console

from . import __version__
from .config import MODEL_FALLBACKS, Config

StatusStatus = str  # one of "ok" | "warn" | "error"


@dataclass
class Check:
    name: str
    status: str  # "ok" | "warn" | "error"
    detail: str
    fix: str = ""


def check_python() -> Check:
    v = sys.version_info
    if v >= (3, 10):
        return Check("Python", "ok", f"{v.major}.{v.minor}.{v.micro}")
    return Check("Python", "error", f"{v.major}.{v.minor}", fix="Install Python 3.10+")


def check_tty(stdout: object = None) -> Check:
    import sys as _sys

    out = stdout if stdout is not None else _sys.stdout
    if getattr(out, "isatty", lambda: False)():
        return Check("Terminal (TTY)", "ok", "interactive — animated spooks enabled")
    return Check(
        "Terminal (TTY)",
        "warn",
        "not a TTY — intro/animation disabled, output stays plain",
    )


def check_color(console: Console) -> Check:
    if console.no_color:
        return Check(
            "Color",
            "warn",
            "NO_COLOR set — ghostly styling off",
            fix="unset NO_COLOR for the full séance",
        )
    levels = {"16": 16, "256": 256, "truecolor": 16_777_216}
    system = str(console.color_system or "none")
    depth = levels.get(system)
    return Check(
        "Color", "ok" if depth else "warn", f"{system}" + (f" ({depth} colors)" if depth else "")
    )


def check_ollama(cfg: Config, client: httpx.Client) -> Check:
    try:
        resp = client.get(f"{cfg.ollama_url}/api/version", timeout=3.0)
        resp.raise_for_status()
        version = resp.json().get("version", "?")
        return Check("Ollama", "ok", f"v{version} at {cfg.ollama_url}")
    except Exception as exc:  # noqa: BLE001 — diagnosis is the point here
        return Check(
            "Ollama",
            "error",
            f"not reachable at {cfg.ollama_url} ({type(exc).__name__})",
            fix="Start Ollama (https://ollama.com/download) — it stays local; no key needed",
        )


def check_models(cfg: Config, client: httpx.Client) -> Check:
    try:
        resp = client.get(f"{cfg.ollama_url}/api/tags", timeout=3.0)
        resp.raise_for_status()
        tags = [m.get("name", "") for m in resp.json().get("models", [])]
    except Exception as exc:  # noqa: BLE001
        return Check("Ghost model", "error", f"could not list models ({type(exc).__name__})")
    if not tags:
        return Check(
            "Ghost model",
            "error",
            "Ollama runs, but no model is installed",
            fix=f"Run: ollama pull {MODEL_FALLBACKS[0]}",
        )
    wanted = cfg.model
    if wanted in tags:
        return Check("Ghost model", "ok", f"{wanted} ready ({len(tags)} installed)")
    fallback = next((t for t in MODEL_FALLBACKS if t in tags), None)
    if fallback:
        return Check(
            "Ghost model",
            "warn",
            f"'{wanted}' missing, will possess {fallback} instead",
            fix=f"Run: ollama pull {wanted}",
        )
    return Check(
        "Ghost model",
        "warn",
        f"'{wanted}' missing; any-installed-model rule gives you '{tags[0]}'",
        fix=f"Run: ollama pull {wanted} (or set POLTERGEIST_MODEL={tags[0]})",
    )


def run_checks(
    *,
    client: httpx.Client | None = None,
    console: Console | None = None,
    cfg: Config | None = None,
) -> list[Check]:
    """All doctor checks. `client` is injected in tests (deterministic)."""
    console = console or Console()
    cfg = cfg or Config()
    checks = [check_python(), check_tty(), check_color(console)]
    try:
        own_client = client or httpx.Client()
        checks.append(check_ollama(cfg, own_client))
        checks.append(check_models(cfg, own_client))
    except Exception:  # noqa: BLE001 — health checks never crash the doctor
        pass
    return checks


def render(checks: list[Check], console: Console) -> str:
    icon = {"ok": "🕯", "warn": "ʬ", "error": "⛧"}
    styles = {"ok": "palegreen3", "warn": "orange3", "error": "red3"}
    lines = [f"[bold]Poltergeist {__version__} — doctor[/bold]", ""]
    for c in checks:
        style = styles[c.status]
        lines.append(f"  {icon[c.status]} [bold]{c.name:<16}[/bold][{style}]{c.detail}[/{style}]")
        if c.fix:
            lines.append(f"    ↳ [dim]{c.fix}[/dim]")
    lines.append("")
    if any(c.status == "error" for c in checks):
        lines.append("The séance is incomplete — fix the ⛧ lines and retry. The ghost waits.")
    else:
        lines.append("The séance is ready — run [bold]haunt[/bold] to begin.")
    return "\n".join(lines)


def main() -> int:
    console = Console()
    checks = run_checks(console=console)
    console.print(render(checks, console))
    return 0
