# NLB Scratch Lottery - Layout Audit Report

Job         : `2026.September.NLB.300`
Layout file : `0351-0352-0353-0114-LAYOUT.TXT`
Generated   : 2026-10-01 11:43:23

## File load summary

- Data rows read : 500,304
- Pages : 83,384
- Live tickets : 2,000,000
- VOID tickets ignored : 1,216 (240 leading rows, 64 trailing)
- Malformed serials : 0
- Duplicate serials : 0
- Rows with an unexpected field count : 0
- QA sample code values : $=2,000,000

Void padding is expected at both ends of the file and is not an exception: VOID rows are identified by the serial value `888888888888888`.

---
# Game 300-0351 - "CAR RACE"

**2 CHECK(S) WITH EXCEPTIONS**

## 1. Play positions - PASS - No exceptions were noted

*Procedure:* Check whether the fields pertaining to the play positions in the data layout have been populated as per the game specifications (win = two similar symbols).

- No exceptions were noted. All play positions are valid and consistent with winner/loser status.

## 2. Prize box / position - PASS - No exceptions were noted

*Procedure:* Check whether the field pertaining to the prize box/position in the data layout has been populated as per the game specifications.

- Not applicable: this game has no prize spot, and the prize print code is blank on every ticket as specified.

## 3. Serial number - PASS - No exceptions were noted

*Procedure:* Check whether the serial-number field is populated per the format PXXXGGGGTTTTTTT with a unique consecutive number from 0000001 to 0500000.

- No exceptions were noted. All 500,000 serials are present exactly once and correctly formatted.

## 4. VIRN and Barcode - PASS - No exceptions were noted

*Procedure:* Check whether the VIRN and Barcode fields are populated per the format PXXXGGGGVVVVVVV, with the barcode carrying a 16th parity digit (parity = sum of the VIRN digits, mod 10).

- No exceptions were noted. All VIRNs are valid, unique and their barcodes carry the correct parity digit.

## 5. Agent validation codes - PASS - No exceptions were noted

*Procedure:* Check whether the agent validation code fields are populated per the rules for high-tier/losing tickets and low-tier winning tickets.

- No exceptions were noted. All agent validation codes follow the prescribed composition rules.

## 6. Prize structure - PASS - No exceptions were noted

*Procedure:* Check whether the prize structure prescribed by the game specification is reflected in the data layout.

- Rs.50 (03/-, Low): expected 100,000, found 100,000  OK
- Rs.500 (07/-, High): expected 12,520, found 12,520  OK
- Rs.5,000 (11/-, High): expected 84, found 84  OK
- Rs.10,000 (12/-, High): expected 42, found 42  OK
- Rs.25,000 (13/-, High): expected 42, found 42  OK
- Rs.100,000 (15/-, High): expected 1, found 1  OK
- Losing tickets (99): expected 387,311, found 387,311  OK
- Total tickets: expected 500,000, found 500,000  OK
- Winners 112,689 (win ratio 1:4.44); prize pool Rs.13,250,000

## 7. GLEPS per book - PASS - No exceptions were noted

*Procedure:* Check whether each book of 40 tickets contains the guaranteed 8 x Rs.50 low-end prizes.

- No exceptions were noted. Every book contains exactly 8 x Rs.50 (Rs.400 per book).

## 8. Packing allocation - PASS - No exceptions were noted

*Procedure:* Check whether each packing slot carries the prescribed prize allocation: 41 x 300 books (Rs.500>=300, Rs.5,000=2, Rs.10,000=1, Rs.25,000=1); 1 x 200 books (Rs.500>=200, Rs.5,000=2, Rs.10,000=1, Rs.25,000=1).

- No exceptions were noted. All 42 packing slots meet the prescribed allocation.

## 9. Per-group prize promises - PASS - No exceptions were noted

