# Scratch Lottery Layout Audit - instructions for Claude

This module audits a scratch-lottery **layout file** (the print data: one row
per print position, one ticket block per channel, millions of tickets) against
the client's **game specifications** and **data generation specification**,
and produces an audit report that a person signs off. Clients so far are NLB
(Sri Lanka); older jobs for Burundi and Panama are kept as archives.

An audit result goes to a lottery client and decides whether tickets are
printed. Treat every number as evidence: report what the tools say, never
round off, soften or "fix" a finding.

## Read first

| File | When |
|---|---|
| [MODULE.md](MODULE.md) | How the platform calls this module: commands, JSON results, exit codes, stages |
| [docs/workflow.md](docs/workflow.md) | What to do at each stage of a job |
| [docs/spec-review.md](docs/spec-review.md) | Helping a person review `spec.md` - the step that needs the most judgement |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Known failure messages and their causes |
| [docs/architecture.md](docs/architecture.md) | **Before changing any code**: data flow, module boundaries, design rules, where each kind of change goes |
| [README.md](README.md) | The engine itself: file formats, settings, checks, tests. Authoritative for engine detail |

Skills for each phase, in `.claude/skills/`: **audit-new-job** (new →
draft), **audit-review-spec** (the review gate), **audit-run** (build →
audit → report).

## Always use the entry point

```
python audit_tool.py status --job <job> --json      # start here, every time
```

`status` says what stage the job is in and what to do next. Drive every step
through `audit_tool.py` (`new`, `probe`, `draft`, `build`, `verify`, `audit`,
`run`, `test`), not the engine scripts directly. It finds the layout file, keeps
the folder layout right and returns a JSON result and an exit code that means
the same thing every time:

| Exit | Meaning | What you do |
|---|---|---|
| 0 | Succeeded. For `audit`/`run`, every check passed | Continue, or report the pass |
| 1 | Refused or failed | Read the log, explain the cause, do not retry blindly |
| 2 | Audit completed **with exceptions** | This is a finding about the client's data, not a tool error. Report it |
| 3 | Waiting on a person: `spec.md` has unticked review items | Stop and hand over to the auditor |

`probe`, `verify`, `audit` and `run` read layout files of 100-230 MB and take
several minutes. Run them in the background and wait. Do not run two on the
same job at once.

## Rules that are never broken

1. **Never edit `engine/` to make a job pass.** A job is described entirely by
   its `spec.md`. The engine changes only when the tool itself needs a new
   capability (a new winning rule, group-promise mode, document template).
   That needs the user's go-ahead, the steps in
   [docs/architecture.md](docs/architecture.md), and a passing
   `python audit_tool.py test` afterwards.
2. **Never edit `job_config.json` by hand.** It is generated from `spec.md` by
   `build`. To change a setting, change the table in `spec.md` and rebuild.
3. **Never tick a review item on your own judgement.** Ticking means the
   auditor has decided. Investigate, quote the documents, propose the table
   correction, and tick only when a person tells you their decision. Then
   record it after the tick, e.g.
   `- [x] **R3 · 0349 · LAYOUT** - ... — confirmed by <name>, <date>: spec is correct`.
4. **LAYOUT items keep the specification's values.** The tables in `spec.md`
   describe what the client *specified*, not what the file contains. Copying
   the file's behaviour into the tables hides the error the audit exists to
   find. Change them only if the client confirms the specification itself is
   wrong, and record who confirmed it.
5. **Never overwrite a reviewed `spec.md`.** A re-draft writes `spec.draft.md`;
   merge from it by hand, with the person.
6. **Never re-record golden results** (`tests/run_regression.py --record`)
   unless the auditor has signed the job off, or has accepted a change in
   results and understands why it happened.
7. **Legacy jobs are read-only.** `status` reports `legacy` for folders that
   came before the engine (one-off `lottery_audit*.py` scripts). Do not
   convert, re-run or tidy them unless asked.
8. **Layout files never go into git** (`*LAYOUT*.TXT`, `*.rar`, offender CSVs
   are ignored; GitHub rejects files over 100 MB). Neither do Office lock files.
9. **Check exceptions are results, not bugs.** If the audit reports exceptions,
   do not look for a way to make them disappear. Report each failed check with
   its offender count and point at `out/game<NNNN>_check<NN>_offenders.csv`.

## A job at a glance

```
jobs/<job>/                       <job> is <year>.<Month>.<Client>.<n>G, e.g. 2026.Sep.NLB.4G
  inputs/                         game specs + data spec (.pdf/.docx/.doc) + *LAYOUT*.TXT
  measured_facts.json             what the layout file contains   (probe)
  spec.md                         THE RECORD - drafted, then reviewed by a person   (draft)
  job_config.json                 generated from spec.md - never edit   (build)
  out/audit_report.md / .docx     the audit report   (audit)
  out/audit_summary.json          machine-readable result
  out/game<NNNN>_check<NN>_offenders.csv   one per failed check
```

The process is: **new → probe → draft → review (person) → build → verify →
audit → sign-off (person)**. `draft` runs `probe` itself when the layout file is
found. `run` does build + verify + audit and stops at the first gate.

## The 15 audit checks

1 play positions · 2 prize box · 3 serial · 4 VIRN / barcode parity ·
5 agent codes · 6 prize structure · 7 GLEPS · 8 packing · 9 group promises ·
10 non-GLEPS prize per book · 11 consecutive play pattern · 12 consecutive
rotation · 13 winner in every N tickets · 14 same-value run · 15 VIRN
independence. Detail in [README.md](README.md) and `engine/audit_engine.py`.

## Vocabulary

| Term | Meaning |
|---|---|
| Layout file | The delivered print data, `*LAYOUT*.TXT`. What is audited |
| Game spec | The client's per-game document. Title line `GAME NO: <n> - "<NAME>" (Rs. <price>)` |
| Data spec | The client's data generation specification covering all games in the job |
| Channel | One ticket column in a layout row. A game may span several channels |
| VIRN | The ticket's validation number. Its barcode carries a parity digit (digit sum mod 10), and it must bear no relation to the play symbols |
| GLEPS | A fixed low prize amount the spec guarantees a set number of times in every book ("GLEPS prize value for each book of N tickets") |
| Book | A pack of consecutive tickets (book size from the spec) |
| Packing | Which prizes go into which books (slot groups) |
| Group promise | A per-book or per-batch prize rule, e.g. "each book contains one Rs.500" |
| Review item | A disagreement between documents and data found by the drafter, listed in `spec.md` |
| Golden result | A signed-off job's recorded results in `tests/golden/`, used as a regression baseline |

## After changing any code

```
python audit_tool.py test                         # unit tests, ~10 seconds
python audit_tool.py test --layouts <folder>      # plus golden jobs, minutes
```

Both must pass before you say a change is done. If they fail, say so and
show the failing output.
