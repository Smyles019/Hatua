"""Swahili for what the server writes: questions, answer options and result labels.

The words live in i18n/sw.json at the repository root, the one file the app, the website
and the backend all read, so a reviewer checks every Swahili line in one place. It is
keyed by the English text. Anything missing falls back to English, so a half-done file
never breaks a page. Keys starting with "_" are notes for the reviewer, not words.
"""
import json
from functools import lru_cache
from pathlib import Path

SW_FILE = Path(__file__).resolve().parents[3] / "i18n" / "sw.json"


def _swahili() -> dict[str, str]:
    """All Swahili lines. Read again whenever the file changes, so a reviewer's fix shows
    without restarting the server."""
    try:
        changed = SW_FILE.stat().st_mtime_ns
    except OSError:
        return {}
    return _read(changed)


@lru_cache(maxsize=2)
def _read(_changed: int) -> dict[str, str]:
    try:
        sections = json.loads(SW_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    words: dict[str, str] = {}
    for key, value in sections.items():
        if not key.startswith("_") and isinstance(value, dict):
            words.update({en: sw for en, sw in value.items() if sw})
    return words


def tr(text: str | None, lang: str | None) -> str | None:
    """text in the person's language ("en" or "sw"); English when there is no Swahili."""
    if not text or lang != "sw":
        return text
    return _swahili().get(text, text)