*Procedure:* Check the per-book and per-batch prize promises: each book: Rs.500 min 1; each book: Rs.5,000/Rs.10,000/Rs.25,000/Rs.100,000 at most each 1.

- No exceptions were noted. Every book and batch meets its prize promise.

## 10. Non-GLEPS per book - PASS - No exceptions were noted

*Procedure:* Check whether each book of 40 tickets contains at least one NON-GLEPS prize.

- No exceptions were noted. Every book contains at least one NON-GLEPS prize.

## 11. Consecutive play pattern - EXCEPTIONS NOTED (3880)

*Procedure:* Check whether consecutive tickets contain the same play symbol pattern.

- 3880 instance(s), affecting 7760 tickets.

## 12. Consecutive symbols (any rotation) - EXCEPTIONS NOTED (3880)

*Procedure:* Check whether consecutive tickets contain the same winning symbols in any rotation.

- 3880 instance(s), affecting 7760 tickets.

## 13. Every 5 tickets contains a winner - PASS - No exceptions were noted

*Procedure:* Check whether each block of 5 tickets starting from ticket 001 in each book contains at least one prize.

- No exceptions were noted. Every block of 5 tickets contains at least one prize.

## 14. Prize value run length - PASS - No exceptions were noted

*Procedure:* Check whether more than 3 consecutive winning tickets contain the same winning value / prize amount.

- No exceptions were noted. No more than 3 consecutive winning tickets share the same prize value.

## 15. VIRN independence - PASS - No exceptions were noted

*Procedure:* Check whether there is any logical relationship between the play patterns and the VIRN.

- Overall winner rate 22.5378%; chi-square across 10 VIRN bands = 6.18 (critical value 27.88 at 0.1%).
- No exceptions were noted. The winner rate is independent of the VIRN.

## Appendix I - Play symbol distribution (0351)

| Play symbol | Code | Position 1 | Position 2 | Total |
|---|---|---:|---:|---:|
| Rs. 50 | KA | 154,212 | 153,272 | 307,484 |
| Rs. 500 | LA | 77,650 | 80,213 | 157,863 |
| Rs. 5,000 | NA | 67,514 | 63,575 | 131,089 |
| Rs. 10,000 | PA | 68,257 | 66,785 | 135,042 |
| Rs. 25,000 | QA | 66,347 | 67,175 | 133,522 |
| Rs. 100,000 | UA | 66,020 | 68,980 | 135,000 |
| **Total** |  | **500,000** | **500,000** | **1,000,000** |

## Appendix II - Prize amount symbol distribution (0351)

| Prize amount | Code | Total |
|---|---|---:|
| Rs.50 | 03 | 100,000 |
| Rs.500 | 07 | 12,520 |
| Rs.5,000 | 11 | 84 |
| Rs.10,000 | 12 | 42 |
| Rs.25,000 | 13 | 42 |
| Rs.100,000 | 15 | 1 |
| Losing | 99 | 387,311 |

## Appendix III - Agent validation code distribution (0351)

| Letter | GLEPS | Non-GLEPS | Losing | Total |
|---|---:|---:|---:|---:|
| A | 34,037 | 6,345 | 195,782 | 236,164 |
| D | 32,593 | 6,358 | 191,262 | 230,213 |
| R | 32,756 | 6,293 | 190,752 | 229,801 |
| S | 32,593 | 6,288 | 190,376 | 229,257 |
| T | 100,000 | 0 | 0 | 100,000 |
| W | 34,077 | 6,308 | 197,214 | 237,599 |
| Z | 33,944 | 6,475 | 196,547 | 236,966 |
| **Total** | **300,000** | **38,067** | **1,161,933** | **1,500,000** |

---
# Game 300-0352 - "LUCKY DUCK"

**ALL CHECKS PASSED**

## 1. Play positions - PASS - No exceptions were noted

*Procedure:* Check whether the fields pertaining to the play positions in the data layout have been populated as per the game specifications (win = a single special symbol (a matching pair does not win)).

