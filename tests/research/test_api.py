"""tests/research/test_api.py - /api/research endpoints against a synthetic local repo."""
from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.routes.research import get_research_source
from api.services.research import queue as queue_mod
from api.services.research.source import LocalSource, SourceNotConfigured
from tests.research.fixtures import write_repo


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    return write_repo(tmp_path)


@pytest.fixture()
def research_client(client: TestClient, repo: Path) -> Generator[TestClient, None, None]:
    from api.main import app

    queue_mod._recent.clear()
    app.dependency_overrides[get_research_source] = lambda: LocalSource(repo)
    yield client
    app.dependency_overrides.pop(get_research_source, None)


def test_overview_has_every_section(research_client: TestClient) -> None:
    body = research_client.get("/api/research").json()
    assert body["warnings"] == []
    status = body["status"]
    assert status["looks"] == 30 and status["trials_run"] == 2 and status["trials_left"] == 8
    assert status["next_trial"] == 3 and status["next_trial_alpha"] == 0.015
    assert [i["status"] for i in body["ideas"]] == ["killed", "candidate"]
    assert body["baseline"]["stages"][0]["strategy"] == "BETA"
    assert [a["state"] for a in body["alpha_plan"]] == ["passed", "failed", "open", "open"]
    kinds = [j["kind"] for j in body["journey"]]
    assert set(kinds) == {"decision", "trial", "exploration"}
    trial_titles = [j["title"] for j in body["journey"] if j["kind"] == "trial"]
    assert "Trial 1 passed: BETA, in-sample" in trial_titles and "Trial 2 failed: GAMMA, confirmation 2018-2026" in trial_titles
    dates = [j["date"] for j in body["journey"]]
    assert dates == sorted(dates, reverse=True)
    assert body["lessons"][0] == "Count every look."


def test_missing_file_becomes_a_warning_not_an_error(client: TestClient, tmp_path: Path) -> None:
    from api.main import app

    write_repo(tmp_path, skip={"registry/trial_log.csv"})
    app.dependency_overrides[get_research_source] = lambda: LocalSource(tmp_path)
    try:
        body = client.get("/api/research").json()
    finally:
        app.dependency_overrides.pop(get_research_source, None)
    assert body["trials"] == [] and len(body["warnings"]) == 1
    assert body["warnings"][0].startswith("Trials")
    assert len(body["ideas"]) == 2  # other sections still render


def test_not_configured_is_503(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom() -> None:
        raise SourceNotConfigured("nothing set")

    monkeypatch.setattr("api.routes.research.get_source", boom)
    assert client.get("/api/research").status_code == 503


def test_requires_login(raw_client: TestClient) -> None:
    assert raw_client.get("/api/research").status_code in (401, 403)
    assert raw_client.post("/api/research/queue", json={}).status_code in (401, 403)


def test_report_only_from_report_folders(research_client: TestClient) -> None:
    ok = research_client.get("/api/research/report", params={"path": "results/exploration/agents/x.md"})
    assert ok.status_code == 200 and ok.json()["text"].startswith("# Report")
    for bad in ("registry/trial_log.csv", "../secrets.md", "results/../registry/round2.yaml", "/etc/passwd"):
        assert research_client.get("/api/research/report", params={"path": bad}).status_code == 400
    missing = research_client.get("/api/research/report", params={"path": "results/phase3/NOPE.md"})
    assert missing.status_code == 404


def test_add_idea_writes_a_new_file_and_lists_it(research_client: TestClient, repo: Path) -> None:
    res = research_client.post("/api/research/queue", json={
        "kind": "idea", "title": "Fade the first hour", "stage": "3",
        "body": "Price overreacts in the first hour and comes back."})
    assert res.status_code == 201
    item = res.json()
    assert item["status"] == "queued" and item["submitted_by"] == "testuser" and item["about"] is None
    files = [p.name for p in (repo / "results/exploration/queue").iterdir()]
    assert len(files) == 1 and files[0].endswith("-fade-the-first-hour.md")
    listed = research_client.get("/api/research/queue").json()
    assert [q["title"] for q in listed] == ["Fade the first hour"]
    assert research_client.get("/api/research").json()["queue"][0]["id"] == item["id"]


def test_note_must_point_at_a_tested_idea(research_client: TestClient) -> None:
    body = {"kind": "note", "title": "A thought", "stage": "any", "body": "Worth checking in 2020 only."}
    assert research_client.post("/api/research/queue", json=body).status_code == 422
    assert research_client.post("/api/research/queue", json={**body, "about": "../x"}).status_code == 422
    assert research_client.post("/api/research/queue", json={**body, "about": "BETA"}).status_code == 201


def test_queue_validation_and_rate_limit(research_client: TestClient) -> None:
    short = {"kind": "idea", "title": "ab", "stage": "3", "body": "too short"}
    assert research_client.post("/api/research/queue", json=short).status_code == 422
    bad_stage = {"kind": "idea", "title": "Valid title", "stage": "9", "body": "long enough body text"}
    assert research_client.post("/api/research/queue", json=bad_stage).status_code == 422
    queue_mod._recent["testuser"].extend([0.0] * 0)
    queue_mod._recent["testuser"].extend([10**12] * 20)
    ok = {"kind": "idea", "title": "Valid title", "stage": "3", "body": "long enough body text"}
    assert research_client.post("/api/research/queue", json=ok).status_code == 429


def test_title_cannot_inject_front_matter(research_client: TestClient, repo: Path) -> None:
    res = research_client.post("/api/research/queue", json={
        "kind": "idea", "title": 'Evil"\nstatus: answered', "stage": "any",
        "body": "Body text long enough here."})
    assert res.status_code == 201
    assert res.json()["status"] == "queued"
    assert res.json()["title"] == 'Evil"\nstatus: answered'
