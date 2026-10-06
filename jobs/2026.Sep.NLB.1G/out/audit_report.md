# NLB Scratch Lottery - Layout Audit Report

Job         : `2026.Sep.NLB.1G`
Layout file : `0115-LAYOUT.TXT`
Generated   : 2026-10-02 18:27:46

## File load summary

- Data rows read : 125,304
- Pages : 20,884
- Live tickets : 500,000
- VOID tickets ignored : 1,216 (240 leading rows, 64 trailing)
- Malformed serials : 0
- Duplicate serials : 0
- Rows with an unexpected field count : 0
- QA sample code values : $=500,000

Void padding is expected at both ends of the file and is not an exception: VOID rows are identified by the serial value `888888888888888`.

---
# Game 320-0115 - "SAKURA MAL"

**ALL CHECKS PASSED**

## 1. Play positions - PASS - No exceptions were noted

*Procedure:* Check whether the fields pertaining to the play positions in the data layout have been populated as per the game specifications (win = two similar symbols).

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
- Rs.1,000 (08/jj, High): expected 1,790, found 1,790  OK
- Rs.5,000 (11/mm, High): expected 42, found 42  OK
- Losing tickets (99): expected 385,668, found 385,668  OK
- Total tickets: expected 500,000, found 500,000  OK
- Winners 114,332 (win ratio 1:4.37); prize pool Rs.13,250,000

## 7. GLEPS per book - PASS - No exceptions were noted

*Procedure:* Check whether each book of 40 tickets contains the guaranteed 8 x Rs.50 low-end prizes.

- No exceptions were noted. Every book contains exactly 8 x Rs.50 (Rs.400 per book).

## 8. Packing allocation - PASS - No exceptions were noted

*Procedure:* Check whether each packing slot carries the prescribed prize allocation: 41 x 300 books (Rs.500=300, Rs.1,000>=42, Rs.5,000=1); 1 x 200 books (Rs.500=200, Rs.1,000>=28, Rs.5,000=1).

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

- Overall winner rate 22.8664%; chi-square across 10 VIRN bands = 4.67 (critical value 27.88 at 0.1%).
- No exceptions were noted. The winner rate is independent of the VIRN.

## Appendix I - Play symbol distribution (0115)

| Play symbol | Code | Position 1 | Position 2 | Total |
|---|---|---:|---:|---:|
| Sun | KA | 83,853 | 84,274 | 168,127 |
| Butterfly | LA | 81,692 | 83,334 | 165,026 |
| Squirrel | NA | 82,281 | 85,350 | 167,631 |
| Bee | PA | 84,312 | 80,972 | 165,284 |
| Bunch of Flower | QA | 85,555 | 82,340 | 167,895 |
| Tree | UA | 82,307 | 83,730 | 166,037 |
| **Total** |  | **500,000** | **500,000** | **1,000,000** |

## Appendix II - Prize amount symbol distribution (0115)

| Prize amount | Code | Total |
|---|---|---:|
| Rs.50 | dd | 177,128 |
| Rs.500 | hh | 113,430 |
| Rs.1,000 | jj | 106,654 |
| Rs.5,000 | mm | 102,788 |

## Appendix III - Agent validation code distribution (0115)

| Letter | GLEPS | Non-GLEPS | Losing | Total |
|---|---:|---:|---:|---:|
| A | 33,844 | 7,330 | 193,274 | 234,448 |
| D | 32,961 | 7,124 | 191,066 | 231,151 |
| R | 32,968 | 7,032 | 193,672 | 233,672 |
| S | 32,641 | 6,887 | 192,785 | 232,313 |
| T | 100,000 | 0 | 0 | 100,000 |
| W | 33,779 | 7,347 | 193,312 | 234,438 |
| Z | 33,807 | 7,276 | 192,895 | 233,978 |
| **Total** | **300,000** | **42,996** | **1,157,004** | **1,500,000** |