- No exceptions were noted. All play positions are valid and consistent with winner/loser status.

## 2. Prize box / position - PASS - No exceptions were noted

*Procedure:* Check whether the field pertaining to the prize box/position in the data layout has been populated as per the game specifications.

- No exceptions were noted. All prize print codes are valid and, for winners, match the system prize code.

## 3. Serial number - PASS - No exceptions were noted

*Procedure:* Check whether the serial-number field is populated per the format PXXXGGGGTTTTTTT with a unique consecutive number from 0000001 to 0500000.

- No exceptions were noted. All 500,000 serials are present exactly once and correctly formatted.

## 4. VIRN and Barcode - PASS - No exceptions were noted

*Procedure:* Check whether the VIRN and Barcode fields are populated per the format PXXXGGGGVVVVVVV, with the barcode carrying a 16th parity digit (parity = sum of the VIRN digits, mod 10).

- No exceptions were noted. All VIRNs are valid, unique and their barcodes carry the correct parity digit.

## 5. Agent validation codes - PASS - No exceptions were noted

*Procedure:* Check whether the agent validation code fields are populated per the rules for high-tier/losing tickets and low-tier winning tickets.

- No exceptions were noted. All agent validation codes follow the prescribed composition rules.

## 6. Prize structure - PASS - No exceptions were noted

*Procedure:* Check whether the prize structure prescribed by the game specification is reflected in the data layout.

- Rs.50 (03/dd, Low): expected 100,000, found 100,000  OK
- Rs.500 (07/hh, High): expected 12,500, found 12,500  OK
- Rs.1,000 (08/jj, High): expected 950, found 950  OK
- Rs.5,000 (11/mm, High): expected 210, found 210  OK
- Losing tickets (99): expected 386,340, found 386,340  OK
- Total tickets: expected 500,000, found 500,000  OK
- Winners 113,660 (win ratio 1:4.40); prize pool Rs.13,250,000

## 7. GLEPS per book - PASS - No exceptions were noted

*Procedure:* Check whether each book of 40 tickets contains the guaranteed 8 x Rs.50 low-end prizes.

- No exceptions were noted. Every book contains exactly 8 x Rs.50 (Rs.400 per book).

## 8. Packing allocation - PASS - No exceptions were noted

*Procedure:* Check whether each packing slot carries the prescribed prize allocation: 41 x 300 books (Rs.500=300, Rs.1,000>=22, Rs.5,000>=5); 1 x 200 books (Rs.500=200, Rs.1,000>=15, Rs.5,000>=3).

- No exceptions were noted. All 42 packing slots meet the prescribed allocation.

## 9. Per-group prize promises - PASS - No exceptions were noted

*Procedure:* Check the per-book and per-batch prize promises: each book: Rs.500 exactly 1; each book: Rs.1,000/Rs.5,000 at most each 1.

- No exceptions were noted. Every book and batch meets its prize promise.

## 10. Non-GLEPS per book - PASS - No exceptions were noted

*Procedure:* Check whether each book of 40 tickets contains at least one NON-GLEPS prize.

- No exceptions were noted. Every book contains at least one NON-GLEPS prize.

## 11. Consecutive play pattern - PASS - No exceptions were noted

*Procedure:* Check whether consecutive tickets contain the same play symbol pattern.

- No exceptions were noted. Consecutive tickets do not contain the same play symbol pattern in any instance.

## 12. Consecutive symbols (any rotation) - PASS - No exceptions were noted

*Procedure:* Check whether consecutive tickets contain the same winning symbols in any rotation.

- No exceptions were noted. Consecutive tickets do not contain the same winning symbols in any rotation in any instance.

## 13. Every 5 tickets contains a winner - PASS - No exceptions were noted

*Procedure:* Check whether each block of 5 tickets starting from ticket 001 in each book contains at least one prize.

- No exceptions were noted. Every block of 5 tickets contains at least one prize.

