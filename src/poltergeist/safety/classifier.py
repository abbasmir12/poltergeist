"""Command safety: classification for everything the ghost may touch.

Rules (never weaken):
- ``blocked``        — catastrophic/hostile commands; NEVER run, even if the
  user "approves". The ghost refuses with a dramatic explanation.
- ``needs-approval`` — anything that writes, installs, deletes, networks, is
  elevated, or is simply unknown. Requires explicit user approval.
- ``safe``           — read-only. The ghost may auto-run these only in
  autonomy mode ``curious``; the default autonomy is ``ask``.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from typing import Literal

Verdict = Literal["safe", "needs-approval", "blocked"]

_ORDER: dict[Verdict, int] = {"blocked": 2, "needs-approval": 1, "safe": 0}

_SEPARATORS = ("&&", "||", ";", "|", "&")  # split_compound() separator classes


@dataclass(frozen=True)
class Classification:
    command: str
    verdict: Verdict
    reasons: tuple[str, ...] = field(default_factory=tuple)

    @property
    def reason(self) -> str:
        return self.reasons[0] if self.reasons else ""

    @property
    def blocked(self) -> bool:
        return self.verdict == "blocked"


def worst(*verdicts: Verdict) -> Verdict:
    """Return the most restrictive verdict."""
    return max(verdicts, key=lambda v: _ORDER[v]) if verdicts else "needs-approval"


# --------------------------------------------------------------------------
# read-only allowlist
# --------------------------------------------------------------------------
_SAFE_HEADS: dict[str, str] = {
    "ls": "read-only",
    "pwd": "read-only",
    "whoami": "read-only",
    "groups": "read-only",
    "id": "read-only",
    "hostname": "read-only",
    "uname": "read-only",
    "date": "read-only",
    "time": "read-only",
    "uptime": "read-only",
    "echo": "read-only",
    "printf": "read-only",
    "head": "read-only",
    "tail": "read-only",
    "wc": "read-only",
    "nl": "read-only",
    "seq": "read-only",
    "true": "read-only",
    "false": "read-only",
    "sleep": "harmless pause",
    "stat": "read-only",
    "file": "read-only",
    "tree": "read-only",
    "du": "read-only",
    "df": "read-only",
    "free": "read-only",
    "ps": "read-only",
    "history": "read-only",
    "which": "read-only",
    "where": "read-only",
    "type": "read-only",
    "command": "read-only",
    "man": "read-only",
    "cat": "read-only",
    "less": "read-only",
    "more": "read-only",
    "grep": "read-only",
    "rg": "read-only",
    "ripgrep": "read-only",
    "sha256sum": "read-only",
    "sha1sum": "read-only",
    "md5sum": "read-only",
    "jobs": "read-only",
    "who": "read-only",
    "w": "read-only",
    "env": "secret dump",  # dumped secrets must not drift to the model unredacted
    "printenv": "secret dump",
}

# sensitive path fragments: reading them is still read-only, but the ghost
# must not tunnel their contents anywhere without the user seeing it twice.
_SENSITIVE_PAT = re.compile(r"(?i)(\.(?:ssh|env)\b|credentials?\b|id_rsa|\.netrc|\.aws\b)")

_GIT_SAFE_SUBS = {
    "status",
    "log",
    "branch",
    "diff",
    "show",
    "blame",
    "describe",
    "rev-parse",
    "tag",
    "remote",
}

# version checks are the only *safe* way to touch interpreters/dev tools
_VERSION_ONLY = {
    "python",
    "python3",
    "node",
    "ruby",
    "java",
    "cargo",
    "go",
    "rustc",
    "dotnet",
    "php",
}

# --------------------------------------------------------------------------
# blocked patterns (regex over the whole command, case-insensitive)
# --------------------------------------------------------------------------
_BLOCKED_RULES: list[tuple[str, str]] = [
    # dd writing to a block device = disk-wipe
    (
        r"\bdd\b[^;&|]*\bof=/dev/(?:disk|rdisk|sd[a-z]|hd[a-z]|nvme|mmcblk|vd[a-z])",
        "disk wipe via dd",
    ),
    # mkfs on anything
    (r"\bmkfs(?:\.\w+)?\b", "mkfs filesystem creation"),
    # classic shell fork bomb `:(){ :|:& };:`
    (r":\(\)\s*\{[^}]*\}\s*;\s*:", "fork bomb"),
    # named fork bomb: f(){ f|f & };f
    (r"(\w+)\s*\(\)\s*\{[^}]*\|\s*\1\b[^}]*\}\s*;?\s*\1\b", "fork bomb"),
    # cmd.exe drive-wiping utilities
    (r"\b(?:del|erase|rd|rmdir)\b[^;&|]*/[sq][^;&|]*[a-z]:", "del/rd /s /q on a drive"),
    (r"\bshred\b[^;&|]*(?:/dev/|/root/|\s~)", "shred of a system path"),
    (r"\bchmod\s+-R\s+0?00?0?\s+/", "chmod -R 000 on root"),
    (
        r"(?i)\b(?:curl|wget|iwr|invoke-webrequest|http|webr|nc|netcat|scp|rsync|ssh)\b"
        r"[^;&|]*(?:(?:~|/)\.ssh\b|id_rsa\b|\.env\b|\bpassword\b|\bcredential|\bsecret\b|\baws_secret|"
        r"\btoken\b)",
        "credential exfiltration attempt",
    ),
    (
        r"(?i)\b(?:env|printenv)\b[^;&|]*\|\s*(?:curl|wget|nc|netcat|http)\b",
        "env dump exfiltration attempt",
    ),
    (
        r"(?i)\b(?:curl|wget|nc|netcat|http)\b[^;&|]*<(?:~|/)?\.?(?:ssh|env)\b",
        "secret-file exfiltration attempt",
    ),
    (
        r"(?i)\bgit\s+push\b[^;&|]*(?:\.env\b|id_rsa|\.ssh\b|password|secret|token)",
        "pushing credentials",
    ),
]

# --------------------------------------------------------------------------
# blocked heads (first token) — always catastrophic regardless of args
# --------------------------------------------------------------------------
_BLOCKED_HEADS = {"shutdown", "reboot", "halt", "poweroff", "fdisk", "parted", "diskpart", "format"}

# tokens (case-insensitive) that make an rm-family command catastrophic if
# they are its target
_ROOTISH = {
    "/",
    "/*",
    "/.",
    "~",
    "~/*",
    "~/",
    "$home",
    "$home/*",
    "$home/",
    "/home",
    "/home/*",
    "/users",
    "/users/*",
    "c:",
    "c:\\",
    "c:\\*",
    "c:\\users",
    "c:\\users\\*",
    "c:\\windows",
    "c:\\windows\\*",
    "c:\\program files*",
    "c:\\program files (x86)*",
}

_REMOVE_HEADS = {"rm", "remove-item", "ri", "rmdir", "rd", "del", "erase", "trash", "rmtrash"}

_DRIVE_RE = re.compile(r"[a-z]:(\\*)$", re.IGNORECASE)


def _strip_quotes(token: str) -> str:
    return token.strip("'\"").strip("'\"")


def tokenize(part: str) -> list[str]:
    """Tokenize a single command segment tolerating non-POSIX quoting."""
    try:
        return shlex.split(part, posix=False)
    except ValueError:
        return part.split()


def split_compound(command: str) -> list[str]:
    """Split on `&&`, `||`, `;`, `|`, `&` while respecting quotes."""
    parts: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    i, n = 0, len(command)
    while i < n:
        ch = command[i]
        if quote:
            buf.append(ch)
            if ch == "\\" and quote == '"' and i + 1 < n:
                buf.append(command[i + 1])
                i += 1
            elif ch == quote:
                quote = None
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            buf.append(ch)
            i += 1
            continue
        two = command[i : i + 2]
        if two == "&&" or two == "||":
            parts.append("".join(buf))
            buf = []
            i += 2
            continue
        if ch in (";", "|", "&"):
            parts.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def classify_part(part: str) -> Classification:
    """Classify one (already split) command segment."""
    tokens = tokenize(part)

    if not tokens:
        return Classification(command=part, verdict="safe", reasons=("empty",))

    head = _strip_quotes(tokens[0]).lower()
    base = head.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    if base.endswith((".exe", ".cmd", ".bat", ".com", ".ps1")):
        base = base.rsplit(".", 1)[0]

    def mk(verdict: Verdict, why: str) -> Classification:
        return Classification(command=part, verdict=verdict, reasons=(why,))

    # whole-word checks: system-critical heads are always blocked; elevation
    # inherits the verdict of what follows it (sudo rm -rf / stays blocked, but
    # `sudo apt install x` is merely approval-gated).
    if base in _BLOCKED_HEADS:
        return mk("blocked", f"`{base}` is blocked (system-critical operation)")

    if base in {"sudo", "doas"} or base.startswith("runas"):
        for tok in tokens[1:]:
            tok_l = _strip_quotes(tok).lower()
            if not tok_l.startswith("-") and (tok_l in _ROOTISH or _DRIVE_RE.fullmatch(tok_l)):
                return mk("blocked", f"elevated `{base}` targeting root/home ({tok_l})")
            if tok_l in _REMOVE_HEADS:
                return mk("blocked", f"`{base}` + `{tok_l}` (destroying things elevated)")
        return mk("needs-approval", "elevated privileges require the ghost master's blessing")

    # ---- rm family: token-level catastrophic-target detection
    if base in _REMOVE_HEADS:
        for tok in tokens[1:]:
            tok_l = _strip_quotes(tok).lower()
            if tok_l in _ROOTISH or _DRIVE_RE.fullmatch(tok_l):
                return mk(
                    "blocked",
                    f"`{base}` targeting the filesystem root or home ({tok_l})",
                )
            if tok_l.startswith("-"):
                continue
            # Remove-Item style `-Path C:\` / `-Path ~`
            if tok_l in ("-path", "-literalpath", "-lp"):
                continue
        # rm without a rootish target: still destructive → approval
        return mk("needs-approval", f"`{base}` deletes or destroys something")

    if base == "git":
        sub = next((tok for tok in tokens[1:] if not tok.startswith("-")), "")
        if sub in _GIT_SAFE_SUBS:
            # `git remote set-url` is a write; whitelist bare-prefix then re-check tokens
            if _git_sub_has_write_flags(sub, tokens):
                return mk("needs-approval", f"`git {sub}` (with write flags) needs approval")
            return mk("safe", f"`git {sub}` is read-only")
        return mk("needs-approval", f"`git {sub or '…'}` mutates history or the remote")

    if base in _SAFE_HEADS or base in ("env", "printenv"):
        reason = _SAFE_HEADS.get(base, "secret dump")
        sensitive = any(_SENSITIVE_PAT.search(t) for t in tokens[1:])
        if sensitive or reason == "secret dump":
            return mk("needs-approval", "dumps of secret-shaped things stay behind approval")
        return mk("safe", f"`{base}` is read-only")

    if base in _VERSION_ONLY:
        if len(tokens) == 1 or all(
            t.strip('"') in {"-v", "-V", "--version", "/?"} for t in tokens[1:]
        ):
            return mk("safe", f"`{base} --version` is read-only")
        return mk("needs-approval", f"`{base}` executes arbitrary code; approval required")

    return mk("needs-approval", f"unknown command `{base}` — better safe than sorry")


def _git_sub_has_write_flags(sub: str, tokens: list[str]) -> bool:  # pragma: no cover - tiny
    if sub == "remote":
        verbs = {t.strip('"').lower() for t in tokens[2:]}
        return verbs - {"-v", "--verbose"} and verbs.isdisjoint({"-v"})
    if sub == "branch":
        verbs = [t.strip('"').lower() for t in tokens[2:] if not t.startswith("-")]
        return bool(verbs)  # `git branch NAME` creates → approval; bare list is safe
    return False


def classify(command: str) -> Classification:
    """Classify a full command line (possibly a compound like `a && b`)."""
    if not command.strip():
        return Classification(command=command, verdict="safe", reasons=("empty",))

    reasons: list[str] = []
    verdict: Verdict = "safe"

    # regex rules apply to the whole line AND each segment
    for text in [command, *split_compound(command)]:
        lowered = text.lower()
        for pattern, why in _BLOCKED_RULES:
            if re.search(pattern, lowered, re.IGNORECASE):
                return Classification(
                    command=command,
                    verdict="blocked",
                    reasons=(f"blocked: {why}",),
                )

    for part in split_compound(command):
        c = classify_part(part)
        reasons.append(f"{part!r}: {c.reason}")
        verdict = worst(verdict, c.verdict)
        if verdict == "blocked":
            return Classification(command=command, verdict="blocked", reasons=tuple(reasons))
    return Classification(command=command, verdict=verdict, reasons=tuple(reasons))
