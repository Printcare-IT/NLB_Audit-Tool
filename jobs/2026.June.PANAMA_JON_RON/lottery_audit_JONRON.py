#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
JOC CARDS PANAMA - "JONRON DE LA SUERTE" - LAYOUT AUDIT TOOL  v1
Game 10 / Lot 01 (serial prefix 1001) - 1,200,000 tickets - B/.1
================================================================================

Reads the print layout file (one record per card, 4 channels, 16 cards per
page) and checks it against the Game Specification (V3, 09 July 2026) and the
Data Generation Specification (V1.0, 10 July 2026).  Writes audit_report.md
and audit_report.docx.  Run:

    python lottery_audit_1001.py <layout_file> [output_dir]

The (A) LAYOUT and (B) GAME_CONFIG blocks below are the only parts to edit
for a new job.

CHECKS PERFORMED
----------------
 1  Play positions: 11 symbols valid; winner = exactly one prize symbol equal
    to its prize amount; loser = no prize symbol (all "X"); no prize symbol
    duplicated on a ticket
 2  Prize print code blank on every ticket (no prize spot in this game)
 3  Serial numbers complete, unique, correctly formatted (GGLL-BBBBB-TTT)
 4  VIRN format / range / uniqueness (8 digits, 10000000-99999999)
 5  Agent validation codes: 3 of 9 positions, letters L,P,S,U,W,Y distinct;
    GLEPS (B/.1) winners carry the letter M plus two of the six
 6  Overall prize structure totals
 7  GLEPS per book: at least 9 x B/.1 in every book of 120
 8  Top prize placement: B/.50,000 in the last 25% of books
 9  No consecutive tickets with the same play pattern (per channel stream,
    incl. press junctions); adjacent winners compared on symbols, all
    adjacent pairs compared on the full scratch appearance
10  Play pattern vs VIRN independence screen (heuristic chi-square)
11  QA sample code: '$' reserved for QA sample tickets, blank otherwise
12  Print layout order: every record in its exact expected file position
    (page interleave, channel-book mapping, ascending within book)

MECHANIC
--------
  single_prize_symbol   winner  = exactly one prize symbol among the 11 play
                        spots, and that symbol equals the symbol assigned to
                        the winning amount; every other spot carries the
                        no-prize symbol ("X" = UU)
                        loser   = all 11 spots carry the no-prize symbol
                        never   = two or more prize symbols on one ticket
