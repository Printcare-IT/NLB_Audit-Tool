# Module integration contract

How a workflow platform runs this audit tool. The machine-readable version
is [module.json](module.json); the agent instructions are [CLAUDE.md](CLAUDE.md).

## Install

```
pip install -r requirements.txt
```

Python 3.9 or later. LibreOffice only if a specification arrives as a legacy
`.doc` (it is found on `PATH` or at the default Windows install location).
No network access, database or service is used. Everything is files.

## Invocation

```
python audit_tool.py <command> --job <job> [--layout <file>] [--out <folder>] --json
```

- Working directory: the repository root.
- `<job>` is a folder name under `jobs/` (`2026.Sep.NLB.4G`) or a path to a job
  folder anywhere.
- With `--json`, progress logs go to **stderr** and exactly one JSON object
  goes to **stdout** when the command ends. Without it, everything goes to stdout.
- `--layout` is optional. If it is missing, the tool looks for `*LAYOUT*.TXT` in
  `jobs/<job>/inputs/`, then in `jobs/<job>/`, then in the folder named by
  `AUDIT_LAYOUTS_DIR`. In that shared folder a file is used only when it is
  the single match (filtered by the job's first game number once
  `job_config.json` exists). The tool never guesses between several files.

## Commands

| Command | Does | Writes | Duration |
|---|---|---|---|
| `status` | Reports the job's stage and next action | nothing | instant |
| `new` | Creates `jobs/<job>/inputs/` and `out/` | folders | instant |
| `probe` | Measures the layout file | `measured_facts.json` | minutes |
| `draft` | Drafts the specification from documents + measurements (runs `probe` if needed) | `spec.md`, or `spec.draft.md` if `spec.md` exists | seconds to minutes |
| `build` | Reviewed `spec.md` → settings, through the review and validation gates | `job_config.json` | seconds |
| `verify` | Compares the settings against the layout file | nothing | minutes |
| `audit` | Runs the 15 checks per game | `out/*` | minutes |
| `run` | `build` → `verify` → `audit`, stopping at the first failure | as above | minutes |
| `test` | Regression suite (`--layouts <folder>` adds golden jobs) | nothing | seconds / minutes |

`run --force-audit` carries on to the audit when `verify` disagrees. Use it
only when every disagreement is a ticked **LAYOUT** review item: the spec
deliberately differs from the file, and the audit reports it.

## Exit codes

| Code | Meaning | Platform should |
|---|---|---|
| 0 | Succeeded; for `audit`/`run`, every check passed | advance the workflow |
| 1 | Refused or failed (gate, missing file, engine error) | show the stderr log; do not auto-retry |
| 2 | Audit completed with exceptions in the layout file | show the report; route to the auditor. Not a tool failure |
| 3 | Waiting on a person: unticked review items in `spec.md` | pause the workflow; assign the review task |

## Stages (`status`)

| `stage` | Meaning | Next |
|---|---|---|
| `missing` | No job folder | `new` |
| `needs_inputs` | No `.pdf/.docx/.doc` in `inputs/` | upload documents |
| `needs_layout` | No layout file found | upload / point at the layout file |
| `needs_draft` | Inputs present, no `spec.md` | `draft` |
| `needs_review` | `spec.md` has unticked review items (exit 3) | **human**: review `spec.md` |
| `spec_unreadable` | An anchored table in `spec.md` cannot be parsed | fix the table (`error` field says which) |
| `needs_build` | `job_config.json` missing or differs from `spec.md` | `build` |
| `ready_to_audit` | Settings current, no audit since they changed | `run` |
| `audited` | `out/audit_summary.json` newer than the settings (exit 2 if exceptions) | **human**: sign off |
| `legacy` | Archived job from before the engine | none |

`pending_redraft` appears beside any stage when a `spec.draft.md` is newer
than `spec.md`. Someone re-drafted, and the differences have to be merged by
hand.

## JSON results

Every result carries `command`, `job` and `exit_code`. In addition:

**status**
```json
{"stage": "needs_review", "next": "a person resolves and ticks every review item in spec.md",
 "path": "...", "layout": "...\\inputs\\0348-...-LAYOUT.TXT", "inputs": ["300-0348 HINA MAL.docx", "..."],
 "review_items": ["- [ ] **R1 · 0349 · LAYOUT** - prize count for Rs.500 is 59,999 in the file, 60,000 in the spec"]}
```
`audited` adds `all_passed` and `exceptions`. `needs_build` adds `reason`.
`spec_unreadable` adds `error`.

**audit / run** (on completion: the contents of `out/audit_summary.json`)
```json
{"job_id": "2026.Sep.NLB.4G", "layout_file": "0351-0352-0353-0114-LAYOUT.TXT",
 "all_passed": false, "exceptions": 1, "out": "...\\out",
 "load": {"rows": 600000, "live_tickets": 2400000, "void_tickets": 0,
          "malformed_serials": 0, "duplicate_serials": 0, "bad_field_count_rows": 0},
 "games": [{"key": "0351", "name": "CAR RACE", "passed": false,
            "checks": [{"index": 1, "title": "...", "passed": true, "offenders": 0}, "..."]}],
 "files": ["audit_report.md", "audit_report.docx", "game0351_check12_offenders.csv"]}
```
`run` that stops early returns `stopped_at` (`build` or `verify`) instead.

**verify** `{"layout": "...", "settings_match_data": true}` ·
**build** `{"config": ".../job_config.json"}` · **test** `{"passed": true}`

## Human gates

The module never passes these by itself, and neither should the platform's
agent:

1. **Specification review** (`needs_review`). An auditor resolves each review
   item in `jobs/<job>/spec.md` and ticks it. Claude can prepare the evidence
   and propose corrections (see [docs/spec-review.md](docs/spec-review.md)).
2. **Sign-off** (`audited`). An auditor reads `out/audit_report.md`, then
   records the job as a regression baseline:
   `python tests/run_regression.py --record --layouts <folder> --job <job>`.

## Files the platform handles

| Direction | Files |
|---|---|
| In | Game specs + data spec → `jobs/<job>/inputs/`. Layout file → `inputs/` or `AUDIT_LAYOUTS_DIR` |
| Human-edited | `jobs/<job>/spec.md` (the record; keep under version control) |
| Out | `out/audit_report.docx` (deliverable), `out/audit_report.md`, `out/audit_summary.json`, `out/*_offenders.csv` |

Layout files are 100-230 MB. They are git-ignored and must not be committed.
Offender CSVs are git-ignored as well; archive them with the job if needed.

## Concurrency

Jobs are independent folders, so different jobs can run in parallel. Run one
command at a time **per job**: `draft`, `build` and `audit` write into the
job folder. An audit loads every ticket of the layout file into memory at
once, so size the worker's RAM for the largest layout files you expect.
