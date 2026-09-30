# NLB Scratch Lottery Audit Tool

One tool for every NLB job. The engine is never edited for a new job: a job is
described by a reviewed markdown specification, and the settings are generated
from it.

```
nlb/
  engine/
    probe_layout.py       measures a layout file (no settings needed)
    draft_spec.py         drafts spec.md from the documents + measurements
    build_config.py       turns the reviewed spec.md into job_config.json
    validate_config.py    arithmetic checks on the settings (used by the above)
    audit_engine.py       the audit
    doc_text.py, spec_parse.py, spec_md.py   helpers
  tests/
    run_regression.py     runs everything below
    test_audit_checks.py  every audit check, one injected defect per test
    test_pipeline.py      validator, parsers, markdown, drafter, gates
    fixtures.py           the synthetic job generator
    golden/               recorded results of real jobs
  jobs/
    <job>/
      inputs/             game specs + data spec (.pdf / .docx / .doc)
                          and the layout file (.TXT) for the job
      measured_facts.json from probe_layout.py
      spec.md             THE RECORD - drafted, then reviewed by you
      job_config.json     generated from spec.md - never edit by hand
      out/                audit reports and offender CSVs
```

**Where the layout file goes.** Put it in `jobs/<job>/inputs/` beside the
specifications, so everything for a job sits together. The tools take its path
as an argument, so it can live anywhere; only `run_regression.py` has to find
it on its own, and it looks in any `--layouts` folder you pass, then the job
folder, then `jobs/<job>/inputs/`. Layout files are large (137 to 226 MB on
recent jobs), so if they already sit on a share, leave them there and point at
them instead of copying: `--layouts <that folder>`. The drafter only reads
`.pdf`, `.docx` and `.doc`, so a `.TXT` layout in `inputs/` is ignored by it.

Setup, once: `pip install python-docx pdfplumber` (there is no
`requirements.txt` yet). LibreOffice is needed only if a specification arrives
as a legacy `.doc`.

**Folder name.** The drafter reads `jobs/<job>/inputs/` - plural. A folder
named `input` is not found; rename it, or pass `--inputs <folder>` to
`draft_spec.py`.

## The process for a new set of games

```
1. mkdir jobs/<job>/inputs     and copy the game specs, data spec and layout file in
2. python engine/probe_layout.py <layout file> --out jobs/<job>/measured_facts.json
3. python engine/draft_spec.py   --job jobs/<job>
4. REVIEW jobs/<job>/spec.md     - resolve and tick every review item
5. python engine/build_config.py --job jobs/<job>
6. python engine/probe_layout.py <layout file> --config jobs/<job>/job_config.json
7. python engine/audit_engine.py --config jobs/<job>/job_config.json \
                                 --layout <layout file> --out jobs/<job>/out
```

Step 3 can run step 2 for you: `draft_spec.py --job jobs/<job> --layout <file>`.

### What the drafter does

It reads every specification in `inputs/`, reads the measurements, and compares
the three sources wherever they speak to the same fact - game spec, data spec,
and the delivered file. **Every disagreement becomes a review item.** It never
overwrites a reviewed `spec.md`; a second run writes `spec.draft.md`.

Things it has caught on real jobs:

- the 0345 batch rule that no data could satisfy (BLOCKING)
- a data spec page range ten pages short of the file
- a data spec saying four channels where the file has five
- a symbol table headed with a game number not in the job, matched to the
  right game by its symbol codes
- a special symbol (Egg, game 0352) that the specification says wins but the
  data never pays

### The game spec title line

The drafter identifies each game specification by its title line, which must
read exactly like this, with the game name **in quotes**:

```
GAME NO: 0351 - "CAR RACE" (Rs. 50)
```

Without the quotes the game number is not read (`game None` in the sources
list). The drafter then falls back to the file name as the game's ID, and one
problem shows up as several review items: *"has a specification but does not
appear in the layout file"*, *"appears in the layout file but no game
specification was supplied"*, *"could not read the game number / name /
price"*, and follow-on symbol and win-rule items for that game. Fix the title
line and re-draft rather than resolving those items one by one.

### Reviewing spec.md

Review items come in three kinds:

| Tag | Meaning | To resolve |
|---|---|---|
| **BLOCKING** | The settings cannot be built as they stand | Correct the table, then tick |
| **LAYOUT** | The layout file disagrees with the specification (a prize count, the win rule, the special symbols, the prize spot, barcode parity) | Confirm the tables follow the **specification**, not the file, and tick. The audit then reports the difference as a layout-file error |
| check | Worth a look; nothing is known to be wrong | Tick once checked |

