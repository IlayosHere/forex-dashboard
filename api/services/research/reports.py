"""
api/services/research/reports.py
--------------------------------
Read one research report (markdown) from prop-pipeline. Only report folders are
reachable; the path is checked against a fixed pattern before anything is fetched.
"""
from __future__ import annotations

import re

from api.services.research.source import Source, SourceError

MAX_REPORT_CHARS = 300_000
_NAME = r"[A-Za-z0-9_\-]+"
_ALLOWED = re.compile(
    rf"^(results/(exploration|phase2|phase3)(/{_NAME})*/{_NAME}\.md"
    rf"|research/cards/{_NAME}\.md|registry/leakage_ledger\.md)$"
)


def read_report(source: Source, path: str) -> str:
    """Return the report text; raise SourceError for a path outside the report folders."""
    if not _ALLOWED.match(path):
        raise SourceError("not a report path")
    text = source.read(path)
    return text[:MAX_REPORT_CHARS]