## 14. Prize value run length - PASS - No exceptions were noted

*Procedure:* Check whether more than 3 consecutive winning tickets contain the same winning value / prize amount.

- No exceptions were noted. No more than 3 consecutive winning tickets share the same prize value.

## 15. VIRN independence - PASS - No exceptions were noted

*Procedure:* Check whether there is any logical relationship between the play patterns and the VIRN.

- Overall winner rate 22.7320%; chi-square across 10 VIRN bands = 4.02 (critical value 27.88 at 0.1%).
- No exceptions were noted. The winner rate is independent of the VIRN.

## Appendix I - Play symbol distribution (0352)

| Play symbol | Code | Position 1 | Position 2 | Total |
|---|---|---:|---:|---:|
| Egg | KB | 28,345 | 28,627 | 56,972 |
| Duck | LB | 29,703 | 26,985 | 56,688 |
| Feather | NB | 106,697 | 114,110 | 220,807 |
| Lotus | PB | 112,350 | 109,622 | 221,972 |
| Tortoise | QB | 112,093 | 110,528 | 222,621 |
| Fish | UB | 110,812 | 110,128 | 220,940 |
| **Total** |  | **500,000** | **500,000** | **1,000,000** |

## Appendix II - Prize amount symbol distribution (0352)

| Prize amount | Code | Total |
|---|---|---:|
| Rs.50 | dd | 178,319 |
| Rs.500 | hh | 114,085 |
| Rs.1,000 | jj | 104,602 |
| Rs.5,000 | mm | 102,994 |

## Appendix III - Agent validation code distribution (0352)

| Letter | GLEPS | Non-GLEPS | Losing | Total |
|---|---:|---:|---:|---:|
| A | 34,665 | 7,039 | 197,944 | 239,648 |
| D | 30,881 | 6,550 | 189,832 | 227,263 |
| R | 31,468 | 6,852 | 192,885 | 231,205 |
| S | 34,091 | 6,789 | 193,476 | 234,356 |
| T | 100,000 | 0 | 0 | 100,000 |
| W | 35,097 | 6,795 | 191,820 | 233,712 |
| Z | 33,798 | 6,955 | 193,063 | 233,816 |
| **Total** | **300,000** | **40,980** | **1,159,020** | **1,500,000** |

---
# Game 300-0353 - "MIX RHYTHM"

**ALL CHECKS PASSED**

## 1. Play positions - PASS - No exceptions were noted

*Procedure:* Check whether the fields pertaining to the play positions in the data layout have been populated as per the game specifications (win = two similar symbols or a single special symbol).

- No exceptions were noted. All play positions are valid and consistent with winner/loser status.

## 2. Prize box / position - PASS - No exceptions were noted

*Procedure:* Check whether the field pertaining to the prize box/position in the data layout has been populated as per the game specifications.

- No exceptions were noted. All prize print codes are valid and, for winners, match the system prize code.

## 3. Serial number - PASS - No exceptions were noted

*Procedure:* Check whether the serial-number field is populated per the format PXXXGGGGTTTTTTT with a unique consecutive number from 0000001 to 0500000.

- No exceptions were noted. All 500,000 serials are present exactly once and correctly formatted.

## 4. VIRN and Barcode - PASS - No exceptions were noted

*Procedure:* Check whether the VIRN and Barcode fields are populated per the format PXXXGGGGVVVVVVV, with the barcode carrying a 16th parity digit (parity = sum of the VIRN digits, mod 10).

- No exceptions were noted. All VIRNs are valid, unique and their barcodes carry the correct parity digit.

## 5. Agent validation codes - PASS - No exceptions were noted

*Procedure:* Check whether the agent validation code fields are populated per the rules for high-tier/losing tickets and low-tier winning tickets.

- No exceptions were noted. All agent validation codes follow the prescribed composition rules.

## 6. Prize structure - PASS - No exceptions were noted

