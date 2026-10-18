"""
api/services/research/queue.py
------------------------------
The owner's idea queue: one small markdown file per item under
results/exploration/queue/ in prop-pipeline. File names are generated here, never
taken from the request, and an existing file is never overwritten.
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Any

import yaml

from api.services.research.source import QUEUE_DIR, Source, SourceError

logger = logging.getLogger(__name__)

MAX_ITEMS_READ = 100
_FRONT = re.compile(r"\A---\n(.*?)\n---\n?(.*)\Z", re.DOTALL)
_IDEA_ID = re.compile(r"^[A-Za-z0-9._-]{1,40}$")


MAX_SUBMISSIONS_PER_HOUR = 20
_recent: dict[str, deque[float]] = defaultdict(deque)
_recent_lock = threading.Lock()


class QueueInputError(ValueError):
    """The submitted idea or note is not acceptable."""


def check_rate(user: str, now: float | None = None) -> bool:
    """True if this user may add another item now (20 per hour)."""
    now = time.monotonic() if now is None else now
    with _recent_lock:
        window = _recent[user]
        while window and now - window[0] > 3600:
            window.popleft()
        if len(window) >= MAX_SUBMISSIONS_PER_HOUR:
            return False
        window.append(now)
        return True


def parse_item(text: str) -> dict[str, Any] | None:
    """Read one queue file; None if it has no usable front matter."""
    match = _FRONT.match(text.replace("\r\n", "\n"))
    if not match:
        return None
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(meta, dict) or not {"id", "kind", "title", "status"} <= meta.keys():
        return None
    return {
        "id": str(meta["id"]),
        "kind": meta["kind"],
        "title": str(meta["title"]),
        "stage": str(meta.get("stage", "any")),
        "about": str(meta["about"]) if meta.get("about") else None,
        "status": meta["status"],
        "submitted_at": str(meta.get("submitted_at", "")),
        "submitted_by": str(meta["submitted_by"]) if meta.get("submitted_by") else None,
        "round": str(meta["round"]) if meta.get("round") else None,
        "answer": str(meta["answer"]) if meta.get("answer") else None,
        "body": match.group(2).strip(),
    }


def list_items(source: Source) -> tuple[list[dict[str, Any]], list[str]]:
    """Newest first. Unreadable files are skipped and reported as warnings."""
    names = [n for n in source.list_dir(QUEUE_DIR) if n.endswith(".md") and n != "README.md"]
    items: list[dict[str, Any]] = []
    warnings: list[str] = []
    for name in sorted(names, reverse=True)[:MAX_ITEMS_READ]:
        try:
            item = parse_item(source.read(f"{QUEUE_DIR}/{name}"))
        except SourceError:
            item = None
        if item is None:
            warnings.append(f"Queue file {name} could not be read")
        else:
            items.append(item)
    return items, warnings


def _slug(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40].strip("-")
    return slug or "item"


def _render(meta: dict[str, Any], body: str) -> str:
    lines = [f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in meta.items() if value]
    return "---\n" + "\n".join(lines) + "\n---\n" + body.strip().replace("\r\n", "\n") + "\n"


def create_item(
    source: Source, payload: dict[str, Any], user: str, idea_ids: set[str], now: datetime,
) -> dict[str, Any]:
    """Validate and write one new queue file; return the item as the page shows it."""
    kind, about = payload["kind"], payload.get("about")
    if kind == "note":
        if not about or not _IDEA_ID.match(about) or about not in idea_ids:
            raise QueueInputError("A note must say which tested idea it is about")
    else:
        about = None
    stamp = now.strftime("%Y%m%d-%H%M%S")
    meta = {
        "id": f"q-{stamp}", "kind": kind, "title": payload["title"].strip(), "stage": payload["stage"],
        "about": about, "status": "queued",
        "submitted_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "submitted_by": user,
    }
    path = f"{QUEUE_DIR}/{now.strftime('%Y-%m-%d-%H%M%S')}-{_slug(meta['title'])}.md"
    source.create(path, _render(meta, payload["body"]), f"Research queue: {kind} from the dashboard")
    logger.info("Queue item %s created by %s", meta["id"], user)
    item = parse_item(_render(meta, payload["body"]))
    if item is None:
        raise SourceError("the new queue item could not be read back")
    return item
