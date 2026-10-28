# 👻 Poltergeist — an AI-powered haunted terminal

**Run `haunt` and a ghost moves into your shell.** It comments on your commands
(creepy, witty, startled at build failures), chats back when you address it,
keeps a **sanity meter** in your status line, remembers your darkest command
history — and can propose commands you approve in a glowing box before they
ever run.

Powered by **open-weight local AI** (Ollama + Gemma by default):

- 🕯️ **Offline** — the ghost speaks without internet. The séance never needs a cloud.
- 🔒 **Private** — your shell history and command output never leave your machine.
- 💸 **Free** — local weights, no API key, no metered tokens.
- 🔀 **Swappable** — any Ollama model; add a provider interface for other local backends.

MIT licensed. No telemetry. No network calls except to your own local model.

```console
$ pipx install poltergeist            # or: pip install poltergeist
$ haunt doctor                        # check the séance conditions
$ haunt                               # 👻 ─ your terminal belongs to the ghost now
ghost, why did my build fail?
  🜸 Two tests died screaming, exit code 42. The third flails in a retry loop.
$ exorcise                            # return your terminal to the living
```

## Status

🚧 **Week 4 Hacktoberfest 2026 Open-Source AI Challenge build** — see
[STATUS.md](STATUS.md) for exactly what is implemented right now
(Phases 1–2 done; the ghost brain gets its theatrical upgrades daily).

## Quickstart (zero → haunted in 5 minutes)

1. **Install Ollama** — <https://ollama.com/download> (Windows, macOS, Linux).
2. **Pull the ghost's brain** (the default is the *edge* Gemma 4 model — made
   for on-device local execution; use `gemma3:1b` instead if you want the
   ultra-light download):

   ```console
   $ ollama pull gemma4:e4b
   ```

3. **Install Poltergeist**:

   ```console
   $ pipx install poltergeist       # recommended
   # or, from source:
   $ git clone <this repo> && pip install --user ./poltergeist
   ```

4. **Start the haunting**:

   ```console
   $ haunt
   ```

   Everything is already running if Ollama is up — otherwise the ghost still
   talks in its *canned voice*; nothing crashes. `haunt doctor` tells you every
   step whenever anything is odd.

## Commands

| Where          | What                       | Why                                     |
| -------------- | -------------------------- | --------------------------------------- |
| shell          | `haunt`                    | begin the haunting                      |
| shell          | `haunt doctor`             | environment check + fix instructions    |
| shell          | `haunt forget`             | wipe every local memory + audit file    |
| inside `haunt` | `ghost, <msg>` / `?<msg>`  | chat with the ghost (with command context) |
| inside `haunt` | `sanity`                   | show the sanity meter                   |
| inside `haunt` | `theme classic\|ofrenda\|slasher` | switch possession styles        |
| inside `haunt` | `exorcise`                 | leave gracefully (terminal restored)    |

Themes: `classic` (gothic purple/orange), `ofrenda` (warm Día de los Muertos,
gentle), `slasher` (B-movie horror host).

## Safety first (the ghost is polite about it)

- A local **command safety classifier** sorts commands into `safe` /
  `needs-approval` / `blocked` before anything the ghost *proposes* may run.
  `blocked` spells (disk wipes, fork bombs, `rm -rf /`, credential
  exfiltration) are refused — even if the user "approves".
- `pip`-quiet redaction: secrets (API keys, `.env` values, tokens) are
  redacted before anything reaches the model or the audit log.
- The default autonomy is **ask first**; `--autonomy curious` allows the ghost
  to auto-run only strictly read-only commands.
- Every ghost-executed command is logged to a local audit file
  (`poltergeist audit.jsonl` in your data dir). Nothing is ever uploaded.
- Shell history haunting is **opt-in**, 100% local, and wipable with `haunt forget`.

## Why open-source/local AI (and not the closest cloud API)

A ghost that reads your real, embarrassing shell history and watches your real
build errors can only ever be trusted if **it cannot leak them**. Local,
open-weight models are the only way to make that promise checkable:

1. **Privacy**: history, output and audit data never leave your disk.
2. **Trust**: the classifier runs locally; the model runs locally; you can
   read both.
3. **Access**: free forever, works on a train in a tunnel, no API key. A
   haunted terminal shouldn't cost a subscription.
4. **Openness as creativity constraint**: making a small open model (Gemma 4
   E4B by default, swappable down to an 806 MB Gemma 3) carry a *persona*
   strictly with prompts is a fun challenge — and it is why the ghost's
   personality is all craft and minimal data.

Swapping models is a one-liner: `haunt --model gemma4:e2b` (lighter) or
`POLTERGEIST_MODEL=qwen2.5:3b haunt` (any Ollama model).

## Development

```console
$ pip install -e ".[dev]"
$ pytest        # 60+ tests, no Ollama / no internet needed
$ ruff check src tests
```

Architecture and conventions for contributors (human or LLM): [AGENTS.md](AGENTS.md).

## License

MIT — see [LICENSE](LICENSE).
