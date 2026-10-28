"""Ghost speech: typewriter delivery, zalgo-lite corruption, rated effects."""

from __future__ import annotations

import random
import time
import unicodedata

MAX_TYPE_TIME = 1.4  # never hold the user hostage with a long line

# combining marks that look cursed but survive terminal wrapping
_GLITCH_MARKS = [
    "́",
    "̈",
    "̂",
    "̧",
    "̸",
    "̆",
    "̊",
    "̑",
    "̓",
]


def glitch_word(word: str, level: int, rng: random.Random, *, unicode: bool = True) -> str:
    """Give a word 0..2 cursed combining marks per character.

    Falls back to plain text when Unicode is unavailable."""
    if not unicode or level <= 0 or len(word) < 2 or "http" in word.lower():
        return word
    marks = min(level, 2)
    out = []
    for idx, ch in enumerate(word):
        out.append(ch)
        if rng.random() < 0.25 and unicodedata.category(ch).startswith("L"):
            out.extend(_GLITCH_MARKS[(idx + len(word)) % len(_GLITCH_MARKS)] for _ in range(marks))
    return "".join(out)


def corrupt(text: str, *, level: int, sanity: int, rng: random.Random, unicode: bool = True) -> str:
    """Corrupt *key words* only. High sanity -> practically nothing."""
    if not unicode or level <= 0:
        return text
    chance = max(0.0, (60 - sanity) / 300)
    words = text.split(" ")
    if len(words) < 3 and level < 2:
        return text
    start = rng.randrange(0, max(1, len(words) // 3))
    for idx in range(start, len(words), max(2, len(words) // 3)):
        if rng.random() < 0.35 + chance:
            words[idx] = glitch_word(words[idx], level, rng, unicode=unicode)
    return " ".join(words)


def typewriter(
    console,
    text: str,
    *,
    style: str,
    lang: float = 0.012,
    max_time: float = MAX_TYPE_TIME,
) -> None:
    """Print text one visible chunk at a time, bounded by max_time."""
    if not text:
        return
    if lang <= 0:
        console.print(text, style=style, end="")
        console.print()
        return
    max_chunks = max(1, int(max_time / lang))
    if len(text) > max_chunks:
        step = (len(text) + max_chunks - 1) // max_chunks
        chunks = [text[i : i + step] for i in range(0, len(text), step)]
    else:
        chunks = list(text)
    try:
        for chunk in chunks:
            console.print(chunk, style=style, end="")
            time.sleep(lang)
    except KeyboardInterrupt:
        console.print("\n[the line was stolen mid-whisper …]", style=style)
        raise
    finally:
        console.print()
