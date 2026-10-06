# NLB Job Specification - 2026.September.NLB.300
<!-- spec-template: 1 -->

> **Draft generated** 2026-10-01 10:30 by `draft_spec.py` from the documents listed below and the measurements in `measured_facts.json`. Review every section against the specification documents, resolve the review items, then run `build_config.py`. It will not produce settings while any review item is unticked or the settings fail validation.

<!-- table:job -->
| Setting | Value |
|---|---|
| Job ID | 2026.September.NLB.300 |
| Client | NLB |
| Title | NLB Scratch Lottery |

**Sources**

<!-- list:sources -->
- 300 - 0351 CAR RACE.docx - game 0351, version 1.0 Final, September 14, 2026
- 300 - 0352 Lucky Duck.docx - game 0352, version 1.0 Final, September 14, 2026
- 300 - 0353 MIX RHYTHM.docx - game 0353, version 1.0 Final, September 14, 2026
- 0114 FREE HIT.docx - game 0114, version 1.0 Final, September 14, 2026
- NLB Data Spec 300 0351 Car Race_300 0352 Lucky Duck_300 0353 Mix Rhythm_320 0114 Free Hit.docx - data specification, V1.0, 25 SEPTEMBER 2026
- measured_facts.json - produced by probe_layout.py

## Review items

No review items. The specifications, the data specification and the measured layout file agree on every point the drafter checks.

## 1. Usage

```
python engine/build_config.py  --job jobs/2026.September.NLB.300
python engine/probe_layout.py  <layout file> --config jobs/2026.September.NLB.300/job_config.json
python engine/audit_engine.py  --config jobs/2026.September.NLB.300/job_config.json --layout <layout file> --out jobs/2026.September.NLB.300/out
```

## 2. Layout file format

<!-- table:layout -->
| Setting | Value |
|---|---|
| Channels | 4 |
| Lead columns | 1 |
| Block length | 21 |
| Serial offset | 0 |
| VIRN offset | 1 |
| Barcode offset | 2 |
| System prize code offset | 3 |
| Prize print code offset | 4 |
| First play offset | 5 |
| Play fields | 6 |
| Play fields used | 2 |
| First agent offset | 11 |
| Agent fields | 9 |
| QA offset | 20 |
| Void serial | 888888888888888 |
| Passive flag | 1 |
| VIRN random range | 2,000,000 - 6,999,999 |
| Parity rule | digit_sum_mod10 |

- Measured: 500,304 data rows, 85 fields per row (1 lead + 4 x 21), 83,384 pages of 6 rows = 24 tickets per page.
- Measured: 1,216 void tickets - 240 leading rows and 64 trailing rows.
- Measured: barcode parity (digit sum of VIRN mod 10) correct on 2,000,000 tickets, wrong on 0.
- Trailing void padding is normal: it completes the final page and is not an exception.

<!-- table:games -->
| Channel | Game | Lottery | Name |
|---|---|---|---|
| 1 | 0351 | 300 | CAR RACE |
| 2 | 0352 | 300 | LUCKY DUCK |
| 3 | 0353 | 300 | MIX RHYTHM |
| 4 | 0114 | 320 | FREE HIT |

## 3. Game mechanics

<!-- table:mechanics -->
| Game | Win rule | Special symbols | Forbidden | Prize spot |
|---|---|---|---|---|
| 0351 | match_two | - | - | no |
| 0352 | special_only | KB, LB | two_special | yes |
| 0353 | match_two_or_special | PC | two_special | yes |
| 0114 | match_two_or_special | LD | two_special | yes |

Win rules: `match_two` - two identical play symbols win; `match_two_or_special` - two identical play symbols win, or a single special symbol wins; `special_only` - a single special symbol wins; a matching pair does NOT win. Forbidden `two_special` rejects any ticket carrying two special symbols.

**0351 CAR RACE**

