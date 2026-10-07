# Troubleshooting

Messages are quoted as the tools print them.

## Drafting

**`No .pdf/.docx/.doc files found in jobs/<job>/inputs`**
The folder is missing, misnamed (`input` rather than `inputs`), or the
documents are still inside an archive. Rename the folder or extract the
files. `--inputs <folder>` on `engine/draft_spec.py` points elsewhere.

**A game shows as `game None` in the sources list, followed by many review items**
(`has a specification but does not appear in the layout file`, `appears in
the layout file but no game specification was supplied`, `could not read the
game number / name / price`, plus symbol and win-rule items for that game.)
One cause: the title line is not
`GAME NO: <number> - "<GAME NAME>" (Rs. <price>)` with the name **in quotes**.
Fix the title in the document (or ask the client for a corrected one) and
re-draft. Do not resolve the items one by one.

**`spec.md already exists - writing spec.draft.md instead`**
This is by design: a reviewed record is never overwritten. Compare the two
files with the user and merge the wanted changes into `spec.md` by hand.
Delete `spec.draft.md` afterwards, or `status` keeps reporting
`pending_redraft`.

**A `.doc` file fails to read**
LibreOffice is needed to convert legacy `.doc` files. Install it, or ask for
the document as `.docx` or `.pdf`. A `BACKUP_*.doc` or `~$*.doc` file in
`inputs/` is a stray copy. Remove it from `inputs/`.

**`no measured_facts.json: nothing in this draft has been` checked against data (BLOCKING)**
The layout file was not found when drafting. Provide it (`--layout`, put it
in `inputs/`, or set `AUDIT_LAYOUTS_DIR`), delete the draft, and re-draft.

## Building

**`NOT BUILT: N review item(s) are still unticked`** (exit 3)
The review gate. See [spec-review.md](spec-review.md).

**`NOT BUILT: the settings in spec.md fail validation`**
Each `X [game] message` names an inconsistency. Correct the table in
`spec.md` from the specification document. A BLOCKING item that was ticked
without its table being corrected ends up here.

**`NOT BUILT: could not read spec.md: ...`**
An anchored table was damaged: renamed heading, missing anchor, or a
non-numeric value in a number column. Compare it with the same table in
another job's `spec.md`.

**`status` says `needs_build` with `job_config.json differs from spec.md`, but nobody edited anything**
Either the engine's settings format changed (rebuild; the builder lists every
change, check that they are format-only), or someone hand-edited
`job_config.json` (rebuild; the hand edit is discarded, as it should be).

## Verifying

**`N disagreement(s)` from `verify`, `run` stops at `verify`**
The settings and the layout file disagree. For each `X` line:
- It matches a ticked **LAYOUT** review item → expected; `run --force-audit`.
- Book size does not divide the data, channel map differs, a prize count is
  off by a few → the settings or the file are wrong. Do not force. Check
  that the right layout file was picked up (the `layout` field in the
  result), then go back to the specification.

## Auditing

**`Settings failed validation - audit not run`**
`job_config.json` was changed outside `build`. Run `build`.

**`(python-docx not installed - Word report skipped)`**
`pip install -r requirements.txt`. The markdown report and the JSON summary
are still written.

**Exit 2 with exceptions**
This is the audit working, not a tool error. Report it. Read the offender
CSVs for the pattern. Exceptions caused by ticked LAYOUT items are expected
findings for the client.

**`No layout file: pass --layout ...`**
Auto-discovery found nothing, or found several candidates in
`AUDIT_LAYOUTS_DIR` and refused to guess. Pass `--layout` explicitly.

## Tests

**`ImportError: Start directory is not importable`**
An older `run_regression.py` passed `-t <root>` to unittest discovery, which
needs `tests/` to be a package. Fixed. If it comes back, check the
`unittest discover` call in `tests/run_regression.py`.

**A golden job fails after an engine change**
The change altered real results. Find out why before doing anything else.
Re-record (`--record`) only if the auditor accepts the new results as
correct.