A LAYOUT item is a finding about the delivered data, not about `spec.md`.
Do not "fix" it by copying the file's behaviour into the tables unless the
client confirms the specification itself is wrong. Record who confirmed it.


- Machine-read tables sit under invisible `<!-- table:... -->` anchors. Change
  their **values** freely; keep their column headings.
- Everything else is prose for you and is ignored by the builder - add notes
  wherever useful.
- Tick each review item with `- [x]` once resolved. Adding a short note after
  the tick records what you decided.
- Several amounts in one cell are separated with ` / `.

### The two gates in build_config.py

1. **Review gate** - refuses while any review item is unticked.
2. **Validation gate** - refuses if the settings contradict themselves. Ticking
   a BLOCKING item without correcting its table fails here.

When `job_config.json` already exists, the builder lists every change before
overwriting it.

## Regression tests

Run after **any** change to the engine, and before trusting a new release:

```
python tests/run_regression.py --unit-only                  # under a second
python tests/run_regression.py --layouts <layout folder>    # a few minutes
```

**Layer 1 - unit tests (58, under a second, no files needed).** A generator
builds a small synthetic job that passes every rule. Each test injects one
defect and asserts that *exactly* the right check fails - no more, no fewer.
They cover all 15 audit checks, the validator, the specification parsers, the
markdown format, the drafter's cross-checks and both build gates. Several are
named after real defects found during development (the losers-run bug, the
nested Word table, thousands separators, the contents page) and fail if that
defect returns.

**Layer 2 - golden results on real jobs.** For each job with
`tests/golden/<job>.json`, the runner confirms that:

1. `job_config.json` is still exactly what `spec.md` produces - catches a
   hand-edited JSON, which can weaken the audit while reports look unchanged
2. the settings still validate
3. the drafter still reads the job's documents exactly as recorded
4. with the layout file present, the probe still agrees and every check
   reports the same offender count as recorded

**Recording.** After a job's audit is signed off, add it to the golden set:

```
python tests/run_regression.py --record --layouts <layout folder> --job <job>
```

Only re-record an existing job when a change in its results is understood and
intended - recording redefines what "correct" means.

The tests use only the Python standard library plus the tool's own
requirements.

## Measuring a layout file

Run this **before** writing settings for a new job, and as a cross-check on an
existing one. It takes no settings and assumes almost nothing: the block
structure, channel-to-game map, prize counts, void convention, parity rule,
winning rule and likely book size are all worked out from the data itself.

```
python engine/probe_layout.py <layout file> \
       --out jobs/<job>/measured_facts.json \
       [--config jobs/<job>/job_config.json]
```

Without `--config` it prints what is in the file, and writes the facts as JSON.
That JSON is the evidence base for drafting the markdown specification, so every
figure in the draft is either quoted from a specification document or measured
here — never guessed.

With `--config` it also compares the measurements against the settings and lists
every disagreement. It checks:

| Area | Catches |
|---|---|
| Channel count, void serial | File shape differs from the settings |
| Channel to game map, lottery code | A game configured on the wrong channel |
| Every prize count and the loser count | Any count out by even one |
| Play symbol set, both directions | A symbol in the data but not the settings, or the reverse |
| Inferred winning rule and special symbols | Settings say `match_two`, data says `special_only` |
| Barcode parity | Any ticket where parity is not digit-sum mod 10 |
| **Book size** | The configured size does not divide the data evenly |
| **GLEPS promise** | Configured as 8 per book, data holds a different number |
| **Packing schedule** | Slot shape or per-slot allocation not met by the data |

Use it as the final check before signing off an audit.

**What it does not check.** Group promises (the per-book Rs.500 rule and the
`at_most_each` caps) are verified by the audit engine, not here. Payout, pool and
win ratio are pure arithmetic on the settings and belong to the validator. And
nothing in the pipeline compares the settings against the written specification
documents — that remains the purpose of your markdown review.

The probe is a deliberately separate, second reading of the same file. It shares
no code with the audit engine, so when the two agree that agreement is evidence.

## What is built in and never configured

The six restrictions identical in every NLB game spec:

- each book contains at least one NON-GLEPS prize
- no consecutive tickets with the same play pattern
- no consecutive tickets with the same winning symbols in any rotation
- no logical relationship between play patterns and VIRN
- no more than three consecutive tickets with the same prize value
- any multiple of five tickets from ticket 001 in a book contains a winner

The two numbers inside them (3 and 5) are still settings, under
`fixed_rules`, with those defaults.

## What the settings must supply

| Section | Contents |
|---|---|
| `job` | id, client, ticket price, source documents |
| `layout` | block length, channels, field offsets, void serial, VIRN range |
| `structure` | tickets per game, book size |
| `agent` | high-tier letters, the low-tier letter per low prize amount |
| `fixed_rules` | run length, winner interval, GLEPS amount |
| `games[]` | per game: symbols, prize table, win rule, packing, group promises |

