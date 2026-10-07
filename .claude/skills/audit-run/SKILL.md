---
name: audit-run
description: Build the settings, verify them against the layout file, run the 15-check audit and report the result for a scratch-lottery job. Use when status is needs_build, ready_to_audit or audited, or the user asks to run, re-run or explain an audit.
---

# Run and report an audit

Full detail: [docs/workflow.md](../../../docs/workflow.md). Failure
messages: [docs/troubleshooting.md](../../../docs/troubleshooting.md).

1. `python audit_tool.py status --job <job> --json`. Expect `needs_build` or
   `ready_to_audit`. If it says `needs_review`, use `audit-review-spec`
   instead.
2. `python audit_tool.py run --job <job> --json` **in the background**
   (minutes; one run per job at a time).
3. By exit code:
   - **3** - unticked review items, so stop (`audit-review-spec`).
   - **1, `stopped_at: build`** - validation. Fix `spec.md` tables with the user.
   - **1, `stopped_at: verify`** - settings and data disagree. If *every*
     disagreement is a ticked LAYOUT item, rerun with `--force-audit`.
     Otherwise stop and investigate. Check first that the right layout file
     was used (`layout` in the result).
   - **0** - every check passed for every game.
   - **2** - exceptions found. A finding, not a tool fault.
4. Report from `out/audit_summary.json` and `out/audit_report.md`: the load
   summary, then per game PASSED or each failed check (number, title,
   offender count). Say which failures were expected from ticked LAYOUT
   items. For each failure, open the offender CSV
   (`out/game<NNNN>_check<NN>_offenders.csv`) and describe the pattern.
5. Never soften, explain away or "fix" an exception. Never edit `engine/` or
   `job_config.json` to change a result.
6. Deliverable: `out/audit_report.docx`. Ask the user what file name the
   client copy should have.
7. Only after the auditor signs off, and only when they ask:
   `python tests/run_regression.py --record --layouts <folder> --job <job>`.
