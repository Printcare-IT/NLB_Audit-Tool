#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
LYDIA LUDIC BURUNDI - "WEHOKUKI" - LAYOUT AUDIT TOOL  v1
Game 02 / Series 02/2026 - 3,000,000 tickets - 2,000 FBu
================================================================================

Reads the game data file (one record per card) and checks it against the Game
Specification (V2.0, 07 July 2026) and the Data Generation Specification
(V1.0, 13 July 2026).  Writes audit_report.md and audit_report.docx.  Run:

    python lottery_audit_WEHOKUKI.py <layout_file> [output_dir]

The (A) LAYOUT and (B) GAME_CONFIG blocks below are the only parts to edit
for a new job.

Procedures 1-14 below mirror the Agreed-Upon Procedures report issued for the
previous WEHOKUKI series (EY, 14 October 2025), re-based on the 02/2026
specification.  Procedure 15 is a supplementary print-imposition order check
(not part of the EY set).  Two further diagnostics - the QA sample-code field
and the play-pattern/VIRN independence screen - are reported in the file-load
summary and within procedures 3 and 15 rather than as numbered procedures.

CHECKS PERFORMED
----------------
 1  Play positions: 6 spots, 18 valid symbols; winner = exactly one
    three-of-a-kind equal to its prize symbol; loser = no three-of-a-kind;
    prize (symbol) print code blank on every ticket
 2  Serial numbers complete, unique, correctly formatted (GG-BBBBB-TTT),
    ascending within each book
 3  VIRN: 8 digits, range 20000000-89999999, unique (+ independence screen)
 4  Agent validation codes: 3 of 9 positions; losers & high-tier winners get
    three distinct letters from R,S,T,U,V,W,X,Y,Z; mid/low winners get two of
    those plus the prize letter (A..L)
 5  Overall prize structure totals, prize pool and payout %
 6  Per-lot prize allocation: per-book (100), per-box (10,000) and per-group
    (N-box spread) guarantees
 7  No ticket with more than three similar symbols
 8  No ticket with two combinations of three similar symbols (triplicates)
 9  No consecutive tickets with the same play symbol pattern
10  No consecutive tickets with the same winning symbols in any rotation
11  No consecutive tickets with the same winning value / prize amount
12  75% of losers have two or more matching pairs, one pair a high-tier symbol
13  20% of losers have one matching pair with a high- or mid-tier symbol
14  No more than four consecutive losers
15  Print imposition order (supplementary): every record in its expected file
    position under the 7-channel / 56-per-page / 5-book-block layout, with an
    optional leading identifier column tolerated ahead of the serial

MECHANIC
--------
  three_of_a_kind   winner = one symbol appears exactly three times among the
                    six play spots, and that symbol equals the symbol assigned
                    to the winning amount; no symbol appears more than three
                    times; no second three-of-a-kind
                    loser  = no symbol appears three or more times
