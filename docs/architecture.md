# Architecture

Read this before changing any code. For running jobs, see
[workflow.md](workflow.md). For the settings format and the checks, see
[README.md](../README.md).

## Data flow

```
 client documents              layout file (*LAYOUT*.TXT, 45-230 MB)
 (game specs, data spec)            │                    │
        │                           │                    │
        │                    probe_layout.py              │
        │                           │                    │
        │                  measured_facts.json            │
        │                           │                    │
        └──────────► draft_spec.py ◄┘                    │
                           │                              │
                        spec.md  ◄── person reviews       │
                           │         and ticks items      │
                    build_config.py                       │
                    (review gate, validation gate)        │
                           │                              │
                    job_config.json ──────┬───────────────┤
                                          │               │
                           probe_layout.py --config   audit_engine.py
                           (verify: settings vs data)     │
                                                    out/audit_report.md/.docx
                                                    out/audit_summary.json
                                                    out/*_offenders.csv
```

Each artifact is derived only from the ones before it. **`spec.md` is the
only file a person edits.** Everything below it is regenerated, never edited
by hand. `audit_tool.py` sits on top and runs these scripts. It contains no
checking logic.

## Modules and allowed imports

| Module | Role | Imports from the engine |
|---|---|---|
| `doc_text.py` | `.pdf`/`.docx`/`.doc` → plain text, then `flatten()` to one normalised form | nothing |
| `spec_parse.py` | Reads facts out of flattened document text (game spec, data spec, restrictions, win rule) | nothing |
| `validate_config.py` | Pure arithmetic checks on a settings dict; holds `WIN_RULES`, `GROUP_MODES` | nothing |
| `spec_md.py` | Writes (`render`) **and** reads (`parse`) the `spec.md` format | `validate_config` |
| `draft_spec.py` | Cross-checks documents against measurements, turns disagreements into review items, renders `spec.md` | `doc_text`, `spec_parse`, `spec_md`, `validate_config` |
| `build_config.py` | `spec.md` → `job_config.json` behind the two gates | `spec_md`, `validate_config` |
| `probe_layout.py` | Measures a layout file with no settings; with `--config`, compares | **nothing, by design** |
| `audit_engine.py` | The 15 checks, the reports | `validate_config` |
| `audit_tool.py` | Entry point: stages, layout discovery, exit codes, JSON | runs scripts as subprocesses; imports `spec_md` for `status` |

The direction is one way: document reading → drafting → building. The audit
engine never imports the drafting side, so the audit cannot be affected by
how the documents were read.

## Design rules - do not break these

1. **The probe is independent of the audit engine.** `probe_layout.py` shares
   no code with `audit_engine.py`: it has its own file parser, prize counting
   and win-rule inference. When the two agree, that agreement is evidence.
   Do not "deduplicate" them into a shared module, even though the code looks
   repetitive.
2. **`spec.md` is written and read by the same module.** `spec_md.render` and
   `spec_md.parse` must stay inverse to each other. Change one, change the
   other. The round-trip tests in `test_pipeline.py` enforce it.
3. **Machine-read tables are found by anchor and column heading.**
   `<!-- table:<name> [game=<key>] -->` plus the heading row. Renaming a
   heading in `render` breaks every existing job's `spec.md`. Treat headings as
   a file format: add columns, do not rename them.
4. **Nothing is guessed silently.** A parser that cannot read a value
   returns a problem, and the drafter turns it into a review item. Do not add
   defaults that hide an unreadable value.
5. **The engine is job-agnostic.** No game number, client name or amount is
   hard-coded in `engine/`. If a job seems to need a special case, express it
   in settings: a new group-promise mode, a new win rule, a new table column.
6. **The validator runs before every build and every audit.** Any new setting
   must be checked there (types, references, arithmetic) so a bad setting
   fails in seconds, not after a multi-minute audit.
7. **Checks report offenders, not just pass/fail.** Each check appends the
   offending items to its `CheckResult`. They become the offender CSV the
   auditor works from.

## Where each kind of change goes

| Change | Edit | Test |
|---|---|---|
| **New winning rule** | `audit_engine.should_win()`; `validate_config.WIN_RULES`; `spec_md.WIN_RULE_TEXT`; `spec_parse.read_win_rule()` so the drafter recognises its wording; `probe_layout.py` win-rule inference (otherwise `verify` reports a disagreement on every job that uses it) | A clean fixture game with the rule, plus one injected-defect test in `test_audit_checks.py`; a parser test in `test_pipeline.py` |
| **New group-promise mode** | `validate_config.GROUP_MODES` and its achievability check; `audit_engine.check_09_group_rules`; `spec_md.MODE_TEXT`; `spec_parse.parse_restrictions()` for the wording | Injected-defect test (check 9); validator test for an impossible promise; restriction-wording parser test |
| **New restriction wording** (same meaning, different phrasing) | `spec_parse.parse_restrictions()` only | Parser test with the exact sentence from the client's document |
| **New document template** (new client, different layout of the game spec) | `spec_parse.py`: `classify()` today only tells a game spec from a data spec by NLB wording. Extend it to recognise the new template, and add a separate parser for it rather than loosening the NLB patterns. `draft_spec.build()` then calls the right parser. `doc_text.py` only if a new file type is involved | Parser tests on flattened text from the new template; golden drafter check once a job is recorded |
| **New audit check** | `audit_engine.py`: a `check_16_...` function returning a `CheckResult`, added to `run_all_checks()`; any new setting in the validator and `spec_md` | Clean job still passes (`test_00_...`); one injected defect makes *exactly* the new check fail |
| **New layout file shape** (different block, extra fields) | Settings first (`layout` table offsets). Only if settings cannot express it: `audit_engine.load_layout()` **and**, independently, `probe_layout.sniff_structure()` | Fixture layout in the new shape through both |
| **New setting / `spec.md` column** | `spec_md.render` + `spec_md.parse` (rule 2), `validate_config`, the consumer | Round-trip test; validator test |
| **Platform interface** (stages, exit codes, JSON) | `audit_tool.py`; update `MODULE.md` and `module.json` together | `tests/test_module.py` |

## Tests

| File | Covers |
|---|---|
| `tests/fixtures.py` | Builds a small synthetic two-game job that passes every rule, writes its layout file and fake specification text |
| `tests/test_audit_checks.py` | Every check: one injected defect → exactly the expected checks fail |
| `tests/test_pipeline.py` | Validator, parsers, `spec.md` round trip, drafter cross-checks, build gates |
| `tests/test_module.py` | `audit_tool.py` stages, gates and exit codes on a real job folder |
| `tests/run_regression.py` | Runs all of the above, then golden results of recorded real jobs (`tests/golden/`) |

Run `python audit_tool.py test` after every change, and
`python audit_tool.py test --layouts <folder>` before a release. A change that
alters a golden job's offender counts is a change in audit results. The
auditor has to accept it before anyone re-records.

## Performance

A layout file is read line by line. The audit keeps every ticket's fields in
per-game lists in memory, then runs the checks over them. A 45 MB file
(500,000 tickets) takes about 30 seconds for verify plus audit; the largest
files are around five times that. The probe makes its own full pass, so
`run` reads the file twice. That is intended (rule 1).
