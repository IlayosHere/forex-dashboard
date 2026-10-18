"""
api/services/research/parse_log.py
----------------------------------
Parse results/exploration/LOG.md: the table of looks, the idea index and the lessons.
"""
from __future__ import annotations

import math
import re
from typing import Any

_RULER = re.compile(r"^\|[\s\-:|]+\|$")
_INDEX_HEADING = "## Idea index"
_LESSONS_MARKER = "Lessons that apply to every new idea"


def clean_cell(cell: str) -> str:
    """Drop markdown bold and code marks from a table cell."""
    return cell.replace("**", "").replace("`", "").strip()


def table_rows(lines: list[str]) -> list[list[str]]:
    """Return the body rows of the first markdown table found in the lines."""
    rows: list[list[str]] = []
    for line in lines:
        line = line.strip()
        if not line.startswith("|") or _RULER.match(line):
            continue
        rows.append([clean_cell(c) for c in line.strip("|").split("|")])
    return rows[1:]  # first row is the header


def promotion_bar(looks: int) -> float:
    """z a new idea must beat after this many looks: sqrt(2 ln N)."""
    return round(math.sqrt(2 * math.log(looks)), 2) if looks > 1 else 0.0


def parse_entries(rows: list[list[str]]) -> list[dict[str, Any]]:
    """Numbered looks: n, date, idea, what was looked at, variants, result."""
    out = []
    for r in rows:
        if len(r) >= 6 and r[0].isdigit() and r[4].isdigit():
            out.append({
                "n": int(r[0]), "date": r[1], "idea": r[2],
                "looked_at": r[3], "variants": int(r[4]), "result": r[5],
            })
    return out


def parse_lessons(text: str) -> list[str]:
    """Bullet lines that follow the 'Lessons that apply' line."""
    if _LESSONS_MARKER not in text:
        return []
    after = text.split(_LESSONS_MARKER, 1)[1].splitlines()[1:]
    lessons = []
    for line in after:
        if line.startswith("- "):
            lessons.append(clean_cell(line[2:]))
        elif lessons and line.strip() == "":
            break
    return lessons


def parse_log(text: str) -> dict[str, Any]:
    """Split LOG.md into numbered looks and lessons; the index is read from ideas.yaml."""
    head = text.split(_INDEX_HEADING, 1)[0]
    entries = parse_entries(table_rows(head.splitlines()))
    looks = sum(e["variants"] for e in entries)
    return {
        "entries": entries,
        "looks": looks,
        "bar": promotion_bar(looks),
        "lessons": parse_lessons(text),
    }