- Specification: "Scratch and match two similar money amounts and win that corresponding amount"
- Data specification: "Scratch and match two similar money amounts and win that corresponding amount."
- Measured: behaves as `match_two` - 112,689 winners with a matching pair, 0 without, 0 losers with one.
- Not allowed (data spec): "N/A".

**0352 LUCKY DUCK**

- Specification: "Scratch and find an "Egg" symbol or a "Duck" symbol and win the corresponding prize"
- Data specification: "Scratch and find an "Egg" symbol or a "Duck" symbol and win the corresponding prize."
- Measured: behaves as `special_only` with special KB, LB - 0 winners with a matching pair, 113,660 without, 0 losers with one.
- Not allowed (data spec): "Two similar "Egg" symbols, two similar "Duck" symbols and "Egg" and "Duck" symbols together.".

**0353 MIX RHYTHM**

- Specification: "Scratch and match two similar symbols or a "Guitar" symbol and win the corresponding prize"
- Data specification: "Scratch and match two similar symbols or a "Guitar" symbol and win the corresponding prize."
- Measured: behaves as `match_two_or_special` with special PC - 61,879 winners with a matching pair, 50,941 without, 0 losers with one.
- Not allowed (data spec): "Two similar "Guitar" symbols".

**0114 FREE HIT**

- Specification: "Scratch and match two similar "Bat" symbols or a "Ball" symbol and win the corresponding prize"
- Data specification: "Scratch and match two similar "Bat" symbols or a "Ball" symbol and win the corresponding prize."
- Measured: behaves as `match_two_or_special` with special LD - 47,617 winners with a matching pair, 65,715 without, 0 losers with one.
- Not allowed (data spec): "Two similar "Ball" symbols, Two similar other symbols except "Bat" symbol and "Bat" and "Ball" symbols together.".

## 4. Prize structures

### 300-0351 CAR RACE

<!-- table:prizes game=0351 -->
| System code | Amount | Label | Print code | Tier | Count | Symbol |
|---|---|---|---|---|---|---|
| 03 | 50 | - | - | Low | 100,000 | KA |
| 07 | 500 | - | - | High | 12,520 | LA |
| 11 | 5,000 | - | - | High | 84 | NA |
| 12 | 10,000 | - | - | High | 42 | PA |
| 13 | 25,000 | - | - | High | 42 | QA |
| 15 | 100,000 | - | - | High | 1 | UA |
| 99 | - | Non-win | - | Loss | 387,311 | - |

- The specification writes the non-win code as 099; the two-digit field holds 99.
- Measured: every prize count and the loser count match the file exactly (500,000 tickets, serials complete, 0 duplicates).
- Source: 300 - 0351 CAR RACE.docx, version 1.0 Final, September 14, 2026.

### 300-0352 LUCKY DUCK

<!-- table:prizes game=0352 -->
| System code | Amount | Label | Print code | Tier | Count | Symbol |
|---|---|---|---|---|---|---|
| 03 | 50 | - | dd | Low | 100,000 | - |
| 07 | 500 | - | hh | High | 12,500 | - |
| 08 | 1,000 | - | jj | High | 950 | - |
| 11 | 5,000 | - | mm | High | 210 | - |
| 99 | - | Non-win | - | Loss | 386,340 | - |

- The specification writes the non-win code as 099; the two-digit field holds 99.
- Measured: every prize count and the loser count match the file exactly (500,000 tickets, serials complete, 0 duplicates).
- Source: 300 - 0352 Lucky Duck.docx, version 1.0 Final, September 14, 2026.

### 300-0353 MIX RHYTHM

<!-- table:prizes game=0353 -->
| System code | Amount | Label | Print code | Tier | Count | Symbol |
|---|---|---|---|---|---|---|
| 03 | 50 | - | dd | Low | 100,000 | - |
| 07 | 500 | - | hh | High | 12,500 | - |
| 08 | 1,000 | - | jj | High | 110 | - |
| 11 | 5,000 | - | mm | High | 126 | - |
| 12 | 10,000 | - | nn | High | 42 | - |
| 37 | 20,000 | - | ww | High | 42 | - |
| 99 | - | Non-win | - | Loss | 387,180 | - |

