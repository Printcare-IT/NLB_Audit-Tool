---
name: audit-new-job
description: Start a new scratch-lottery layout audit job - create the job folder, collect the game specs, data spec and layout file, measure the layout and draft spec.md. Use when the user has a new set of games / a new layout file to audit, or a job's status is missing, needs_inputs, needs_layout or needs_draft.
---

# Start a new audit job

Follow [CLAUDE.md](../../../CLAUDE.md) rules throughout. Full detail:
[docs/workflow.md](../../../docs/workflow.md).

1. Agree the job name with the user: `<year>.<Mon>.<Client>.<n>G`, e.g.
   `2026.Oct.NLB.3G` (n = number of games). Check that `jobs/<job>` does not
   already exist.
2. `python audit_tool.py new --job <job> --json`
3. Get the files into `jobs/<job>/inputs/`: one game spec per game, the data
   spec, and the `*LAYOUT*.TXT` file (or `--layout <path>` /
   `AUDIT_LAYOUTS_DIR` if it stays on a share). Extract archives; leave the
   archives out of git.
4. Check that each game spec's title line reads
   `GAME NO: <number> - "<GAME NAME>" (Rs. <price>)` with the quotes. Tell the
   user about any that do not. Never edit the client's original.
5. `python audit_tool.py status --job <job> --json` should now say
   `needs_draft`.
6. `python audit_tool.py draft --job <job> --json`. It measures the layout
   first if needed (minutes, so run it in the background).
7. Report: games found (number, name, price, channels), and the review items
   grouped as BLOCKING / LAYOUT / check. Spot cascades that share one cause
   (e.g. a missing title quote) and say so.
8. If there are review items (exit 3), hand over to the `audit-review-spec`
   skill. If there are none (exit 0), continue with `audit-run`.
