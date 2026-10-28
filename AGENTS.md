# AGENTS.md — Poltergeist

> ## ⚠️ THE FIRST RULE
>
> **Before doing anything, read `STATUS.md`.**
> **After EVERY completed task (and whenever scope, decisions or blockers change),
> update `STATUS.md` before moving on or ending your session.**

---

## 1. What Poltergeist is

Poltergeist is a cross-platform CLI that turns the user's terminal into a
haunted, AI-controlled experience. Running `haunt` performs a cinematic
transformation sequence; afterwards a theatrical local-AI ghost comments on
your commands, chats with you, notices things on its own, remembers your shell
history (opt-in), and can propose commands that you approve before they run.
`exorcise` restores the terminal.

### Hacktoberfest context

- **Event:** Hacktoberfest 2026 Open-Source AI Challenge: Week 4 —
  "Ghost in the Machine" (DEV).
- **Deadline: October 31, 2026, 11:59 PM PDT.** We have ~3 days.
  This is not a PR contest: it is a new project with **open-source /
  open-weight AI at its core**, plus a written DEV post.
- **Judging:** Writing quality > theme relevance > creativity > technical
  execution > optional partner tech.
- **Why open-source/local AI (our answer, state it in every doc):** it runs
  **fully offline** on the user's own machine, is **private** (shell history
  and command output never leave the computer), **free** to run, and the model
  is **swappable** (any Ollama model). Core features must never require a paid
  or closed API.
- **License:** MIT.
- **DEV post tags:** `#devchallenge` `#hf26challenge`.

### Prioritization rule

Polished working demo-able core > breadth. When in doubt, make the core loop
(`haunt` → spooky REPL → ghost commentary → `exorcise`) excellent.

## 2. Tech stack

| Layer         | Choice                                                      |
| ------------- | ----------------------------------------------------------- |
| Language      | Python **3.10+** (test on 3.10–3.13)                         |
| TUI           | `rich` (output), `prompt_toolkit` (input + `patch_stdout`)   |
| Model backend | **Ollama** (local HTTP, streaming). Default model `gemma3:1b` |
| HTTP          | `httpx` (streaming to `http://localhost:11434`)              |
| Config paths  | `platformdirs` (+ `tomllib`/`tomli` for config files)        |
| Packaging     | `pyproject.toml` (hatchling), pip/pipx installable           |
| Entry points  | `haunt`, `poltergeist` (same CLI)                            |
| CI            | GitHub Actions: ubuntu + windows + macos × Python 3.10–3.13  |

Default model: `gemma3:1b` (verified against Ollama's library: 806 MB,
text-only, 32k context — runs on a laptop). Configurable via `--model`,
`POLTERGEIST_MODEL` env var, or config file. Fallback chain: configured →
`gemma3:1b` → `gemma3:270m` → any installed model → canned fallback lines.

## 3. Architecture overview

```
CLI (argparse: haunt | haunt doctor | haunt forget | poltergeist)
 └─ REPL (prompt_toolkit loop)
     ├─ shell/    cross-platform command runner (posix.py / windows.py)
     ├─ safety/   classifier, redaction, audit log
     ├─ ghost/    provider interface, ollama client, persona, fallbacks
     ├─ ui/       themes, intro/outro, speech bubble, sanity meter
     └─ memory/   shell-history readers, local store
```

Key design decisions:

- **No PTY hooking on the core path.** Commands run in the user's native shell
  via `subprocess` (PowerShell/cmd on Windows, `$SHELL` on macOS/Linux);
  stdout/stderr are captured and streamed live. PTY/ConPTY "possess mode" is a
  stretch goal only.
- `cd` and `export`/`env`-style assignments are **intercepted in Python** so
  working directory persists between commands on every platform.
- Offline resilience: if Ollama is down/uninstalled the ghost uses canned
  fallback lines. `haunt doctor` diagnoses everything and prints fix steps.

## 4. Repository structure

```
poltergeist/
  AGENTS.md STATUS.md README.md LICENSE pyproject.toml
  src/poltergeist/
    cli.py        # entry points, subcommands
    repl.py       # haunted REPL loop
    config.py     # config load/save (platformdirs)
    doctor.py     # environment check
    shell/        # base.py, posix.py, windows.py
    ghost/        # provider.py, ollama.py, persona.py, fallbacks.py
    safety/       # classifier.py, redact.py, audit.py
    ui/           # theme.py, intro.py (more in phase 2+)
    memory/       # history readers, store
  tests/
  .github/workflows/ci.yml
  docs/           # architecture, demo script, DEV post outline
```

## 5. How to run / test / lint

```bash
# dev install
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# run
haunt --help
haunt doctor

# tests (must pass with no model/Ollama installed)
pytest

# lint
ruff check src tests
```

CI runs the pytest matrix (3 OSes × Python 3.10–3.13) — **tests must not
require a running Ollama or any network access.**

## 6. Coding conventions

- Formatting: black-style, 4-space indent, line length 100.
- Type hints on all public functions; docstrings on public API.
- Tests live in `tests/`, named `test_*.py`, one module per source module.
- No print-debugging in shipped code; use the `log` module or remove it.
- Keep changes small; **commit often** with clear messages so a new agent can
  resume at any point (STATus.md tracks "what works right now").
- Never `git commit --force`; never commit secrets (and never copy real
  `.env` values into test fixtures — always placeholders like `sk-xxx`).

## 7. Cross-platform rules (never weakened)

- Never assume a POSIX shell, a bash variant, `/usr/bin/env`, Linux-only paths
  (`/home`, `/tmp`), or POSIX CLI tools; never assume Windows-only paths or
  PowerShell either. All platform differences go through `poltergeist.shell` /
  `poltergeist.platform_syms`.
- ANSI/Unicode: detect capabilities (color depth, Unicode, TTY) and degrade
  gracefully — 16 colors, ASCII fallbacks, no animation when not a TTY or when
  `NO_COLOR` is set.
- Respect `Ctrl+C`/`Ctrl+D`: never crash; always restore the terminal
  (`try/finally` + signal handlers).
- Keep dependencies minimal and open source. No closed-API requirement in core.

## 8. Safety rules (never weaken these)

- Every command the **ghost** may execute goes through `safety.classifier`:
  - `safe` — read-only (`ls`, `dir`, `pwd`, `git status`, `cat`, ...) —
    auto-run only in autonomy mode `curious`; default autonomy is `ask`.
  - `needs-approval` — anything that writes/installs/deletes/networks or is
    unknown — requires explicit user approval in a glowing box.
  - `blocked` — `rm -rf /` on root/home, `format`, `del /s /q C:\`,
    fork bombs, `Remove-Item -Recurse -Force` on root/home, credential
    exfiltration patterns — **never executed, even if the user approves.**
- Redact secrets (tokens, keys, passwords, `.env` values) before anything is
  sent to the model or logged.
- **No telemetry and no network calls** except the local model endpoint (and
  optional user-enabled voice). State this in the README.
- Every ghost-executed command is written to the local audit log.
- History reading is **opt-in**, 100% local, wipeable with `haunt forget`.

## 9. Definition of done for a task

1. Code written and consistent with surrounding style.
2. Tests exist and pass locally (`pytest`) — add tests for anything
   safety/parsing related.
3. Docs updated where relevant (README, docs/).
4. **`STATUS.md` updated** (phase, checklist, decisions if any).
5. A clean git commit with a clear conventional message
   (e.g. `feat(shell): persist cwd across commands`).

## 10. Communication

- Log every non-obvious decision and its "why" in `STATUS.md` → Decisions log.
- Blockers go in `STATUS.md` → Known issues, never silently skipped.