- The specification writes the non-win code as 099; the two-digit field holds 99.
- Measured: every prize count and the loser count match the file exactly (500,000 tickets, serials complete, 0 duplicates).
- Source: 300 - 0353 MIX RHYTHM.docx, version 1.0 Final, September 14, 2026.

### 320-0114 FREE HIT

<!-- table:prizes game=0114 -->
| System code | Amount | Label | Print code | Tier | Count | Symbol |
|---|---|---|---|---|---|---|
| 03 | 50 | - | dd | Low | 100,000 | - |
| 07 | 500 | - | hh | High | 12,500 | - |
| 09 | 2,000 | - | kk | High | 790 | - |
| 12 | 10,000 | - | nn | High | 42 | - |
| 99 | - | Non-win | - | Loss | 386,668 | - |

- The specification writes the non-win code as 099; the two-digit field holds 99.
- Measured: every prize count and the loser count match the file exactly (500,000 tickets, serials complete, 0 duplicates).
- Source: 0114 FREE HIT.docx, version 1.0 Final, September 14, 2026.

**Declared parameters** (checked by the validator, never used to compute):

<!-- table:expected -->
| Game | Revenue | Pool | Payout % | Win ratio |
|---|---|---|---|---|
| 0351 | 25,000,000 | 13,250,000 | 53.0 | 4.44 |
| 0352 | 25,000,000 | 13,250,000 | 53.0 | 4.40 |
| 0353 | 25,000,000 | 13,250,000 | 53.0 | 4.43 |
| 0114 | 25,000,000 | 13,250,000 | 53.0 | 4.41 |

## 5. Play symbol codes

Play codes are capitals; prize print codes are smalls.

**0351 CAR RACE**

<!-- table:symbols game=0351 -->
| Code | Symbol |
|---|---|
| KA | Rs. 50 |
| LA | Rs. 500 |
| NA | Rs. 5,000 |
| PA | Rs. 10,000 |
| QA | Rs. 25,000 |
| UA | Rs. 100,000 |

**0352 LUCKY DUCK**

<!-- table:symbols game=0352 -->
| Code | Symbol |
|---|---|
| KB | Egg |
| LB | Duck |
| NB | Feather |
| PB | Lotus |
| QB | Tortoise |
| UB | Fish |

**0353 MIX RHYTHM**

<!-- table:symbols game=0353 -->
| Code | Symbol |
|---|---|
| KC | Drum |
| LC | Microphone |
| NC | Radio |
| PC | Guitar |
| QC | Trumpet |
| UC | Piano |

**0114 FREE HIT**

<!-- table:symbols game=0114 -->
| Code | Symbol |
|---|---|
| KD | Bat |
| LD | Ball |
| ND | Hat |
| PD | Wicket |
| QD | Trophy |
| UD | Shoe |

## 6. Agent validation codes

<!-- table:agent -->
| Setting | Value |
|---|---|
| High-tier letters | W, S, A, D, Z, R |
| Low-tier letter (Rs. 50) | T |
| Positions | 9 |
| Letters per ticket | 3 |

Non-winning and high-tier winning tickets carry three distinct high-tier letters; low-tier winners carry the low-tier letter plus two distinct high-tier letters.

- High-tier letters from the game specifications; low-tier letters: Rs.50=T.

## 7. Ticket and packaging

<!-- table:ticket -->
| Setting | Value |
|---|---|
| Ticket price | 50 |
| Tickets per game | 500,000 |
| Book size | 40 |

<!-- table:gleps -->
| Game | GLEPS per book |
|---|---|
| 0351 | 8 |
| 0352 | 8 |
| 0353 | 8 |
| 0114 | 8 |