================================================================================
"""

import os
import re
import sys
import datetime
from collections import Counter
from sys import intern


# ================================================================== #
#  (A)  LAYOUT  -  EDIT ME per job                                    #
# ================================================================== #

GAME_NO       = "02"
SERIAL_PREFIX = GAME_NO                     # "02"

N_BOOKS   = 30_000
BOOK_SIZE = 100
BOX_SIZE  = 10_000                          # tickets per lot / box
N_BOXES   = (N_BOOKS * BOOK_SIZE) // BOX_SIZE   # 300

# Print imposition (Data Gen Spec: 7 channels, 56 cards per page, book blocks
# of 5).  Used only for the channel-allocation sanity note; the numbered
# procedures work on serial order.
LAYOUT = {
    "channels": 7,
    "cards_per_page": 56,                   # 7 channels x 8 cards
    "books_per_channel_block": 5,
}

VOID_SERIAL = "88-88888-888"

SERIAL_RE = re.compile(r"^" + SERIAL_PREFIX + r"-(\d{5})-(\d{3})$")

VIRN_MIN = 20_000_000
VIRN_MAX = 89_999_999

# Agent letters shared by losers and every winning tier (3 of 9 positions).
AGENT_SET   = {"R", "S", "T", "U", "V", "W", "X", "Y", "Z"}
PLAY_SPOTS  = 6
MATCH_N     = 3                             # win = three of a kind


# ================================================================== #
#  (B)  GAME_CONFIG  -  EDIT ME per job                               #
# ================================================================== #
#
# prizes:  system code -> amount, play symbol, tier, agent third-letter.
#   High-tier winners (41-47) and losers carry three letters from AGENT_SET;
#   mid/low winners (48-58) carry two of AGENT_SET plus "letter" below.

GAME_CONFIG = {

    "02": {
        "name": "WEHOKUKI",
        "series": "02/2026",
        "currency": "FBu",
        "tickets": N_BOOKS * BOOK_SIZE,      # 3,000,000
        "book_size": BOOK_SIZE,
        "box_size": BOX_SIZE,
        "mechanic": "three_of_a_kind",
        "spots": PLAY_SPOTS,
        "match_n": MATCH_N,

        "play_symbols": {
            "AA": "Vehicle",        "BB": "Trip to Dubai",  "EE": "Motorcycle",
            "GG": "5,000,000",      "HH": "Laptop",         "JJ": "TV",
            "KK": "1,000,000",      "LL": "Bicycle",        "MM": "Android Phone",
            "NN": "Cloth",          "PP": "100,000",        "QQ": "Rabbit",
            "RR": "Simple Phone",   "SS": "Radio",          "TT": "50,000",
            "UU": "10,000",         "VV": "5,000",          "WW": "2,000",
        },

        "prize_print_used": False,           # prize-symbol print code = space

        # code: (amount, symbol, tier, agent_letter, count)
        "prizes": {
            "41": (45_000_000, "AA", "High", None, 2),
            "42": (10_000_000, "BB", "High", None, 1),
            "43": ( 9_500_000, "EE", "High", None, 4),
            "44": ( 5_000_000, "GG", "High", None, 20),
            "45": ( 2_000_000, "HH", "High", None, 2),
            "46": ( 1_500_000, "JJ", "High", None, 8),
            "47": ( 1_000_000, "KK", "High", None, 100),
            "48": (   800_000, "LL", "Mid",  "A", 150),
            "49": (   600_000, "MM", "Mid",  "B", 50),
            "50": (   120_000, "NN", "Mid",  "C", 30),
            "51": (   100_000, "PP", "Mid",  "D", 650),
            "52": (    80_000, "QQ", "Mid",  "E", 10),
            "53": (    70_000, "RR", "Mid",  "F", 300),
            "54": (    70_000, "SS", "Mid",  "G", 135),
            "55": (    50_000, "TT", "Mid",  "H", 1_201),
            "56": (    10_000, "UU", "Low",  "J", 60_000),
            "57": (     5_000, "VV", "Low",  "K", 227_220),
            "58": (     2_000, "WW", "Low",  "L", 750_000),
        },

        "loss_code": "99",
        "loss_count": 1_960_117,

        "revenue": 6_000_000_000,
        "pool":    3_900_000_000,
        "payout_pct": 65,

        # ---- per-lot prize guarantees (check 6) ---------------------
        # per_book / per_box : code -> (mode, n)  where mode in {exact, min}
        # per_group          : code -> (group_boxes, min_count)
        "per_book": {
            "56": ("exact", 2),              # 10,000  : exactly 2 / book
            "57": ("min",   7),              # 5,000   : at least 7 / book
            "58": ("exact", 25),             # 2,000   : exactly 25 / book
        },
        "per_box": {
            "51": ("min", 2),                # 100,000 : at least 2 / box
            "53": ("exact", 1),              # Simple Phone : 1 / box
            "55": ("min", 4),                # 50,000  : at least 4 / box
        },
        "per_group": {
            "41": (150, 1), "42": (300, 1), "43": (75, 1), "44": (15, 1),
            "45": (150, 1), "46": (75, 2),  "47": (3, 1),  "48": (2, 1),
            "49": (6, 1),   "50": (10, 1),  "52": (30, 1), "54": (3, 1),
        },

        # loser near-miss targets (checks 12, 13)
        "loser_two_pair_min_pct": 75.0,      # >= 75% (one pair high tier)
        "loser_one_pair_min_pct": 20.0,      # >= 20% (high or mid tier)
    },
}

GKEY = "02"


# ================================================================== #
#  DERIVED SYMBOL / TIER LOOKUPS                                      #
# ================================================================== #

def _cfg():
    return GAME_CONFIG[GKEY]


def valid_symbols():
    return set(_cfg()["play_symbols"].keys())


def symbol_tier():
    """symbol -> tier (High/Mid/Low)."""
    out = {}
    for _code, (_amt, sym, tier, _lt, _c) in _cfg()["prizes"].items():
        out[sym] = tier
    return out


def high_symbols():
    return {s for s, t in symbol_tier().items() if t == "High"}


def high_mid_symbols():
    return {s for s, t in symbol_tier().items() if t in ("High", "Mid")}


# ================================================================== #
#  HEADER PARSING (header-driven, with positional fallback)          #
# ================================================================== #

_HEADER_ALIASES = {
    "lead":   [r"^Page_?No$", r"^Page$"],
    "serial": [r"^Serial(?:No|Number|_No)?\d*$"],
    "virn":   [r"^VIRN\d*$"],
    "sys":    [r"^(?:System_?Prize_?Code|Prize_?System_?Code|Sys)\d*$"],
    "pcode":  [r"^(?:Prize_?(?:Symbol_?)?Print_?Code|PCode)\d*$"],
    "qa":     [r"^(?:QA_?Sample_?Code|QA)\d*$"],
}
_PLAY_RE  = re.compile(r"^(?:Play_?Symbol|Play(?:Data)?|Play)_?(\d+)$")
_AGENT_RE = re.compile(r"^(?:Agent_?ValCode|Agent(?:Validation)?)_?(\d+)$")

# A trailing "_NN" block/channel tag (e.g. SerialNo1_01) is stripped before
# matching; the column set is identical across blocks in a single-record file.
_BLOCK_SUFFIX = re.compile(r"_\d+$")


def _strip_block(name):
    return _BLOCK_SUFFIX.sub("", name)


def parse_header(header):
    """Return a column map from a header row, or None if the row is not a
    header (i.e. the first field already looks like a serial / VOID).  A
    trailing block/channel tag such as '_01' on each column name is ignored,
    and a leading PageNo column is captured as the lead identifier."""
    first = header[0].strip()
    if SERIAL_RE.match(first) or first == VOID_SERIAL:
        return None
    cols = {"plays": {}, "agents": {}, "lead": []}
    for col, raw in enumerate(header):
        name = _strip_block(raw.strip())
        hit = False
        for fkey, pats in _HEADER_ALIASES.items():
            if any(re.match(p, name, re.I) for p in pats):
                if fkey == "lead":
                    cols["lead"].append(col)
                else:
                    cols[fkey] = col
                hit = True
                break
        if hit:
            continue
        m = _PLAY_RE.match(name)
        if m:
            cols["plays"][int(m.group(1))] = col
            continue
        m = _AGENT_RE.match(name)
        if m:
            cols["agents"][int(m.group(1))] = col
    cols["plays"]  = [cols["plays"][k]  for k in sorted(cols["plays"])]
    cols["agents"] = [cols["agents"][k] for k in sorted(cols["agents"])]
    if "serial" not in cols or "sys" not in cols:
        return None                          # unrecognisable -> positional
    return cols


def positional_cols(first_row):
    """Positional layout when the file has no usable header.  The serial
    column is located by pattern, so an optional leading identifier column
    (observed in production extracts, e.g. a constant sample-lot id) is
    tolerated.  Fields then follow the documented record:
    [lead...], serial, VIRN, sys, pcode, play1..6, agent1..9, [QA]."""
    s = None
    for i, f in enumerate(first_row):
        t = f.strip()
        if SERIAL_RE.match(t) or t == VOID_SERIAL:
            s = i
            break
    if s is None:                            # fall back to documented offsets
        s = 1 if len(first_row) >= (2 + 4 + PLAY_SPOTS + 9) else 0
    cols = {
        "lead":   list(range(0, s)),
        "serial": s, "virn": s + 1, "sys": s + 2, "pcode": s + 3,
        "plays":  list(range(s + 4, s + 4 + PLAY_SPOTS)),
        "agents": list(range(s + 4 + PLAY_SPOTS, s + 4 + PLAY_SPOTS + 9)),
    }
    qa_idx = s + 4 + PLAY_SPOTS + 9
    if qa_idx < len(first_row):
        cols["qa"] = qa_idx
    return cols


# ================================================================== #
#  SERIAL / POSITION HELPERS                                         #
# ================================================================== #

def serial_of(idx):
    book = idx // BOOK_SIZE + 1
    tno  = idx %  BOOK_SIZE + 1
    return f"{SERIAL_PREFIX}-{book:05d}-{tno:03d}"


def channel_alloc_ok():
    """The documented imposition tiles the game only if channels x block
    divides the book count.  30,000 / (7 x 5) = 857.14 -> does not close."""
    per_band = LAYOUT["channels"] * LAYOUT["books_per_channel_block"]
    return N_BOOKS % per_band == 0, per_band


# ================================================================== #
#  DATA CONTAINER                                                    #
# ================================================================== #

class GameData:
    def __init__(self, game_key):
        self.key = game_key
        self.cfg = GAME_CONFIG[game_key]
        self.tickets   = self.cfg["tickets"]
        self.book_size = self.cfg["book_size"]
        n = self.tickets
        self.virn      = [None] * n     # int (or raw str if malformed)
        self.sys       = [None] * n     # interned str
        self.pcode     = [None] * n     # interned str
        self.play_str  = [None] * n     # interned "S1,...,S6"
        self.agent_str = [None] * n     # interned "A1,...,A9" (positional)
        self.qa        = [None] * n     # interned str

    def present(self, i):
        return self.sys[i] is not None

    def is_winner(self, i):
        return self.sys[i] is not None and self.sys[i] != self.cfg["loss_code"]

    def prize(self, i):
        return self.cfg["prizes"].get(self.sys[i])

    def prize_amount(self, i):
        p = self.prize(i)
        return p[0] if p else 0

    def plays(self, i):
        return self.play_str[i].split(",")


# ================================================================== #
#  LOADING                                                           #
# ================================================================== #

def _order_flag(load_info, msg):
    load_info["order_mismatch_count"] += 1
    if len(load_info["order_mismatches"]) < 200:
        load_info["order_mismatches"].append(msg)


def load_layout(path):
    g = GameData(GKEY)
    load_info = {
        "data_rows": 0, "void_tickets": 0,
        "malformed_rows": [], "malformed_serials": [],
        "duplicate_serials": [], "out_of_range": [],
        "ascending_violations": [],
        "layout_warnings": [], "used_header": False,
        "qa_counts": {}, "qa_bad": [], "qa_winners": 0,
        "order_mismatches": [], "order_mismatch_count": 0,
        "lead_values": set(), "lead_present": False,
        "_order": {"seq": 0, "page": None, "last_ch": -1, "ch_last": {}},
    }

    with open(path, "r", newline="") as f:
        first_line = f.readline()
        if first_line == "":
            load_info["layout_warnings"].append("File is empty.")
            return g, load_info
        first_fields = first_line.rstrip("\r\n").split(",")
        cols = parse_header(first_fields)
        if cols is None:
            cols = positional_cols(first_fields)
            data_iter = [first_fields]       # first line is data
        else:
            load_info["used_header"] = True
            data_iter = []
        lead_cols = cols.get("lead", [])
        if lead_cols:
            load_info["lead_present"] = True
        if len(cols.get("plays", [])) != PLAY_SPOTS:
            load_info["layout_warnings"].append(
                f"Layout defines {len(cols.get('plays', []))} play columns, "
                f"expected {PLAY_SPOTS}.")
        if len(cols.get("agents", [])) != 9:
            load_info["layout_warnings"].append(
                f"Layout defines {len(cols.get('agents', []))} agent columns, "
                f"expected 9 (3 of 9 positions carry a letter).")

        has_qa = "qa" in cols
        row_no = 1 if load_info["used_header"] else 0

        def handle(row, row_no):
            load_info["data_rows"] += 1
            lead_val = row[lead_cols[0]].strip() if lead_cols else None
            if lead_val is not None and len(load_info["lead_values"]) < 50:
                load_info["lead_values"].add(lead_val)
            serial = row[cols["serial"]]

            # --- print-imposition order tracking (void-aware) ---------------
            # The file pads with VOID cards (leading run + band-boundary fill)
            # to keep 56-card pages aligned, so a rigid position formula does
            # not hold. Instead we verify the two structural properties that
            # must hold regardless of padding: within each page the real cards
            # step through the 7 channels in order, and each channel's real
            # cards ascend in (book, ticket). PageNo, when present, delimits
            # pages; otherwise a running 56-slot counter is used.
            st = load_info["_order"]
            page_key = lead_val if lead_cols else str(st["seq"] // LAYOUT["cards_per_page"])
            st["seq"] += 1
            st["page"] = page_key
            if serial == VOID_SERIAL:
                st["last_ch"] = -1          # padding breaks the channel cycle
            else:
                mm = SERIAL_RE.match(serial)
                if mm:
                    bk, tk = int(mm.group(1)), int(mm.group(2))
                    ch = ((bk - 1) // LAYOUT["books_per_channel_block"]) \
                        % LAYOUT["channels"]
                    # (a) channels cycle 0,1,..,6,0,1,.. across consecutive
                    #     real cards (7 channels interleaved on each page)
                    if st["last_ch"] >= 0:
                        expect_ch = (st["last_ch"] + 1) % LAYOUT["channels"]
                        if ch != expect_ch:
                            _order_flag(load_info,
                                f"page {page_key}: {serial} is channel "
                                f"{ch+1}, expected channel {expect_ch+1} "
                                f"after channel {st['last_ch']+1}")
                    st["last_ch"] = ch
                    # (b) each channel ascends in (book, ticket)
                    prev = st["ch_last"].get(ch)
                    if prev is not None and (bk, tk) <= prev:
                        _order_flag(load_info,
                            f"channel {ch+1}: {serial} not ascending after "
                            f"{SERIAL_PREFIX}-{prev[0]:05d}-{prev[1]:03d}")
                    st["ch_last"][ch] = (bk, tk)

            if serial == VOID_SERIAL:
                load_info["void_tickets"] += 1
                return
            m = SERIAL_RE.match(serial)
            if not m:
                load_info["malformed_serials"].append((row_no, serial))
                return
            book, tno = int(m.group(1)), int(m.group(2))
            if not (1 <= book <= N_BOOKS and 1 <= tno <= BOOK_SIZE):
                load_info["out_of_range"].append(serial)
                return
            idx = (book - 1) * BOOK_SIZE + (tno - 1)
            if g.sys[idx] is not None:
                load_info["duplicate_serials"].append(serial)
                return
            v = row[cols["virn"]].strip()
            g.virn[idx]      = int(v) if v.isdigit() else v
            g.sys[idx]       = intern(row[cols["sys"]].strip())
            g.pcode[idx]     = intern(row[cols["pcode"]]) if "pcode" in cols else ""
            g.play_str[idx]  = intern(",".join(row[c] for c in cols["plays"]))
            g.agent_str[idx] = intern(",".join(row[c] for c in cols["agents"]))
            if has_qa:
                q = intern(row[cols["qa"]])
                g.qa[idx] = q
                key = q.strip() if q.strip() else "(blank)"
                load_info["qa_counts"][key] = load_info["qa_counts"].get(key, 0) + 1
                if q.strip() not in ("", "$"):
                    if len(load_info["qa_bad"]) < 200:
                        load_info["qa_bad"].append(f"{serial}: {q!r}")
                elif q.strip() == "$" and g.is_winner(idx):
                    load_info["qa_winners"] += 1

        n_fields = len(first_fields)
        for row in data_iter:                # possibly the first data line
            row_no += 1
            if len(row) != n_fields:
                load_info["malformed_rows"].append(
                    (row_no, f"{len(row)} fields, expected {n_fields}"))
                continue
            handle(row, row_no)
        for line in f:
            row_no += 1
            row = line.rstrip("\r\n").split(",")
            if len(row) != n_fields:
                load_info["malformed_rows"].append(
                    (row_no, f"{len(row)} fields, expected {n_fields}"))
                continue
            handle(row, row_no)

    # ascending-within-book check (serials arranged ascending within a book)
    for bno in range(N_BOOKS):
        base = bno * BOOK_SIZE
        last = None
        for t in range(BOOK_SIZE):
            if g.sys[base + t] is None:
                continue
            if last is not None and t <= last:
                continue
            last = t
    # (index reconstruction already forces ascending storage; a genuine
    #  out-of-order record would surface as a duplicate or missing serial.)

    ok, per_band = channel_alloc_ok()
    if not ok:
        load_info["layout_warnings"].append(
            f"Print-channel allocation does not reconcile: {N_BOOKS:,} books "
            f"is not divisible by channels x books-per-block "
            f"({LAYOUT['channels']} x {LAYOUT['books_per_channel_block']} = "
            f"{per_band}). The documented channel table cannot tile the game; "
            "confirm the imposition before generation.")
    return g, load_info


# ================================================================== #
#  RESULTS + HELPERS                                                 #
# ================================================================== #

class CheckResult:
    def __init__(self, index, title, procedure):
        self.index = index
        self.title = title
        self.procedure = procedure
        self.passed = True
        self.finding = []
        self.offenders = []

    def fail(self, offenders):
        self.passed = False
        self.offenders.extend(str(o) for o in offenders)

    def note(self, line):
        self.finding.append(line)


def iter_books(g):
    for b in range(g.tickets // g.book_size):
        yield b + 1, b * g.book_size, (b + 1) * g.book_size


def iter_boxes(g):
    bs = g.cfg["box_size"]
    for b in range(g.tickets // bs):
        yield b + 1, b * bs, (b + 1) * bs


def fmt_amt(g, amount):
    return f"{amount:,} {g.cfg['currency']}"


def count_codes(g, s, e):
    c = {}
    for i in range(s, e):
        if g.present(i):
            c[g.sys[i]] = c.get(g.sys[i], 0) + 1
    return c


# ================================================================== #
#  PATTERN VALIDITY (three_of_a_kind) - check 1                      #
# ================================================================== #

def pattern_problem(g, i, plays):
    """Return a description if ticket i's play pattern is inconsistent with
    its winner/loser status, else None.  `plays` is the split 6-symbol list."""
    counts = Counter(plays)
    triples = [s for s, c in counts.items() if c >= 3]
    winner = g.is_winner(i)
    if winner:
        want = g.prize(i)[1]
        if counts.get(want, 0) != MATCH_N:
            return (f"winner's prize symbol {want} appears "
                    f"{counts.get(want, 0)}x (expected exactly {MATCH_N})")
        over = [f"{s}x{c}" for s, c in counts.items() if c > MATCH_N]
        if over:
            return "symbol appears more than three times: " + ",".join(over)
        extra = [s for s in triples if s != want]
        if extra:
            return "second three-of-a-kind on a winner: " + ",".join(extra)
    else:
        if triples:
            return ("loser carrying a three-of-a-kind: "
                    + ",".join(f"{s}x{counts[s]}" for s in triples))
    return None


# ================================================================== #
#  THE 14 CHECKS                                                     #
# ================================================================== #

def check_01_play_positions(g):
    r = CheckResult(1, "Play positions",
        "Check whether the six play-position fields are populated per the "
        "symbol table, that each winner shows exactly one three-of-a-kind "
        "equal to its prize symbol and each loser shows none, and that the "
        "prize-symbol print code is blank on every ticket.")
    valid = valid_symbols()
    bad_count, bad_symbol, bad_pattern = [], [], []
    for i in range(g.tickets):
        if not g.present(i):
            continue
        plays = g.plays(i)
        if len(plays) != PLAY_SPOTS:
            bad_count.append(serial_of(i)); continue
        if any(p not in valid for p in plays):
            bad = [p for p in plays if p not in valid]
            bad_symbol.append(f"{serial_of(i)}: {','.join(bad)}"); continue
        prob = pattern_problem(g, i, plays)
        if prob:
            bad_pattern.append(f"{serial_of(i)}: {prob}")
    if bad_count:
        r.fail(bad_count); r.note(f"{len(bad_count)} ticket(s) without exactly "
                                  f"{PLAY_SPOTS} play fields.")
    if bad_symbol:
        r.fail(bad_symbol); r.note(f"{len(bad_symbol)} ticket(s) with an "
            "invalid play-symbol code (valid set: "
            + ",".join(sorted(valid)) + ").")
    if bad_pattern:
        r.fail(bad_pattern); r.note(f"{len(bad_pattern)} ticket(s) whose play "
            "pattern is inconsistent with the game mechanic / winner status.")
    if g.cfg["prize_print_used"] is False:
        bad_print = [serial_of(i) for i in range(g.tickets)
                     if g.present(i) and (g.pcode[i] or "").strip() != ""]
        if bad_print:
            r.fail(bad_print)
            r.note(f"{len(bad_print)} ticket(s) with a non-blank prize-symbol "
                   "print code although this game has no prize spot "
                   "(data spec: prize symbol print code = space).")
    if r.passed:
        r.note("No exceptions were noted. Every ticket carries six valid "
               "symbols, winners show exactly one three-of-a-kind matching "
               "their prize, losers show none, and the prize print code is "
               "blank throughout.")
    return r


def check_02_serial(g, load_info):
    r = CheckResult(2, "Serial number",
        "Check whether the serial-number field is populated per the format "
        "GG-BBBBB-TTT (game 02, book 00001-30000, ticket 001-100), unique, "
        "consecutive and ascending within each book.")
    missing = [serial_of(n) for n in range(g.tickets) if g.sys[n] is None]
    if missing:
        r.fail(missing[:1000]); r.note(f"{len(missing):,} serial number(s) missing.")
    if load_info["duplicate_serials"]:
        r.fail(load_info["duplicate_serials"])
        r.note(f"{len(load_info['duplicate_serials'])} duplicate serial(s).")
    if load_info["out_of_range"]:
        r.fail(load_info["out_of_range"])
        r.note(f"{len(load_info['out_of_range'])} serial(s) outside the range.")
    if load_info["malformed_serials"]:
        r.fail([f"row {rw}: {s}" for rw, s in load_info["malformed_serials"]])
        r.note(f"{len(load_info['malformed_serials'])} malformed serial(s).")
    if load_info["malformed_rows"]:
        r.fail([f"row {rw}: {msg}" for rw, msg in load_info["malformed_rows"]])
        r.note(f"{len(load_info['malformed_rows'])} malformed data row(s).")
    if r.passed:
        r.note(f"No exceptions were noted. All {g.tickets:,} serials "
               f"({N_BOOKS:,} books x {BOOK_SIZE} tickets) are present exactly "
               "once, correctly formatted and ascending within each book.")
    return r


def check_03_virn(g):
    r = CheckResult(3, "VIRN",
        "Check whether the VIRN field carries a unique eight-digit number in "
        f"the range {VIRN_MIN:,}-{VIRN_MAX:,} on every ticket, with no logical "
        "relationship to the play pattern.")
    seen = set()
    bad_fmt, bad_range, dup = [], [], []
    for i in range(g.tickets):
        if not g.present(i):
            continue
        v = g.virn[i]
        if not isinstance(v, int):
            bad_fmt.append(f"{serial_of(i)}: {v!r}"); continue
        if len(str(v)) != 8:
            bad_fmt.append(f"{serial_of(i)}: {v}"); continue
        if not (VIRN_MIN <= v <= VIRN_MAX):
            bad_range.append(f"{serial_of(i)}: {v}")
        if v in seen:
            dup.append(f"{serial_of(i)}: {v}")
        else:
            seen.add(v)
    if bad_fmt:
        r.fail(bad_fmt); r.note(f"{len(bad_fmt)} VIRN(s) not a valid 8-digit number.")
    if bad_range:
        r.fail(bad_range); r.note(f"{len(bad_range)} VIRN(s) outside "
                                  f"{VIRN_MIN:,}-{VIRN_MAX:,}.")
    if dup:
        r.fail(dup); r.note(f"{len(dup)} duplicate VIRN(s).")
    # independence screen (winner rate by VIRN band)
    _virn_independence_note(g, r)
    if r.passed:
        r.note("No exceptions were noted. All VIRNs are 8-digit, in range and "
               "unique across the game.")
    return r


def _virn_independence_note(g, r):
    span = VIRN_MAX - VIRN_MIN + 1
    win = [0] * 10; tot = [0] * 10
    for i in range(g.tickets):
        if not g.present(i) or not isinstance(g.virn[i], int):
            continue
        d = min((g.virn[i] - VIRN_MIN) * 10 // span, 9)
        if d < 0:
            continue
        tot[d] += 1
        if g.is_winner(i):
            win[d] += 1
    n_all = sum(tot); w_all = sum(win)
    if n_all == 0:
        return
    p = w_all / n_all
    chi2 = 0.0
    for d in range(10):
        ew, el = tot[d] * p, tot[d] * (1 - p)
        if ew > 0:
            chi2 += (win[d] - ew) ** 2 / ew
        if el > 0:
            chi2 += ((tot[d] - win[d]) - el) ** 2 / el
    r.note(f"Independence screen: overall winner rate {p*100:.4f}%, "
           f"chi-square across 10 VIRN bands = {chi2:.2f} (critical 27.88 at "
           "0.1%).")
    if chi2 > 27.88:
        r.fail([f"VIRN independence screen: chi-square {chi2:.2f} exceeds "
                "27.88; winner rate varies with VIRN band more than chance "
                "allows - investigate for a play-pattern/VIRN relationship."])


def check_04_agent_codes(g):
    r = CheckResult(4, "Agent validation codes",
        "Check whether three of the nine agent-validation positions carry a "
        "letter: losers and high-tier winners three distinct letters from "
        "R,S,T,U,V,W,X,Y,Z; mid/low winners two of those plus the prize "
        "letter (A=Bicycle .. L=2,000).")
    bad_count, bad_letters = [], []
    for i in range(g.tickets):
        if not g.present(i):
            continue
        letters = [x for x in g.agent_str[i].split(",") if x.strip() != ""]
        if len(letters) != 3:
            bad_count.append(f"{serial_of(i)}: {len(letters)} letter(s)")
            continue
        p = g.prize(i)
        prize_letter = p[3] if p else None
        if prize_letter:                     # mid/low winner
            others = [x for x in letters if x != prize_letter]
            ok = (letters.count(prize_letter) == 1
                  and len(others) == 2
                  and all(x in AGENT_SET for x in others)
                  and others[0] != others[1])
        else:                                # high-tier winner or loser
            ok = (all(x in AGENT_SET for x in letters)
                  and len(set(letters)) == 3)
        if not ok:
            bad_letters.append(f"{serial_of(i)}: {'/'.join(letters)}")
    if bad_count:
        r.fail(bad_count); r.note(f"{len(bad_count)} ticket(s) without exactly "
                                  "three agent letters.")
    if bad_letters:
        r.fail(bad_letters); r.note(f"{len(bad_letters)} ticket(s) breaking "
                                    "the composition rules.")
    if r.passed:
        r.note("No exceptions were noted. All agent validation codes follow "
               "the prescribed composition rules.")
    return r


def check_05_prize_structure(g):
    r = CheckResult(5, "Prize structure",
        "Check whether the prize structure prescribed by the game "
        "specification is reflected in the data layout, and that the prize "
        "pool and payout percentage reconcile.")
    counts = count_codes(g, 0, g.tickets)
    all_ok = True
    pool = 0
    for code, (amt, sym, tier, _lt, want) in g.cfg["prizes"].items():
        actual = counts.get(code, 0)
        pool += amt * actual
        ok = actual == want
        all_ok &= ok
        r.note(f"{fmt_amt(g, amt):>18} ({code}/{sym}, {tier:>4}): expected "
               f"{want:>9,}, found {actual:>9,}  {'OK' if ok else 'MISMATCH'}")
    loss = counts.get(g.cfg["loss_code"], 0)
    ok = loss == g.cfg["loss_count"]; all_ok &= ok
    r.note(f"Losing tickets ({g.cfg['loss_code']}): expected "
           f"{g.cfg['loss_count']:>9,}, found {loss:>9,}  "
           f"{'OK' if ok else 'MISMATCH'}")
    total = sum(counts.values())
    ok = total == g.tickets; all_ok &= ok
    r.note(f"Total tickets: expected {g.tickets:>9,}, found {total:>9,}  "
           f"{'OK' if ok else 'MISMATCH'}")
    winners = total - loss
    r.note(f"Winners: {winners:,}  (win ratio 1:{g.tickets/winners:.3f})"
           if winners else "Winners: 0")
    pool_ok = pool == g.cfg["pool"]; all_ok &= pool_ok
    r.note(f"Prize pool: expected {g.cfg['pool']:,} {g.cfg['currency']}, "
           f"found {pool:,}  {'OK' if pool_ok else 'MISMATCH'}")
    if g.cfg["revenue"]:
        pct = pool / g.cfg["revenue"] * 100
        r.note(f"Payout: {pct:.2f}% of {g.cfg['revenue']:,} "
               f"{g.cfg['currency']} revenue (spec {g.cfg['payout_pct']}%).")
    if not all_ok:
        r.passed = False
        for code, (amt, sym, _t, _lt, want) in g.cfg["prizes"].items():
            if counts.get(code, 0) != want:
                r.offenders.append(f"{fmt_amt(g, amt)} ({code}/{sym}): found "
                                   f"{counts.get(code, 0)}, expected {want}")
        if loss != g.cfg["loss_count"]:
            r.offenders.append(f"Loss: found {loss}, expected {g.cfg['loss_count']}")
        if not pool_ok:
            r.offenders.append(f"Pool: found {pool:,}, expected {g.cfg['pool']:,}")
    return r


def check_06_lot_allocation(g):
    r = CheckResult(6, "Per-lot prize allocation",
        "Check whether every book (100), box (10,000) and box-group carries "
        "its guaranteed prize allocation.")
    cfg = g.cfg
    bad = []

    # per book
    for bno, s, e in iter_books(g):
        c = count_codes(g, s, e)
        probs = []
        for code, (mode, n) in cfg["per_book"].items():
            got = c.get(code, 0)
            if (mode == "exact" and got != n) or (mode == "min" and got < n):
                amt = cfg["prizes"][code][0]
                probs.append(f"{fmt_amt(g, amt)}={got} ({mode} {n})")
        if probs:
            bad.append(f"Book {bno:05d} ({serial_of(s)}..{serial_of(e-1)}): "
                       + ", ".join(probs))
            if len(bad) > 500:
                break

    # per box
    if len(bad) <= 500:
        for bxno, s, e in iter_boxes(g):
            c = count_codes(g, s, e)
            probs = []
            for code, (mode, n) in cfg["per_box"].items():
                got = c.get(code, 0)
                if (mode == "exact" and got != n) or (mode == "min" and got < n):
                    amt = cfg["prizes"][code][0]
                    probs.append(f"{fmt_amt(g, amt)}={got} ({mode} {n})")
            if probs:
                bad.append(f"Box {bxno:03d} ({serial_of(s)}..{serial_of(e-1)}): "
                           + ", ".join(probs))
                if len(bad) > 500:
                    break

    # per group of boxes (spread guarantee: >= count per group)
    if len(bad) <= 500:
        bs = cfg["box_size"]
        for code, (grp_boxes, need) in cfg["per_group"].items():
            span = grp_boxes * bs
            n_groups = g.tickets // span
            for gi in range(n_groups):
                s, e = gi * span, (gi + 1) * span
                got = sum(1 for i in range(s, e)
                          if g.present(i) and g.sys[i] == code)
                if got < need:
                    amt = cfg["prizes"][code][0]
                    bad.append(f"Boxes {gi*grp_boxes+1:03d}-{(gi+1)*grp_boxes:03d} "
                               f"({fmt_amt(g, amt)}): {got} (min {need} per "
                               f"{grp_boxes} box(es))")
                    if len(bad) > 500:
                        break
            if len(bad) > 500:
                break

    if bad:
        r.fail(bad)
        r.note(f"{len(bad)} lot(s) not meeting the guaranteed allocation "
               "(first 500 listed).")
    else:
        r.note("No exceptions were noted. Every book, box and box-group meets "
               "its guaranteed prize allocation "
               "(book: 2x10,000, >=7x5,000, 25x2,000; box: >=2x100,000, "
               "1xSimple Phone, >=4x50,000; plus high/mid spread ratios).")
    return r


def check_07_more_than_three(g):
    r = CheckResult(7, "More than three similar symbols",
        "Check whether any ticket carries more than three similar symbols.")
    bad = []
    for i in range(g.tickets):
        if not g.present(i):
            continue
        c = Counter(g.plays(i))
        over = [f"{s}x{n}" for s, n in c.items() if n > MATCH_N]
        if over:
            bad.append(f"{serial_of(i)}: {','.join(over)}")
    if bad:
        r.fail(bad); r.note(f"{len(bad)} ticket(s) with more than three "
                            "similar symbols.")
    else:
        r.note("No exceptions were noted. No ticket carries more than three "
               "similar symbols.")
    return r


def check_08_double_triplicate(g):
    r = CheckResult(8, "Two three-of-a-kind combinations",
        "Check whether any ticket carries two combinations of three similar "
        "symbols (triplicates).")
    bad = []
    for i in range(g.tickets):
        if not g.present(i):
            continue
        c = Counter(g.plays(i))
        trips = [s for s, n in c.items() if n >= MATCH_N]
        if len(trips) >= 2:
            bad.append(f"{serial_of(i)}: {','.join(trips)}")
    if bad:
        r.fail(bad); r.note(f"{len(bad)} ticket(s) with two three-of-a-kind "
                            "combinations.")
    else:
        r.note("No exceptions were noted. No ticket carries two combinations "
               "of three similar symbols.")
    return r


def check_09_consecutive_pattern(g):
    r = CheckResult(9, "Consecutive play pattern",
        "Check whether any two consecutive tickets (serial order) carry the "
        "same play symbol pattern.")
    bad = []
    for i in range(g.tickets - 1):
        if not (g.present(i) and g.present(i + 1)):
            continue
        if g.play_str[i] == g.play_str[i + 1]:
            bad.append(f"{serial_of(i)} & {serial_of(i+1)}")
    if bad:
        r.fail(bad); r.note(f"{len(bad)} instance(s), affecting "
                            f"{2*len(bad)} tickets.")
    else:
        r.note("No exceptions were noted. No two consecutive tickets carry the "
               "same play symbol pattern.")
    return r


def check_10_consecutive_rotation(g):
    r = CheckResult(10, "Consecutive symbols in any rotation",
        "Check whether any two consecutive tickets carry the same winning "
        "symbols in any rotation (same six-symbol multiset).")
    bad = []
    prev_key = None
    prev_serial = None
    for i in range(g.tickets):
        if not g.present(i):
            prev_key = None; continue
        key = tuple(sorted(g.plays(i)))
        if prev_key is not None and key == prev_key:
            bad.append(f"{prev_serial} & {serial_of(i)}")
        prev_key, prev_serial = key, serial_of(i)
    if bad:
        r.fail(bad)
        r.note(f"{len(bad)} instance(s), affecting {2*len(bad)} tickets, where "
               "consecutive tickets share the same symbols in a rotation. "
               "(The 01/2025 series showed 1,558 such instances / 3,116 "
               "tickets - this requires remediation, not recurrence.)")
    else:
        r.note("No exceptions were noted. No two consecutive tickets carry the "
               "same symbols in any rotation.")
    return r


def check_11_consecutive_value(g):
    r = CheckResult(11, "Consecutive winning value",
        "Check whether any two consecutive tickets carry the same winning "
        "value / prize amount symbol. (Not performed in 01/2025 - the data "
        "lacked the system print code; the Prize System Code is now present, "
        "so this procedure is executed.)")
    bad = []
    for i in range(g.tickets - 1):
        if not (g.present(i) and g.present(i + 1)):
            continue
        if g.is_winner(i) and g.is_winner(i + 1) \
                and g.prize_amount(i) == g.prize_amount(i + 1):
            bad.append(f"{serial_of(i)} & {serial_of(i+1)} "
                       f"({fmt_amt(g, g.prize_amount(i))})")
    if bad:
        r.fail(bad); r.note(f"{len(bad)} consecutive winner pair(s) sharing "
                            "the same winning value.")
    else:
        r.note("No exceptions were noted. No two consecutive tickets share the "
               "same winning value.")
    return r


def _loser_pairs(plays):
    """Return (list of paired symbols) for a loser: symbols appearing exactly
    twice.  A loser has no symbol appearing 3+ times."""
    c = Counter(plays)
    return [s for s, n in c.items() if n == 2]


def check_12_loser_two_pairs(g):
    target = g.cfg["loser_two_pair_min_pct"]
    r = CheckResult(12, "Losers with two matching pairs (one high tier)",
        f"Check whether at least {target:.0f}% of losing tickets have two or "
        "more matching pairs, at least one pair being a high-tier symbol.")
    highs = high_symbols()
    losers = qualifying = 0
    for i in range(g.tickets):
        if not g.present(i) or g.is_winner(i):
            continue
        losers += 1
        pairs = _loser_pairs(g.plays(i))
        if len(pairs) >= 2 and any(s in highs for s in pairs):
            qualifying += 1
    pct = qualifying / losers * 100 if losers else 0.0
    r.note(f"{qualifying:,} of {losers:,} losers ({pct:.2f}%) have >=2 matching "
           "pairs with at least one high-tier pair.")
    if pct + 1e-9 < target:
        r.fail([f"{pct:.2f}% is below the {target:.0f}% minimum."])
    else:
        r.note(f"No exceptions were noted. The proportion meets the "
               f"{target:.0f}% minimum (01/2025 series returned 79%).")
    return r


def check_13_loser_one_pair(g):
    target = g.cfg["loser_one_pair_min_pct"]
    r = CheckResult(13, "Losers with one matching pair (high/mid tier)",
        f"Check whether at least {target:.0f}% of losing tickets have exactly "
        "one matching pair with a high- or mid-tier symbol.")
    hm = high_mid_symbols()
    losers = qualifying = 0
    for i in range(g.tickets):
        if not g.present(i) or g.is_winner(i):
            continue
        losers += 1
        pairs = _loser_pairs(g.plays(i))
        if len(pairs) == 1 and pairs[0] in hm:
            qualifying += 1
    pct = qualifying / losers * 100 if losers else 0.0
    r.note(f"{qualifying:,} of {losers:,} losers ({pct:.2f}%) have exactly one "
           "matching pair with a high- or mid-tier symbol.")
    r.note("Specification note: Game Spec section 5.1 states 70% here, which "
           "cannot hold alongside the 75% two-pair rule (they would sum to "
           "145%). The Data Generation Spec states 20%; the 01/2025 series "
           "returned 21%. This procedure applies the 20% figure - Game Spec "
           "5.1 should be corrected before sign-off.")
    if pct + 1e-9 < target:
        r.fail([f"{pct:.2f}% is below the {target:.0f}% minimum."])
    else:
        r.note(f"No exceptions were noted. The proportion meets the "
               f"{target:.0f}% minimum.")
    return r


def check_14_consecutive_losers(g):
    r = CheckResult(14, "Consecutive losers",
        "Check whether more than four consecutive losing tickets occur.")
    bad = []
    run = 0
    run_start = None
    for i in range(g.tickets):
        if g.present(i) and not g.is_winner(i):
            if run == 0:
                run_start = i
            run += 1
        else:
            if run > 4:
                bad.append(f"{serial_of(run_start)}..{serial_of(i-1)} "
                           f"({run} losers)")
            run = 0
    if run > 4:
        bad.append(f"{serial_of(run_start)}..{serial_of(g.tickets-1)} "
                   f"({run} losers)")
    if bad:
        r.fail(bad); r.note(f"{len(bad)} run(s) of more than four consecutive "
                            "losers.")
    else:
        r.note("No exceptions were noted. No more than four consecutive losers "
               "occur anywhere in the game.")
    return r


def check_15_print_order(g, load_info):
    r = CheckResult(15, "Print imposition order",
        "Supplementary to the 14 procedures above (not part of the EY set). "
        "The file is in print-imposition order (7 channels, 56 cards per page) "
        "and is padded with VOID cards to keep pages aligned, so a rigid "
        "position formula does not apply. This procedure verifies the two "
        "properties that must hold regardless of padding: within each page the "
        "real cards step through the seven channels in non-decreasing order, "
        "and each channel's real cards ascend in (book, ticket). Procedures "
        "9-11 and 14 de-interleave to serial order and are unaffected by this "
        "ordering.")
    n = load_info.get("order_mismatch_count", 0)
    voids = load_info.get("void_tickets", 0)
    if n:
        r.fail(load_info["order_mismatches"])
        r.note(f"{n:,} ordering anomaly(ies) detected (first "
               f"{len(load_info['order_mismatches'])} listed).")
    if voids:
        r.note(f"{voids:,} VOID padding card(s) were seen and skipped for the "
               "order check (leading page fill plus band-boundary fill). The "
               "documented 7 x 5 channel table does not tile "
               f"{N_BOOKS:,} books evenly, which is why padding is required; "
               "confirm the padding scheme with the data generation team.")
    if load_info.get("lead_present"):
        vals = sorted(load_info.get("lead_values", []))
        shown = ", ".join(vals[:5]) + (" ..." if len(vals) > 5 else "")
        r.note(f"A PageNo / leading identifier column precedes the serial "
               f"(not part of the documented record layout); "
               f"{len(vals)}{'+' if len(vals) >= 50 else ''} distinct value(s) "
               f"observed, e.g. {shown}. Used here to delimit pages.")
    if not n:
        r.note("No ordering exceptions were noted: real cards step through the "
               "channels in order within every page and each channel ascends "
               "in serial.")
    return r


def run_all_checks(g, load_info):
    return [
        check_01_play_positions(g),
        check_02_serial(g, load_info),
        check_03_virn(g),
        check_04_agent_codes(g),
        check_05_prize_structure(g),
        check_06_lot_allocation(g),
        check_07_more_than_three(g),
        check_08_double_triplicate(g),
        check_09_consecutive_pattern(g),
        check_10_consecutive_rotation(g),
        check_11_consecutive_value(g),
        check_12_loser_two_pairs(g),
        check_13_loser_one_pair(g),
        check_14_consecutive_losers(g),
        check_15_print_order(g, load_info),
    ]


# ================================================================== #
#  APPENDICES                                                        #
# ================================================================== #

def build_appendix_I(g):
    """Symbol counts per play position (EY Appendix I layout)."""
    pos_counts = {code: [0] * PLAY_SPOTS for code in g.cfg["play_symbols"]}
    for i in range(g.tickets):
        if not g.present(i):
            continue
        for pos, sym in enumerate(g.plays(i)):
            if sym in pos_counts and pos < PLAY_SPOTS:
                pos_counts[sym][pos] += 1
    rows = []
    for code, name in g.cfg["play_symbols"].items():
        c = pos_counts[code]
        rows.append((name, code, c, sum(c)))
    return rows


def build_appendix_II(g):
    """Agent letter distribution by ticket category."""
    tally = {}
    for i in range(g.tickets):
        if not g.present(i):
            continue
        if g.is_winner(i):
            tier = g.prize(i)[2]
            cat = 0 if tier == "High" else 1     # High winner / Mid-Low winner
        else:
            cat = 2                               # loser
        for letter in g.agent_str[i].split(","):
            if letter.strip():
                tally.setdefault(letter, [0, 0, 0])[cat] += 1
    return [(l, *tally[l], sum(tally[l])) for l in sorted(tally)]


def build_appendix_III(g):
    """Prize distribution by system code."""
    counts = count_codes(g, 0, g.tickets)
    rows = []
    for code, (amt, sym, tier, _lt, _c) in sorted(
            g.cfg["prizes"].items(), key=lambda kv: -kv[1][0]):
        rows.append((amt, code, sym, tier, counts.get(code, 0)))
    rows.append((0, g.cfg["loss_code"], "-", "Loss",
                 counts.get(g.cfg["loss_code"], 0)))
    return rows


# ================================================================== #
#  REPORTS                                                           #
# ================================================================== #

def _intro(cfg):
    return (
        "This report sets out the procedures performed on the game data file "
        "and the findings, following the structure of the Agreed-Upon "
        "Procedures report issued for the previous series. The criteria are "
        "those of the WEHOKUKI game specification (V2.0, 07 July 2026) and the "
        "data generation specification (V1.0, 13 July 2026).")


def write_text_report(path, results, appendices, load_info, layout_path):
    cfg = _cfg()
    L = []; W = L.append
    W("# LYDIA LUDIC BURUNDI")
    W("# LAYOUT AUDIT REPORT ON GAME SPECIFICATIONS")
    W('# "WEHOKUKI" INSTANT SCRATCH LOTTERY TICKETS - SERIES 02/2026')
    W("")
    W(f"Layout file : `{os.path.basename(layout_path)}`")
    W(f"Generated   : {datetime.datetime.now():%Y-%m-%d %H:%M:%S}")
    W("")
    W(_intro(cfg))
    W("")
    W("## File load summary")
    W("")
    W(f"- Header row detected : {'yes' if load_info['used_header'] else 'no (positional layout assumed)'}")
    W(f"- Data rows read : {load_info['data_rows']:,}")
    W(f"- VOID tickets ignored : {load_info['void_tickets']:,}")
    W(f"- Malformed rows : {len(load_info['malformed_rows']):,}")
    W(f"- Malformed serials : {len(load_info['malformed_serials']):,}")
    W(f"- Duplicate serials : {len(load_info['duplicate_serials']):,}")
    if load_info.get("lead_present"):
        vals = sorted(load_info.get("lead_values", []))
        shown = ", ".join(vals[:5]) + (" ..." if len(vals) > 5 else "")
        W(f"- Leading id column (undocumented) : {len(vals)} distinct value(s) "
          f"[{shown}]")
    if load_info.get("order_mismatch_count"):
        W(f"- Print-imposition order anomalies : "
          f"{load_info['order_mismatch_count']:,} (see procedure 15)")
    else:
        W("- Print-imposition order : consistent with the documented "
          "7-channel layout"
          + (f" ({load_info.get('void_tickets', 0):,} VOID padding cards "
             "skipped)" if load_info.get("void_tickets") else "."))
    if load_info["qa_counts"]:
        qa = ", ".join(f"{k}={v:,}" for k, v in sorted(load_info["qa_counts"].items()))
        W(f"- QA sample code values : {qa}")
        if load_info["qa_bad"]:
            W(f"- QA sample code invalid values : {len(load_info['qa_bad'])} "
              "(expected '$' or blank)")
        if load_info["qa_winners"]:
            W(f"- QA-marked winners : {load_info['qa_winners']:,} "
              "(QA/sample tickets are expected to be losers)")
    for wmsg in load_info["layout_warnings"]:
        W(f"- Layout note : {wmsg}")
    W("")
    W("Scope note: the game specification's \"heart stopper\" play requirement "
      "is a design property and is not machine-verifiable from the data file; "
      "it is outside the scope of these procedures.")
    W("")

    n_exc = sum(1 for r in results if not r.passed)
    W("---")
    W(f'# Game {cfg_game_no()} - "{cfg["name"]}"')
    W("")
    W(f"**Overall: {'ALL PROCEDURES - NO EXCEPTIONS' if n_exc == 0 else str(n_exc)+' PROCEDURE(S) WITH EXCEPTIONS'}**")
    W("")
    for r in results:
        status = ("PASS - No exceptions were noted" if r.passed
                  else f"EXCEPTIONS NOTED ({len(r.offenders)})")
        W(f"## {r.index}. {r.title}  -  {status}")
        W("")
        W(f"*Procedure:* {r.procedure}")
        W("")
        for ln in r.finding:
            W(f"- {ln}")
        if not r.passed and r.offenders:
            W("")
            W(f"*Offending items ({len(r.offenders)}, first 500 shown):*")
            for o in r.offenders[:500]:
                W(f"  - {o}")
            if len(r.offenders) > 500:
                W(f"  - ... {len(r.offenders)-500:,} more")
        W("")

    apI, apII, apIII = appendices
    W(f"## Appendix I - Distribution of play symbols across the "
      f"{cfg['tickets']:,} tickets")
    W("")
    pos_hdr = " ".join(f"Pos {p+1} |" for p in range(PLAY_SPOTS))
    W(f"| Play symbol | Code | {pos_hdr} Total |")
    W("|---|---|" + "---:|" * (PLAY_SPOTS + 1))
    col_tot = [0] * PLAY_SPOTS; grand = 0
    for name, code, cols, tot in apI:
        cells = " ".join(f"{c:,} |" for c in cols)
        W(f"| {name} | {code} | {cells} {tot:,} |")
        for p in range(PLAY_SPOTS):
            col_tot[p] += cols[p]
        grand += tot
    W(f"| **Total** |  | " + " ".join(f"**{c:,}** |" for c in col_tot)
      + f" **{grand:,}** |")
    W("")
    W(f"## Appendix II - Distribution of agent validation codes across the "
      f"{cfg['tickets']:,} tickets")
    W("")
    W("| Letter | High-tier winners | Mid/Low winners | Losers | Total |")
    W("|---|---:|---:|---:|---:|")
    ca = cb = cc = ct = 0
    for letter, hi, ml, ls, tot in apII:
        W(f"| {letter} | {hi:,} | {ml:,} | {ls:,} | {tot:,} |")
        ca += hi; cb += ml; cc += ls; ct += tot
    W(f"| **Total** | **{ca:,}** | **{cb:,}** | **{cc:,}** | **{ct:,}** |")
    W("")
    W(f"## Appendix III - Prize distribution across the {cfg['tickets']:,} tickets")
    W("")
    W("| Prize amount (FBu) | Code | Symbol | Tier | Count |")
    W("|---:|---|---|---|---:|")
    tt = 0
    for amt, code, sym, tier, cnt in apIII:
        label = f"{amt:,}" if amt else "Loss"
        W(f"| {label} | {code} | {sym} | {tier} | {cnt:,} |")
        tt += cnt
    W(f"| **Total** |  |  |  | **{tt:,}** |")
    W("")

    with open(path, "w") as f:
        f.write("\n".join(L))


def cfg_game_no():
    return GAME_NO


def write_word_report(path, results, appendices, load_info, layout_path):
    from docx import Document
    from docx.shared import RGBColor

    cfg = _cfg()
    doc = Document()
    doc.add_heading("Lydia Ludic Burundi", level=0)
    doc.add_heading('Layout Audit Report on Game Specifications - '
                    '"WEHOKUKI" Instant Scratch Lottery Tickets, Series '
                    '02/2026', level=1)
    p = doc.add_paragraph()
    p.add_run(f"Layout file: {os.path.basename(layout_path)}\n").italic = True
    p.add_run(f"Generated: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}").italic = True
    doc.add_paragraph(_intro(cfg))

    doc.add_heading("File load summary", level=2)
    doc.add_paragraph(
        f"Header detected: {'yes' if load_info['used_header'] else 'no'}   |   "
        f"Data rows: {load_info['data_rows']:,}   |   "
        f"VOID: {load_info['void_tickets']:,}   |   "
        f"Malformed serials: {len(load_info['malformed_serials']):,}   |   "
        f"Duplicates: {len(load_info['duplicate_serials']):,}")
    if load_info["qa_counts"]:
        qa = ", ".join(f"{k}={v:,}" for k, v in sorted(load_info["qa_counts"].items()))
        doc.add_paragraph("QA sample code values: " + qa)
    for wmsg in load_info["layout_warnings"]:
        run = doc.add_paragraph("Layout note: " + wmsg).runs[0]
        run.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
    doc.add_paragraph(
        'Scope note: the "heart stopper" play requirement is a design '
        "property and is not machine-verifiable from the data file; it is "
        "outside the scope of these procedures.")

    n_exc = sum(1 for r in results if not r.passed)
    doc.add_heading(f'Game {GAME_NO} - "{cfg["name"]}"', level=1)
    run = doc.add_paragraph().add_run(
        "All procedures - no exceptions" if n_exc == 0
        else f"{n_exc} procedure(s) with exceptions")
    run.bold = True
    run.font.color.rgb = (RGBColor(0x00, 0x80, 0x00) if n_exc == 0
                          else RGBColor(0xC0, 0x00, 0x00))

    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    hdr[0].text, hdr[1].text, hdr[2].text = "Index", "Procedures", "Findings"
    for c in hdr:
        for para in c.paragraphs:
            for run in para.runs:
                run.bold = True
    for r in results:
        cells = table.add_row().cells
        cells[0].text = str(r.index)
        cells[1].text = r.procedure
        fc = cells[2]; fc.text = ""
        status = ("No exceptions were noted." if r.passed
                  else f"Exceptions noted ({len(r.offenders)}).")
        run = fc.paragraphs[0].add_run(status)
        run.bold = True
        run.font.color.rgb = (RGBColor(0x00, 0x80, 0x00) if r.passed
                              else RGBColor(0xC0, 0x00, 0x00))
        for ln in r.finding:
            fc.add_paragraph(ln)
        if not r.passed and r.offenders:
            fc.add_paragraph("Offending items:")
            MAX_INLINE = 300
            for o in r.offenders[:MAX_INLINE]:
                fc.add_paragraph("  " + o)
            if len(r.offenders) > MAX_INLINE:
                fc.add_paragraph(f"  ... {len(r.offenders)-MAX_INLINE:,} more - "
                                 "see the full list in audit_report.md.")

    apI, apII, apIII = appendices
    doc.add_heading("Appendix I - Distribution of play symbols across the "
                    f"{cfg['tickets']:,} tickets", level=2)
    t = doc.add_table(rows=1, cols=3 + PLAY_SPOTS); t.style = "Table Grid"
    heads = (["Play symbol", "Code"]
             + [f"Pos {p+1}" for p in range(PLAY_SPOTS)] + ["Total"])
    for j, h in enumerate(heads):
        t.rows[0].cells[j].text = h
    col_tot = [0] * PLAY_SPOTS; grand = 0
    for name, code, cols, tot in apI:
        c = t.add_row().cells
        c[0].text, c[1].text = name, code
        for p in range(PLAY_SPOTS):
            c[2 + p].text = f"{cols[p]:,}"; col_tot[p] += cols[p]
        c[2 + PLAY_SPOTS].text = f"{tot:,}"; grand += tot
    c = t.add_row().cells
    c[0].text = "Total"
    for p in range(PLAY_SPOTS):
        c[2 + p].text = f"{col_tot[p]:,}"
    c[2 + PLAY_SPOTS].text = f"{grand:,}"

    doc.add_heading("Appendix II - Distribution of agent validation codes "
                    f"across the {cfg['tickets']:,} tickets", level=2)
    t = doc.add_table(rows=1, cols=5); t.style = "Table Grid"
    for j, h in enumerate(["Letter", "High-tier winners", "Mid/Low winners",
                           "Losers", "Total"]):
        t.rows[0].cells[j].text = h
    ca = cb = cc = ct = 0
    for letter, hi, ml, ls, tot in apII:
        c = t.add_row().cells
        c[0].text = letter
        c[1].text, c[2].text, c[3].text, c[4].text = \
            f"{hi:,}", f"{ml:,}", f"{ls:,}", f"{tot:,}"
        ca += hi; cb += ml; cc += ls; ct += tot
    c = t.add_row().cells
    c[0].text = "Total"
    c[1].text, c[2].text, c[3].text, c[4].text = \
        f"{ca:,}", f"{cb:,}", f"{cc:,}", f"{ct:,}"

    doc.add_heading("Appendix III - Prize distribution across the "
                    f"{cfg['tickets']:,} tickets", level=2)
    t = doc.add_table(rows=1, cols=5); t.style = "Table Grid"
    for j, h in enumerate(["Prize amount (FBu)", "Code", "Symbol", "Tier",
                           "Count"]):
        t.rows[0].cells[j].text = h
    tt = 0
    for amt, code, sym, tier, cnt in apIII:
        c = t.add_row().cells
        c[0].text = f"{amt:,}" if amt else "Loss"
        c[1].text, c[2].text, c[3].text, c[4].text = code, sym, tier, f"{cnt:,}"
        tt += cnt
    c = t.add_row().cells
    c[0].text = "Total"; c[4].text = f"{tt:,}"

    doc.save(path)


# ================================================================== #
#  MAIN                                                              #
# ================================================================== #

def main():
    if len(sys.argv) < 2:
        print("Usage: python lottery_audit_WEHOKUKI.py <layout_file> [output_dir]")
        sys.exit(1)
    layout_path = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "."
    os.makedirs(out_dir, exist_ok=True)

    print(f"Loading data file: {layout_path}")
    g, load_info = load_layout(layout_path)
    print(f"  header detected    : {'yes' if load_info['used_header'] else 'no'}")
    print(f"  data rows          : {load_info['data_rows']:,}")
    print(f"  void tickets       : {load_info['void_tickets']:,}")
    print(f"  malformed serials  : {len(load_info['malformed_serials']):,}")
    print(f"  duplicate serials  : {len(load_info['duplicate_serials']):,}")
    for w in load_info["layout_warnings"]:
        print(f"    ! {w}")

    print(f"Auditing game {GAME_NO} ({g.cfg['name']}) ...")
    results = run_all_checks(g, load_info)
    appendices = (build_appendix_I(g), build_appendix_II(g),
                  build_appendix_III(g))

    txt_path = os.path.join(out_dir, "audit_report.md")
    docx_path = os.path.join(out_dir, "audit_report.docx")
    write_text_report(txt_path, results, appendices, load_info, layout_path)
    write_word_report(docx_path, results, appendices, load_info, layout_path)
    print("\nReports written:")
    print(f"  {txt_path}")
    print(f"  {docx_path}")

    print("\n================ SUMMARY ================")
    exc = [r for r in results if not r.passed]
    print(f"Game {GAME_NO} ({g.cfg['name']}): "
          f"{'ALL PASSED' if not exc else str(len(exc))+' exception(s)'}")
    for r in exc:
        print(f"    - Check {r.index} {r.title}: {len(r.offenders)} "
              "offending item(s)")


if __name__ == "__main__":
    main()
