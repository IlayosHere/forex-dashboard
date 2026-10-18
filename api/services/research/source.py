"""
api/services/research/source.py
-------------------------------
Where the research files come from: the private prop-pipeline repo on GitHub, or a
local folder (development and tests). Reads are cached for a short time. The only
write is creating a NEW file under the queue folder; nothing is ever overwritten.

Env:
  PROP_PIPELINE_LOCAL_DIR     read (and write) a local clone instead of GitHub
  PROP_PIPELINE_GITHUB_TOKEN  fine-grained token limited to the prop-pipeline repo
  PROP_PIPELINE_REPO          owner/name, default IlayosHere/prop-pipeline
  PROP_PIPELINE_BRANCH        default main
"""
from __future__ import annotations

import base64
import json
import logging
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from functools import lru_cache
from pathlib import Path
from typing import Protocol

logger = logging.getLogger(__name__)

CACHE_SECONDS = 60
HTTP_TIMEOUT_SECONDS = 10
QUEUE_DIR = "results/exploration/queue"


class SourceError(Exception):
    """The research files could not be read or written."""


class SourceNotFound(SourceError):
    """A file or folder does not exist in the source."""


class SourceNotConfigured(SourceError):
    """Neither a local folder nor a GitHub token is configured."""


class Source(Protocol):
    """Read files from the research repo and add new queue files to it."""

    label: str

    def read(self, path: str) -> str: ...

    def list_dir(self, path: str) -> list[str]: ...

    def create(self, path: str, text: str, message: str) -> None: ...


def check_path(path: str) -> str:
    """Reject anything that could leave the repo; return the path unchanged."""
    parts = path.split("/")
    if not path or path.startswith("/") or "\\" in path or ".." in parts or "" in parts:
        raise SourceError(f"bad path: {path!r}")
    return path


class LocalSource:
    """A local clone of prop-pipeline."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.label = f"local:{self.root.name}"

    def _resolve(self, path: str) -> Path:
        full = (self.root / check_path(path)).resolve()
        if self.root not in full.parents and full != self.root:
            raise SourceError(f"path escapes the repo: {path!r}")
        return full

    def read(self, path: str) -> str:
        full = self._resolve(path)
        if not full.is_file():
            raise SourceNotFound(path)
        return full.read_text(encoding="utf-8")

    def list_dir(self, path: str) -> list[str]:
        full = self._resolve(path)
        if not full.is_dir():
            return []
        return sorted(p.name for p in full.iterdir() if p.is_file())

    def create(self, path: str, text: str, message: str) -> None:
        full = self._resolve(path)
        if full.exists():
            raise SourceError(f"already exists: {path}")
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(text, encoding="utf-8")


class GitHubSource:
    """prop-pipeline on GitHub through the contents API, with a short read cache."""

    api = "https://api.github.com"

    def __init__(self, repo: str, token: str, branch: str = "main") -> None:
        self.repo = repo
        self.branch = branch
        self.label = f"github:{repo}@{branch}"
        self._token = token
        self._cache: dict[str, tuple[float, object]] = {}
        self._lock = threading.Lock()

    def _request(self, method: str, path: str, accept: str, body: dict | None = None) -> bytes:
        quoted = urllib.parse.quote(check_path(path))
        url = f"{self.api}/repos/{self.repo}/contents/{quoted}"
        if method == "GET":
            url += f"?ref={urllib.parse.quote(self.branch)}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self._token}")
        req.add_header("Accept", accept)
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        req.add_header("User-Agent", "forex-dashboard-research")
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as res:
                return res.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise SourceNotFound(path) from exc
            logger.warning("GitHub %s %s failed: %s", method, path, exc.code)
            raise SourceError(f"GitHub answered {exc.code} for {path}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            logger.warning("GitHub unreachable for %s: %s", path, exc)
            raise SourceError("GitHub could not be reached") from exc

    def _cached(self, key: str) -> object | None:
        with self._lock:
            hit = self._cache.get(key)
        if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
            return hit[1]
        return None

    def _store(self, key: str, value: object) -> None:
        with self._lock:
            self._cache[key] = (time.monotonic(), value)

    def read(self, path: str) -> str:
        cached = self._cached(f"file:{path}")
        if isinstance(cached, str):
            return cached
        text = self._request("GET", path, "application/vnd.github.raw").decode("utf-8")
        self._store(f"file:{path}", text)
        return text

    def list_dir(self, path: str) -> list[str]:
        cached = self._cached(f"dir:{path}")
        if isinstance(cached, list):
            return cached
        try:
            raw = self._request("GET", path, "application/vnd.github+json")
        except SourceNotFound:
            return []
        names = sorted(e["name"] for e in json.loads(raw) if e.get("type") == "file")
        self._store(f"dir:{path}", names)
        return names

    def create(self, path: str, text: str, message: str) -> None:
        body = {
            "message": message,
            "content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
            "branch": self.branch,
        }
        self._request("PUT", path, "application/vnd.github+json", body)
        with self._lock:
            self._cache.pop(f"dir:{path.rsplit('/', 1)[0]}", None)


@lru_cache(maxsize=1)
def get_source() -> Source:
    """Build the configured source once per process (FastAPI dependency)."""
    local = os.getenv("PROP_PIPELINE_LOCAL_DIR", "").strip()
    if local:
        return LocalSource(Path(local).expanduser())
    token = os.getenv("PROP_PIPELINE_GITHUB_TOKEN", "").strip()
    if not token:
        raise SourceNotConfigured("set PROP_PIPELINE_GITHUB_TOKEN or PROP_PIPELINE_LOCAL_DIR")
    return GitHubSource(
        os.getenv("PROP_PIPELINE_REPO", "IlayosHere/prop-pipeline"),
        token,
        os.getenv("PROP_PIPELINE_BRANCH", "main"),
    )
