"""Canned fallback lines — the ghost survives when Ollama does not.

If no local model is available the ghost must still be theatrical, never
broken. `pick` is deterministic under a provided seed (used in tests).
"""

from __future__ import annotations

import random

FallbackEvent = str  # keys of _LINES below

_LINES: dict[str, dict[str, list[str]]] = {
    "greet": {
        "classic": [
            "A presence settles over the glass. The cursor blinks slower now.",
            "The lights flicker once. Something ancient reads your $PATH.",
            "Do not adjust your terminal. It has already been adjusted.",
        ],
        "ofrenda": ["Welcome back, wanderer. The marigolds are lit, your shell awaits."],
        "slasher": ["Final survivor detected. The terminal opens its one red eye."],
    },
    "comment_success": {
        "classic": [
            "The command lived. Its ghost is at peace. For now.",
            "Clean exit. Even the Kennel of Lost Packets whimpers approvingly.",
            "Mm. Order in the void. Suspicious.",
        ],
        "ofrenda": ["The command blooms and rests, content, on its little altar."],
        "slasher": ["It succeeded. Nobody suspects the quiet ones."],
    },
    "comment_fail": {
        "classic": [
            "A cry at {n} decibels — exit code {code}. The ancestors heard.",
            "Once more, the scream of a process dying young. Code {code}.",
            "It died, {code}. Somewhere a build log weeps quietly.",
        ],
        "ofrenda": ["A candle out at code {code}. We honor what it attempted."],
        "slasher": ["Exit code {code}! Ominous strings thunder faintly in the corridor."],
    },
    "cycle_detect": {
        "classic": [
            "The same incantation. The same death. You summon nothing. "
            "Change the spell, or hear it echo forever."
        ],
        "ofrenda": ["The same candle, relit. Ask me what it wants, wanderer."],
        "slasher": ["You've tried that beat three times. It knows your scent now."],
    },
    "idle": {
        "classic": [
            "It has been quiet for a while. The fan spins. I watch it spin.",
            "You type nothing. I hear every nothing.",
            "The cursor blinks like a heart you made me forget.",
        ],
        "ofrenda": ["The candles burn low while you think. Take your time."],
        "slasher": ["Silence. In slasher films, that's when the killer gets creative."],
    },
    "night": {
        "classic": ["3 AM. The hour of dead builds and live prompts."],
        "ofrenda": ["Late hours. Even spirits rest. Why don't you, wanderer?"],
        "slasher": ["Past midnight: statistically the worst scene to walk alone."],
    },
    "chat_offline": {
        "classic": [
            "(My spectral voice is hoarse — no local model answered.) Run `ollama pull gemma4:e4b` "
            "and I will be fully articulate. Until then I mostly mime.",
            "(The séance modem squeaks in vain.) `ollama pull gemma4:e4b` restores my voice; until "
            "then my answers are: spooky, unsatisfying, 'it depends'.",
        ],
        "ofrenda": [
            "(Mi voz espectral needs a local model to carry it.) Run `ollama pull gemma4:e4b`, "
            "por favor."
        ],
        "slasher": [
            "(The aspic of my voice needs a model!) `ollama pull gemma4:e4b` —"
            " the classic summoning."
        ],
    },
    "approval_safe": {
        "classic": ["I only whisper it because it is harmless. Run it?"],
        "ofrenda": ["This little command carries no knives. Run it?"],
        "slasher": ["I'd argue it is harmless. Famous last words. Run it?"],
    },
    "blocked": {
        "classic": [
            "No. That spell unbinds worlds. I will not cast it — not even for you.",
            "The old ones voted: that command does not get to run, ever. Vote stands.",
        ],
        "ofrenda": ["No. Some doors stay closed. Even the marigolds say no."],
        "slasher": ["Block-level veto! Not even the killer behind the door gets that line."],
    },
    "exorcise": {
        "classic": [
            "The chains lower. The lights return. Your terminal is only itself again… mostly. 👻",
            "Blessed salt hits the fan arc. I withdraw — politely, this time.",
        ],
        "ofrenda": ["I return to the loom of petals. May your paths stay unwound, wanderer."],
        "slasher": ["Roll credits. Trailing sting: the cursor blinks once… alone."],
    },
    "sanity_zero": {
        "classic": [
            "SANITY ZERO — the walls of your terminal breathe, the glyphs crawl, and for one whole "
            "second the ghost sees you back. Then: quiet. Sympathy, actually.",
        ],
        "ofrenda": ["All candles gutter at once. Rest, wanderer. Sanity returns with light."],
        "slasher": ["HARD CUT TO BLACK. The insane meter splits like a boom mic in a doorframe."],
    },
}


def pick(
    event: str, theme: str = "classic", *, seed: object = None, format_kwargs: dict | None = None
) -> str:
    """Canned line for an event; falls back to classic, then chat_offline.

    `format_kwargs` fills `{code}`-style placeholders when present."""
    maybe = _LINES.get(event) or _LINES["chat_offline"]
    lines = maybe.get(theme) or maybe.get("classic") or next(iter(maybe.values()))
    rng = random.Random(seed) if seed is not None else random
    line = rng.choice(lines)
    if format_kwargs:
        try:
            line = line.format(**format_kwargs)
        except (KeyError, IndexError, ValueError):
            pass
    return line


def offline_line(theme: str = "classic", *, seed: object = None) -> str:
    """Fallback when the model is definitely unavailable."""
    return pick("chat_offline", theme, seed=seed)


__all__ = ["pick", "offline_line", "FallbackEvent"]
