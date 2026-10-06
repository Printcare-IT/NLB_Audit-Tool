# NLB Job Specification - 2026.Sep.NLB.1G
<!-- spec-template: 1 -->

> **Draft generated** 2026-10-02 18:12 by `draft_spec.py` from the documents listed below and the measurements in `measured_facts.json`. Review every section against the specification documents, resolve the review items, then run `build_config.py`. It will not produce settings while any review item is unticked or the settings fail validation.

<!-- table:job -->
| Setting | Value |
|---|---|
| Job ID | 2026.Sep.NLB.1G |
| Client | NLB |
| Title | NLB Scratch Lottery |

**Sources**

<!-- list:sources -->
- 0115 Sakura Mal.docx - game 0115, version 1.0 Final, September 14, 2026
- NLB Data Spec 320 0115 Sakura Mal.docx - data specification, V1.0, 25 SEPTEMBER 2026
- measured_facts.json - produced by probe_layout.py

## Review items

No review items. The specifications, the data specification and the measured layout file agree on every point the drafter checks.

## 1. Usage

```
python engine/build_config.py  --job jobs/2026.Sep.NLB.1G
python engine/probe_layout.py  <layout file> --config jobs/2026.Sep.NLB.1G/job_config.json
python engine/audit_engine.py  --config jobs/2026.Sep.NLB.1G/job_config.json --layout <layout file> --out jobs/2026.Sep.NLB.1G/out
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

- Measured: game 0115 is printed on channels 1, 2, 3, 4 (channel 1: 1 - 125,000; channel 2: 125,001 - 250,000; channel 3: 250,001 - 375,000; channel 4: 375,001 - 500,000). Its figures below are for the whole game.
- Measured: 125,304 data rows, 85 fields per row (1 lead + 4 x 21), 20,884 pages of 6 rows = 24 tickets per page.
- Measured: 1,216 void tickets - 240 leading rows and 64 trailing rows.
- Measured: barcode parity (digit sum of VIRN mod 10) correct on 500,000 tickets, wrong on 0.
- Trailing void padding is normal: it completes the final page and is not an exception.

<!-- table:games -->
| Channel | Game | Lottery | Name |
|---|---|---|---|
| 1 / 2 / 3 / 4 | 0115 | 320 | SAKURA MAL |

## 3. Game mechanics

<!-- table:mechanics -->
| Game | Win rule | Special symbols | Forbidden | Prize spot |
|---|---|---|---|---|
| 0115 | match_two | - | - | yes |

Win rules: `match_two` - two identical play symbols win; `match_two_or_special` - two identical play symbols win, or a single special symbol wins; `special_only` - a single special symbol wins; a matching pair does NOT win. Forbidden `two_special` rejects any ticket carrying two special symbols.

**0115 SAKURA MAL**

- Specification: "Scratch and match two similar symbols and win the corresponding prize"
- Data specification: "Scratch and match two similar symbols and win the corresponding prize."
- Measured: behaves as `match_two` - 114,332 winners with a matching pair, 0 without, 0 losers with one.
- Not allowed (data spec): "N/A".

## 4. Prize structures

### 320-0115 SAKURA MAL

<!-- table:prizes game=0115 -->
| System code | Amount | Label | Print code | Tier | Count | Symbol |
|---|---|---|---|---|---|---|
| 03 | 50 | - | dd | Low | 100,000 | - |
| 07 | 500 | - | hh | High | 12,500 | - |
| 08 | 1,000 | - | jj | High | 1,790 | - |
| 11 | 5,000 | - | mm | High | 42 | - |
| 99 | - | Non-win | - | Loss | 385,668 | - |

- The specification writes the non-win code as 099; the two-digit field holds 99.
- Measured: every prize count and the loser count match the file exactly (500,000 tickets, serials complete, 0 duplicates).
- Source: 0115 Sakura Mal.docx, version 1.0 Final, September 14, 2026.

**Declared parameters** (checked by the validator, never used to compute):

<!-- table:expected -->
| Game | Revenue | Pool | Payout % | Win ratio |
|---|---|---|---|---|
| 0115 | 25,000,000 | 13,250,000 | 53.0 | 4.37 |

## 5. Play symbol codes

Play codes are capitals; prize print codes are smalls.

**0115 SAKURA MAL**

<!-- table:symbols game=0115 -->
| Code | Symbol |
|---|---|
| KA | Sun |
| LA | Butterfly |
| NA | Squirrel |
| PA | Bee |
| QA | Bunch of Flower |
| UA | Tree |

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
| 0115 | 8 |

Packing: each slot group is a run of identical slots covering whole books, in serial order. Mode `exact` must match; `min` is a floor.

**0115 SAKURA MAL**

<!-- table:packing game=0115 -->
| Slot group | Slots | Books per slot | Amount | Mode | N |
|---|---|---|---|---|---|
| 1 | 41 | 300 | 500 | exact | 300 |
| 1 | 41 | 300 | 1,000 | min | 42 |
| 1 | 41 | 300 | 5,000 | exact | 1 |
| 2 | 1 | 200 | 500 | exact | 200 |
| 2 | 1 | 200 | 1,000 | min | 28 |
| 2 | 1 | 200 | 5,000 | exact | 1 |

- Slot group 1: 41 x 300 books, from the specification's restrictions.
- Slot group 2: 1 x 200 books, from the specification's restrictions.
- Rs.1,000: packing minimum 1,750, prize table 1,790 (slack 40).

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

**0115 SAKURA MAL**

<!-- table:groups game=0115 -->
| Group | Size (books) | Amounts | Mode | N | Note |
|---|---|---|---|---|---|
| book | 1 | 500 | exactly | 1 | - |
| book | 1 | 1,000 / 5,000 | at_most_each | 1 | - |

- "Each book should contain one prize of Rs. 500." -> `exactly`
- "Each book should not contain more than one prize of Rs.1,000 and Rs.5,000." -> `at_most_each`

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
