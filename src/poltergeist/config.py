"""Single TOML config file in the platform config dir + env overrides."""

from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from platformdirs import user_config_dir, user_data_dir

try:  # py3.11+
    import tomllib as _toml_reader  # type: ignore[import-not-found]
except ModuleNotFoundError:  # py3.10
    import tomli as _toml_reader  # type: ignore[no-redef]

APP_NAME = "poltergeist"
DEFAULT_MODEL = "gemma4:e4b"
# Fallback chain — verified against Ollama's library on 2026-10-28:
# gemma4:e4b (6.6–9.5 GB, effective-4B edge model, 128k ctx)
# → gemma3:1b (806 MB, text) → gemma3:270m (292 MB, text).
# The real last resort is *any* installed model; see poltergeist.ghost.ollama.
MODEL_FALLBACKS = ("gemma4:e4b", "gemma3:1b", "gemma3:270m")
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"

_THEMES = ("classic", "ofrenda", "slasher")


@dataclass
class Config:
    model: str = DEFAULT_MODEL
    ollama_url: str = DEFAULT_OLLAMA_URL
    theme: str = "classic"
    autonomy: str = "ask"  # "ask" | "curious"
    intro: bool = True
    flicker: bool = True
    voice: bool = False
    # Opt-in shell-history haunting; None = not asked yet (first-run onboarding)
    history_consent: bool | None = None
    commentary_rate: float = 0.35  # probability ghost comments on a trivial command
    extra: dict[str, str] = field(default_factory=dict)  # unknown keys preserved

    # -- paths -------------------------------------------------------------
    @staticmethod
    def config_dir() -> Path:
        return Path(user_config_dir(APP_NAME, appauthor=False))

    @staticmethod
    def config_path() -> Path:
        return Config.config_dir() / "config.toml"

    @staticmethod
    def data_dir() -> Path:
        return Path(user_data_dir(APP_NAME, appauthor=False))

    @staticmethod
    def audit_path() -> Path:
        return Config.data_dir() / "audit.jsonl"

    @staticmethod
    def memory_path() -> Path:
        return Config.data_dir() / "memory.json"


def _sanitize_theme(value: str) -> str | None:
    value = value.strip().lower()
    return value if value in _THEMES else None


def load_config(path: Path | None = None, *, environ: dict[str, str] | None = None) -> Config:
    """Load config, apply env overrides, ignore unreadable files gracefully."""
    env = environ if environ is not None else os.environ
    cfg = Config()
    real_path = path or Config.config_path()
    if real_path.exists():
        try:
            with real_path.open("rb") as fh:
                doc = _toml_reader.load(fh)
        except Exception:  # noqa: BLE001 — corrupt config must not crash the ghost
            doc = {}
        known = {f.name for f in fields(Config)}
        known.discard("extra")
        for key, value in doc.items():
            if key in known:
                try:
                    setattr(cfg, key, _cast(key, value))
                except Exception:  # noqa: BLE001
                    continue
            else:
                cfg.extra[str(key)] = str(value)
    # env always wins (12-factor-ish, but the factors are spectral)
    if env.get("POLTERGEIST_MODEL"):
        cfg.model = env["POLTERGEIST_MODEL"].strip()
    if env.get("POLTERGEIST_OLLAMA_URL") or env.get("OLLAMA_HOST"):
        raw = (env.get("POLTERGEIST_OLLAMA_URL") or env.get("OLLAMA_HOST", "")).strip()
        if raw and not re.match(r"^https?://", raw):
            raw = f"http://{raw}"
        cfg.ollama_url = raw.rstrip("/")
    if env.get("POLTERGEIST_THEME"):
        cfg.theme = _sanitize_theme(env["POLTERGEIST_THEME"]) or cfg.theme
    if env.get("POLTERGEIST_AUTONOMY"):
        value = env["POLTERGEIST_AUTONOMY"].strip().lower()
        if value in ("ask", "curious"):
            cfg.autonomy = value
    if env.get("NO_COLOR"):
        cfg.flicker = False
    return cfg


def _cast(key: str, value: object) -> object:
    types = {f.name: f.type for f in fields(Config)}
    expected = str(types.get(key, "str"))
    if key in ("intro", "flicker", "voice") or "bool" in expected:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("true", "1", "yes", "on")
    if key == "history_consent":
        if value is None or isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("true", "1", "yes", "on")
    if key == "commentary_rate":
        return float(value)  # type: ignore[arg-type]
    if isinstance(value, (int, float)):
        return str(value)
    if not isinstance(value, str):
        return str(value)
    if key == "theme":
        return _sanitize_theme(value) or Config().theme
    if key == "autonomy":
        cleaned = value.strip().lower()
        return cleaned if cleaned in ("ask", "curious") else "ask"
    return value


def _toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


_BOOL_KEYS = ("intro", "flicker", "voice")
_QUERY_KEYS = ("history_consent",)
_STR_KEYS = ("model", "ollama_url", "theme", "autonomy")


def save_config(config: Config, path: Path | None = None) -> Path:
    """Serialize only known fields as TOML; returns the path written."""
    real_path = path or Config.config_path()
    data = asdict(config)
    lines = ["# poltergeist config — edit freely, the ghost prefers you not to"]
    for key in _STR_KEYS + _BOOL_KEYS + _QUERY_KEYS + ("commentary_rate",):
        value = data[key]
        if key in _BOOL_KEYS:
            lines.append(f"{key} = {'true' if value else 'false'}")
        elif key == "history_consent":
            if value is None:
                lines.append(f"# {key} = (asked at first haunt; true|false)")
            else:
                lines.append(f"{key} = {'true' if value else 'false'}")
        elif key == "commentary_rate":
            lines.append(f"commentary_rate = {float(value):.2f}")
        else:
            lines.append(f'{key} = "{_toml_escape(str(value))}"')
    for key in sorted(config.extra):
        lines.append(f'{key} = "{_toml_escape(config.extra[key])}"')
    real_path.parent.mkdir(parents=True, exist_ok=True)
    plain = "\n".join(lines) + "\n"
    real_path.write_text(plain, encoding="utf-8")
    return real_path
