"""
api/services/research/overview.py
---------------------------------
Assemble the Research page payload from the prop-pipeline files. Every section is
read on its own: if one file is missing or malformed the rest still render and the
problem is reported in `warnings`.
"""
from __future__ import annotations

import logging
import re
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, TypeVar

import yaml

from api.services.research.parse_log import parse_log
from api.services.research.parse_registry import (
    next_trial_alpha,
    parse_alpha_plan,
    parse_baseline,
    parse_trial_budget,
    parse_trials,
)
from api.services.research.queue import list_items
from api.services.research.source import Source, SourceError

logger = logging.getLogger(__name__)

T = TypeVar("T")
PATHS = {
    "log": "results/exploration/LOG.md",
    "ideas": "results/exploration/ideas.yaml",
    "journey": "results/journey.yaml",
    "trials": "registry/trial_log.csv",
    "baseline": "registry/baseline_v1.yaml",
    "round2": "registry/round2.yaml",
    "hypotheses": "registry/hypotheses.yaml",
}
_READ_ERRORS = (SourceError, yaml.YAMLError, KeyError, ValueError, TypeError, AttributeError)
_PERIOD_WORDS = {"in_sample": "in-sample", "out_of_sample": "out of sample",
                 "fresh_2010_2017": "fresh data 2010-2017", "confirm_2018_2026": "confirmation 2018-2026"}


def _safe(name: str, load: Callable[[], T], default: T, warnings: list[str]) -> T:
    """Run one section loader; on a read or parse problem keep the default and warn."""
    try:
        return load()
    except _READ_ERRORS as exc:
        logger.warning("Research section %s failed: %s", name, exc)
        warnings.append(f"{name}: {exc}")
        return default


def _journey(decisions: list[dict], trials: list[dict], entries: list[dict]) -> list[dict[str, str]]:
    """Decisions, trials and looks on one timeline, newest first."""
    items = [{"date": str(d["date"]), "kind": "decision", "title": d["decision"], "detail": d["why"]}
             for d in decisions]
    for t in trials:
        period = _PERIOD_WORDS.get(t["period"], t["period"])
        bits = [f"{t['n_trades']} trades"] if t["n_trades"] else []
        if t["excess_pts"] is not None:
            bits.append(f"{t['excess_pts']:+.1f} points over control")
        z = t["z_decision"] if t["z_decision"] is not None else t["z_vs_control"]
        if z is not None:
            bits.append(f"z {z:.2f}")
        outcome = {"PASS": "passed", "FAIL": "failed"}.get(t["verdict"], t["verdict"])
        items.append({"date": t["when"], "kind": "trial", "detail": ", ".join(bits),
                      "title": f"Trial {t['trial_no']} {outcome}: {t['hypothesis_id']}, {period}"})
    items += [{"date": e["date"], "kind": "exploration", "title": f"Look {e['n']}: {e['idea']}",
               "detail": e["result"]} for e in entries]
    return list(reversed(sorted(items, key=lambda i: i["date"])))


def _status(log: dict, trials: list[dict], baseline: dict | None, budget: int,
            alpha_total: float | None) -> dict[str, Any]:
    run = max((t["trial_no"] for t in trials), default=0)
    nxt = next_trial_alpha(baseline["budget_text"]) if baseline else None
    return {
        "looks": log["looks"], "promotion_bar": log["bar"], "log_entries": len(log["entries"]),
        "trials_run": run, "trials_budget": budget, "trials_left": max(budget - run, 0),
        "next_trial": run + 1,
        "next_trial_alpha": nxt[1] if nxt and nxt[0] == run + 1 else None,
        "alpha_project_total": alpha_total,
        "pipeline_value": baseline["pipeline_value"] if baseline else None,
    }


def build_overview(source: Source) -> dict[str, Any]:
    """Read every research file and return the page payload (see ResearchOverview)."""
    warnings: list[str] = []
    read = source.read
    empty_log: dict[str, Any] = {"entries": [], "looks": 0, "bar": 0.0, "lessons": []}
    log = _safe("Exploration log", lambda: parse_log(read(PATHS["log"])), empty_log, warnings)
    ideas = _safe("Ideas", lambda: yaml.safe_load(read(PATHS["ideas"]))["ideas"], [], warnings)
    trials = _safe("Trials", lambda: parse_trials(read(PATHS["trials"])), [], warnings)
    baseline = _safe("Baseline", lambda: parse_baseline(read(PATHS["baseline"])), None, warnings)
    decisions = _safe("Journey", lambda: yaml.safe_load(read(PATHS["journey"]))["entries"], [], warnings)
    budget = _safe("Trial budget", lambda: parse_trial_budget(read(PATHS["hypotheses"])), 10, warnings)
    total, plan = _safe("Alpha plan", lambda: parse_alpha_plan(read(PATHS["round2"]), trials), (None, []), warnings)
    queue, queue_warnings = _safe("Queue", lambda: list_items(source), ([], []), warnings)
    return {
        "status": _status(log, trials, baseline, budget, total),
        "baseline": baseline, "ideas": ideas, "trials": trials, "alpha_plan": plan,
        "exploration_log": log["entries"], "lessons": log["lessons"],
        "journey": _journey(decisions, trials, log["entries"]),
        "queue": queue, "warnings": warnings + queue_warnings,
        "source": source.label, "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


def idea_ids(source: Source) -> set[str]:
    """Ids of every tested idea, used to check what a note is about."""
    data = yaml.safe_load(source.read(PATHS["ideas"]))["ideas"]
    return {str(i["id"]) for i in data if re.match(r"^[A-Za-z0-9._-]+$", str(i["id"]))}
