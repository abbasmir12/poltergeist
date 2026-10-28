"""Secret redaction — nothing secret-shaped reaches the model or the logs.

Best-effort pattern matching for common token shapes plus `.env`-style
assignments. We state openly in the README that this is a helper, not a
hardened security boundary against novel secret formats.
"""

from __future__ import annotations

import re

_PLACEHOLDER = "●●●REDACTED●●●"

# ordered: most specific shapes first
_PATTERNS: list[str] = [
    # Bearer headers and JWT-shaped blobs
    r"(?i)\bbearer\s+[a-z0-9._~+/-]{16,}",
    r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}",
    # OpenAI / Anthropic / GitHub / Slack tokens
    r"\bsk-[A-Za-z0-9_-]{12,}",
    r"\bgh[pousr]_[A-Za-z0-9]{20,}",
    r"\bgithub_pat_[A-Za-z0-9_]{20,}",
    r"\bxox[baprs]-[A-Za-z0-9-]{10,}",
    # AWS access key id
    r"\bAKIA[0-9A-Z]{16}\b",
    # PEM private key blocks
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----(?s:.)*?-----END [A-Z ]*PRIVATE KEY-----",
]

_COMPILED = [re.compile(p) for p in _PATTERNS]

# key=value lines whose KEY looks secret-y (leading whitespace, export/set prefixes).
# The value is one quoted chunk or one whitespace-delimited token — commands
# like `SECRET=x haunt doctor` keep their tail intact.
_ASSIGNMENT_RE = re.compile(
    r"^(?P<lead>\s*(?:export\s+|set\s+|setx\s+|\$env:)?\s*)"
    r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)"
    r"(?P<eq>\s*[:=]\s*)"
    r"(?P<val>\"[^\"]*\"|'[^']*'|\S+)"
)

_SECRET_KEY_HINT = re.compile(
    r"(?i)(pass(?:word)?|passwd|secret|token|api_?key|access_?key|credential|"
    r"private_?key|auth(?:entication|orization|token|key|code)?\b|salt|seed|client_?id)"
)

_KNOWN_KEYS = {
    "GITHUB_TOKEN",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "ELEVEN_API_KEY",
    "ELEVENLABS_API_KEY",
    "PRIVATE_KEY",
    "PASSWORD",
    "SECRET_KEY",
    "API_KEY",
    "SESSION_COOKIE",
    "ADMIN_PASSWORD",
}

_INLINE_ENV_RE = re.compile(
    r"(?i)\b([A-Za-z_][A-Za-z0-9_]*"
    r"(?:pass(?:word)?|passwd|secret|token|api|key|credential|auth)[A-Za-z0-9_]*)=([^\s;&|']+)"
)

# YAML/JSON/TOML/PROPERTIES-ish `key: value` / `"key": "value"` in output
_OUTPUT_KV_RE = re.compile(r"^(\s*['\"]?)([A-Za-z0-9_.-]+?)(['\"]?\s*[:=]\s*)(['\"].*|.+?)$")


def _is_secret_key(key: str) -> bool:
    return key.upper() in _KNOWN_KEYS or bool(_SECRET_KEY_HINT.search(key))


def redact_text(text: str) -> str:
    """Return `text` with secret-shaped content replaced by placeholders."""
    out = text
    for pattern in _COMPILED:
        out = pattern.sub(_PLACEHOLDER, out)

    masked: list[str] = []
    for line in out.splitlines(keepends=True):
        eol = "\n" if line.endswith("\n") else ""
        body = line[: len(line) - len(eol)]
        m = _ASSIGNMENT_RE.match(body)
        if m and _is_secret_key(m.group("key")):
            stripped = body[: m.start("val")] + _PLACEHOLDER + body[m.end("val") :]
            masked.append(stripped + eol)
        else:
            masked.append(line)
    return "".join(masked)


def redact_command(command: str) -> str:
    """Redact a command line before it reaches the model or the audit log."""
    plain = redact_text(command)
    # `SECRET=x cmd` style inline env prefixes
    return _INLINE_ENV_RE.sub(r"\1=" + _PLACEHOLDER, plain)


def redact_output(output: str) -> str:
    """Redact command *output* (also handles `key: value` / quoted keys)."""
    plain = redact_text(output)
    masked: list[str] = []
    for line in plain.splitlines(keepends=True):
        eol = "\n" if line.endswith("\n") else ""
        body = line[: len(line) - len(eol)]
        m = _OUTPUT_KV_RE.match(body)
        if m and _is_secret_key(m.group(2)):
            masked.append(f"{m.group(1)}{m.group(2)}{m.group(3)}{_PLACEHOLDER}{eol}")
        else:
            masked.append(line)
    return "".join(masked)
