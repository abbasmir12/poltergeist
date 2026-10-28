# STATUS.md

> **Agent rule:** read this file first; update it after every completed task
> and whenever scope, decisions or blockers change.

## Project snapshot

Poltergeist is a cross-platform (`haunt` / `poltergeist` CLI) haunted terminal
powered by an open-weight local LLM (Ollama + Gemma) that comments on your
commands, chats with you, proposes commands (safety-gated), and restores your
terminal on `exorcise`. **Current phase: 1 — Foundation (in progress).**

## Last updated

2026-10-28, by GLM agent (session 1 — repo bootstrap).

## Completed tasks

- [x] 2026-10-28 — Verified Ollama Gemma tags against the live library:
      `gemma3:270m` (292 MB), `gemma3:1b` (806 MB), `gemma3:4b` (3.4 GB),
      `1b-it-qat`, etc. → default model will be `gemma3:1b` (see Decisions).
- [x] 2026-10-28 — AGENTS.md, STATUS.md, LICENSE (MIT), .gitignore created.
- [x] 2026-10-28 — pyproject.toml with `haunt`/`poltergeist` entry points.
- [x] 2026-10-28 — Cross-platform shell abstraction (`shell/base.py`,
      `shell/posix.py`, `shell/windows.py`) with cwd + env persistence handled
      in Python, live output streaming, and unit tests.
- [x] 2026-10-28 — `config.py` (platformdirs + TOML, env overrides).
- [x] 2026-10-28 — `cli.py`: `haunt`, `poltergeist`, `haunt doctor`,
      `haunt forget` wired with flags (`--theme`, `--model`, `--no-intro`,
      `--autonomy`, `--no-flicker`).
- [x] 2026-10-28 — `doctor.py`: Python version, TTY/color/Unicode capabilities,
      Ollama connectivity, model availability + fix instructions.
- [x] 2026-10-28 — Minimal haunted REPL (`repl.py`): runs commands in the
      native shell, streams output, `exorcise`/`help`/`sanity`/`theme` handled,
      Ctrl+C/Ctrl+D safe.
- [x] 2026-10-28 — Safety module skeleton: classifier with `safe` /
      `needs-approval` / `blocked` + redaction + audit log, with unit tests.
- [x] 2026-10-28 — Ghost module skeleton: provider interface, Ollama streaming
      client (httpx), canned offline fallbacks; REPL uses fallback lines when
      Ollama is unavailable (tested off-line).
- [x] 2026-10-28 — GitHub Actions CI matrix (ubuntu/windows/macos × 3.10–3.13).
- [x] 2026-10-28 — Phase 1 acceptance: `pytest` green locally (156 tests +
      3 Windows-skips), `ruff` clean, manual smoke of the full loop
      (`echo`, `cd /`, `git status`, `ghost,` chat, `sanity`, `exorcise`) on
      Linux with Ollama offline (canned voice path).

## In progress

- Nothing right now (session ended here — next agent: pick up "Next up").

## Next up (prioritized)

1. Phase 2 — Haunted look: `ui/theme.py` (classic/ofrenda/slasher palettes),
   intro/outro transformation animation (<4 s, skippable), speech-bubble panel
   with typewriter + glitch effects, spooky prompt (Unicode + ASCII fallback),
   guaranteed terminal restore.
2. Phase 2 — Capability detection (color depth / Unicode / width) + graceful
   degradation incl. `NO_COLOR`, non-TTY.
3. Phase 3 — Ghost brain: prompt assembly with real command context, streaming
   commentary with rate limiting, `ghost,` chat, richer fallbacks.
4. Phase 4 — Safety & agency: `--autonomy curious` auto-run path, glowing
   approval box, autonomous idle/whisper thread via `patch_stdout`.
5. Phase 5 — Memory: shell-history readers (bash/zsh/fish/PSReadLine) with
   opt-in consent + `haunt forget`; sanity meter with meltdown scene.
6. Phase 6 — Ship: README (zero→haunted in 5 min), demo script + GIF,
   DEV post outline in `docs/`.

## Known issues / blockers

- None blocking. (Sandbox here has no GPU/Ollama daemon; model serving is
  exercised via contract tests + doctor, verified by the user locally.)

## Decisions log

| Date       | Decision                                                                 | Why                                                                                             |
| ---------- | ------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------- |
| 2026-10-28 | Default model **`gemma3:1b`** (806 MB, text-only, 32k ctx)                | Verified against Ollama library today; small enough for laptops; `270m` kept as fallback after it |
| 2026-10-28 | No PTY/ConPTY on core path; `subprocess` + native shells                  | Fragile cross-platform; capture+stream via pipes is reliable and testable                        |
| 2026-10-28 | `cd`/`export`/`set` intercepted in Python, shell spawned per command       | Shells don't share state between invocations; interception is portable and testable              |
| 2026-10-28 | httpx for Ollama streaming                                               | Cleaner streaming (SSE/NDJSON) than urllib, still fully local/libre                              |
| 2026-10-28 | Raw ANSI control codes guarded behind a capability check                  | rich handles most styling; low-level cursor/screen control must degrade                          |
| 2026-10-28 | Config file is TOML in platformdirs user config dir                       | Human-friendly single file; `tomllib` is stdlib on 3.11+, `tomli` marker dep for 3.10            |

## How to run/test right now

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest                     # 156 passed + 3 windows-skips as of last update (no Ollama needed)
ruff check src tests
haunt doctor               # status of Python/TTY/Ollama/model
haunt                      # haunted REPL (canned ghost lines without Ollama)
```

## Demo & submission checklist

- [ ] Demo GIF/video recorded
- [ ] README done (install incl. Ollama + `gemma3:1b`, why-open-source section)
- [ ] Demo script in `docs/`
- [ ] DEV post drafted (tags `#devchallenge` `#hf26challenge`)
- [ ] Submitted before **Oct 31 2026, 11:59 PM PDT**
