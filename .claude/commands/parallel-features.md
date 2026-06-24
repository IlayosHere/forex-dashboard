You are orchestrating parallel feature development. You take several feature
descriptions and fan them out to isolated background sub-agents, each on its own git
branch in its own worktree, so multiple features progress concurrently without
touching each other's files or the current conversation's working tree.

## Context

- Each feature runs in its own sub-agent via the `Agent` tool with
  `isolation: "worktree"` (new branch + new checkout under `.claude/worktrees/`,
  fresh from `origin/main` — see `.claude/settings.json` `worktree.baseRef`) and
  `run_in_background: true`.
- All agents are spawned **in a single message** (N parallel `Agent` tool calls in
  one assistant turn) — this is what makes them concurrent. Never spawn one, wait,
  then spawn the next.
- The current working tree (whatever branch it's on, including uncommitted changes)
  is never touched — worktree isolation guarantees a separate checkout. Hard safety
  property, not optional.
- Execution agents run on `model: "sonnet"` per the CLAUDE.md model-routing rule
  (these are implementation agents, not planning/architecture agents).
- Sub-agents commit their work but **never push and never open a PR**. Integration
  into `main` is manual and sequential — see below.

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
   matching `.claude/agents/*.md` file as `subagent_type` — **not the filename**:

   | Keywords in description | `subagent_type` |
   |---|---|
   | api, endpoint, route, backend, pydantic, sqlalchemy, fastapi, scanner, strategy | `Python FastAPI Engineer` |
   | ui, component, page, frontend, button, layout, card, form, chart, dashboard | `Rapid Prototyper` |
   | accessibility, responsive, performance, pixel, styling polish | `Frontend Developer` |
   | schema, migration, index, query performance, db, table, column | `Database Optimizer` |
   | docker, deploy, cloud run, nginx, infra, ci, secret, env | `DevOps Automator` |
   | ambiguous / mixed / none of the above | `general-purpose` |

3. Spawn ALL agents in ONE message: one `Agent` tool call per feature, each with
   `subagent_type`, `model` (default `"sonnet"`), `isolation: "worktree"`,
   `run_in_background: true`, and the prompt template from step 4.

4. Per-agent prompt template — self-contained, the sub-agent has no memory of this
   conversation:

   ```
   You are implementing ONE feature in an isolated git worktree on branch <branch>.

   Required reading FIRST, in this order:
   1. CLAUDE.md
   2. docs/coding-standards.md

   Feature to implement:
   <full feature description>

   Rules:
   - Implement ONLY this feature. Do not refactor unrelated code.
   - Follow docs/coding-standards.md exactly (file/function size limits, naming,
     import order, type safety). Non-compliant code must be fixed before you finish.
   - Run and pass relevant tests before committing:
       * Backend changes: python -m pytest tests/ -v --tb=short
       * Frontend changes (anything under ui/): cd ui && npx vitest run
     If you added backend behavior, add tests following tests/conftest.py patterns.
   - When tests pass, stage and commit on THIS branch only:
       git add -A && git commit -m "<conventional, descriptive message>"
   - Git safety (MANDATORY, from CLAUDE.md):
       * Do NOT push. Do NOT open a PR. Do NOT amend existing commits (new commits only).
       * Do NOT checkout, create, or touch any other branch.
       * Do NOT run destructive git ops (no reset --hard, no force, no rebase onto
         other branches).
   - Production safety: do NOT add ALTER TABLE to api/startup/migrations.py, do NOT
     run any /prod-* or deploy commands, do NOT touch Terraform or Cloud SQL.

   Final message: report what you implemented, files changed, test pass counts, and
   the exact commit SHA + branch name. State clearly if you committed nothing.
   ```

5. Immediately after spawning, print a tracking table:

   | # | Feature | Branch | Persona | Model | Status |
   |---|---|---|---|---|---|
   | 1 | … | feat/… | Python FastAPI Engineer | sonnet | running (background) |

   Tell the user results arrive asynchronously as each background agent finishes —
   do not block waiting for all of them.

6. As each background agent completes, report that one row: update status to
   `done` / `done (no changes)` / `failed`, with the worktree path, branch, and
   commit SHA from its result.

7. Never auto-remove worktrees and never auto-merge branches. Agents that made no
   changes are auto-cleaned by the harness; agents that committed leave their
   worktree in place for manual review (next section).

## How the user reviews and integrates

- List everything: `git worktree list` and `git branch --list 'feat/*'`.
- Review one feature: `git log origin/main..<branch> --stat` and
  `git diff origin/main..<branch>`.
- Integrate **sequentially, one branch at a time**, running tests after each:
  ```
  git checkout main && git merge <branch-1>
  python -m pytest tests/ -v && (cd ui && npx vitest run)
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
- Use `model: "opus"` for these execution agents unless a feature is explicitly a
  design/architecture task.
- Instruct any agent to push, open a PR, amend, or touch another branch.
- Auto-remove worktrees or auto-merge branches — review is always manual.
- Override `isolation` away from `"worktree"`.
- Set up cron/loop/CI/daemon infrastructure — this is a single-turn fan-out, nothing
  persistent.
- Use agent filenames as `subagent_type` — use the frontmatter `name:` strings.

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
