"""tests/research/test_source.py - GitHub and local sources (no network: urlopen is mocked)."""
from __future__ import annotations

import base64
import io
import json
import urllib.error
from pathlib import Path
from typing import Any

import pytest

from api.services.research import source as src
from api.services.research.source import GitHubSource, LocalSource, SourceError, SourceNotFound, check_path


class _Resp(io.BytesIO):
    def __enter__(self) -> "_Resp":
        return self

    def __exit__(self, *a: object) -> None:
        return None


def _gh(monkeypatch: pytest.MonkeyPatch, reply: Any) -> list[Any]:
    calls: list[Any] = []

    def fake(req: Any, timeout: int = 0) -> _Resp:
        calls.append(req)
        if isinstance(reply, Exception):
            raise reply
        return _Resp(reply if isinstance(reply, bytes) else json.dumps(reply).encode())

    monkeypatch.setattr(src.urllib.request, "urlopen", fake)
    return calls


def test_check_path_blocks_escapes() -> None:
    for bad in ("", "/abs", "a/../b", "a//b", "a\\b", ".."):
        with pytest.raises(SourceError):
            check_path(bad)
    assert check_path("results/phase3/TRIAL7_REPORT.md")


def test_github_read_is_cached_and_sends_token(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _gh(monkeypatch, b"hello")
    gh = GitHubSource("o/r", "tok", "main")
    assert gh.read("a/b.md") == "hello" and gh.read("a/b.md") == "hello"
    assert len(calls) == 1
    assert calls[0].get_header("Authorization") == "Bearer tok"
    assert calls[0].full_url.endswith("/repos/o/r/contents/a/b.md?ref=main")


def test_github_404_and_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    err = urllib.error.HTTPError("u", 404, "nf", {}, None)  # type: ignore[arg-type]
    _gh(monkeypatch, err)
    gh = GitHubSource("o/r", "tok")
    with pytest.raises(SourceNotFound):
        gh.read("x.md")
    assert gh.list_dir("results/exploration/queue") == []
    _gh(monkeypatch, urllib.error.URLError("down"))
    with pytest.raises(SourceError):
        gh.read("y.md")


def test_github_list_and_create(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _gh(monkeypatch, [{"name": "b.md", "type": "file"}, {"name": "sub", "type": "dir"}, {"name": "a.md", "type": "file"}])
    gh = GitHubSource("o/r", "tok")
    assert gh.list_dir("q") == ["a.md", "b.md"]
    _gh(monkeypatch, {"content": {}})
    calls = _gh(monkeypatch, {"content": {}})
    gh.create("q/new.md", "text", "msg")
    req = calls[0]
    body = json.loads(req.data)
    assert req.get_method() == "PUT" and body["branch"] == "main" and body["message"] == "msg"
    assert base64.b64decode(body["content"]).decode() == "text"
    assert "sha" not in body  # create only, never overwrite


def test_local_source_never_overwrites_or_escapes(tmp_path: Path) -> None:
    local = LocalSource(tmp_path)
    local.create("q/one.md", "x", "m")
    with pytest.raises(SourceError):
        local.create("q/one.md", "y", "m")
    assert local.read("q/one.md") == "x"
    with pytest.raises(SourceNotFound):
        local.read("q/none.md")
    with pytest.raises(SourceError):
        local.read("../outside.md")
    assert local.list_dir("q") == ["one.md"] and local.list_dir("nope") == []


def test_get_source_from_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    src.get_source.cache_clear()
    monkeypatch.delenv("PROP_PIPELINE_LOCAL_DIR", raising=False)
    monkeypatch.delenv("PROP_PIPELINE_GITHUB_TOKEN", raising=False)
    with pytest.raises(src.SourceNotConfigured):
        src.get_source()
    src.get_source.cache_clear()
    monkeypatch.setenv("PROP_PIPELINE_LOCAL_DIR", str(tmp_path))
    assert isinstance(src.get_source(), LocalSource)
    src.get_source.cache_clear()
