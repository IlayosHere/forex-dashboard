"""tests/research/test_parsers.py - parsing of the log, trial log, baseline and queue files."""
from __future__ import annotations

from api.services.research.parse_log import parse_log, promotion_bar
from api.services.research.parse_registry import (
    next_trial_alpha,
    parse_alpha_plan,
    parse_baseline,
    parse_trial_budget,
    parse_trials,
)
from api.services.research.queue import check_rate, parse_item
from tests.research import fixtures as fx


def test_log_counts_looks_and_bar() -> None:
    log = parse_log(fx.LOG)
    assert [e["n"] for e in log["entries"]] == [1, 2]
    assert log["looks"] == 30
    assert log["bar"] == promotion_bar(30)
    assert log["entries"][1]["idea"] == "Beta idea"  # bold marks removed
    assert log["lessons"] == ["Count every look.", "Split by information known at entry only."]


def test_promotion_bar_matches_formula() -> None:
    assert promotion_bar(110) == 3.07
    assert promotion_bar(1) == 0.0


def test_trials_prefer_notes_excess_and_read_alpha() -> None:
    first, second = parse_trials(fx.TRIALS)
    assert first["excess_pts"] == 5.0 and first["alpha"] == 0.02 and first["z_decision"] == 2.5
    assert parse_trials(fx.TRIALS)[1]["z_decision"] is None
    assert second["excess_pts"] == 4.9 and second["alpha"] == 0.0075
    assert second["n_trades"] == 300 and second["hit_rate"] == 0.70


def test_baseline_cards_and_next_alpha() -> None:
    base = parse_baseline(fx.BASELINE)
    stage1, stage2 = base["stages"]
    assert stage1["label"] == "Stage 1: Eval"
    assert stage1["planning_value"] == "+5"
    assert stage1["edges"] == [{"period": "in sample 2018-2022", "value": "+4.6"}]
    assert stage2["edges"] == [] and stage2["fires_on"] is None
    assert base["mechanism"] == "One mechanism, wrapped over lines."
    assert next_trial_alpha(base["budget_text"]) == (3, 0.015)
    assert next_trial_alpha("nothing here") is None


def test_alpha_plan_states_follow_trial_verdicts() -> None:
    total, rows = parse_alpha_plan(fx.ROUND2, parse_trials(fx.TRIALS))
    assert total == 0.05
    assert [(r["trial"], r["state"]) for r in rows] == [(1, "passed"), (2, "failed"), (3, "open"), (10, "open")]
    assert parse_trial_budget(fx.HYPOTHESES) == 10
    assert parse_trial_budget("") == 10


def test_queue_item_front_matter_and_body_with_dashes() -> None:
    text = '---\nid: "q-1"\nkind: "idea"\ntitle: "T"\nstatus: "queued"\n---\nBody\n---\nmore\n'
    item = parse_item(text)
    assert item is not None and item["body"] == "Body\n---\nmore"
    assert parse_item("no front matter") is None
    assert parse_item("---\nid: 1\n---\nx") is None  # missing required keys


def test_rate_limit_allows_twenty_per_hour() -> None:
    assert all(check_rate("rate-user", now=float(i)) for i in range(20))
    assert check_rate("rate-user", now=21.0) is False
    assert check_rate("rate-user", now=4000.0) is True
