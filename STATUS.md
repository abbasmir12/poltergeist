# STATUS.md

> **Agent rule:** read this file first; update it after every completed task
> and whenever scope, decisions or blockers change.

## Project snapshot

Poltergeist is a cross-platform (`haunt` / `poltergeist` CLI) haunted terminal
powered by an open-weight local LLM (Ollama + Gemma) that comments on your
commands, chats with you, proposes commands (safety-gated), and restores your
terminal on `exorcise`. **Current phase: 2 — Haunted look (complete); Phase 3 —
Ghost brain (core paths wired, polish remaining).**

## Last updated

2026-10-28 (session 3), by GLM agent — Windows bugs #1 and #2 fixed and pushed
(`5fc4835`); awaiting user's Windows re-verification.

## Completed tasks

- [x] 2026-10-28 — Verified Ollama Gemma tags against the live library:
      `gemma3:270m` (292 MB), `gemma3:1b` (806 MB), `gemma3:4b` (3.4 GB),
      `1b-it-qat`, etc. → default model was `gemma3:1b` (see Decisions).
- [x] 2026-10-28 — Default model switched to **`gemma4:e4b`** at the user's
      request; tag verified against Ollama's live library (effective-4B edge
      model, 6.6–9.5 GB, 128k ctx). Fallback chain extended:
      `gemma4:e4b` → `gemma3:1b` → `gemma3:270m` → any installed model.
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
- [x] 2026-10-28 — Phase 1 acceptance: `pytest` green locally (173 tests +
      3 Windows-skips), `ruff` clean, manual smoke of the full loop
      (`echo`, `cd /`, `git status`, `ghost,` chat, `sanity`, `exorcise`) on
      Linux with Ollama offline (canned voice path).
- [x] 2026-10-28 — Phase 2: `ui/theme.py` — classic/ofrenda/slasher palettes,
      glyphs, ASCII-art fallbacks; all colors validated against rich in tests
      (a bad name — `blanched_almond` — crashed one live séance and was caught
      by a PTY smoke test; fixed + regression test added).
- [x] 2026-10-28 — Phase 2: capability detection (`ui/capabilities.py`) —
      TTY/Unicode/color-depth; NO_COLOR and non-TTY force plain+ASCII,
      animations off; `POLTERGEIST_NO_ANIM` escape hatch.
- [x] 2026-10-28 — Phase 2: skippable intro (`ui/sequences.py`) — flicker →
      glitch static → ghost art materializes → first words; time-budgeted
      (≤4 s) + any-key skip; `outro` exorcism sequence; terminal always
      restored (cursor visible, SGR reset).
- [x] 2026-10-28 — Phase 2: ghost speech via typewriter + zalgo-lite word
      corruption that scales DOWN as sanity drops (glitch level 2 only below
      sanity 30); tombstone-style `☠ exit N` framing for failures; themed
      prompts (👻/🕯️/🩸 or ASCII fallback).

## In progress

- Nothing right now (session ended here — next agent: pick up "Next up").

## Next up (prioritized)

1. Phase 3 — Ghost brain polish: verify against a live Ollama + `gemma4:e4b`
   (commentary quality, `ghost,` chat with real output context); tune
   `commentary_rate`; add one-off `haunt "command"` non-interactive demo mode
   (nice for GIF).
2. Phase 4 — Safety & agency: `--autonomy curious` auto-run path for `safe`
   verdicts, glowing approval box for `needs-approval` proposals, autonomous
   idle/night whisper thread using `prompt_toolkit`'s `patch_stdout`.
3. Phase 5 — Memory: opt-in shell-history readers (bash/zsh/fish/PSReadLine +
   Poltergeist audit), "I remember" hauntings, `haunt forget` wiring (exists —
   extend to history store), sanity meter full meltdowns at 0.
4. Phase 6 — Ship: README GIF, demo script in `docs/`, DEV post outline,
   first-run onboarding consent screen, CI green on all 3 OSes.
5. Stretch (only if solid): voice (`--voice`), PTY possess mode.

## Known issues / blockers

- None blocking. (Sandbox here has no GPU/Ollama daemon; model serving is
  exercised via contract tests + doctor, verified by the user locally.)

## Decisions log

| Date       | Decision                                                                 | Why                                                                                             |
| ---------- | ------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------- |
| 2026-10-28 | Default model **`gemma4:e4b`** (effective-4B edge model, 6.6–9.5 GB, 128k ctx) | User request; tag verified against Ollama's library the same day — it is the on-device Edge class. Fallback chain keeps `gemma3:1b` (806 MB) for tiny machines |
| 2026-10-28 | (superseded) Default was `gemma3:1b` at bootstrap                        | Verified small-then; kept in the fallback chain for lightweight laptops                          |
| 2026-10-28 | No PTY/ConPTY on core path; `subprocess` + native shells                  | Fragile cross-platform; capture+stream via pipes is reliable and testable                        |
| 2026-10-28 | `cd`/`export`/`set` intercepted in Python, shell spawned per command       | Shells don't share state between invocations; interception is portable and testable              |
| 2026-10-28 | httpx for Ollama streaming                                               | Cleaner streaming (SSE/NDJSON) than urllib, still fully local/libre                              |
| 2026-10-28 | Raw ANSI control codes guarded behind a capability check                  | rich handles most styling; low-level cursor/screen control must degrade                          |
| 2026-10-28 | Config file is TOML in platformdirs user config dir                       | Human-friendly single file; `tomllib` is stdlib on 3.11+, `tomli` marker dep for 3.10            |
| 2026-10-28 | Phase 2 regression: every theme color validated against rich in tests        | A bad color name (`blanched_almond`) crashed a live séance; caught by a PTY smoke test           |
| 2026-10-28 | Non-TTY stdin falls back from prompt_toolkit to `input()`                     | prompt_toolkit can't drive pipes; the plain path keeps demos/tests working                      |
| 2026-10-28 | Typewriter bounded at 1.4 s per line; corruption only below sanity 60         | The ghost must never hold the user hostage; sanity 100+ stays readable                          |

## How to run/test right now

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest                     # 173 passed + 3 windows-skips as of last update (no Ollama needed)
ruff check src tests
haunt doctor               # status of Python/TTY/Ollama/model
haunt                      # full haunted session (intro animation on a TTY)
haunt --no-intro           # skip the transformation sequence
```

## Demo & submission checklist

- [ ] Demo GIF/video recorded
- [ ] README done (install incl. Ollama + `gemma4:e4b`, why-open-source section)
- [ ] Demo script in `docs/`
- [ ] DEV post drafted (tags `#devchallenge` `#hf26challenge`)
- [ ] Submitted before **Oct 31 2026, 11:59 PM PDT**