*Procedure:* Check whether the prize structure prescribed by the game specification is reflected in the data layout.

- Rs.50 (03/dd, Low): expected 100,000, found 100,000  OK
- Rs.500 (07/hh, High): expected 12,500, found 12,500  OK
- Rs.1,000 (08/jj, High): expected 110, found 110  OK
- Rs.5,000 (11/mm, High): expected 126, found 126  OK
- Rs.10,000 (12/nn, High): expected 42, found 42  OK
- Rs.20,000 (37/ww, High): expected 42, found 42  OK
- Losing tickets (99): expected 387,180, found 387,180  OK
- Total tickets: expected 500,000, found 500,000  OK
- Winners 112,820 (win ratio 1:4.43); prize pool Rs.13,250,000

## 7. GLEPS per book - PASS - No exceptions were noted

*Procedure:* Check whether each book of 40 tickets contains the guaranteed 8 x Rs.50 low-end prizes.

- No exceptions were noted. Every book contains exactly 8 x Rs.50 (Rs.400 per book).

## 8. Packing allocation - PASS - No exceptions were noted

*Procedure:* Check whether each packing slot carries the prescribed prize allocation: 41 x 300 books (Rs.500=300, Rs.1,000>=2, Rs.5,000>=3, Rs.10,000=1, Rs.20,000=1); 1 x 200 books (Rs.500=200, Rs.1,000>=1, Rs.5,000>=2, Rs.10,000=1, Rs.20,000=1).

- No exceptions were noted. All 42 packing slots meet the prescribed allocation.

## 9. Per-group prize promises - PASS - No exceptions were noted

*Procedure:* Check the per-book and per-batch prize promises: each book: Rs.500 exactly 1; each book: Rs.1,000/Rs.5,000/Rs.10,000/Rs.20,000 at most each 1.

- No exceptions were noted. Every book and batch meets its prize promise.

## 10. Non-GLEPS per book - PASS - No exceptions were noted

*Procedure:* Check whether each book of 40 tickets contains at least one NON-GLEPS prize.

- No exceptions were noted. Every book contains at least one NON-GLEPS prize.

## 11. Consecutive play pattern - PASS - No exceptions were noted

*Procedure:* Check whether consecutive tickets contain the same play symbol pattern.

- No exceptions were noted. Consecutive tickets do not contain the same play symbol pattern in any instance.

## 12. Consecutive symbols (any rotation) - PASS - No exceptions were noted

*Procedure:* Check whether consecutive tickets contain the same winning symbols in any rotation.

- No exceptions were noted. Consecutive tickets do not contain the same winning symbols in any rotation in any instance.

## 13. Every 5 tickets contains a winner - PASS - No exceptions were noted

*Procedure:* Check whether each block of 5 tickets starting from ticket 001 in each book contains at least one prize.

- No exceptions were noted. Every block of 5 tickets contains at least one prize.

## 14. Prize value run length - PASS - No exceptions were noted

*Procedure:* Check whether more than 3 consecutive winning tickets contain the same winning value / prize amount.

- No exceptions were noted. No more than 3 consecutive winning tickets share the same prize value.

## 15. VIRN independence - PASS - No exceptions were noted

*Procedure:* Check whether there is any logical relationship between the play patterns and the VIRN.

- Overall winner rate 22.5640%; chi-square across 10 VIRN bands = 11.62 (critical value 27.88 at 0.1%).
- No exceptions were noted. The winner rate is independent of the VIRN.

## Appendix I - Play symbol distribution (0353)

| Play symbol | Code | Position 1 | Position 2 | Total |
|---|---|---:|---:|---:|
| Drum | KC | 91,690 | 98,980 | 190,670 |
| Microphone | LC | 96,063 | 92,883 | 188,946 |
| Radio | NC | 95,978 | 93,896 | 189,874 |
| Guitar | PC | 24,336 | 26,605 | 50,941 |
| Trumpet | QC | 96,776 | 92,005 | 188,781 |
| Piano | UC | 95,157 | 95,631 | 190,788 |
| **Total** |  | **500,000** | **500,000** | **1,000,000** |

