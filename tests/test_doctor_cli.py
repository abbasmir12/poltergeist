"""CLI parsing and doctor output (offline)."""

import io

import httpx  # noqa: F401 (used by handler fixtures below)
import pytest
from rich.console import Console

from poltergeist import cli
from poltergeist.config import Config
from poltergeist.doctor import Check, render, run_checks

# ---------------------------------------------------------------- CLI ----


def test_version_flag():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["--version"])


def test_default_is_haunt_with_flags():
    args = cli.build_parser().parse_args(["--model", "gemma3:4b", "--no-intro", "--no-flicker"])
    assert args.model == "gemma3:4b"
    assert args.no_intro is True
    assert args.command is None


def test_subcommand_haunt():
    args = cli.build_parser().parse_args(["haunt", "--theme", "ofrenda"])
    assert args.command == "haunt"
    assert args.theme == "ofrenda"


def test_doctor_and_forget_parse():
    args = cli.build_parser().parse_args(["doctor", "--json"])
    assert args.command == "doctor"
    args2 = cli.build_parser().parse_args(["forget"])
    assert args2.command == "forget"


def test_resolve_overrides_applies_flags():
    args = cli.build_parser().parse_args(
        ["--model", "gemma3:270m", "--theme", "ofrenda", "--autonomy", "curious"]
    )
    cfg = cli._resolve_overrides(args)
    assert cfg.model == "gemma3:270m"
    assert cfg.theme == "ofrenda"
    assert cfg.autonomy == "curious"


# -------------------------------------------------------------- doctor ----


def doctored_console() -> Console:

    return Console(file=io.StringIO(), color_system=None, force_terminal=False)


def test_render_offline_checks():
    console = doctored_console()
    checks = run_checks(console=console)
    assert any(c.name == "Python" for c in checks)
    assert any(c.name == "Terminal (TTY)" for c in checks)
    out = render(checks, console)
    assert "doctor" in out
    assert "séance" in out  # summary line present regardless of Ollama status


def test_render_indicates_errors_and_fixes():
    console = doctored_console()
    checks = [Check("Python", "ok", "3.12.0"), Check("Ollama", "error", "down", fix="start it")]
    out = render(checks, console)
    assert "⛨" in out or "⛧" in out
    assert "start it" in out


def test_checks_with_failing_client():

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("ghost modem")

    checks = run_checks(client=httpx.Client(transport=httpx.MockTransport(handler)))
    statuses = {c.name: c.status for c in checks}
    assert statuses["Ollama"] == "error"
    assert statuses["Ghost model"] == "error"


def test_checks_with_healthy_olama_and_wanted_model():

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "0.9.9"})
        models = [{"name": "gemma3:1b"}, {"name": "gemma3:270m"}]
        return httpx.Response(200, json={"models": models})

    cfg = Config()
    cfg.model = "gemma3:1b"  # tag present in the mocked /api/tags list
    checks = run_checks(client=httpx.Client(transport=httpx.MockTransport(handler)), cfg=cfg)
    statuses = {c.name: c.status for c in checks}
    assert statuses["Ollama"] == "ok"
    assert statuses["Ghost model"] == "ok"


def test_checks_warn_on_model_fallback():

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "0.9.9"})
        return httpx.Response(200, json={"models": [{"name": "llama3:8b"}]})

    cfg = Config()
    cfg.model = "gemma3:4b"
    checks = run_checks(client=httpx.Client(transport=httpx.MockTransport(handler)), cfg=cfg)
    model_check = next(c for c in checks if c.name == "Ghost model")
    assert model_check.status == "warn"
    assert "llama3:8b" in model_check.detail
