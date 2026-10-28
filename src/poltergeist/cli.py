"""Entry points: `haunt`, `poltergeist`, `haunt doctor`, `haunt forget`."""

from __future__ import annotations

import argparse
import sys

from rich.console import Console

from . import __version__
from .config import Config
from .shell import create_shell

_THEMES = ("classic", "ofrenda", "slasher")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="haunt",
        description="Invite a ghost into your terminal — 100% local, open-weights, offline-safe.",
    )
    parser.add_argument("--version", action="version", version=f"poltergeist {__version__}")
    sub = parser.add_subparsers(dest="command")

    doctor = sub.add_parser("doctor", help="check python, tty, ollama and installed models")
    doctor.add_argument("--json", action="store_true", help="machine-readable output")

    sub.add_parser("forget", help="wipe all local memory, history and audit data")

    haunt = sub.add_parser("haunt", help="start the haunted session")
    _add_session_flags(haunt)

    # `haunt --model X` with no subcommand also starts the haunted session
    _add_session_flags(parser)
    return parser


def _add_session_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--model", default=None, metavar="NAME", help="Ollama model (default: gemma3:1b)"
    )
    parser.add_argument("--theme", default=None, choices=_THEMES, help="possession style")
    parser.add_argument("--no-intro", action="store_true", help="skip the transformation sequence")
    parser.add_argument("--no-flicker", action="store_true", help="disable screen flicker effects")
    parser.add_argument(
        "--voice", action="store_true", help="experimental offline TTS (stretch goal)"
    )
    parser.add_argument(
        "--autonomy",
        default=None,
        choices=("ask", "curious"),
        help="ask = approve every ghost action (default); "
        "curious = ghost may auto-run `safe` commands",
    )
    parser.add_argument(
        "--host",
        default=None,
        metavar="URL",
        help="ollama base url (default http://127.0.0.1:11434)",
    )


def _resolve_overrides(args: argparse.Namespace) -> Config:
    from . import config as config_module

    cfg = config_module.load_config()
    if args.model:
        cfg.model = args.model
    if args.theme:
        cfg.theme = args.theme
    if args.autonomy:
        cfg.autonomy = args.autonomy
    if args.host:
        cfg.ollama_url = args.host
    if args.no_intro:
        cfg.intro = False
    if args.no_flicker:
        cfg.flicker = False
    if args.voice:
        cfg.voice = True
    return cfg


def cmd_repl(args: argparse.Namespace) -> int:
    from .repl import HauntedRepl

    cfg = _resolve_overrides(args)
    console = Console(highlight=False)
    shell = create_shell()
    repl = HauntedRepl(cfg, shell, console=console)
    try:
        return repl.run()
    except Exception as exc:  # noqa: BLE001 — a haunted CLI must not traceback at users
        console.print(f"[red3]The séance collapsed unexpectedly:[/red3] {exc}")
        console.print("[dim]Please report the replay steps to the project issue tracker.[/dim]")
        return 1


def cmd_doctor(args: argparse.Namespace) -> int:
    import json

    import httpx

    from .doctor import Check, run_checks

    console = Console()
    if getattr(args, "json", False):
        with httpx.Client() as client:
            checks: list[Check] = run_checks(console=console, client=client)
        payload = [
            {"name": c.name, "status": c.status, "detail": c.detail, "fix": c.fix} for c in checks
        ]
        console.print(json.dumps(payload, indent=2))
        return 0
    from .doctor import main as doctor_main

    return doctor_main()


def cmd_forget(args: argparse.Namespace) -> int:
    from .config import load_config, save_config

    console = Console()
    data_dir = Config.data_dir()
    wiped: list[str] = []
    for path in (Config.audit_path(), Config.memory_path()):
        if path.exists():
            path.unlink(missing_ok=True)
            wiped.append(path.name)
    if data_dir.exists():
        for stale in data_dir.glob("*.json*"):
            if stale.name not in wiped:
                stale.unlink(missing_ok=True)
                wiped.append(stale.name)
    if wiped:
        console.print("[orange3]The ghosts of your past drift out of the fan exhaust.[/orange3]")
        for name in wiped:
            console.print(f"[dim]  wiped: {name}[/dim]")
    else:
        console.print("[dim]Nothing to forget — this poltergeist barely remembers yesterday.[/dim]")
    # reset history consent so the ghost asks again before haunting your past
    try:
        if Config.config_path().exists():
            cfg = load_config()
            cfg.history_consent = None
            save_config(cfg, Config.config_path())
    except Exception:  # noqa: BLE001 — forgetting must not fail loudly
        pass
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        return cmd_doctor(args)
    if args.command == "forget":
        return cmd_forget(args)
    # haunt / poltergeist / no subcommand → haunted REPL
    return cmd_repl(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