### Winning rules

| Value | Meaning | Seen in |
|---|---|---|
| `match_two` | two identical play symbols win | 0110, 0111, 0347, 0349, 0350, 0112, 0113, 0351 |
| `match_two_or_special` | two identical, or one special symbol alone | 0345 (Flag), 0348 (Sun), 0353 (Guitar) |
| `special_only` | one special symbol wins; a matching pair does **not** | 0346 (Gold Coin / Diamond), 0352 (Egg / Duck) |

`forbidden: "two_special"` additionally rejects tickets carrying two special
symbols (0345, 0346, 0348, 0352, 0353).

### Packing schedule

A list of slot groups, covering every book exactly once:

```json
"packing": [
  { "slots": 41, "books": 300,
    "allocation": [ {"amount": 500, "mode": "min", "n": 300} ] },
  { "slots": 1,  "books": 200,
    "allocation": [ {"amount": 500, "mode": "min", "n": 200} ] }
]
```

`mode` is `exact` or `min`, per line — the same slot can mix both.

### Group promises

Every per-book and per-batch rule uses one shape:

```json
{ "group": "book",  "size": 1,   "amounts": [500],       "mode": "exactly",      "n": 1 }
{ "group": "book",  "size": 1,   "amounts": [500],       "mode": "min",          "n": 1 }
{ "group": "book",  "size": 1,   "amounts": [200, 500],  "mode": "exactly_one_total" }
{ "group": "book",  "size": 1,   "amounts": [200, 500],  "mode": "at_least_one_total", "n": 1 }
{ "group": "book",  "size": 1,   "amounts": [1000,5000], "mode": "at_most_each", "n": 1 }
{ "group": "batch", "size": 150, "amounts": [10000],     "mode": "min",          "n": 1 }
```

Note the difference the word "both" makes in the spec: where the restriction
reads *"Rs.200, Rs.500 or both"* use `at_least_one_total`; where it reads
*"either Rs.200 or Rs.500"* use `exactly_one_total`. *"contain one prize of
Rs.500"* is `exactly`; *"contain at least one prize of Rs.500"* is `min`
(the drafter reads both, and the number may be written as a word or a digit).

## What the validator catches

Run before every audit. It has already found a real specification error.

- prize counts against the stated sub-total and ticket count
- pool, revenue, payout percentage and win ratio
- GLEPS promise against the prize table
- packing allocation against per-game totals (exact must match, minimum must fit)
- **whether a group promise is achievable at all**
- symbols referenced by prizes and special rules actually exist
- print codes present or absent according to `has_prize_spot`

## Specification notes

**Game 0345 — batch rule withdrawn.** An earlier draft required *"each batch of
75 books should contain a minimum of one Rs.10,000 winner"*, which was
impossible (167 batches needed, 84 prizes available). The revised specification
replaces it with a per-slot guarantee of **2 x Rs.10,000 per box**, which the
delivered data satisfies exactly (41 x 2 + 2 = 84, matching the prize table with
zero slack). The settings reflect the revised rule; no batch rule is configured.

**Game 0347 — 59% payout is intentional.** A special promotional case, confirmed
by NLB. Every other NLB game runs at 53%. The validator checks payout against
the figure declared in the settings, so no change is needed — but do not
"correct" it to 53%.

**Game 0347 — three standing exceptions.** 1,787 books carry no NON-GLEPS prize,
and 3,627 consecutive ticket pairs repeat a play pattern. Both were reproduced
directly from the raw file. A likely contributing factor: 0347 uses only **four**
play symbols (others use six), giving just 16 possible ordered pairs across
500,000 tickets, which makes consecutive repeats hard to avoid. Raise with the
data generation team.

**Game 0352 (Lucky Duck) — Egg does not win in the data. OPEN.** Both the
game spec and the data spec read *"find an Egg symbol or a Duck symbol and win
the corresponding prize"*. In the September 2026 layout file only Duck (`LB`)
wins: it appears exactly once on each of the 113,660 winners and on no loser,
while Egg (`KB`) appears 177,298 times, about as often as the plain symbols,
at least 63,638 of them on losing tickets. To be raised with the data
generation team and NLB. If the specification stands, the data must be regenerated. If
NLB confirms Duck alone wins, change the special symbols to `LB` in `spec.md`
and record the confirmation.

## Adding a new winning rule

Only reason to touch the engine. Add a branch to `should_win()` and the new
name to `WIN_RULES` in `validate_config.py`. Everything else is settings.