## Appendix II - Prize amount symbol distribution (0353)

| Prize amount | Code | Total |
|---|---|---:|
| Rs.50 | dd | 150,131 |
| Rs.500 | hh | 78,987 |
| Rs.1,000 | jj | 68,422 |
| Rs.5,000 | mm | 68,607 |
| Rs.10,000 | nn | 65,370 |
| Rs.20,000 | ww | 68,483 |

## Appendix III - Agent validation code distribution (0353)

| Letter | GLEPS | Non-GLEPS | Losing | Total |
|---|---:|---:|---:|---:|
| A | 34,266 | 6,517 | 195,187 | 235,970 |
| D | 32,254 | 6,208 | 193,874 | 232,336 |
| R | 31,573 | 6,121 | 193,056 | 230,750 |
| S | 36,237 | 6,814 | 192,456 | 235,507 |
| T | 100,000 | 0 | 0 | 100,000 |
| W | 34,737 | 6,616 | 197,250 | 238,603 |
| Z | 30,933 | 6,184 | 189,717 | 226,834 |
| **Total** | **300,000** | **38,460** | **1,161,540** | **1,500,000** |

---
# Game 320-0114 - "FREE HIT"

**ALL CHECKS PASSED**

## 1. Play positions - PASS - No exceptions were noted

*Procedure:* Check whether the fields pertaining to the play positions in the data layout have been populated as per the game specifications (win = two similar symbols or a single special symbol).

- No exceptions were noted. All play positions are valid and consistent with winner/loser status.

## 2. Prize box / position - PASS - No exceptions were noted

*Procedure:* Check whether the field pertaining to the prize box/position in the data layout has been populated as per the game specifications.

- No exceptions were noted. All prize print codes are valid and, for winners, match the system prize code.

## 3. Serial number - PASS - No exceptions were noted

*Procedure:* Check whether the serial-number field is populated per the format PXXXGGGGTTTTTTT with a unique consecutive number from 0000001 to 0500000.

- No exceptions were noted. All 500,000 serials are present exactly once and correctly formatted.

## 4. VIRN and Barcode - PASS - No exceptions were noted

*Procedure:* Check whether the VIRN and Barcode fields are populated per the format PXXXGGGGVVVVVVV, with the barcode carrying a 16th parity digit (parity = sum of the VIRN digits, mod 10).

- No exceptions were noted. All VIRNs are valid, unique and their barcodes carry the correct parity digit.

## 5. Agent validation codes - PASS - No exceptions were noted

*Procedure:* Check whether the agent validation code fields are populated per the rules for high-tier/losing tickets and low-tier winning tickets.

- No exceptions were noted. All agent validation codes follow the prescribed composition rules.

## 6. Prize structure - PASS - No exceptions were noted

*Procedure:* Check whether the prize structure prescribed by the game specification is reflected in the data layout.

- Rs.50 (03/dd, Low): expected 100,000, found 100,000  OK
- Rs.500 (07/hh, High): expected 12,500, found 12,500  OK
- Rs.2,000 (09/kk, High): expected 790, found 790  OK
- Rs.10,000 (12/nn, High): expected 42, found 42  OK
- Losing tickets (99): expected 386,668, found 386,668  OK
- Total tickets: expected 500,000, found 500,000  OK
- Winners 113,332 (win ratio 1:4.41); prize pool Rs.13,250,000

## 7. GLEPS per book - PASS - No exceptions were noted

*Procedure:* Check whether each book of 40 tickets contains the guaranteed 8 x Rs.50 low-end prizes.

- No exceptions were noted. Every book contains exactly 8 x Rs.50 (Rs.400 per book).

## 8. Packing allocation - PASS - No exceptions were noted

