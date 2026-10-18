"""
api/services/research/parse_registry.py
---------------------------------------
Parse the prop-pipeline registry files: trial log (CSV), baseline and alpha plan (YAML).
"""
from __future__ import annotations

import csv
import io
import re
from typing import Any

import yaml

STAGE_LABELS = {
    "stage_1_eval": "Stage 1: Eval",
    "stage_2_buffer": "Stage 2: Buffer",
    "stage_3_green_days": "Stage 3: Green days",
}
_NOTE_ALPHA = re.compile(r"alpha ([0-9]*\.?[0-9]+)")
_NOTE_ZDEC = re.compile(r"z_decision ([+-]?[0-9]*\.?[0-9]+)")
_NOTE_EXCESS = re.compile(r"excess ([+-]?[0-9]*\.?[0-9]+)")
_NEXT_ALPHA = re.compile(r"trial (\d+) may use alpha ([0-9]*\.?[0-9]+)", re.IGNORECASE)
_BUDGET = re.compile(r"trial_budget_total:\s*(\d+)")


def _num(value: str | None) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except ValueError:
        return None


def _excess_points(row: dict[str, str]) -> float | None:
    """Hit-rate points over the control: from the notes when given, else the logged column."""
    match = _NOTE_EXCESS.search(row.get("notes", ""))
    if match:
        return round(float(match.group(1)) * 100, 1)
    return _num(row.get("mean_pts_vs_control"))


def parse_trials(text: str) -> list[dict[str, Any]]:
    """One dict per row of registry/trial_log.csv, oldest first."""
    out = []
    for row in csv.DictReader(io.StringIO(text)):
        n = _num(row.get("n_trades"))
        alpha = _NOTE_ALPHA.search(row.get("notes", ""))
        zdec = _NOTE_ZDEC.search(row.get("notes", ""))
        out.append({
            "trial_no": int(row["trial_no"]),
            "hypothesis_id": row["hypothesis_id"],
            "period": row["period"],
            "when": row["timestamp_utc"][:10],
            "n_trades": int(n) if n is not None else None,
            "hit_rate": _num(row.get("hit_rate")),
            "control_hit_rate": _num(row.get("control_hit_rate")),
            "z_vs_control": _num(row.get("z_vs_control")),
            "z_decision": float(zdec.group(1)) if zdec else None,
            "excess_pts": _excess_points(row),
            "verdict": row["verdict"],
            "alpha": float(alpha.group(1)) if alpha else None,
            "notes": row.get("notes", ""),
        })
    return out


def _pretty(key: str) -> str:
    """in_sample_2018_2022 -> in sample 2018-2022."""
    return re.sub(r"(\d{4}) (\d{4})", r"\1-\2", key.replace("_", " "))


def _stage_card(key: str, stage: dict[str, Any]) -> dict[str, Any]:
    edges = dict(stage.get("edge_vs_random") or {})
    planning = edges.pop("planning_value", None)
    return {
        "key": key,
        "label": STAGE_LABELS.get(key, _pretty(key).title()),
        "strategy": str(stage.get("strategy", "")),
        "rule": str(stage.get("rule", "")),
        "fires_on": stage.get("fires_on"),
        "edges": [{"period": _pretty(k), "value": str(v)} for k, v in edges.items()],
        "planning_value": str(planning) if planning is not None else None,
    }


def _notes(block: dict[str, Any] | None) -> list[dict[str, str]]:
    return [{"label": _pretty(k).capitalize(), "text": str(v)} for k, v in (block or {}).items()]


def parse_baseline(text: str) -> dict[str, Any]:
    """Baseline v1 as cards per stage plus the funded-phase and challenger rules."""
    data = yaml.safe_load(text)
    return {
        "version": int(data["baseline_version"]),
        "adopted_on": str(data["adopted_on"]),
        "mechanism": " ".join(str(data.get("mechanism", "")).split()),
        "stages": [_stage_card(k, v) for k, v in data["stages"].items()],
        "funded_rules": _notes(data.get("funded_phase_rules")),
        "challenger_rules": _notes(data.get("challenger_rules")),
        "pipeline_value": " ".join(str(data.get("pipeline_value", "")).split()) or None,
        "budget_text": str((data.get("challenger_rules") or {}).get("budget", "")),
    }


def next_trial_alpha(budget_text: str) -> tuple[int, float] | None:
    """Pick 'trial 8 may use alpha 0.015' out of the baseline's budget sentence."""
    match = _NEXT_ALPHA.search(budget_text)
    return (int(match.group(1)), float(match.group(2))) if match else None


def parse_trial_budget(hypotheses_text: str) -> int:
    """Total trial budget (10) from hypotheses.yaml, without parsing the whole file."""
    match = _BUDGET.search(hypotheses_text)
    return int(match.group(1)) if match else 10


def parse_alpha_plan(round2_text: str, trials: list[dict[str, Any]]) -> tuple[float | None, list[dict[str, Any]]]:
    """Project alpha total and one row per planned trial with its state."""
    plan = yaml.safe_load(round2_text).get("alpha_plan", {})
    verdicts = {t["trial_no"]: t["verdict"] for t in trials}
    rows = []
    for key, alpha in sorted((plan.get("allocations") or {}).items(), key=lambda kv: int(kv[0].split("_")[1])):
        number = int(key.split("_")[1])
        verdict = verdicts.get(number)
        state = "passed" if verdict == "PASS" else "failed" if verdict == "FAIL" else "open"
        rows.append({"trial": number, "alpha": float(alpha), "state": state})
    total = plan.get("project_total")
    return (float(total) if total is not None else None), rows
