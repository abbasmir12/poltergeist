"""Cross-platform parsing for the builtins Poltergeist intercepts.

Shells do not share state between Poltergeist's subprocess invocations, so
`cd`, env-assignment and env-unset builtins are executed by Python itself.
Everything here is pure (no I/O) and platform-flag driven so it can be unit
tested on any OS.
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

PosixLike = bool  # True for bash/zsh/fish/sh; False for cmd.exe / PowerShell

EnvOpKind = Literal["set", "unset"]
CdTargetKind = Literal["home", "prev", "path", None]


@dataclass
class BuiltinOp:
    kind: Literal["cd", "env"]
    # cd
    target: CdTargetKind | str = None  # type: ignore[assignment]
    # env
    env_kind: EnvOpKind | None = None
    key: str = ""
    value: str = ""


def first_tokens(command: str, *, posix: bool) -> list[str]:
    """Split a command into tokens, tolerating nothing but a single line."""
    try:
        if posix:
            return shlex.split(command)
        # Windows: shlex with posix=False keeps quotes intact for tokens.
        return shlex.split(command, posix=False)
    except ValueError:
        return []


def _is_simple(command: str, tokens: list[str]) -> bool:
    """Only intercept when the whole line is exactly one builtin.

    Compound forms (`x && cd y`, `cd y && x`, pipelines) must reach the real
    shell, where they behave as the user expects.
    """
    stripped = command.strip()
    return bool(tokens) and not any(sep in stripped for sep in ("&&", "||", "|", ";", "&"))


def parse_cd(command: str, *, posix: bool) -> BuiltinOp | None:
    """Detect a standalone `cd`/`chdir`/`Set-Location` command."""
    tokens = first_tokens(command, posix=posix)
    if not _is_simple(command, tokens):
        return None
    head = tokens[0].lower().strip('"')
    if posix:
        heads = ("cd", "chdir")
    else:
        heads = ("cd", "chdir", "set-location", "sl")
    if head not in heads:
        return None
    rest = tokens[1:]
    # PowerShell `Set-Location -Path X`; cmd `cd /d X`. POSIX paths start with
    # "/", so only strip short-ish modifier flags. `cd -` must survive filter.
    rest = [
        t
        for t in rest
        if t == "-" or (not t.startswith("-") and (posix or t.lower() not in ("/d", "/q", "/s")))
    ]
    if not rest:
        return BuiltinOp(kind="cd", target="home")
    target = rest[0].strip('"')
    if target == "-":
        return BuiltinOp(kind="cd", target="prev")
    return BuiltinOp(kind="cd", target=target)


ident_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_:")


def parse_env(command: str, *, posix: bool) -> BuiltinOp | None:
    """Detect a standalone env assignment/unassignment.

    POSIX:   `export VAR=value`  |  `VAR=value`  |  `unset VAR [VAR2 ...]`
    Windows (cmd): `set VAR=value` | `set VAR=`
    Windows (PowerShell): `$env:VAR = "value"` | `$env:VAR = $null`
    """
    tokens = first_tokens(command, posix=posix)
    if not _is_simple(command, tokens):
        return None

    if posix:
        head = tokens[0].lower()
        if head == "export" and len(tokens) == 2:
            assignment = tokens[1].strip('"')
            if _looks_like_assignment(assignment):
                key, _, value = assignment.partition("=")
                return BuiltinOp(kind="env", env_kind="set", key=key, value=value)
        elif head in ("unset", "unsetenv") and len(tokens) == 2:
            key = tokens[1].strip('"')
            if key.isidentifier():
                return BuiltinOp(kind="env", env_kind="unset", key=key)
        first = tokens[0]
        # bare `VAR=value` is only an assignment when nothing follows it;
        # `VAR=x cmd …` must reach the real shell.
        if len(tokens) == 1 and "=" in first and _looks_like_assignment(first):
            key, _, value = first.partition("=")
            return BuiltinOp(kind="env", env_kind="set", key=key, value=value.strip('"'))
        return None

    head = tokens[0].strip('"').lower()
    # cmd.exe: set VAR=value / set VAR=   and PowerShell: $env:VAR = value
    if head == "set" and len(tokens) >= 2:
        assignment = tokens[1]
        key, eq, value = assignment.partition("=")
        if eq and key and key.replace("_", "a").replace("-", "a").isalnum():
            if value:
                return BuiltinOp(kind="env", env_kind="set", key=key, value=value.strip('"'))
            return BuiltinOp(kind="env", env_kind="unset", key=key)
        return None
    first = tokens[0].strip('"')
    if first.lower().startswith("$env:") and len(tokens) >= 3 and tokens[1] == "=":
        key = first[5:]
        if key and key.isidentifier():
            value = tokens[2].strip("\"'")
            if value in ("$null", ""):
                return BuiltinOp(kind="env", env_kind="unset", key=key)
            return BuiltinOp(kind="env", env_kind="set", key=key, value=value)
    return None


def _looks_like_assignment(token: str) -> bool:
    key, eq, _ = token.partition("=")
    return bool(eq) and bool(key) and key.isidentifier()


def resolve_cd_target(op: BuiltinOp, cwd: Path, prev: Path | None) -> Path:
    """Turn a CdTarget into a concrete Path (calls expanduser on `~...`)."""
    if op.target == "home":
        return Path.home().resolve()
    if op.target == "prev":
        return (prev or cwd).resolve()
    raw = str(op.target)
    if raw == "~" or raw.startswith("~/"):
        return Path(raw).expanduser().resolve()
    return (cwd / raw).resolve()
