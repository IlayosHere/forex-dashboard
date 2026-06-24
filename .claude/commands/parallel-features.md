You are orchestrating parallel feature development. You take several feature
descriptions, fan the drafting work out to isolated background sub-agents (each in
its own git worktree), then personally finish each one — rename its branch, run its
tests, and commit — once it reports back.

## Context — why this is split into two phases

Background, unattended sub-agents (`run_in_background: true`) cannot run mutating or
process-spawning `Bash` commands — confirmed empirically: `git commit`, `git branch
-m`, `python -m pytest`, `npm install`, `npx vitest` were all denied in background
worktree agents even with blanket `Bash` permission grants and
`dangerouslyDisableSandbox: true`. Only read-only commands (`git status`, `git log`,
`ls`) got through. This is a hard, harness-level safety boundary for agents with no
human present to approve a mutating shell command — **not** something fixable via
`.claude/settings.json` permissions. `Read`/`Edit`/`Write` are NOT affected by this —
background agents can write files freely, just not execute or commit anything.

So the work splits into two phases:

- **Phase 1 (background, parallel)**: each sub-agent only reads and writes files —
  implements the feature and its tests, but never touches git or runs a test runner.
- **Phase 2 (foreground, sequential, you)**: once a sub-agent reports its files are
  written, you — the orchestrator, in this live conversation, where Bash works
  normally — rename its branch, run its tests, and commit if they pass.

Other facts that still hold:
- Each feature still gets `isolation: "worktree"` (new checkout under
  `.claude/worktrees/`, fresh from `origin/main` — see `.claude/settings.json`
  `worktree.baseRef`). The current working tree is never touched.
- `.claude/settings.json` `worktree.symlinkDirectories` symlinks `.venv`,
  `node_modules`, and `ui/node_modules` into every new worktree, so Phase 2 can run
  tests immediately without a fresh `pip`/`npm install`.