Packing: each slot group is a run of identical slots covering whole books, in serial order. Mode `exact` must match; `min` is a floor.

**0351 CAR RACE**

<!-- table:packing game=0351 -->
| Slot group | Slots | Books per slot | Amount | Mode | N |
|---|---|---|---|---|---|
| 1 | 41 | 300 | 500 | min | 300 |
| 1 | 41 | 300 | 5,000 | exact | 2 |
| 1 | 41 | 300 | 10,000 | exact | 1 |
| 1 | 41 | 300 | 25,000 | exact | 1 |
| 2 | 1 | 200 | 500 | min | 200 |
| 2 | 1 | 200 | 5,000 | exact | 2 |
| 2 | 1 | 200 | 10,000 | exact | 1 |
| 2 | 1 | 200 | 25,000 | exact | 1 |

- Slot group 1: 41 x 300 books, from the specification's restrictions.
- Slot group 2: 1 x 200 books, from the specification's restrictions.
- Rs.500: packing minimum 12,500, prize table 12,520 (slack 20).

**0352 LUCKY DUCK**

<!-- table:packing game=0352 -->
| Slot group | Slots | Books per slot | Amount | Mode | N |
|---|---|---|---|---|---|
| 1 | 41 | 300 | 500 | exact | 300 |
| 1 | 41 | 300 | 1,000 | min | 22 |
| 1 | 41 | 300 | 5,000 | min | 5 |
| 2 | 1 | 200 | 500 | exact | 200 |
| 2 | 1 | 200 | 1,000 | min | 15 |
| 2 | 1 | 200 | 5,000 | min | 3 |

- Slot group 1: 41 x 300 books, from the specification's restrictions.
- Slot group 2: 1 x 200 books, from the specification's restrictions.
- Rs.1,000: packing minimum 917, prize table 950 (slack 33).
- Rs.5,000: packing minimum 208, prize table 210 (slack 2).

**0353 MIX RHYTHM**

<!-- table:packing game=0353 -->
| Slot group | Slots | Books per slot | Amount | Mode | N |
|---|---|---|---|---|---|
| 1 | 41 | 300 | 500 | exact | 300 |
| 1 | 41 | 300 | 1,000 | min | 2 |
| 1 | 41 | 300 | 5,000 | min | 3 |
| 1 | 41 | 300 | 10,000 | exact | 1 |
| 1 | 41 | 300 | 20,000 | exact | 1 |
| 2 | 1 | 200 | 500 | exact | 200 |
| 2 | 1 | 200 | 1,000 | min | 1 |
| 2 | 1 | 200 | 5,000 | min | 2 |
| 2 | 1 | 200 | 10,000 | exact | 1 |
| 2 | 1 | 200 | 20,000 | exact | 1 |

- Slot group 1: 41 x 300 books, from the specification's restrictions.
- Slot group 2: 1 x 200 books, from the specification's restrictions.
- Rs.1,000: packing minimum 83, prize table 110 (slack 27).
- Rs.5,000: packing minimum 125, prize table 126 (slack 1).

**0114 FREE HIT**

<!-- table:packing game=0114 -->
| Slot group | Slots | Books per slot | Amount | Mode | N |
|---|---|---|---|---|---|
| 1 | 41 | 300 | 500 | exact | 300 |
| 1 | 41 | 300 | 2,000 | min | 18 |
| 1 | 41 | 300 | 10,000 | exact | 1 |
| 2 | 1 | 200 | 500 | exact | 200 |
| 2 | 1 | 200 | 2,000 | min | 12 |
| 2 | 1 | 200 | 10,000 | exact | 1 |

- Slot group 1: 41 x 300 books, from the specification's restrictions.
- Slot group 2: 1 x 200 books, from the specification's restrictions.
- Rs.2,000: packing minimum 750, prize table 790 (slack 40).

## 8. Audit procedures

The six restrictions identical in every NLB game specification are built into the engine. Their two embedded numbers are settings:

