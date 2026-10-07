# Job workflow - what to do at each stage

Start every session on a job with:

```
python audit_tool.py status --job <job> --json
```

Then follow the section for the `stage` it reports. Commands below omit
`--json`; add it whenever the platform reads the result.

---

## `missing` → create the job

Job folder names follow `<year>.<Mon>.<Client>.<n>G`, where `n` is the number
of games, e.g. `2026.Sep.NLB.4G`. Agree the name with the user, then:

```
python audit_tool.py new --job <job>
```

## `needs_inputs` / `needs_layout` → collect the files

`jobs/<job>/inputs/` needs:

- one **game specification** per game (`.pdf`, `.docx` or `.doc`)
- the **data generation specification** covering all games
- the **layout file** `*LAYOUT*.TXT`, or set `AUDIT_LAYOUTS_DIR` to the share
  that holds it, or pass `--layout <path>` on every command

Before drafting, check each game spec's title line. It must read
`GAME NO: <number> - "<GAME NAME>" (Rs. <price>)`, **with the quotes**.
Without them the drafter cannot read the game number, and one cause turns into
a cascade of review items (see [troubleshooting.md](troubleshooting.md)). If a
title line is wrong, tell the user. Do not edit the client's document.

The folder must be `inputs` (plural). If files arrive in archives (`.rar`,
`.zip`), extract the layout file into `inputs/` and leave the archive out of
git.

## `needs_draft` → draft the specification

```
python audit_tool.py draft --job <job>
```

This measures the layout file first if `measured_facts.json` is missing
(minutes). The drafter reads every document, compares game spec, data spec
and measured data wherever they cover the same fact, and writes `spec.md` with
one review item per disagreement. It exits 3 if there are review items, 0 if
there are none.

Report to the user: the number of games found, and the review items grouped
by kind (BLOCKING / LAYOUT / check).

If `spec.md` already existed, the draft goes to `spec.draft.md`. Never copy
it over `spec.md`. Show the user the differences and merge the parts they
accept.

## `needs_review` → the human gate

Stop driving the pipeline. The auditor decides each item; you help. Follow
[spec-review.md](spec-review.md). `build` and `run` refuse with exit 3 until
every item is ticked.

## `spec_unreadable` → repair a table

Someone has edited an anchored table so it no longer parses. The `error`
field names it. Usual causes: a renamed column heading, a deleted
`<!-- table:... -->` anchor, or a number written with words or units. Restore
the heading and anchor from another job's `spec.md`, or from
`engine/spec_md.py`. Change values only, never headings.

## `needs_build` → build the settings

```
python audit_tool.py build --job <job>
```

The build has two gates. **Review**: every item must be ticked. **Validation**:
the settings must be arithmetically consistent: prize counts against the
sub-total, pool and payout, packing against the prize table, group promises
achievable, and so on. If validation fails, each `X [game] message` line
names a table in `spec.md` to correct. Correct the table with the user's
agreement, against the specification documents, and build again.

If `job_config.json` existed, the build lists every change before writing.
Read the list. A change you cannot explain from the edits just made is a
problem: stop and raise it.

`reason: job_config.json differs from spec.md` on a job nobody has touched
usually means the engine's format moved on (for example `channel` became
`channels` when multi-channel games were added). Rebuilding is safe in that
case. Show the change list to the user.

## `ready_to_audit` → verify and audit

```
python audit_tool.py run --job <job>
```

Run it in the background; it takes minutes. `run` = `build` → `verify` →
`audit`.

- **Stops at verify (exit 1)**: `probe_layout.py --config` found the settings
  and the data disagree. Compare each `X` line with the ticked review items
  in `spec.md`:
  - every disagreement is a ticked **LAYOUT** item → expected; rerun with
    `--force-audit` and the audit reports them as layout-file errors
  - anything else → the settings are wrong for this file, or the wrong layout
    file was picked up. Do not force it. Investigate with the user.
- **Exit 0**: every check passed for every game.
- **Exit 2**: the audit found exceptions. Go to the next section.

## `audited` → report the result

Read `out/audit_summary.json` and `out/audit_report.md`. For the user, give:

- the load summary (live tickets, void tickets, malformed / duplicate serials)
- per game: PASSED, or each failed check with its number, title and offender
  count
- where the evidence is: `out/game<NNNN>_check<NN>_offenders.csv`
- which failures were expected from ticked LAYOUT review items, and which
  are new

Open a few rows of each offender CSV and describe the pattern you see (for
example "all 12 are consecutive-pattern repeats in books 1404-1411"). Do not
call an exception a false positive unless you can show it in the data and the
specification. Even then, put it to the auditor as a question, not a
conclusion.

The Word report is `out/audit_report.docx`. Past deliverables were renamed for
the client (`audit_report_<games>.docx`). Ask the user what name to use.

## Sign-off → record the golden result

After the auditor has signed off:

```
python tests/run_regression.py --record --layouts <folder with the layout file> --job <job>
```

This makes the job part of the regression baseline. Only do it on the
auditor's instruction.

## Committing

Commit `inputs/` documents, `measured_facts.json`, `spec.md`,
`job_config.json` and `out/` reports. Never commit layout files, archives,
offender CSVs, `BACKUP_*` files or Office lock files (`.gitignore` covers
them). Use the existing message style, e.g. *"Generated audit report and job
specification for NLB Scratch Lottery 2026.Sep.NLB.1G"*.
