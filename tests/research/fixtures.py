"""
tests/research/fixtures.py
--------------------------
Synthetic prop-pipeline files with the same shape as the real ones. No real
research content lives in this public repo.
"""
from __future__ import annotations

from pathlib import Path

LOG = """# Exploration log (synthetic)

| # | Date | Idea | What was looked at | Variants | Result |
| --- | --- | --- | --- | --- | --- |
| 1 | 2026-01-02 | Alpha idea | Market X, 3 thresholds | 10 | Nothing. |
| 2 | 2026-01-05 | **Beta idea** | Market X and Y | 20 | **Promoted** at z 3.2. |

## Idea index (synthetic)

| Idea | Rule in one line | Verdict | Where |
| --- | --- | --- | --- |
| Alpha idea | Do a thing | Killed (nothing) | LOG 1 |

Lessons that apply to every new idea:
- Count every look.
- Split by information known at entry only.
"""

IDEAS = """schema_version: 1
ideas:
  - id: "ALPHA"
    log_name: "Alpha idea"
    name: "Alpha"
    stage: "3"
    status: "killed"
    rule: "Do a thing"
    plain: "Nothing there."
    report: "results/exploration/agents/x.md"
    log: [1]
    trials: []
    results: []
  - id: "BETA"
    name: "Beta"
    stage: "1,2"
    status: "candidate"
    rule: "Do another thing"
    plain: "Looks promising."
    report: "results/exploration/agents/x.md"
    log: [2]
    trials: [1]
    results: [{label: "Exploration", market: "X", n: 100, hit: 70.0, control: 65.0, excess: 5.0, z: 3.2}]
"""

JOURNEY = """entries:
  - date: 2026-01-01
    decision: "Start the project"
    why: "Because"
  - date: 2026-01-06
    decision: "Lock the baseline"
    why: "It passed"
"""

TRIALS = """timestamp_utc,trial_no,hypothesis_id,period,git_commit,hypotheses_sha256,params,n_trades,hit_rate,control_hit_rate,z_vs_breakeven,z_vs_control,mean_pts_vs_control,verdict,notes
2026-01-03T10:00:00+00:00,1,BETA,in_sample,abc,def,p,200,0.65,0.60,1.0,2.5,5.0,PASS,"alpha 0.02; z_decision +2.5"
2026-01-04T10:00:00+00:00,2,GAMMA,confirm_2018_2026,abc,def,p,300,0.70,0.65,,3.0,,FAIL,"alpha 0.0075; excess +0.0488"
"""

BASELINE = """baseline_version: 1
adopted_on: 2026-01-06
mechanism: "One mechanism,
  wrapped over lines."
stages:
  stage_1_eval:
    strategy: BETA
    rule: "Beta rule"
    fires_on: "about 24% of sessions"
    edge_vs_random: {in_sample_2018_2022: "+4.6", planning_value: "+5"}
  stage_2_buffer:
    strategy: BETA
    rule: "Same signal"
pipeline_value: "Pays $400 per eval."
challenger_rules:
  principle: "Add value on top of the baseline."
  budget: "Trials 3-10 remain. Trial 3 may use alpha 0.015."
funded_phase_rules:
  payout_policy: "Max as soon as eligible"
"""

ROUND2 = """alpha_plan:
  project_total: 0.05
  allocations: {trial_10: 0.0075, trial_1: 0.02, trial_2: 0.0075, trial_3: 0.0075}
"""

HYPOTHESES = "registry_version: 1\ntrial_budget_total: 10\n"

FILES = {
    "results/exploration/LOG.md": LOG,
    "results/exploration/ideas.yaml": IDEAS,
    "results/journey.yaml": JOURNEY,
    "registry/trial_log.csv": TRIALS,
    "registry/baseline_v1.yaml": BASELINE,
    "registry/round2.yaml": ROUND2,
    "registry/hypotheses.yaml": HYPOTHESES,
    "results/exploration/agents/x.md": "# Report\n\nBody.\n",
}


def write_repo(root: Path, skip: set[str] | None = None) -> Path:
    """Write the synthetic repo under root, leaving out any paths in skip."""
    for path, text in FILES.items():
        if skip and path in skip:
            continue
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return root