<!-- table:fixed -->
| Setting | Value |
|---|---|
| Max same-value run | 3 |
| Winner every N tickets | 5 |
| GLEPS amount | 50 |

- All six standard restrictions were found word for word in every game specification.

Per-game prize promises (per book, or per batch of books). Separate several amounts with ` / `. Modes: `exactly` - exactly N of each; `min` - at least N in total; `at_most_each` - at most N of each; `at_least_one_total` - at least one of the set, at most N of each; `exactly_one_total` - exactly one of the set in total.

**0351 CAR RACE**

<!-- table:groups game=0351 -->
| Group | Size (books) | Amounts | Mode | N | Note |
|---|---|---|---|---|---|
| book | 1 | 500 | min | 1 | - |
| book | 1 | 5,000 / 10,000 / 25,000 / 100,000 | at_most_each | 1 | - |

- "Each book should contain at least one prize of Rs. 500." -> `min`
- "Each book should not contain more than one prize of Rs. 5,000, Rs. 10,000, Rs. 25,000 and Rs. 100,000." -> `at_most_each`

**0352 LUCKY DUCK**

<!-- table:groups game=0352 -->
| Group | Size (books) | Amounts | Mode | N | Note |
|---|---|---|---|---|---|
| book | 1 | 500 | exactly | 1 | - |
| book | 1 | 1,000 / 5,000 | at_most_each | 1 | - |

- "Each book should contain one prize of Rs. 500." -> `exactly`
- "Each book should not contain more than one prize of Rs.1,000 and Rs.5,000." -> `at_most_each`

**0353 MIX RHYTHM**

<!-- table:groups game=0353 -->
| Group | Size (books) | Amounts | Mode | N | Note |
|---|---|---|---|---|---|
| book | 1 | 500 | exactly | 1 | - |
| book | 1 | 1,000 / 5,000 / 10,000 / 20,000 | at_most_each | 1 | - |

- "Each book should contain one prize of Rs. 500." -> `exactly`
- "Each book should not contain more than one prize of Rs. 1,000, Rs. 5,000, Rs. 10,000 and Rs. 20,000." -> `at_most_each`

**0114 FREE HIT**

<!-- table:groups game=0114 -->
| Group | Size (books) | Amounts | Mode | N | Note |
|---|---|---|---|---|---|
| book | 1 | 500 | exactly | 1 | - |
| book | 1 | 2,000 / 10,000 | at_most_each | 1 | - |

- "Each book should contain one prize of Rs. 500." -> `exactly`
- "Each book should not contain more than one prizes of Rs. 2,000 and Rs. 10,000." -> `at_most_each`

Procedures run per game: 1 play positions · 2 prize box · 3 serial numbers · 4 VIRN and barcode · 5 agent codes · 6 prize structure · 7 GLEPS per book · 8 packing allocation · 9 per-group promises · 10 NON-GLEPS per book · 11 consecutive play pattern · 12 consecutive symbols in any rotation · 13 winner in every block of N · 14 prize value run length · 15 VIRN independence.

## 9. Tool configuration

`job_config.json` is generated from this document by `build_config.py`. Do not edit the JSON by hand: change the anchored tables here and rebuild, so this document stays the record of what was audited.

## 10. Modelling conventions

- Consecutive tickets means consecutive serial numbers within a game.
- Book = (serial - 1) // book size + 1; slots are counted in whole books from serial 1.
- `min` rules pass when the actual count meets or exceeds the floor; the actual figure is always reported.
- VOID rows are identified by serial value, not position; padding at either end of the file is expected.
- The prize-value run-length rule applies to winning tickets only.
- The QA sample code is not audited.

## 11. Tool structure and limitations

- `draft_spec.py` reads NLB specifications with patterns written for the NLB template. A specification that departs from that template produces review items rather than guesses, but read every table regardless.
- Nothing in the pipeline compares the settings against the written specification except this review.
- The whole layout file is held in memory during the audit.
