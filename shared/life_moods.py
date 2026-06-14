"""
shared/life_moods.py
--------------------
Life mood taxonomy constants shared between scanner and API layers.
"""
from __future__ import annotations

LIFE_MOOD_VALUES: list[str] = [
    "happy",
    "excited",
    "calm",
    "sad",
    "anxious",
    "angry",
]

# Negative moods win in tie-break (higher index = more negative wins)
_MOOD_NEGATIVITY_RANK: dict[str, int] = {
    "excited": 0,
    "calm": 1,
    "happy": 2,
    "sad": 3,
    "anxious": 4,
    "angry": 5,
}


def dominant_mood(moods: list[str]) -> str | None:
    """Return the most negative mood from a list, or None if empty."""
    valid = [m for m in moods if m in _MOOD_NEGATIVITY_RANK]
    if not valid:
        return None
    return max(valid, key=lambda m: _MOOD_NEGATIVITY_RANK[m])
