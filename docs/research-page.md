# Research page

`/research` shows the prop-pipeline research in plain language: the baseline strategies, every idea
tested with its verdict, the trials and alpha budget, the project journey, and a queue where the owner
adds ideas and notes for the next round.

Nothing is copied by hand. The API reads these files from the private `prop-pipeline` repo each time
(cached for about a minute), so the page stays current by itself.

| Page section | File in prop-pipeline |
|---|---|
| Baseline and confirmed edges | `registry/baseline_v1.yaml` |
| Ideas board | `results/exploration/ideas.yaml` |
| Looks and the promotion bar | the numbered table in `results/exploration/LOG.md` |
| Trials | `registry/trial_log.csv` |
| Alpha budget | `registry/round2.yaml`, `registry/hypotheses.yaml` |
| Journey | `results/journey.yaml` plus the trial log and `LOG.md` |
| Reports (side panel) | `results/**/*.md`, `research/cards/*.md` |
| Your ideas | `results/exploration/queue/*.md` (written by the page) |

If a file is missing or malformed the rest of the page still renders and a banner names the file.
`python scripts/research/check_index.py` in prop-pipeline checks that these files agree.

## Code

- `api/routes/research.py`, `api/schemas_research.py`
- `api/services/research/` (`source.py` reads GitHub or a local folder, `parse_*.py`, `overview.py`, `queue.py`, `reports.py`)
- `ui/app/research/page.tsx`, `ui/components/research/`, `ui/lib/research*.ts`, `ui/lib/useResearch.ts`
- tests: `tests/research/` (synthetic fixtures, no real research content) and `ui/tests/research/`

The repo is public, so no research text or token is ever stored here.

## Safety of the queue

The page can write exactly one kind of thing: a new file under `results/exploration/queue/`. The file name
is generated on the server, an existing file is never overwritten, titles are JSON-quoted into the front
matter, notes must point at a known idea id, and each user can add at most 20 items an hour. Reports are
only readable from the report folders (the path is matched against a fixed pattern).

## Setup

Local development (no GitHub needed):

    PROP_PIPELINE_LOCAL_DIR=~/Documents/prop-pipeline

Production (Cloud Run):

1. Create a fine-grained GitHub token: Settings, Developer settings, Fine-grained tokens. Resource owner:
   your account. Repository access: only `prop-pipeline`. Permissions: Contents, read and write
   (read-only works for browsing; adding ideas then fails with a clear error).
2. `terraform apply` creates the `prop_pipeline_github_token` secret with a placeholder first version and
   passes it to the API as `PROP_PIPELINE_GITHUB_TOKEN`. The API starts fine before the real token exists;
   the Research page shows a GitHub 401 error until it does.
3. Add the real token as a new version:
   `gcloud secrets versions add prop_pipeline_github_token --data-file=<(printf '%s' "$TOKEN")`
4. Deploy a new API revision (any push to main) so it picks up `latest`.