*Procedure:* Check whether each packing slot carries the prescribed prize allocation: 41 x 300 books (Rs.500=300, Rs.2,000>=18, Rs.10,000=1); 1 x 200 books (Rs.500=200, Rs.2,000>=12, Rs.10,000=1).

- No exceptions were noted. All 42 packing slots meet the prescribed allocation.

## 9. Per-group prize promises - PASS - No exceptions were noted

*Procedure:* Check the per-book and per-batch prize promises: each book: Rs.500 exactly 1; each book: Rs.2,000/Rs.10,000 at most each 1.

- No exceptions were noted. Every book and batch meets its prize promise.

## 10. Non-GLEPS per book - PASS - No exceptions were noted

*Procedure:* Check whether each book of 40 tickets contains at least one NON-GLEPS prize.

- No exceptions were noted. Every book contains at least one NON-GLEPS prize.

## 11. Consecutive play pattern - PASS - No exceptions were noted

*Procedure:* Check whether consecutive tickets contain the same play symbol pattern.

- No exceptions were noted. Consecutive tickets do not contain the same play symbol pattern in any instance.

## 12. Consecutive symbols (any rotation) - PASS - No exceptions were noted

*Procedure:* Check whether consecutive tickets contain the same winning symbols in any rotation.

- No exceptions were noted. Consecutive tickets do not contain the same winning symbols in any rotation in any instance.

## 13. Every 5 tickets contains a winner - PASS - No exceptions were noted

*Procedure:* Check whether each block of 5 tickets starting from ticket 001 in each book contains at least one prize.

- No exceptions were noted. Every block of 5 tickets contains at least one prize.

## 14. Prize value run length - PASS - No exceptions were noted

*Procedure:* Check whether more than 3 consecutive winning tickets contain the same winning value / prize amount.

- No exceptions were noted. No more than 3 consecutive winning tickets share the same prize value.

## 15. VIRN independence - PASS - No exceptions were noted

*Procedure:* Check whether there is any logical relationship between the play patterns and the VIRN.

- Overall winner rate 22.6664%; chi-square across 10 VIRN bands = 12.41 (critical value 27.88 at 0.1%).
- No exceptions were noted. The winner rate is independent of the VIRN.

## Appendix I - Play symbol distribution (0114)

| Play symbol | Code | Position 1 | Position 2 | Total |
|---|---|---:|---:|---:|
| Bat | KD | 120,699 | 123,610 | 244,309 |
| Ball | LD | 29,328 | 36,387 | 65,715 |
| Hat | ND | 83,897 | 87,275 | 171,172 |
| Wicket | PD | 87,640 | 84,421 | 172,061 |
| Trophy | QD | 92,969 | 81,175 | 174,144 |
| Shoe | UD | 85,467 | 87,132 | 172,599 |
| **Total** |  | **500,000** | **500,000** | **1,000,000** |

## Appendix II - Prize amount symbol distribution (0114)

| Prize amount | Code | Total |
|---|---|---:|
| Rs.50 | dd | 176,776 |
| Rs.500 | hh | 114,129 |
| Rs.2,000 | kk | 106,147 |
| Rs.10,000 | nn | 102,948 |

## Appendix III - Agent validation code distribution (0114)

| Letter | GLEPS | Non-GLEPS | Losing | Total |
|---|---:|---:|---:|---:|
| A | 35,013 | 6,747 | 195,402 | 237,162 |
| D | 30,375 | 6,293 | 194,852 | 231,520 |
| R | 34,421 | 6,625 | 194,096 | 235,142 |
| S | 32,812 | 6,633 | 190,126 | 229,571 |
| T | 100,000 | 0 | 0 | 100,000 |
| W | 33,943 | 7,093 | 194,359 | 235,395 |
| Z | 33,436 | 6,605 | 191,169 | 231,210 |
| **Total** | **300,000** | **39,996** | **1,160,004** | **1,500,000** |