================================================================================
"""

import os
import re
import sys
import datetime
from sys import intern


# ================================================================== #
#  (A)  LAYOUT  -  EDIT ME per job                                    #
# ================================================================== #

GAME_NO = "10"
LOT_NO  = "01"
SERIAL_PREFIX = GAME_NO + LOT_NO          # "1001"

N_BOOKS   = 10_000
BOOK_SIZE = 120

LAYOUT = {
    "channels": 4,
    "cards_per_page": 16,      # 4 channels x 4 cards
    "books_per_channel_block": 5,
}

VOID_SERIAL = "8888-88888-888"

SERIAL_RE = re.compile(
    r"^" + SERIAL_PREFIX + r"-(\d{5})-(\d{3})$")

VIRN_MIN = 10_000_000
VIRN_MAX = 99_999_999

AGENT_SET       = {"L", "P", "S", "U", "W", "Y"}
AGENT_LOW_THIRD = "M"

NO_PRIZE_SYMBOL = "UU"
PLAY_SPOTS      = 11


# ================================================================== #
#  (B)  GAME_CONFIG  -  EDIT ME per job                               #
# ================================================================== #

GAME_CONFIG = {

    "1001": {
        "name": "JONRON DE LA SUERTE",
        "currency": "B/.",
        "tickets": N_BOOKS * BOOK_SIZE,          # 1,200,000
        "book_size": BOOK_SIZE,
        "mechanic": "single_prize_symbol",
        "play_symbols": {"LL": "B/.1", "MM": "B/.5", "NN": "B/.10",
                         "PP": "B/.50", "QQ": "B/.500", "RR": "B/.1,000",
                         "SS": "B/.5,000", "TT": "B/.50,000",
                         NO_PRIZE_SYMBOL: "X (no prize)"},
        "prize_print_used": False,
        "prizes": {
            "02": {"amount": 1,      "symbol": "LL", "count": 95_000},
            "06": {"amount": 5,      "symbol": "MM", "count": 5_000},
            "08": {"amount": 10,     "symbol": "NN", "count": 5_000},
            "14": {"amount": 50,     "symbol": "PP", "count": 4_500},
            "17": {"amount": 500,    "symbol": "QQ", "count": 180},
            "18": {"amount": 1_000,  "symbol": "RR", "count": 50},
            "21": {"amount": 5_000,  "symbol": "SS", "count": 3},
            "25": {"amount": 50_000, "symbol": "TT", "count": 1},
        },
        "loss_code": "99",
        "loss_count": 1_090_266,
        "gleps_amount": 1,
        "gleps_min_per_book": 9,               # spec: "At least 9" per book
        "top_prize_rule": {"amount": 50_000, "last_fraction": 0.25},
    },
}


# ================================================================== #
#  HEADER PARSING                                                    #
# ================================================================== #

def parse_header(header):
    """Map the singular column names of this file format to indices."""
    simple = {
        "page":   re.compile(r"^PageNo$"),
        "serial": re.compile(r"^SerialNo$"),
        "virn":   re.compile(r"^VIRN$"),
        "sys":    re.compile(r"^System_Prize_Code$"),
        "pcode":  re.compile(r"^Prize_Print_Code$"),
        "qa":     re.compile(r"^QA_Sample_Code$"),
    }
    pat_play  = re.compile(r"^Play_Symbol(\d+)$")
    pat_agent = re.compile(r"^Agent_ValCode(\d+)$")
    cols = {"plays": {}, "agents": {}}
    for col, raw in enumerate(header):
        name = raw.strip()
        matched = False
        for fkey, pat in simple.items():
            if pat.match(name):
                cols[fkey] = col
                matched = True
                break
        if matched:
            continue
        m = pat_play.match(name)
        if m:
            cols["plays"][int(m.group(1))] = col
            continue
        m = pat_agent.match(name)
        if m:
            cols["agents"][int(m.group(1))] = col
    cols["plays"]  = [cols["plays"][k]  for k in sorted(cols["plays"])]
    cols["agents"] = [cols["agents"][k] for k in sorted(cols["agents"])]
    return cols


# ================================================================== #
#  DATA CONTAINER                                                    #
# ================================================================== #

def serial_of(idx):
    """Reconstruct the serial string of ticket index idx (0-based)."""
    book = idx // BOOK_SIZE + 1
    tno  = idx %  BOOK_SIZE + 1
    return f"{SERIAL_PREFIX}-{book:05d}-{tno:03d}"


def expected_position(live_seq):
    """(book, ticket_no) expected at 0-based live record position live_seq,
    derived from the print imposition: pages of 16 cards, channels cycling
    1-2-3-4, four cards per channel per page, channel blocks of 5 books."""
    page, slot = divmod(live_seq, LAYOUT["cards_per_page"])
    ch, within = slot % LAYOUT["channels"], slot // LAYOUT["channels"]
    p = page * 4 + within                      # position in channel stream
    blk = LAYOUT["books_per_channel_block"] * BOOK_SIZE   # 600
    grp, off = divmod(p, blk)
    book = (grp * LAYOUT["channels"] + ch) * LAYOUT["books_per_channel_block"] \
           + off // BOOK_SIZE + 1
    tno = off % BOOK_SIZE + 1
    return book, tno


def channel_of_book(book):
    """1-based channel that carries a 1-based book number."""
    return ((book - 1) // LAYOUT["books_per_channel_block"]) \
           % LAYOUT["channels"] + 1


class GameData:
    def __init__(self, game_key):
        self.key = game_key
        self.cfg = GAME_CONFIG[game_key]
        self.tickets   = self.cfg["tickets"]
        self.book_size = self.cfg["book_size"]
        n = self.tickets
        self.virn      = [None] * n     # int
        self.sys       = [None] * n     # interned str
        self.pcode     = [None] * n     # interned str
        self.play_str  = [None] * n     # interned "S1,S2,...,S11"
        self.agent_str = [None] * n     # interned "A1,...,A9" (positional)
        self.qa        = [None] * n     # interned str
        self.streams   = []             # per channel: list of (start, end)

    def present(self, i):
        return self.sys[i] is not None

    def is_winner(self, i):
        return self.sys[i] is not None and self.sys[i] != self.cfg["loss_code"]

    def prize_amount(self, i):
        p = self.cfg["prizes"].get(self.sys[i])
        return p["amount"] if p else 0

    def build_streams(self):
        """Per-channel ordered contiguous serial runs (5 books = 600 tickets),
        in press order."""
        blk = LAYOUT["books_per_channel_block"]
        n_groups = N_BOOKS // (blk * LAYOUT["channels"])
        self.streams = []
        for ch in range(LAYOUT["channels"]):
            runs = []
            for grp in range(n_groups):
                first_book = (grp * LAYOUT["channels"] + ch) * blk + 1
                s = (first_book - 1) * BOOK_SIZE
                runs.append((s, s + blk * BOOK_SIZE))
            self.streams.append(runs)


# ================================================================== #
#  LOADING                                                           #
# ================================================================== #

def load_layout(path):
    g = GameData("1001")
    load_info = {
        "data_rows": 0, "void_tickets": 0, "void_pages": set(),
        "malformed_rows": [], "malformed_serials": [],
        "duplicate_serials": [], "out_of_range": [],
        "order_mismatches": [], "order_mismatch_count": 0,
        "page_counts": {}, "layout_warnings": [],
    }
    n_cols_expected = None
    live_seq = 0

    with open(path, "r", newline="") as f:
        header = f.readline().rstrip("\r\n").split(",")
        cols = parse_header(header)
        for key in ("page", "serial", "virn", "sys", "pcode", "qa"):
            if key not in cols:
                load_info["layout_warnings"].append(
                    f"Header column for '{key}' not found.")
        if len(cols.get("plays", [])) != PLAY_SPOTS:
            load_info["layout_warnings"].append(
                f"Header defines {len(cols.get('plays', []))} play columns, "
                f"expected {PLAY_SPOTS}.")
        if len(cols.get("agents", [])) != 9:
            load_info["layout_warnings"].append(
                f"Header defines {len(cols.get('agents', []))} agent columns, "
                f"expected 9.")
        n_cols_expected = len(header)

        row_no = 1
        for line in f:
            row_no += 1
            row = line.rstrip("\r\n").split(",")
            load_info["data_rows"] += 1
            if len(row) != n_cols_expected:
                load_info["malformed_rows"].append(
                    (row_no, f"{len(row)} fields, expected {n_cols_expected}"))
                continue
            page = row[cols["page"]]
            load_info["page_counts"][page] = \
                load_info["page_counts"].get(page, 0) + 1
            serial = row[cols["serial"]]
            if serial == VOID_SERIAL:
                load_info["void_tickets"] += 1
                load_info["void_pages"].add(page)
                continue
            m = SERIAL_RE.match(serial)
            if not m:
                load_info["malformed_serials"].append((row_no, serial))
                continue
            book, tno = int(m.group(1)), int(m.group(2))
            if not (1 <= book <= N_BOOKS and 1 <= tno <= BOOK_SIZE):
                load_info["out_of_range"].append(serial)
                continue
            idx = (book - 1) * BOOK_SIZE + (tno - 1)
            if g.sys[idx] is not None:
                load_info["duplicate_serials"].append(serial)
                continue

            v = row[cols["virn"]]
            g.virn[idx] = int(v) if v.isdigit() else v   # keep raw if bad
            g.sys[idx]      = intern(row[cols["sys"]])
            g.pcode[idx]    = intern(row[cols["pcode"]])
            g.play_str[idx] = intern(",".join(row[c] for c in cols["plays"]))
            g.agent_str[idx] = intern(",".join(row[c] for c in cols["agents"]))
            g.qa[idx]       = intern(row[cols["qa"]])

            # --- print-imposition order verification -------------------
            eb, et = expected_position(live_seq)
            if (book, tno) != (eb, et):
                load_info["order_mismatch_count"] += 1
                if len(load_info["order_mismatches"]) < 200:
                    load_info["order_mismatches"].append(
                        f"row {row_no}: found {serial}, expected "
                        f"{SERIAL_PREFIX}-{eb:05d}-{et:03d}")
            live_seq += 1

    g.build_streams()

    bad_pages = {p: c for p, c in load_info["page_counts"].items()
                 if c != LAYOUT["cards_per_page"]}
    if bad_pages:
        sample = ", ".join(f"{p}={c}" for p, c in list(bad_pages.items())[:10])
        load_info["layout_warnings"].append(
            f"{len(bad_pages)} page(s) without exactly "
            f"{LAYOUT['cards_per_page']} records (e.g. {sample}).")
    return g, load_info


# ================================================================== #
#  RESULTS + RANGE HELPERS                                           #
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


def fmt_amt(g, amount):
    return f"{g.cfg['currency']}{amount:,}"


# ================================================================== #
#  PATTERN VALIDITY (single_prize_symbol mechanic) - check 1         #
# ================================================================== #

def pattern_problem(g, i, plays):
    """Return a description string if ticket i's play pattern is invalid,
    else None.  `plays` is the split list of the 11 symbols."""
    cfg = g.cfg
    prize_syms = [p for p in plays if p != NO_PRIZE_SYMBOL]
    if len(prize_syms) >= 2:
        if len(set(prize_syms)) == 1:
            return (f"prize symbol {prize_syms[0]} duplicated "
                    f"({len(prize_syms)}x) on one ticket (forbidden)")
        return (f"more than one prize symbol on one ticket (forbidden): "
                + ",".join(prize_syms))
    winner = g.is_winner(i)
    if winner:
        want = cfg["prizes"][g.sys[i]]["symbol"]
        if len(prize_syms) == 0:
            return "winner without a prize symbol"
        if prize_syms[0] != want:
            return (f"winner's symbol {prize_syms[0]} does not match its "
                    f"prize (expects {want})")
    else:
        if len(prize_syms) == 1:
            return f"loser carrying prize symbol {prize_syms[0]}"
    return None


# ================================================================== #
#  THE CHECKS                                                        #
# ================================================================== #

def check_01_play_positions(g):
    r = CheckResult(1, "Play positions",
        "Check whether the play position fields are populated per the game "
        "specification, including the single-prize-symbol win rule and the "
        "blank prize print code.")
    valid = set(g.cfg["play_symbols"].keys())
    bad_symbol, bad_count, bad_pattern = [], [], []
    for i in range(g.tickets):
        if not g.present(i):
            continue
        plays = g.play_str[i].split(",")
        if len(plays) != PLAY_SPOTS:
            bad_count.append(serial_of(i))
            continue
        if any(p not in valid for p in plays):
            bad_symbol.append(serial_of(i))
            continue
        prob = pattern_problem(g, i, plays)
        if prob:
            bad_pattern.append(f"{serial_of(i)}: {prob}")
    if bad_count:
        r.fail(bad_count); r.note(f"{len(bad_count)} ticket(s) without exactly "
                                  f"{PLAY_SPOTS} play fields.")
    if bad_symbol:
        r.fail(bad_symbol); r.note(f"{len(bad_symbol)} ticket(s) with an "
                                   "invalid play-symbol code.")
    if bad_pattern:
        r.fail(bad_pattern); r.note(f"{len(bad_pattern)} ticket(s) with a play "
                                    "pattern inconsistent with the game "
                                    "mechanic / winner status.")
    bad_print = [serial_of(i) for i in range(g.tickets)
                 if g.present(i) and g.pcode[i].strip() != ""]
    if bad_print:
        r.fail(bad_print)
        r.note(f"{len(bad_print)} ticket(s) with a non-blank prize print code "
               "although this game has no prize spot (data specification: "
               "'Space - NOT APPLICABLE FOR THIS GAME').")
    if r.passed:
        r.note("No exceptions were noted. All play patterns are valid for the "
               "game mechanic and consistent with winner/loser status, and the "
               "prize print code field is blank on every ticket, as this game "
               "has no prize spot.")
    return r


def check_dup_symbols(g):
    r = CheckResult(0, "Duplicate play symbols",
        "Check whether any ticket is populated with duplicate play symbols "
        "(more than one prize symbol on a ticket).")
    bad = []
    for i in range(g.tickets):
        if not g.present(i):
            continue
        prize_syms = [p for p in g.play_str[i].split(",")
                      if p != NO_PRIZE_SYMBOL]
        if len(prize_syms) >= 2:
            bad.append(f"{serial_of(i)}: {','.join(prize_syms)}")
    if bad:
        r.fail(bad)
        r.note(f"{len(bad)} ticket(s) carrying more than one prize symbol.")
    else:
        r.note("No exceptions were noted. No ticket is populated with "
               "duplicate prize symbols or more than one prize symbol.")
    return r


def check_03_serial(g, load_info):
    r = CheckResult(3, "Serial number",
        "Check whether the serial number field is populated per the format "
        "GGLL-BBBBB-TTT with every book/ticket number present exactly once.")
    missing = [serial_of(n) for n in range(g.tickets) if g.sys[n] is None]
    if missing:
        r.fail(missing); r.note(f"{len(missing)} serial number(s) missing.")
    if load_info["duplicate_serials"]:
        r.fail(load_info["duplicate_serials"])
        r.note(f"{len(load_info['duplicate_serials'])} duplicate serial number(s).")
    if load_info["out_of_range"]:
        r.fail(load_info["out_of_range"])
        r.note(f"{len(load_info['out_of_range'])} serial(s) outside the range.")
    if load_info["malformed_serials"]:
        r.fail([f"row {rw}: {s}" for rw, s in load_info["malformed_serials"]])
        r.note(f"{len(load_info['malformed_serials'])} malformed serial value(s).")
    if load_info["malformed_rows"]:
        r.fail([f"row {rw}: {msg}" for rw, msg in load_info["malformed_rows"]])
        r.note(f"{len(load_info['malformed_rows'])} malformed data row(s).")
    if r.passed:
        r.note(f"No exceptions were noted. All {g.tickets:,} serials "
               f"({N_BOOKS:,} books x {BOOK_SIZE} tickets) are present "
               "exactly once and correctly formatted.")
    return r


def check_04_virn(g):
    r = CheckResult(4, "VIRN",
        "Check whether the VIRN field carries a unique eight-digit number in "
        "the specified range on every ticket.")
    seen = set()
    bad_fmt, bad_range, dup_virn = [], [], []
    for i in range(g.tickets):
        if not g.present(i):
            continue
        v = g.virn[i]
        if not isinstance(v, int):
            bad_fmt.append(f"{serial_of(i)}: {v!r}")
            continue
        if not (VIRN_MIN <= v <= VIRN_MAX):
            bad_range.append(f"{serial_of(i)}: {v}")
        if v in seen:
            dup_virn.append(f"{serial_of(i)}: {v}")
        else:
            seen.add(v)
    if bad_fmt:
        r.fail(bad_fmt); r.note(f"{len(bad_fmt)} VIRN(s) not numeric.")
    if bad_range:
        r.fail(bad_range); r.note(f"{len(bad_range)} VIRN(s) outside "
                                  f"{VIRN_MIN:,}-{VIRN_MAX:,}.")
    if dup_virn:
        r.fail(dup_virn); r.note(f"{len(dup_virn)} duplicate VIRN(s).")
    if r.passed:
        r.note("No exceptions were noted. All VIRNs are 8-digit, in range and "
               "unique across the game.")
    r.note("Note: this data file carries no ticket barcode field; the book "
           "label barcode (GGLLBBBBBB) is produced at packing and is outside "
           "the scope of this file.")
    return r


def check_05_agent_codes(g):
    r = CheckResult(5, "Agent validation codes",
        "Check whether the agent validation code fields are populated per the "
        "composition rules for GLEPS winners and for other winning / losing "
        "tickets.")
    bad_count, bad_letters = [], []
    for i in range(g.tickets):
        if not g.present(i):
            continue
        letters = [x for x in g.agent_str[i].split(",") if x.strip() != ""]
        if len(letters) != 3:
            bad_count.append(serial_of(i)); continue
        low = g.is_winner(i) and g.prize_amount(i) == g.cfg["gleps_amount"]
        if low:
            others = [x for x in letters if x != AGENT_LOW_THIRD]
            ok = (letters.count(AGENT_LOW_THIRD) == 1 and len(others) == 2
                  and all(x in AGENT_SET for x in others)
                  and others[0] != others[1])
        else:
            ok = (all(x in AGENT_SET for x in letters)
                  and len(set(letters)) == 3)
        if not ok:
            bad_letters.append(serial_of(i))
    if bad_count:
        r.fail(bad_count); r.note(f"{len(bad_count)} ticket(s) without exactly "
                                  "3 agent letters.")
    if bad_letters:
        r.fail(bad_letters); r.note(f"{len(bad_letters)} ticket(s) breaking "
                                    "the composition rules.")
    if r.passed:
        r.note("No exceptions were noted. All agent validation codes follow "
               "the prescribed composition rules.")
    return r


def check_06_prize_structure(g):
    r = CheckResult(6, "Prize structure",
        "Check whether the prize structure prescribed by the game "
        "specification (section 4.2) is reflected in the data layout.")
    counts = {}
    for i in range(g.tickets):
        if g.present(i):
            counts[g.sys[i]] = counts.get(g.sys[i], 0) + 1
    all_ok = True
    for code, spec in g.cfg["prizes"].items():
        actual = counts.get(code, 0)
        ok = actual == spec["count"]
        all_ok &= ok
        r.note(f"{fmt_amt(g, spec['amount']):>10} ({code}): expected "
               f"{spec['count']:>9,}, found {actual:>9,}  "
               f"{'OK' if ok else 'MISMATCH'}")
    loss = counts.get(g.cfg["loss_code"], 0)
    ok = loss == g.cfg["loss_count"]
    all_ok &= ok
    r.note(f"Losing tickets ({g.cfg['loss_code']}): expected "
           f"{g.cfg['loss_count']:>9,}, found {loss:>9,}  "
           f"{'OK' if ok else 'MISMATCH'}")
    total = sum(counts.values())
    ok = total == g.tickets
    all_ok &= ok
    r.note(f"Total tickets: expected {g.tickets:>9,}, found {total:>9,}  "
           f"{'OK' if ok else 'MISMATCH'}")
    if not all_ok:
        r.passed = False
        for code, spec in g.cfg["prizes"].items():
            if counts.get(code, 0) != spec["count"]:
                r.offenders.append(
                    f"{fmt_amt(g, spec['amount'])} ({code}): found "
                    f"{counts.get(code, 0)}, expected {spec['count']}")
        if loss != g.cfg["loss_count"]:
            r.offenders.append(f"Loss: found {loss}, "
                               f"expected {g.cfg['loss_count']}")
    return r


def check_07_gleps(g):
    need, amt = g.cfg["gleps_min_per_book"], g.cfg["gleps_amount"]
    r = CheckResult(7, "GLEPS per book",
        "Check whether each book contains at least the minimum number of "
        "guaranteed low-end (GLEPS) prizes.")
    bad = []
    for bno, s, e in iter_books(g):
        got = sum(1 for i in range(s, e) if g.prize_amount(i) == amt)
        if got < need:
            bad.append(f"Book {bno:05d} (serials "
                       f"{serial_of(s)}..{serial_of(e-1)}): {got} x "
                       f"{fmt_amt(g, amt)} (min {need})")
    if bad:
        r.fail(bad); r.note(f"{len(bad)} book(s) with fewer than {need} x "
                            f"{fmt_amt(g, amt)}.")
    else:
        r.note(f"No exceptions were noted. Every book contains at least "
               f"{need} x {fmt_amt(g, amt)}.")
    return r


def check_08_top_prize_placement(g):
    rule = g.cfg.get("top_prize_rule")
    r = CheckResult(8, "Top prize placement",
        "Check whether the highest prize is distributed among the last 25% "
        "of books in the lot.")
    if not rule:
        r.note("Not applicable for this game.")
        return r
    amt = rule["amount"]
    first_ok_book = N_BOOKS - int(N_BOOKS * rule["last_fraction"]) + 1
    r.procedure = ("Check whether the highest prize is distributed among "
                   "the last 25% of books in the lot.")
    hits, bad = [], []
    for i in range(g.tickets):
        if g.present(i) and g.prize_amount(i) == amt:
            book = i // BOOK_SIZE + 1
            hits.append((book, serial_of(i)))
            if book < first_ok_book:
                bad.append(f"{serial_of(i)} (book {book:05d}, before "
                           f"{first_ok_book:05d})")
    for book, s in hits:
        r.note(f"{fmt_amt(g, amt)} found at {s} (book {book:05d}).")
    if bad:
        r.fail(bad); r.note(f"{len(bad)} top prize(s) outside the last "
                            f"{int(rule['last_fraction']*100)}% of books.")
    elif hits:
        r.note("No exceptions were noted. The top prize lies within the "
               "required book range.")
    else:
        r.note("No top-prize ticket found (see check 6 for structure counts).")
    return r


def _press_junctions(g):
    """Yield (i, j) index pairs that are adjacent in press-feed order within
    a channel but not serially consecutive (last ticket of one 5-book run,
    first ticket of the channel's next run)."""
    for runs in g.streams:
        prev_last = None
        for s, e in runs:
            if prev_last is not None:
                yield prev_last, s
            prev_last = e - 1


def _pair_matches(g, i, j):
    """Classify a ticket pair: return (winner_pattern_match, full_match)."""
    if not (g.present(i) and g.present(j)):
        return False, False
    if g.play_str[i] != g.play_str[j]:
        return False, False
    win = g.is_winner(i) and g.is_winner(j)
    full = g.agent_str[i] == g.agent_str[j]
    return win, full


def check_09_consecutive_play_pattern(g):
    r = CheckResult(9, "Consecutive play pattern",
        "Check whether consecutive tickets contain the same play symbol "
        "pattern in any instance.")
    bad_win, bad_full = [], []
    for i in range(g.tickets - 1):
        win, full = _pair_matches(g, i, i + 1)
        if win:
            bad_win.append(f"{serial_of(i)} & {serial_of(i+1)}")
        if full:
            bad_full.append(f"{serial_of(i)} & {serial_of(i+1)}")
    info_win, info_full = [], []
    for i, j in _press_junctions(g):
        win, full = _pair_matches(g, i, j)
        if win:
            info_win.append(f"{serial_of(i)} & {serial_of(j)}")
        if full:
            info_full.append(f"{serial_of(i)} & {serial_of(j)}")
    if bad_win:
        r.fail(bad_win)
        r.note(f"{len(bad_win)} consecutive winner pair(s) with an identical "
               "play symbol pattern.")
    if bad_full:
        r.fail(bad_full)
        r.note(f"{len(bad_full)} consecutive pair(s) with an identical full "
               "scratch appearance (symbols and agent letter placement).")
    if r.passed:
        r.note("No exceptions were noted. No two serially consecutive "
               "tickets share the same play pattern under either comparison.")
    if info_win or info_full:
        for p in info_win:
            r.note(f"For information: press-junction winner pair with "
                   f"identical symbols (16 books apart serially): {p}")
        for p in info_full:
            r.note(f"For information: press-junction pair with identical "
                   f"full scratch appearance (16 books apart serially): {p}")
        r.note("Press-junction pairs are adjacent only in the press feed of "
               "a channel, not consecutive tickets in the packaged product; "
               "they are reported for information and not counted as "
               "exceptions.")
    r.note("Interpretation note: losing tickets all carry eleven X symbols, "
           "so adjacent losers can only be differentiated by the agent "
           "letter placement; this reading should be confirmed with the "
           "client if a stricter one is intended.")
    return r


def check_10_virn_independence(g):
    r = CheckResult(10, "Play pattern vs VIRN independence",
        "Check whether there is any logical relationship between the play "
        "patterns and the VIRN (statistical screen).")
    span = VIRN_MAX - VIRN_MIN + 1
    win = [0] * 10
    tot = [0] * 10
    for i in range(g.tickets):
        if not g.present(i) or not isinstance(g.virn[i], int):
            continue
        d = min((g.virn[i] - VIRN_MIN) * 10 // span, 9)
        tot[d] += 1
        if g.is_winner(i):
            win[d] += 1
    n_all = sum(tot)
    w_all = sum(win)
    if n_all == 0:
        r.note("No data available for the screen.")
        return r
    p = w_all / n_all
    chi2 = 0.0
    for d in range(10):
        exp_w = tot[d] * p
        exp_l = tot[d] * (1 - p)
        if exp_w > 0:
            chi2 += (win[d] - exp_w) ** 2 / exp_w
        if exp_l > 0:
            chi2 += ((tot[d] - win[d]) - exp_l) ** 2 / exp_l
        r.note(f"VIRN band {d+1:>2}: tickets {tot[d]:>9,}, winners "
               f"{win[d]:>7,} ({win[d]/tot[d]*100 if tot[d] else 0:6.3f}%)")
    r.note(f"Overall winner rate {p*100:.4f}%; chi-square = {chi2:.2f} "
           f"(critical 27.88 at 0.1%).")
    if chi2 > 27.88:
        r.fail([f"chi-square {chi2:.2f} exceeds 27.88 - winner rate varies "
                "with VIRN band more than chance allows; investigate."])
    else:
        r.note("No exceptions were noted. Winner rates are consistent across "
               "VIRN bands.")
    return r


def check_11_qa_code(g):
    r = CheckResult(11, "QA sample code",
        "Check whether the QA sample code field is populated per the data "
        "specification ('$' for QA sample tickets, blank otherwise).")
    counts = {}
    bad_value, dollar_winners = [], []
    n_dollar = 0
    for i in range(g.tickets):
        if not g.present(i):
            continue
        q = g.qa[i].strip()
        counts[q if q else "(blank)"] = counts.get(q if q else "(blank)", 0) + 1
        if q not in ("", "$"):
            bad_value.append(f"{serial_of(i)}: {g.qa[i]!r}")
        elif q == "$":
            n_dollar += 1
            if g.is_winner(i):
                dollar_winners.append(serial_of(i))
    for val, c in sorted(counts.items()):
        r.note(f"QA value {val}: {c:,} ticket(s)")
    if bad_value:
        r.fail(bad_value)
        r.note(f"{len(bad_value)} ticket(s) with an invalid QA value.")
    all_dollar = n_dollar > 0 and n_dollar == sum(counts.values())
    if all_dollar:
        r.fail([f"All {n_dollar:,} live tickets carry '$' although the data "
                "specification reserves '$' for QA sample tickets only."])
        r.note("Exception: every production ticket is QA-marked; the marking "
               "carries no selective meaning. Clarify the intended use of "
               "this field with the data generation team.")
        if dollar_winners:
            r.note(f"As a consequence, all {len(dollar_winners):,} winning "
                   "tickets carry the QA mark as well (individual serials "
                   "omitted; implied by the exception above).")
    elif dollar_winners:
        r.fail(dollar_winners)
        r.note(f"{len(dollar_winners)} winning ticket(s) carry the QA mark; "
               "QA/sample tickets are expected to be losing tickets.")
    if r.passed:
        r.note("No exceptions were noted.")
    return r


def check_12_print_order(g, load_info):
    r = CheckResult(12, "Print layout order",
        "Check whether every live record sits in its exact expected file "
        "position derived from the print imposition: pages of 16 cards, "
        "channels cycling 1-2-3-4 within each page, four cards per channel "
        "per page, channel book blocks of 5 (channel 1 = books 1-5, 21-25, "
        "...; channel 4 ends at book 10000), tickets ascending 001-120 "
        "within each book.")
    n = load_info["order_mismatch_count"]
    if n:
        r.fail(load_info["order_mismatches"])
        r.note(f"{n:,} record(s) out of the expected print order "
               f"(first {len(load_info['order_mismatches'])} listed; a single "
               "missing or shifted record cascades into all later positions).")
    else:
        r.note("No exceptions were noted. All 1,200,000 live records follow "
               "the print imposition exactly.")
    for wmsg in load_info["layout_warnings"]:
        r.fail([wmsg])
        r.note(wmsg)
    return r


def run_all_checks(g, load_info):
    """Procedures follow the structure and ordering of the reference
    Agreed-Upon Procedures report, mapped onto this game's specification.
    Every procedure below is a written requirement of the JONRON game
    specification (V3) or data generation specification (V1.0). The one
    reference procedure with no counterpart in this game's spec (a winner in
    every 5 tickets) is omitted; the print-imposition order verification is
    reported in the file-load summary rather than as a numbered procedure."""
    ordered = [
        check_01_play_positions(g),            # play positions + print code
        check_03_serial(g, load_info),         # serial number
        check_04_virn(g),                      # VIRN
        check_05_agent_codes(g),               # agent validation codes
        check_06_prize_structure(g),           # prize structure
        check_09_consecutive_play_pattern(g),  # consecutive play pattern
        check_08_top_prize_placement(g),       # highest prize last 25% books
        check_dup_symbols(g),                  # duplicate play symbols
        check_07_gleps(g),                     # minimum GLEPS per book
        check_10_virn_independence(g),         # play pattern vs VIRN
        check_11_qa_code(g),                   # QA sample code
    ]
    for n, r in enumerate(ordered, 1):
        r.index = n
    return ordered


# ================================================================== #
#  APPENDICES                                                        #
# ================================================================== #

def build_appendix_I(g):
    """Symbol counts per play position (EY Appendix I layout): one row per
    symbol, one column per play position, plus the row total."""
    pos_counts = {code: [0] * PLAY_SPOTS for code in g.cfg["play_symbols"]}
    for i in range(g.tickets):
        if not g.present(i):
            continue
        for pos, sym in enumerate(g.play_str[i].split(",")):
            if sym in pos_counts:
                pos_counts[sym][pos] += 1
    rows = []
    for code, name in g.cfg["play_symbols"].items():
        c = pos_counts[code]
        rows.append((name, code, c, sum(c)))
    return rows


def build_appendix_II(g):
    counts = {}
    for i in range(g.tickets):
        if g.present(i):
            counts[g.sys[i]] = counts.get(g.sys[i], 0) + 1
    rows = []
    for code, p in sorted(g.cfg["prizes"].items(),
                          key=lambda kv: kv[1]["amount"]):
        rows.append((p["amount"], code, counts.get(code, 0)))
    rows.append((0, g.cfg["loss_code"], counts.get(g.cfg["loss_code"], 0)))
    return rows


def build_appendix_III(g):
    amt = g.cfg["gleps_amount"]
    tally = {}
    for i in range(g.tickets):
        if not g.present(i):
            continue
        cat = (0 if g.prize_amount(i) == amt else 1) if g.is_winner(i) else 2
        for letter in g.agent_str[i].split(","):
            if letter.strip():
                tally.setdefault(letter, [0, 0, 0])[cat] += 1
    return [(l, *tally[l], sum(tally[l])) for l in sorted(tally)]


# ================================================================== #
#  REPORTS                                                           #
# ================================================================== #

def write_text_report(path, all_results, appendices, load_info, layout_path):
    L = []
    W = L.append
    W("# JOC CARDS, SA - PANAMA")
    W("# LAYOUT AUDIT REPORT ON GAME SPECIFICATIONS")
    W('# "JONRON DE LA SUERTE" INSTANT SCRATCH LOTTERY TICKETS - GAME 10 / 2026')
    W("")
    W(f"Layout file : `{os.path.basename(layout_path)}`")
    W(f"Generated   : {datetime.datetime.now():%Y-%m-%d %H:%M:%S}")
    W("")
    W("This report sets out the procedures performed on the print layout data "
      "file and the findings, following the structure of an agreed-upon "
      "procedures report. The criteria are those of the JONRON de la Suerte "
      "game specification (V3, 09 July 2026) and the data generation "
      "specification (V1.0, 10 July 2026).")
    W("")
    W("## File load summary")
    W("")
    W(f"- Data rows read : {load_info['data_rows']:,}")
    W(f"- VOID tickets ignored : {load_info['void_tickets']:,} "
      f"(on {len(load_info['void_pages'])} page(s))")
    W(f"- Malformed rows : {len(load_info['malformed_rows']):,}")
    W(f"- Malformed serials : {len(load_info['malformed_serials']):,}")
    W(f"- Duplicate serials : {len(load_info['duplicate_serials']):,}")
    W(f"- Pages seen : {len(load_info['page_counts']):,}")
    if load_info["order_mismatch_count"]:
        W(f"- Print-imposition order mismatches : "
          f"{load_info['order_mismatch_count']:,} (see note below)")
    else:
        W("- Print-imposition order : all live records in the expected "
          "position (pages of 16 cards, channels 1-4, book blocks of 5, "
          "tickets ascending within each book).")
    for wmsg in load_info["layout_warnings"]:
        W(f"- Layout note : {wmsg}")
    W("")
    W("Scope note: the game specification's 'No heart stoppers' play "
      "requirement is a ticket-design property and cannot be verified from "
      "the layout data file; it is outside the scope of these procedures.")
    W("")

    for gkey, results in all_results.items():
        cfg = GAME_CONFIG[gkey]
        n_exc = sum(1 for r in results if not r.passed)
        W("---")
        W(f'# Game {gkey} - "{cfg["name"]}"')
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
                W(f"*Offending items ({len(r.offenders)}):*")
                for o in r.offenders:
                    W(f"  - {o}")
            W("")

        apI, apII = appendices[gkey]
        W(f"## Appendix I - The distribution of play symbols across the "
          f"{cfg['tickets']:,} tickets")
        W("")
        pos_hdr = " ".join(f"Pos {p+1} |" for p in range(PLAY_SPOTS))
        W(f"| Play symbol | Code | {pos_hdr} Total |")
        W("|---|---|" + "---:|" * (PLAY_SPOTS + 1))
        col_tot = [0] * PLAY_SPOTS
        grand = 0
        for name, code, cols, tot in apI:
            cells = " ".join(f"{c:,} |" for c in cols)
            W(f"| {name} | {code} | {cells} {tot:,} |")
            for p in range(PLAY_SPOTS):
                col_tot[p] += cols[p]
            grand += tot
        tot_cells = " ".join(f"**{c:,}** |" for c in col_tot)
        W(f"| **Total** |  | {tot_cells} **{grand:,}** |")
        W("")
        W(f"## Appendix II - The distribution of agent validation codes "
          f"across the {cfg['tickets']:,} tickets")
        W("")
        W("| Letter | GLEPs | Non GLEPs | Losing tickets | Total |")
        W("|---|---:|---:|---:|---:|")
        cg = cn = cl = ct = 0
        for letter, gl, ng, ls, tot in apII:
            W(f"| {letter} | {gl:,} | {ng:,} | {ls:,} | {tot:,} |")
            cg += gl; cn += ng; cl += ls; ct += tot
        W(f"| **Total** | **{cg:,}** | **{cn:,}** | **{cl:,}** | **{ct:,}** |")
        W("")

    with open(path, "w") as f:
        f.write("\n".join(L))


def write_word_report(path, all_results, appendices, load_info, layout_path):
    from docx import Document
    from docx.shared import RGBColor, Pt

    doc = Document()
    doc.add_heading("JOC CARDS, SA - Panama", level=0)
    doc.add_heading('Layout Audit Report on Game Specifications - '
                    '"Jonron de la Suerte" Instant Scratch Lottery Tickets, '
                    'Game 10 / 2026', level=1)
    p = doc.add_paragraph()
    p.add_run(f"Layout file: {os.path.basename(layout_path)}\n").italic = True
    p.add_run(f"Generated: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}").italic = True
    doc.add_paragraph(
        "This report sets out the procedures performed on the print layout "
        "data file and the findings, following the structure of an "
        "agreed-upon procedures report. The criteria are those of the JONRON "
        "de la Suerte game specification (V3, 09 July 2026) and the data "
        "generation specification (V1.0, 10 July 2026).")

    doc.add_heading("File load summary", level=2)
    doc.add_paragraph(
        f"Data rows: {load_info['data_rows']:,}   |   "
        f"VOID tickets: {load_info['void_tickets']:,}   |   "
        f"Malformed: {len(load_info['malformed_serials']):,}   |   "
        f"Duplicates: {len(load_info['duplicate_serials']):,}   |   "
        f"Pages: {len(load_info['page_counts']):,}")
    if load_info["order_mismatch_count"]:
        doc.add_paragraph(
            f"Print-imposition order mismatches: "
            f"{load_info['order_mismatch_count']:,}.")
    else:
        doc.add_paragraph(
            "Print-imposition order: all live records occupy their expected "
            "position (pages of 16 cards, channels 1-4, book blocks of 5, "
            "tickets ascending within each book).")
    for wmsg in load_info["layout_warnings"]:
        doc.add_paragraph("Layout note: " + wmsg)
    doc.add_paragraph(
        "Scope note: the game specification's 'No heart stoppers' play "
        "requirement is a ticket-design property and cannot be verified from "
        "the layout data file; it is outside the scope of these procedures.")

    for gkey, results in all_results.items():
        cfg = GAME_CONFIG[gkey]
        n_exc = sum(1 for r in results if not r.passed)
        doc.add_heading(f'Game {gkey} - "{cfg["name"]}"', level=1)
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
            fc = cells[2]
            fc.text = ""
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
                MAX_INLINE = 500
                for o in r.offenders[:MAX_INLINE]:
                    fc.add_paragraph("  " + o)
                if len(r.offenders) > MAX_INLINE:
                    fc.add_paragraph(f"  ... {len(r.offenders)-MAX_INLINE:,} "
                                     "more - see the full list in "
                                     "audit_report.md.")

        apI, apII = appendices[gkey]
        doc.add_heading("Appendix I - The distribution of play symbols across "
                        f"the {cfg['tickets']:,} tickets", level=2)
        t = doc.add_table(rows=1, cols=3 + PLAY_SPOTS); t.style = "Table Grid"
        heads = (["Play symbol", "Code"]
                 + [f"Pos {p+1}" for p in range(PLAY_SPOTS)] + ["Total"])
        for j, h in enumerate(heads):
            t.rows[0].cells[j].text = h
        col_tot = [0] * PLAY_SPOTS
        grand = 0
        for name, code, cols, tot in apI:
            c = t.add_row().cells
            c[0].text, c[1].text = name, code
            for p in range(PLAY_SPOTS):
                c[2 + p].text = f"{cols[p]:,}"
                col_tot[p] += cols[p]
            c[2 + PLAY_SPOTS].text = f"{tot:,}"
            grand += tot
        c = t.add_row().cells
        c[0].text = "Total"
        for p in range(PLAY_SPOTS):
            c[2 + p].text = f"{col_tot[p]:,}"
        c[2 + PLAY_SPOTS].text = f"{grand:,}"

        doc.add_heading("Appendix II - The distribution of agent validation "
                        f"codes across the {cfg['tickets']:,} tickets", level=2)
        t = doc.add_table(rows=1, cols=5); t.style = "Table Grid"
        for j, h in enumerate(["Letter", "GLEPs", "Non GLEPs",
                               "Losing tickets", "Total"]):
            t.rows[0].cells[j].text = h
        cg = cn = cl = ct = 0
        for letter, gl, ng, ls, tot in apII:
            c = t.add_row().cells
            c[0].text = letter
            c[1].text, c[2].text, c[3].text, c[4].text = \
                f"{gl:,}", f"{ng:,}", f"{ls:,}", f"{tot:,}"
            cg += gl; cn += ng; cl += ls; ct += tot
        c = t.add_row().cells
        c[0].text = "Total"
        c[1].text, c[2].text, c[3].text, c[4].text = \
            f"{cg:,}", f"{cn:,}", f"{cl:,}", f"{ct:,}"

    doc.save(path)


# ================================================================== #
#  MAIN                                                              #
# ================================================================== #

def main():
    if len(sys.argv) < 2:
        print("Usage: python lottery_audit_1001.py <layout_file> [output_dir]")
        sys.exit(1)
    layout_path = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "."
    os.makedirs(out_dir, exist_ok=True)

    print(f"Loading layout file: {layout_path}")
    g, load_info = load_layout(layout_path)
    print(f"  data rows          : {load_info['data_rows']:,}")
    print(f"  void tickets       : {load_info['void_tickets']:,}")
    print(f"  malformed serials  : {len(load_info['malformed_serials']):,}")
    print(f"  duplicate serials  : {len(load_info['duplicate_serials']):,}")
    print(f"  order mismatches   : {load_info['order_mismatch_count']:,}")
    if load_info["layout_warnings"]:
        print("  LAYOUT WARNINGS:")
        for w in load_info["layout_warnings"]:
            print(f"    ! {w}")

    all_results, appendices = {}, {}
    for gkey in GAME_CONFIG:
        print(f"Auditing game {gkey} ({GAME_CONFIG[gkey]['name']}) ...")
        all_results[gkey] = run_all_checks(g, load_info)
        appendices[gkey] = (build_appendix_I(g), build_appendix_III(g))

    txt_path = os.path.join(out_dir, "audit_report.md")
    docx_path = os.path.join(out_dir, "audit_report.docx")
    write_text_report(txt_path, all_results, appendices, load_info, layout_path)
    write_word_report(docx_path, all_results, appendices, load_info, layout_path)
    print("\nReports written:")
    print(f"  {txt_path}")
    print(f"  {docx_path}")

    print("\n================ SUMMARY ================")
    for gkey, results in all_results.items():
        exc = [r for r in results if not r.passed]
        print(f"Game {gkey} ({GAME_CONFIG[gkey]['name']}): "
              f"{'ALL PASSED' if not exc else str(len(exc))+' exception(s)'}")
        for r in exc:
            print(f"    - Check {r.index} {r.title}: "
                  f"{len(r.offenders)} offending item(s)")


if __name__ == "__main__":
    main()