- Backend tests need the venv's interpreter explicitly: `.venv/bin/python -m pytest`,
  not bare `python` (the system Python doesn't have fastapi/sqlalchemy/pytest).
- Execution agents run on `model: "sonnet"` per the CLAUDE.md model-routing rule.
- Branches commit but **never push and never open a PR**. Integration into `main` is
  manual and sequential — see below.

## Input format

`$ARGUMENTS` is one feature per line. Blank lines are ignored. Each line may carry
optional overrides after a `|` delimiter:

```
<feature description> [| branch=<name>] [| agent=<persona>] [| model=<sonnet|opus>]
```

- `branch` omitted → slugify the description into `feat/<slug>` (lowercase,
  non-alphanumeric runs collapsed to `-`, trimmed, max ~40 chars).
- `agent` omitted → infer from keywords (table below).
- `model` omitted → `sonnet`.

## What to do

1. Parse `$ARGUMENTS` into a feature list. For each, resolve branch name, persona,
   and model. Print the resolved plan as a table before spawning anything. If a
   description is too ambiguous to infer a persona AND no override was given, ask
   the user once rather than guessing — otherwise proceed without confirmation.

2. Persona inference table. Use the exact frontmatter `name:` string from the
   matching `.claude/agents/*.md` file as `subagent_type` — **not the filename**.
   Plain Python/calculation work with no other signal still counts as backend:

   | Keywords in description | `subagent_type` |
   |---|---|
   | api, endpoint, route, backend, pydantic, sqlalchemy, fastapi, scanner, strategy, utility, calculator, calculation | `Python FastAPI Engineer` |
   | ui, component, page, frontend, button, layout, card, form, chart, dashboard | `Rapid Prototyper` |
   | accessibility, responsive, performance, pixel, styling polish | `Frontend Developer` |
   | schema, migration, index, query performance, db, table, column | `Database Optimizer` |
   | docker, deploy, cloud run, nginx, infra, ci, secret, env | `DevOps Automator` |
   | ambiguous / mixed / none of the above | `general-purpose` |

3. Spawn ALL agents in ONE message: one `Agent` tool call per feature, each with
   `subagent_type`, `model` (default `"sonnet"`), `isolation: "worktree"`,
   `run_in_background: true`, and the Phase 1 prompt template from step 4.

4. Phase 1 prompt template — self-contained, the sub-agent has no memory of this
   conversation, and must NOT touch git or run anything:

   ```
   You are drafting ONE feature's code in an isolated git worktree. Another process
   will handle git and test execution after you're done — your job is ONLY to read
   and write files.

   Required reading FIRST, in this order:
   1. CLAUDE.md
   2. docs/coding-standards.md

   Feature to implement:
   <full feature description>

   Rules:
   - Implement ONLY this feature. Do not refactor unrelated code.
   - Follow docs/coding-standards.md exactly (file/function size limits, naming,
     import order, type safety). Non-compliant code must be fixed before you finish.
   - Write tests for any new behavior, following existing patterns in tests/ or
     ui/tests/components/ as appropriate. You will NOT be able to run them — write
     them as carefully and correctly as you can, by inspection.
   - Do NOT run git (no commit, no branch rename, no add). Do NOT run a test runner,
     a package manager, or any other Bash command that executes/installs/mutates —
     these are blocked in this environment and will just fail. Read-only inspection
     (ls, cat, git status) is fine if genuinely useful, but isn't required.
   - Do NOT push, open a PR, or touch any branch other than the one you're already on.

   Final message must report: (1) every file you created or modified (full paths),
   (2) a short description of what each change does, (3) whether you wrote tests and
   where, (4) anything in these instructions or the codebase that was unclear or
   caused you to guess.
   ```

5. Immediately after spawning, print a tracking table:

   | # | Feature | Branch (target) | Persona | Model | Phase 1 | Phase 2 |
   |---|---|---|---|---|---|---|
   | 1 | … | feat/… | Python FastAPI Engineer | sonnet | running (background) | pending |

   Tell the user results arrive asynchronously as each background agent finishes —
   do not block waiting for all of them.

6. **Phase 2 — when a background agent's notification arrives**, do this yourself,
   in this foreground conversation, for that one worktree (path comes from the
   notification's `worktree` field):

   a. Rename the branch to the intended name:
      `git -C <worktree-path> branch -m <branch>`
   b. Run the relevant tests, from this conversation's own Bash (not the sub-agent's):
      - Backend: `(cd <worktree-path> && .venv/bin/python -m pytest tests/ -v --tb=short)`
      - Frontend: `(cd <worktree-path>/ui && npx vitest run)`
   c. If tests fail: report the failure with output, leave the worktree uncommitted,
      mark Phase 2 as `failed (tests)` in the tracking table. Do not attempt to fix
      it yourself unless the user asks — that's a judgment call, not a mechanical step.
   d. If tests pass: `git -C <worktree-path> add -A && git -C <worktree-path> commit -m "<descriptive message>"`
   e. Update the tracking table row: Phase 2 → `done` (with commit SHA) or
      `failed (tests)` / `failed (no changes)`.

7. Never auto-remove worktrees and never auto-merge branches. Leave finished
   worktrees in place for manual review (next section), whether Phase 2 succeeded
   or not.

## How the user reviews and integrates

- List everything: `git worktree list` and `git branch --list 'feat/*'`.
- Review one feature: `git log origin/main..<branch> --stat` and
  `git diff origin/main..<branch>`.
- Integrate **sequentially, one branch at a time**, running tests after each:
  ```
  git checkout main && git merge <branch-1>
  .venv/bin/python -m pytest tests/ -v && (cd ui && npx vitest run)
  git checkout main && git merge <branch-2>
  ```
- After a branch is merged and confirmed: clean up manually with
  `git worktree remove <path>` and optionally `git branch -d <branch>`.

## Expected risk: cross-feature conflicts

Every branch starts fresh from `origin/main`. If two parallel features edit the same
file (e.g. both touch `ui/lib/types.ts` or `api/main.py` router mounts), the second
merge will conflict. This is expected and is NOT auto-resolved — merge sequentially,
resolve by hand, re-run tests between merges. Scope feature descriptions to disjoint
files where possible to minimize this.

## Do NOT

- Spawn agents one at a time — emit all `Agent` calls in a single message.
- Tell a background (Phase 1) sub-agent to run git, install dependencies, or run a
  test runner — it will be denied and waste the run. Phase 2 (you, foreground) does
  all of that instead.
- Use `model: "opus"` for Phase 1 execution agents unless a feature is explicitly a
  design/architecture task.
- Push, open a PR, amend, or touch another branch — in either phase.
- Auto-remove worktrees or auto-merge branches — review is always manual.
- Override `isolation` away from `"worktree"`.
- Set up cron/loop/CI/daemon infrastructure — this is a single-turn fan-out, nothing
  persistent.
- Use agent filenames as `subagent_type` — use the frontmatter `name:` strings.
- Run backend tests with bare `python` — use `.venv/bin/python` or they'll fail on
  missing imports.

## Example invocations

```
/parallel-features
Add a CSV export button to the trade journal page
Add GET /api/trades/monthly-summary endpoint returning P&L grouped by month | agent=Python FastAPI Engineer
Add a composite index on trades(strategy, status, candle_time) | agent=Database Optimizer | branch=feat/trades-perf-index
```

```
/parallel-features
Add a dark-mode toggle persistence bug fix to the journal filters | branch=fix/filter-persistence
Add equity-curve line chart component to the dashboard
```
