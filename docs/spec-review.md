# Reviewing `spec.md` - helping the auditor

`jobs/<job>/spec.md` is the job's record. The drafter fills it from the
client's documents and the measured layout file. Every place where those
sources disagree, or could not be read, becomes a **review item** at the top.
`build` will not produce settings until every item is ticked, so this is
where the auditor's judgement enters the process.

**Your role: prepare, do not decide.** For each item, find the evidence,
explain it in plain terms, and propose what to change. The auditor decides,
and only then is the item ticked. Never tick an item yourself to unblock the
pipeline.

## The file's format

- Review items look like
  `- [ ] **R3 · 0349 · LAYOUT** - <what the drafter found>`.
  Ticked: `- [x] ...`, followed by a note of the decision:
  `— <who>, <date>: <decision>`.
- Machine-read tables sit under invisible `<!-- table:<name> [game=<key>] -->`
  anchors. **Change values; never rename a column heading or remove an
  anchor.** The builder reads only these tables.
- Everything else is prose for people. Notes can go anywhere.
- Several amounts in one cell are separated with ` / `. Numbers are plain;
  thousands separators are accepted.

Sections: 1 Usage · 2 Layout file format · 3 Game mechanics · 4 Prize
structures · 5 Play symbol codes · 6 Agent validation codes · 7 Ticket and
packaging · 8 Audit procedures · 9 Tool configuration · 10 Modelling
conventions · 11 Tool structure and limitations.

## The three kinds of item

| Tag | Means | Resolution |
|---|---|---|
| **BLOCKING** | The settings cannot be built as they stand: a value is unreadable, contradictory or impossible | Correct the table (from the documents), then tick. A tick without the correction fails the validation gate |
| **LAYOUT** | The layout file disagrees with the specification (a prize count, the win rule, special symbols, prize spot, barcode parity) | Leave the tables as the **specification** says and tick. The audit will report the difference as a layout-file error. This is a finding |
| check | Worth a look; nothing is known to be wrong | Confirm against the documents and tick |

### LAYOUT items: the important one

A LAYOUT item means the delivered data does not do what the client
specified. That is the kind of error the audit is there to catch. The
tempting "fix", making the tables match the file so everything passes,
hides it. Change a table to the file's behaviour only when **the client** has
confirmed that the specification itself is wrong. Record who confirmed it
and when, in the note after the tick.

## How to prepare each item

1. Read the item. Note the game number and the fact in question.
2. Find the fact in each source:
   - game spec: `jobs/<job>/inputs/<game spec>`
   - data spec: `jobs/<job>/inputs/<data spec>`
   - measured data: `jobs/<job>/measured_facts.json`
   - current table: the anchored table in `spec.md`

   To read a document as the drafter sees it:
   ```
   python -c "import sys; sys.path.insert(0,'engine'); from doc_text import to_text, flatten; print(flatten(to_text(sys.argv[1])))" "jobs/<job>/inputs/<file>"
   ```
3. Give the auditor: the item, what each source says (quoted, with the
   document name), your reading of the cause, and the exact table cell change
   you propose, or "no table change, tick as LAYOUT".
4. Once the auditor decides, make the edit, tick the item, and add the note.
5. When all items are ticked, run `python audit_tool.py build --job <job>`.

Group related items: one root cause often produces several of them.

## Common items and their usual cause

| Item text contains | Usual cause | Usual resolution |
|---|---|---|
| `has a specification but does not appear in the layout file` together with `appears in the layout file but no game specification was supplied` | The game spec's title line lacks the quotes: `GAME NO: 0349 - "KASI WASI" (Rs. 20)` | Ask for a corrected document or fix the title in a copy, re-draft (`spec.draft.md`) and merge. Do not resolve the cascade item by item |
| `could not read the game number / name / price` | Same as above | Same as above |
| `play symbol table headed ... ` with a game number not in the job | The client reused a table heading from an older job; the drafter matched it by symbol codes | Confirm the codes are right for this game, tick |
| `data spec says ... channel(s)` / page range / tickets per page | Data spec prose is out of date against the delivered file | Usually a check. Confirm with the measured facts, tick, note the discrepancy for the client |
| `barcodes fail the digit-sum-mod-10` (LAYOUT) | Real barcode errors in the data | Tick as LAYOUT. The audit lists them (check 4) |
| `the specification describes '<rule>' but the` data ... (LAYOUT) | The win rule in the data differs from the spec | Tick as LAYOUT unless the client confirms the spec is wrong |
| `special symbol ... named in the mechanism is` not in the symbol table (BLOCKING) | Name mismatch between game spec and data spec | Find the right code in the data spec symbol table, enter it in the special symbols cell |
| `restriction not understood - add it to the tables` (BLOCKING) | A group promise worded in a way the parser does not know | Encode it as a row in the `groups` table, per README "Group promises". Mind "or both" (`at_least_one_total`) against "either ... or" (`exactly_one_total`) |
| `book size ... does not divide` (BLOCKING) | Book size misread, or the ticket count is wrong | Check both against the game spec |
| `validation: ...` | The arithmetic does not add up: prize counts, pool, payout, packing | Re-read the prize table in the game spec. A count is usually mistyped in the table or in the client's document. If it is the client's document, raise it with the client |

## When the auditor wants to change a table without an item

That is allowed: the tables are theirs. Make the edit and say what changed.
`build` will list the change against the previous `job_config.json`. Keep a
note in the prose beside the table explaining why.
