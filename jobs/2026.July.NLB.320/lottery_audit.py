#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
NLB SCRATCH LOTTERY  -  LAYOUT AUDIT TOOL   (adjustable layout version)
================================================================================

This tool reads a print LAYOUT file (one CSV/TXT file holding the data for every
ticket) and checks it against the GAME SPECIFICATION, reproducing the 15
procedures of the sample EY audit report.  It writes:
    * audit_report.md    - detailed markdown report
    * audit_report.docx  - Word report in the EY table layout

--------------------------------------------------------------------------------
HOW TO CONFIGURE IT FOR A NEW JOB  (this is the only part you normally edit)
--------------------------------------------------------------------------------
There are TWO editable blocks near the top of this file:

  (A) LAYOUT       - describes how the file is arranged:
                       * how many ticket blocks (channels) are in each row, and
                       * which channels belong to which game.
                     You may leave the auto-detect fields blank and the tool
                     will work them out from the serial numbers, but whatever
                     you DO fill in is VERIFIED against the file and any
                     mismatch is reported.

  (B) GAME_CONFIG  - one entry per game, holding that game's own specification:
                       tickets, book size, carton layout, play symbols, prize
                       structure, agent-code rules, etc.  These may DIFFER from
                       one game to the next.

Everything else (the 15 checks, the appendices, the reports) adapts itself to
whatever you put in those two blocks - the number of blocks and the number of
games are no longer hard-coded.

--------------------------------------------------------------------------------
WHAT THE LAYOUT FILE LOOKS LIKE
--------------------------------------------------------------------------------
* Header row, then one row per "PageNo".
* Each row = PageNo column + N ticket blocks (one block per print channel).
* Each block = SerialNo, VIRN, BAR, SystemPrizeCode, PrizePrintCode,
               Play1..PlayK, Agent_ValCode1..AgentM, QA_SampleCode.
  The tool reads the header names, so K (play positions) and M (agent
  positions) and N (channels) are all detected automatically.
* Each ticket's SerialNo encodes P + lottery code + GAME + ticket number, e.g.
  "1 320 0110 0099760".  That embedded game number is how the tool knows which
  game a channel belongs to.
* VOID / filler rows carry SerialNo = "888888888888888" and are ignored.

RUN IT:
    python lottery_audit.py <layout_file> [output_folder]
================================================================================
"""

import os
import re
import sys
import datetime


# ================================================================== #
#  (A)  LAYOUT  -  EDIT ME per job                                    #
# ================================================================== #
# Describe how the file is arranged.  Anything set to None is auto-detected
# from the file; anything you fill in is checked against the file.

LAYOUT = {
    # Number of ticket blocks (channels) in one data row.
    # Set to an integer to enforce it, or None to auto-detect from the header.
    "blocks_per_row": 4,

    # Which channels (1-based ticket-block numbers) hold each game.
    # Set to None to let the tool discover it from the serial numbers.
    # If you provide it, the tool VERIFIES the file matches and reports if not.
    "game_channels": {
        "0110": [1, 2],
        "0111": [3, 4],
    },
}

# These identify a valid serial and are shared by all games in the file.
# (Edit only if a future file uses a different passive flag / lottery code.)
PASSIVE_FLAG = "1"      # "P" position: 1 = passive / scratch
LOTTERY_CODE = "320"    # 3-digit lottery code
VOID_SERIAL  = "8" * 15 # serial value printed on VOID / filler rows

# Agent-validation-code alphabet (shared by the games seen so far; if a game
# ever differs, move these into that game's GAME_CONFIG entry instead).
AGENT_HIGH_LETTERS = {"W", "S", "A", "D", "Z", "R"}   # high-tier & losers
AGENT_LOW_THIRD    = "T"                              # low-tier winners' 3rd letter


# ================================================================== #
#  (B)  GAME_CONFIG  -  EDIT ME per job (one entry per game)          #
# ================================================================== #
# Every figure below comes from the game-spec / data-spec documents.
# Games may differ from each other - each has its own tickets/book/carton/prizes.

GAME_CONFIG = {

    "0110": {
        "name": "LUCKY WHEEL",
        "tickets": 500_000,             # total tickets in this game
        "book_size": 40,                # tickets per book
        "play_positions_used": 2,       # how many play spots carry a symbol
        # Play symbol print code -> readable name
        "play_symbols": {
            "KA": "One", "LA": "Two", "NA": "Three",
            "PA": "Four", "QA": "Five", "UA": "Six",
        },
        # System prize code -> (amount, print code, tier, expected count)
        "prizes": {
            "03": {"amount": 50,     "print": "dd", "tier": "Low",  "count": 100_000},
            "07": {"amount": 500,    "print": "hh", "tier": "High", "count": 12_500},
            "08": {"amount": 1_000,  "print": "jj", "tier": "High", "count": 1_580},
            "12": {"amount": 10_000, "print": "nn", "tier": "High", "count": 42},
        },
        "loss_code":  "99",
        "loss_count": 385_878,
        "top_prize_amount": 10_000,     # 1 per carton
        "gleps_amount": 50,             # guaranteed low-end prize
        "gleps_per_book": 8,            # 8 x Rs.50 guaranteed per book
        # Carton (a.k.a. "box") layout, in serial order: a "first" group then a
        # "last" group.  exact = must equal, atleast = must be >=, top = number
        # of top-tier prizes required per carton.
        "carton_spec": {
            "first": {"count": 41, "size": 12_000,
                      "exact": {500: 300}, "atleast": {1_000: 37}, "top": 1},
            "last":  {"count": 1,  "size": 8_000,
                      "exact": {500: 200}, "atleast": {1_000: 25}, "top": 1},
        },
    },

    "0111": {
        "name": "CASH POWER",
        "tickets": 500_000,
        "book_size": 40,
        "play_positions_used": 2,
        "play_symbols": {
            "KB": "Star", "LB": "Key", "NB": "Purse",
            "PB": "Crown", "QB": "Gift Box", "UB": "Bundle of Money",
        },
        "prizes": {
            "03": {"amount": 50,    "print": "dd", "tier": "Low",  "count": 100_000},
            "07": {"amount": 500,   "print": "hh", "tier": "High", "count": 12_500},
            "08": {"amount": 1_000, "print": "jj", "tier": "High", "count": 1_790},
            "11": {"amount": 5_000, "print": "mm", "tier": "High", "count": 42},
        },
        "loss_code":  "99",
        "loss_count": 385_668,
        "top_prize_amount": 5_000,
        "gleps_amount": 50,
        "gleps_per_book": 8,
        "carton_spec": {
            "first": {"count": 41, "size": 12_000,
                      "exact": {500: 300}, "atleast": {1_000: 43}, "top": 1},
            "last":  {"count": 1,  "size": 8_000,
                      "exact": {500: 200}, "atleast": {1_000: 27}, "top": 1},
        },
    },

    # ---- To add a game, copy a block above and change the numbers. ----
}


# ================================================================== #
#  HEADER PARSING  (works out channels / play / agent columns)       #
# ================================================================== #

def parse_header(header):
    """
    Read the header row and return, for every channel found, the exact column
    indices of its fields.  This is what makes the tool adapt to any number of
    blocks / play positions / agent positions.

    Returns: channels = { channel_no: {
                 'serial','virn','bar','sys','pcode','qa' : column index,
                 'plays'  : [col, col, ...] in position order,
                 'agents' : [col, col, ...] in position order } }
    """
    simple = {
        "serial": re.compile(r"^SerialNo(\d+)$"),
        "virn":   re.compile(r"^VIRN(\d+)$"),
        "bar":    re.compile(r"^BAR(\d+)$"),
        "sys":    re.compile(r"^SystemPrizeCode(\d+)$"),
        "pcode":  re.compile(r"^PrizePrintCode(\d+)$"),
        "qa":     re.compile(r"^QA_SampleCode(\d+)$"),
    }
    pat_play  = re.compile(r"^Play(\d)(\d+)$")            # Play<channel><position>
    pat_agent = re.compile(r"^Agent_ValCode(\d)(\d+)$")   # Agent_ValCode<ch><pos>

    channels = {}

    def slot(ch):
        return channels.setdefault(ch, {"plays": {}, "agents": {}})

    for col, raw in enumerate(header):
        # Field names carry a trailing panel suffix like "_01"; drop it.
        name = raw.rsplit("_", 1)[0] if "_" in raw else raw

        done = False
        for fkey, pat in simple.items():
            m = pat.match(name)
            if m:
                slot(int(m.group(1)))[fkey] = col
                done = True
                break
        if done:
            continue

        m = pat_play.match(name)
        if m:
            ch, pos = int(m.group(1)), int(m.group(2))
            slot(ch)["plays"][pos] = col
            continue

        m = pat_agent.match(name)
        if m:
            ch, pos = int(m.group(1)), int(m.group(2))
            slot(ch)["agents"][pos] = col
            continue
        # anything else (PageNo, unknown columns) is ignored

    # Convert the play/agent position maps into ordered lists of columns.
    for ch, d in channels.items():
        d["plays"]  = [d["plays"][k]  for k in sorted(d["plays"])]
        d["agents"] = [d["agents"][k] for k in sorted(d["agents"])]

    return channels


# ================================================================== #
#  DATA CONTAINER FOR ONE GAME                                       #
# ================================================================== #

class GameData:
    """Holds every ticket of one game, indexed by (serial number - 1)."""

    def __init__(self, game_key):
        self.key = game_key
        self.cfg = GAME_CONFIG[game_key]
        self.tickets   = self.cfg["tickets"]
        self.book_size = self.cfg["book_size"]
        n = self.tickets
        self.serial = [None] * n
        self.virn   = [None] * n
        self.bar    = [None] * n
        self.sys    = [None] * n
        self.pcode  = [None] * n
        self.p1     = [None] * n
        self.p2     = [None] * n
        self.plays  = [None] * n     # tuple of all play fields
        self.agent  = [None] * n     # tuple of all agent fields
        # Filled in after loading:
        self.channels = []           # channel numbers that belong to this game
        self.channel_range = {}      # channel -> (min_serial, max_serial)
        self.streams = []            # list of (lo_idx, hi_idx_exclusive) per channel

    def present(self, i):
        """True if a ticket was actually loaded at serial index i."""
        return self.serial[i] is not None

    def is_winner(self, i):
        if self.sys[i] is None:
            return False
        return self.sys[i] != self.cfg["loss_code"]

    def prize_amount(self, i):
        p = self.cfg["prizes"].get(self.sys[i])
        return p["amount"] if p else 0


# ================================================================== #
#  LOADING THE LAYOUT FILE                                           #
# ================================================================== #

def load_layout(path):
    """
    Read the whole file once and fill a GameData per game.  The game a ticket
    belongs to is taken from the game number embedded in its serial, so this
    works for any channel arrangement.  Layout facts are also verified against
    the LAYOUT block and any discrepancy is recorded.
    """
    games = {k: GameData(k) for k in GAME_CONFIG}

    load_info = {
        "data_rows": 0,
        "void_tickets": 0,
        "blocks_per_row": None,
        "malformed_serials": [],      # (row_no, channel, raw_serial)
        "duplicate_serials": [],      # (game, serial)
        "unknown_game": [],           # (row_no, channel, game_code)
        "out_of_range": [],           # (game, serial)
        "layout_warnings": [],        # human-readable verification messages
        "detected_channels": {},      # game -> [channels]
    }

    # per-channel observations used for verification
    ch_games = {}     # channel -> set of game codes seen
    ch_min   = {}     # channel -> smallest serial number seen
    ch_max   = {}     # channel -> largest serial number seen

    with open(path, "r", newline="") as f:
        header = f.readline().rstrip("\r\n").split(",")
        channels = parse_header(header)
        n_blocks = len(channels)
        load_info["blocks_per_row"] = n_blocks

        # Verify block count against the LAYOUT declaration.
        if LAYOUT.get("blocks_per_row") not in (None, n_blocks):
            load_info["layout_warnings"].append(
                f"Declared blocks_per_row={LAYOUT['blocks_per_row']} but the file "
                f"header contains {n_blocks} ticket blocks.")

        row_no = 1
        for line in f:
            row_no += 1
            row = line.rstrip("\r\n").split(",")
            load_info["data_rows"] += 1

            for ch, cols in channels.items():
                serial = row[cols["serial"]]

                if serial == VOID_SERIAL:
                    load_info["void_tickets"] += 1
                    continue

                # Basic serial sanity.
                ok = (len(serial) == 15 and serial.isdigit()
                      and serial[0] == PASSIVE_FLAG
                      and serial[1:4] == LOTTERY_CODE)
                if not ok:
                    load_info["malformed_serials"].append((row_no, ch, serial))
                    continue

                game_code = serial[4:8]
                if game_code not in games:
                    load_info["unknown_game"].append((row_no, ch, game_code))
                    continue

                ticket_no = int(serial[8:])
                game = games[game_code]
                if not (1 <= ticket_no <= game.tickets):
                    load_info["out_of_range"].append((game_code, serial))
                    continue

                idx = ticket_no - 1
                if game.serial[idx] is not None:
                    load_info["duplicate_serials"].append((game_code, serial))
                    continue

                # Store the ticket.
                game.serial[idx] = serial
                game.virn[idx]   = row[cols["virn"]]
                game.bar[idx]    = row[cols["bar"]]
                game.sys[idx]    = row[cols["sys"]]
                game.pcode[idx]  = row[cols["pcode"]]
                plays = tuple(row[c] for c in cols["plays"])
                game.plays[idx]  = plays
                game.p1[idx]     = plays[0] if len(plays) > 0 else ""
                game.p2[idx]     = plays[1] if len(plays) > 1 else ""
                game.agent[idx]  = tuple(row[c] for c in cols["agents"])

                # observations
                ch_games.setdefault(ch, set()).add(game_code)
                ch_min[ch] = min(ch_min.get(ch, ticket_no), ticket_no)
                ch_max[ch] = max(ch_max.get(ch, ticket_no), ticket_no)

    _finalise_layout(games, ch_games, ch_min, ch_max, load_info)
    return games, load_info


def _finalise_layout(games, ch_games, ch_min, ch_max, load_info):
    """Work out channel->game mapping + streams and verify against LAYOUT."""
    # channel -> single game (warn if a channel mixes games)
    channel_game = {}
    for ch, gset in ch_games.items():
        if len(gset) == 1:
            channel_game[ch] = next(iter(gset))
        else:
            channel_game[ch] = None
            load_info["layout_warnings"].append(
                f"Channel {ch} contains more than one game: {sorted(gset)}.")

    # group channels by game and build each game's streams (one per channel)
    detected = {}
    for ch, gkey in channel_game.items():
        if gkey is None:
            continue
        detected.setdefault(gkey, []).append(ch)
    for gkey in detected:
        detected[gkey].sort()
    load_info["detected_channels"] = detected

    for gkey, chans in detected.items():
        game = games[gkey]
        game.channels = chans
        ranges = []
        for ch in chans:
            lo, hi = ch_min[ch], ch_max[ch]
            game.channel_range[ch] = (lo, hi)
            ranges.append((lo - 1, hi))       # index range, hi exclusive
        game.streams = sorted(ranges)

        # Verify the channels tile 1..tickets with no gap / overlap.
        covered = sorted(game.channel_range.values())
        expect_next = 1
        for lo, hi in covered:
            if lo != expect_next:
                load_info["layout_warnings"].append(
                    f"Game {gkey}: serial gap/overlap - expected next serial "
                    f"{expect_next} but a channel starts at {lo}.")
            expect_next = hi + 1
        if expect_next - 1 != game.tickets:
            load_info["layout_warnings"].append(
                f"Game {gkey}: channels cover up to serial {expect_next-1}, "
                f"but the game is configured for {game.tickets} tickets.")

    # Verify against the declared LAYOUT["game_channels"], if provided.
    declared = LAYOUT.get("game_channels")
    if declared:
        for gkey, decl_chans in declared.items():
            det = detected.get(gkey, [])
            if sorted(decl_chans) != det:
                load_info["layout_warnings"].append(
                    f"Game {gkey}: declared channels {sorted(decl_chans)} but the "
                    f"file shows {det}.")
        for gkey in detected:
            if gkey not in declared:
                load_info["layout_warnings"].append(
                    f"Game {gkey} found in the file but not declared in LAYOUT.")


# ================================================================== #
#  RESULT OBJECT + RANGE HELPERS                                     #
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
    """Yield (book_no, start_idx, end_idx) for each book of the game."""
    n_books = g.tickets // g.book_size
    for b in range(n_books):
        yield b + 1, b * g.book_size, (b + 1) * g.book_size


def iter_cartons(g):
    """Yield (carton_no, start_idx, end_idx, kind) using the game's carton_spec."""
    idx = 0
    num = 0
    for kind in ("first", "last"):
        grp = g.cfg["carton_spec"].get(kind)
        if not grp:
            continue
        for _ in range(grp["count"]):
            num += 1
            yield num, idx, idx + grp["size"], kind
            idx += grp["size"]


def count_amounts(g, s, e):
    """Count winning amounts in the serial index range [s, e)."""
    counts = {}
    for i in range(s, e):
        if not g.present(i):
            continue
        a = g.prize_amount(i)
        if a:
            counts[a] = counts.get(a, 0) + 1
    return counts


# ================================================================== #
#  THE 15 CHECKS                                                     #
# ================================================================== #

def check_01_play_positions(g):
    """Procedure 1: play fields populated per spec.
    Positions 1..U carry a valid symbol (U = play_positions_used); the rest are
    blank; winners show matching symbols and losers do not.
    """
    r = CheckResult(1, "Play positions",
        "Check whether the fields pertaining to the play positions in the data "
        "layout have been populated as per the game specifications.")
    valid = set(g.cfg["play_symbols"].keys())
    used = g.cfg.get("play_positions_used", 2)
    bad_symbol, bad_blank, bad_match = [], [], []
    for i in range(g.tickets):
        if not g.present(i):
            continue
        p = g.plays[i]
        if any(p[k] not in valid for k in range(used)):
            bad_symbol.append(g.serial[i])
        if any(p[k].strip() != "" for k in range(used, len(p))):
            bad_blank.append(g.serial[i])
        matched = (g.p1[i] == g.p2[i])
        if g.is_winner(i) != matched:      # winner<=>matched must hold
            bad_match.append(g.serial[i])
    if bad_symbol:
        r.fail(bad_symbol); r.note(f"{len(bad_symbol)} ticket(s) with an invalid play-symbol code.")
    if bad_blank:
        r.fail(bad_blank);  r.note(f"{len(bad_blank)} ticket(s) with a non-blank unused play position.")
    if bad_match:
        r.fail(bad_match);  r.note(f"{len(bad_match)} ticket(s) where winner/loser status does not match the play symbols.")
    if r.passed:
        r.note("No exceptions were noted. All play positions are valid and "
               "consistent with winner/loser status.")
    return r


def check_02_prize_box(g):
    """Procedure 2: prize print code populated per spec (and matches the system
    prize code on winning tickets)."""
    r = CheckResult(2, "Prize box / position",
        "Check whether the field pertaining to the prize box/position in the "
        "data layout has been populated as per the game specifications.")
    valid_print = {p["print"] for p in g.cfg["prizes"].values()}
    bad_symbol, bad_map = [], []
    for i in range(g.tickets):
        if not g.present(i):
            continue
        pc = g.pcode[i]
        if pc not in valid_print:
            bad_symbol.append(g.serial[i]); continue
        if g.is_winner(i):
            expected = g.cfg["prizes"][g.sys[i]]["print"]
            if pc != expected:
                bad_map.append(g.serial[i])
    if bad_symbol:
        r.fail(bad_symbol); r.note(f"{len(bad_symbol)} ticket(s) with an invalid prize print code.")
    if bad_map:
        r.fail(bad_map); r.note(f"{len(bad_map)} winning ticket(s) whose prize print code does not match the system prize code.")
    if r.passed:
        r.note("No exceptions were noted. All prize print codes are valid and, "
               "for winners, match the system prize code.")
    return r


def check_03_serial(g, load_info):
    """Procedure 3: every serial 1..tickets present exactly once, well formatted."""
    r = CheckResult(3, "Serial number",
        "Check whether the serial-number field is populated per the format "
        "PXXXGGGGTTTTTTT with a unique consecutive number over the full range.")
    width = len(str(g.tickets))
    width = max(width, 7)
    missing = [f"{PASSIVE_FLAG}{LOTTERY_CODE}{g.key}{n+1:0{width}d}"
               for n in range(g.tickets) if g.serial[n] is None]
    dups = [s for (gk, s) in load_info["duplicate_serials"] if gk == g.key]
    oor  = [s for (gk, s) in load_info["out_of_range"] if gk == g.key]
    malformed = [f"row {rw} ch{ch}: {s}" for (rw, ch, s) in load_info["malformed_serials"]]
    if missing:
        r.fail(missing); r.note(f"{len(missing)} serial number(s) missing from the file.")
    if dups:
        r.fail(dups); r.note(f"{len(dups)} duplicate serial number(s).")
    if oor:
        r.fail(oor); r.note(f"{len(oor)} serial(s) outside the configured range.")
    if malformed:
        r.fail(malformed); r.note(f"{len(malformed)} malformed serial value(s) in the file.")
    if r.passed:
        r.note(f"No exceptions were noted. All {g.tickets:,} serials are present "
               "exactly once and correctly formatted.")
    return r


def _barcode_parity(virn):
    return sum(int(d) for d in virn) % 10


def check_04_virn_barcode(g):
    """Procedure 4: VIRN format + range + uniqueness, and barcode parity."""
    r = CheckResult(4, "VIRN and Barcode",
        "Check whether the VIRN and Barcode fields are populated per the format "
        "PXXXGGGGVVVVVVV, with the barcode carrying a parity digit.")
    seen = set()
    bad_fmt, bad_range, dup_virn, bad_bar = [], [], [], []
    for i in range(g.tickets):
        if not g.present(i):
            continue
        v, b = g.virn[i], g.bar[i]
        if (len(v) != 15 or not v.isdigit()
                or v[0] != PASSIVE_FLAG or v[1:4] != LOTTERY_CODE or v[4:8] != g.key):
            bad_fmt.append(g.serial[i]); continue
        if not (2_000_000 <= int(v[8:]) <= 6_999_999):
            bad_range.append(g.serial[i])
        if v in seen:
            dup_virn.append(g.serial[i])
        else:
            seen.add(v)
        if b != v + str(_barcode_parity(v)):
            bad_bar.append(g.serial[i])
    if bad_fmt:
        r.fail(bad_fmt); r.note(f"{len(bad_fmt)} VIRN(s) with an invalid format.")
    if bad_range:
        r.fail(bad_range); r.note(f"{len(bad_range)} VIRN(s) whose random part is outside 2,000,000-6,999,999.")
    if dup_virn:
        r.fail(dup_virn); r.note(f"{len(dup_virn)} duplicate VIRN(s) within the game.")
    if bad_bar:
        r.fail(bad_bar); r.note(f"{len(bad_bar)} barcode(s) whose value/parity digit is incorrect.")
    if r.passed:
        r.note("No exceptions were noted. All VIRNs are valid, unique and their "
               "barcodes carry the correct parity digit.")
    return r


def _agent_letters(agent_tuple):
    return [x for x in agent_tuple if x.strip() != ""]


def check_05_agent_codes(g):
    """Procedure 5: agent validation codes composed per the tier rules."""
    r = CheckResult(5, "Agent validation codes",
        "Check whether the agent validation code fields are populated per the "
        "rules for high-tier/losing tickets and low-tier winning tickets.")
    bad_count, bad_letters = [], []
    for i in range(g.tickets):
        if not g.present(i):
            continue
        letters = _agent_letters(g.agent[i])
        if len(letters) != 3:
            bad_count.append(g.serial[i]); continue
        is_low_winner = (g.is_winner(i) and g.prize_amount(i) == g.cfg["gleps_amount"])
        if is_low_winner:
            others = [x for x in letters if x != AGENT_LOW_THIRD]
            ok = (letters.count(AGENT_LOW_THIRD) == 1
                  and len(others) == 2
                  and all(x in AGENT_HIGH_LETTERS for x in others)
                  and others[0] != others[1])
        else:
            ok = (all(x in AGENT_HIGH_LETTERS for x in letters)
                  and len(set(letters)) == 3)
        if not ok:
            bad_letters.append(g.serial[i])
    if bad_count:
        r.fail(bad_count); r.note(f"{len(bad_count)} ticket(s) not carrying exactly 3 agent letters.")
    if bad_letters:
        r.fail(bad_letters); r.note(f"{len(bad_letters)} ticket(s) whose agent letters break the composition rules.")
    if r.passed:
        r.note("No exceptions were noted. All agent validation codes follow the "
               "prescribed composition rules.")
    return r


def check_06_prize_structure(g):
    """Procedure 6: total prize structure matches the specification."""
    r = CheckResult(6, "Prize structure",
        "Check whether the prize structure prescribed by the game "
        "specification is reflected in the data layout.")
    counts = {}
    for i in range(g.tickets):
        if not g.present(i):
            continue
        counts[g.sys[i]] = counts.get(g.sys[i], 0) + 1
    all_ok = True
    for code, spec in g.cfg["prizes"].items():
        actual = counts.get(code, 0)
        ok = (actual == spec["count"])
        all_ok = all_ok and ok
        r.note(f"Rs.{spec['amount']:>7,} ({code}/{spec['print']}, {spec['tier']:>4}): "
               f"expected {spec['count']:>7,}, found {actual:>7,}  {'OK' if ok else 'MISMATCH'}")
    loss_actual = counts.get(g.cfg["loss_code"], 0)
    loss_ok = (loss_actual == g.cfg["loss_count"])
    all_ok = all_ok and loss_ok
    r.note(f"Losing tickets ({g.cfg['loss_code']}): expected {g.cfg['loss_count']:>7,}, "
           f"found {loss_actual:>7,}  {'OK' if loss_ok else 'MISMATCH'}")
    total = sum(counts.values())
    total_ok = (total == g.tickets)
    all_ok = all_ok and total_ok
    r.note(f"Total tickets: expected {g.tickets:>7,}, found {total:>7,}  "
           f"{'OK' if total_ok else 'MISMATCH'}")
    if not all_ok:
        r.passed = False
        for code, spec in g.cfg["prizes"].items():
            if counts.get(code, 0) != spec["count"]:
                r.offenders.append(f"Rs.{spec['amount']} ({code}): found {counts.get(code,0)}, expected {spec['count']}")
        if not loss_ok:
            r.offenders.append(f"Loss ({g.cfg['loss_code']}): found {loss_actual}, expected {g.cfg['loss_count']}")
    return r


def check_07_gleps(g):
    """Procedure 7: each book carries the guaranteed low-end prizes."""
    need = g.cfg["gleps_per_book"]
    amt  = g.cfg["gleps_amount"]
    r = CheckResult(7, "GLEPS per book",
        f"Check whether each book of {g.book_size} tickets contains the "
        f"guaranteed {need} x Rs.{amt} low-end prizes.")
    bad = []
    for book_no, s, e in iter_books(g):
        got = sum(1 for i in range(s, e) if g.prize_amount(i) == amt)
        if got != need:
            bad.append(f"Book {book_no} (serials {s+1}-{e}): found {got} x Rs.{amt} (expected {need})")
    if bad:
        r.fail(bad); r.note(f"{len(bad)} book(s) without exactly {need} x Rs.{amt}.")
    else:
        r.note(f"No exceptions were noted. Every book contains exactly {need} x Rs.{amt}.")
    return r


def _check_carton_group(g, kind, index, title):
    spec = g.cfg["carton_spec"].get(kind)
    top = g.cfg["top_prize_amount"]
    r = CheckResult(index, title,
        f"Check whether each '{kind}' carton carries the prescribed prize allocation.")
    if not spec:
        r.note(f"No '{kind}' carton group is configured for this game.")
        return r
    bad = []
    example = None
    for carton_no, s, e, k in iter_cartons(g):
        if k != kind:
            continue
        counts = count_amounts(g, s, e)
        problems = []
        for amt, need in spec.get("exact", {}).items():
            got = counts.get(amt, 0)
            if got != need:
                problems.append(f"Rs.{amt}={got} (expected {need})")
        for amt, mn in spec.get("atleast", {}).items():
            got = counts.get(amt, 0)
            if got < mn:
                problems.append(f"Rs.{amt}={got} (min {mn})")
        if "top" in spec:
            gott = counts.get(top, 0)
            if gott != spec["top"]:
                problems.append(f"Rs.{top}(top)={gott} (expected {spec['top']})")
        if problems:
            bad.append(f"Carton {carton_no} (serials {s+1}-{e}): " + ", ".join(problems))
        elif example is None:
            example = (carton_no, dict(counts))
    if bad:
        r.fail(bad); r.note(f"{len(bad)} '{kind}' carton(s) not meeting the allocation.")
    else:
        parts = []
        for amt, need in spec.get("exact", {}).items():
            parts.append(f"Rs.{amt}={need}")
        for amt, mn in spec.get("atleast", {}).items():
            parts.append(f"Rs.{amt}>={mn}")
        if "top" in spec:
            parts.append(f"Rs.{top}={spec['top']}")
        r.note("No exceptions were noted. Every '" + kind + "' carton meets the "
               "allocation (" + ", ".join(parts) + ").")
    return r


def check_08_first_cartons(g):
    """Procedure 8: first carton group."""
    return _check_carton_group(g, "first", 8, "First cartons")


def check_09_last_carton(g):
    """Procedure 9: last carton group."""
    return _check_carton_group(g, "last", 9, "Last carton")


def check_10_nonglep_per_book(g):
    """Procedure 10: each book has at least one NON-GLEPS prize."""
    r = CheckResult(10, "Non-GLEPS per book",
        f"Check whether each book of {g.book_size} tickets contains at least one "
        "NON-GLEPS prize.")
    gleps_amt = g.cfg["gleps_amount"]
    bad = []
    for book_no, s, e in iter_books(g):
        ok = any(g.is_winner(i) and g.prize_amount(i) != gleps_amt for i in range(s, e))
        if not ok:
            bad.append(f"Book {book_no} (serials {s+1}-{e})")
    if bad:
        r.fail(bad); r.note(f"{len(bad)} book(s) with no NON-GLEPS prize.")
    else:
        r.note("No exceptions were noted. Every book contains at least one NON-GLEPS prize.")
    return r


def check_11_one_rs500_per_book(g):
    """Procedure 11: exactly one Rs.500 per book (and at most one Rs.1,000 / top)."""
    r = CheckResult(11, "One Rs.500 per book",
        f"Check whether each book of {g.book_size} tickets contains exactly one "
        "prize of Rs.500 (and no more than one Rs.1,000 or top-tier prize).")
    top = g.cfg["top_prize_amount"]
    bad = []
    for book_no, s, e in iter_books(g):
        c500  = sum(1 for i in range(s, e) if g.prize_amount(i) == 500)
        c1000 = sum(1 for i in range(s, e) if g.prize_amount(i) == 1000)
        ctop  = sum(1 for i in range(s, e) if g.prize_amount(i) == top)
        problems = []
        if c500 != 1: problems.append(f"Rs.500={c500} (expected 1)")
        if c1000 > 1: problems.append(f"Rs.1000={c1000} (max 1)")
        if ctop > 1:  problems.append(f"Rs.{top}={ctop} (max 1)")
        if problems:
            bad.append(f"Book {book_no} (serials {s+1}-{e}): " + ", ".join(problems))
    if bad:
        r.fail(bad); r.note(f"{len(bad)} book(s) breaking the per-book prize rule.")
    else:
        r.note("No exceptions were noted. Every book contains exactly one Rs.500 "
               "and at most one Rs.1,000 / top-tier prize.")
    return r


def check_12_consecutive_play_pattern(g):
    """Procedure 12: no two consecutive tickets share the same ordered play pair.
    Runs inside each channel stream separately."""
    r = CheckResult(12, "Consecutive play pattern",
        "Check whether consecutive tickets contain the same play symbol pattern.")
    bad = []
    for s, e in g.streams:
        for i in range(s, e - 1):
            if not (g.present(i) and g.present(i + 1)):
                continue
            if (g.p1[i], g.p2[i]) == (g.p1[i + 1], g.p2[i + 1]):
                bad.append(f"{g.serial[i]} & {g.serial[i + 1]}")
    if bad:
        r.fail(bad); r.note(f"{len(bad)} instance(s) of two consecutive tickets sharing "
                            f"the same play pattern, affecting {2*len(bad)} tickets.")
    else:
        r.note("No exceptions were noted. Consecutive tickets do not contain the "
               "same play symbol pattern in any instance.")
    return r


def check_13_consecutive_symbols_rotation(g):
    """Procedure 13: no two consecutive tickets share the same unordered pair.
    Runs inside each channel stream separately."""
    r = CheckResult(13, "Consecutive symbols (any rotation)",
        "Check whether consecutive tickets contain the same winning symbols in "
        "any rotation.")
    bad = []
    for s, e in g.streams:
        for i in range(s, e - 1):
            if not (g.present(i) and g.present(i + 1)):
                continue
            if {g.p1[i], g.p2[i]} == {g.p1[i + 1], g.p2[i + 1]}:
                bad.append(f"{g.serial[i]} & {g.serial[i + 1]}")
    if bad:
        r.fail(bad); r.note(f"{len(bad)} instance(s) of two consecutive tickets sharing "
                            f"the same symbols in a rotation, affecting {2*len(bad)} tickets.")
    else:
        r.note("No exceptions were noted. Consecutive tickets do not contain the "
               "same winning symbols in any rotation in any instance.")
    return r


def check_14_five_block_winner(g):
    """Procedure 14: every block of 5 tickets from ticket 001 in each book has a winner."""
    r = CheckResult(14, "Five-ticket block has a winner",
        "Check whether each block of five tickets starting from ticket 001 in "
        "each book contains at least one prize.")
    bad = []
    for book_no, s, e in iter_books(g):
        for blk in range(0, g.book_size, 5):
            bs = s + blk
            be = min(bs + 5, e)
            if not any(g.is_winner(i) for i in range(bs, be)):
                first = bs - s + 1
                bad.append(f"Book {book_no} tickets {first}-{first+4} (serials {bs+1}-{be})")
    if bad:
        r.fail(bad); r.note(f"{len(bad)} five-ticket block(s) with no winner.")
    else:
        r.note("No exceptions were noted. Every block of five tickets contains at "
               "least one prize.")
    return r


def check_15_prize_symbol_run(g):
    """Procedure 15: no run of more than 3 consecutive tickets with the same prize
    print code.  Runs inside each channel stream separately."""
    r = CheckResult(15, "Prize symbol run length",
        "Check whether more than three consecutive tickets contain the same "
        "winning value / prize amount symbol.")
    bad = []
    for s, e in g.streams:
        run_start = s
        for i in range(s + 1, e + 1):
            same = (i < e and g.present(i) and g.present(run_start)
                    and g.pcode[i] == g.pcode[run_start])
            if same:
                continue
            run_len = i - run_start
            if run_len > 3 and g.present(run_start) and g.present(i - 1):
                bad.append(f"{g.pcode[run_start]} x{run_len}: "
                           f"serials {g.serial[run_start]}..{g.serial[i-1]}")
            run_start = i
    if bad:
        r.fail(bad); r.note(f"{len(bad)} run(s) of more than three identical prize symbols.")
    else:
        r.note("No exceptions were noted. No more than three consecutive tickets "
               "share the same prize amount symbol.")
    return r


def run_all_checks(g, load_info):
    return [
        check_01_play_positions(g),
        check_02_prize_box(g),
        check_03_serial(g, load_info),
        check_04_virn_barcode(g),
        check_05_agent_codes(g),
        check_06_prize_structure(g),
        check_07_gleps(g),
        check_08_first_cartons(g),
        check_09_last_carton(g),
        check_10_nonglep_per_book(g),
        check_11_one_rs500_per_book(g),
        check_12_consecutive_play_pattern(g),
        check_13_consecutive_symbols_rotation(g),
        check_14_five_block_winner(g),
        check_15_prize_symbol_run(g),
    ]


# ================================================================== #
#  APPENDICES                                                        #
# ================================================================== #

def build_appendix_I(g):
    """Play symbol distribution across positions 1 and 2."""
    rows = []
    for code, name in g.cfg["play_symbols"].items():
        pos1 = sum(1 for i in range(g.tickets) if g.p1[i] == code)
        pos2 = sum(1 for i in range(g.tickets) if g.p2[i] == code)
        rows.append((name, code, pos1, pos2, pos1 + pos2))
    return rows


def build_appendix_II(g):
    """Prize amount symbol distribution."""
    amt_of = {p["print"]: p["amount"] for p in g.cfg["prizes"].values()}
    counts = {}
    for i in range(g.tickets):
        if not g.present(i):
            continue
        counts[g.pcode[i]] = counts.get(g.pcode[i], 0) + 1
    return [(amt_of[c], c, counts.get(c, 0)) for c in sorted(amt_of, key=lambda c: amt_of[c])]


def build_appendix_III(g):
    """Agent letter distribution by GLEPS / Non-GLEPS / Losing."""
    gleps_amt = g.cfg["gleps_amount"]
    tally = {}
    for i in range(g.tickets):
        if not g.present(i):
            continue
        if g.is_winner(i):
            cat = 0 if g.prize_amount(i) == gleps_amt else 1
        else:
            cat = 2
        for letter in _agent_letters(g.agent[i]):
            tally.setdefault(letter, [0, 0, 0])[cat] += 1
    rows = []
    for letter in sorted(tally):
        gl, ng, ls = tally[letter]
        rows.append((letter, gl, ng, ls, gl + ng + ls))
    return rows


# ================================================================== #
#  TEXT / MARKDOWN REPORT                                            #
# ================================================================== #

def write_text_report(path, all_results, appendices, load_info, layout_path):
    L = []
    W = L.append
    W("# NLB SCRATCH LOTTERY - LAYOUT AUDIT REPORT")
    W("")
    W(f"Layout file : `{os.path.basename(layout_path)}`")
    W(f"Generated   : {datetime.datetime.now():%Y-%m-%d %H:%M:%S}")
    W("")
    W("## File load summary")
    W("")
    W(f"- Blocks (channels) per row : {load_info['blocks_per_row']}")
    W(f"- Data rows read : {load_info['data_rows']:,}")
    W(f"- VOID tickets ignored : {load_info['void_tickets']:,}")
    W(f"- Malformed serials : {len(load_info['malformed_serials']):,}")
    W(f"- Duplicate serials : {len(load_info['duplicate_serials']):,}")
    for gkey, chans in load_info["detected_channels"].items():
        W(f"- Detected: game {gkey} on channels {chans}")
    W("")
    W("## Layout verification")
    W("")
    if load_info["layout_warnings"]:
        W("The following layout discrepancies were found:")
        for wmsg in load_info["layout_warnings"]:
            W(f"- {wmsg}")
    else:
        W("- The file arrangement matches the declared LAYOUT (no discrepancies).")
    W("")

    for game_key, results in all_results.items():
        cfg = GAME_CONFIG[game_key]
        n_exc = sum(1 for r in results if not r.passed)
        W("---")
        W(f"# Game {game_key} - \"{cfg['name']}\"")
        W("")
        W(f"**Overall: {'ALL CHECKS PASSED' if n_exc == 0 else str(n_exc)+' CHECK(S) WITH EXCEPTIONS'}**")
        W("")
        for r in results:
            status = "PASS - No exceptions" if r.passed else f"EXCEPTIONS ({len(r.offenders)})"
            W(f"## {r.index}. {r.title}  -  {status}")
            W("")
            W(f"*Procedure:* {r.procedure}")
            W("")
            for ln in r.finding:
                W(f"- {ln}")
            if not r.passed:
                W("")
                W(f"*Offending items ({len(r.offenders)}):*")
                for o in r.offenders:
                    W(f"  - {o}")
            W("")

        apI, apII, apIII = appendices[game_key]
        W(f"## Appendix I - Play symbol distribution ({game_key})")
        W("")
        W("| Play symbol | Code | Position 1 | Position 2 | Total |")
        W("|---|---|---:|---:|---:|")
        t1 = t2 = tt = 0
        for name, code, p1, p2, tot in apI:
            W(f"| {name} | {code} | {p1:,} | {p2:,} | {tot:,} |")
            t1 += p1; t2 += p2; tt += tot
        W(f"| **Total** |  | **{t1:,}** | **{t2:,}** | **{tt:,}** |")
        W("")
        W(f"## Appendix II - Prize amount symbol distribution ({game_key})")
        W("")
        W("| Prize amount (LKR) | Code | Total |")
        W("|---:|---|---:|")
        tt = 0
        for amt, code, tot in apII:
            W(f"| {amt:,} | {code} | {tot:,} |")
            tt += tot
        W(f"| **Total** |  | **{tt:,}** |")
        W("")
        W(f"## Appendix III - Agent validation code distribution ({game_key})")
        W("")
        W("| Letter | GLEPS | Non-GLEPS | Losing | Total |")
        W("|---|---:|---:|---:|---:|")
        cg = cn = cl = ct = 0
        for letter, gl, ng, ls, tot in apIII:
            W(f"| {letter} | {gl:,} | {ng:,} | {ls:,} | {tot:,} |")
            cg += gl; cn += ng; cl += ls; ct += tot
        W(f"| **Total** | **{cg:,}** | **{cn:,}** | **{cl:,}** | **{ct:,}** |")
        W("")

    with open(path, "w") as f:
        f.write("\n".join(L))


# ================================================================== #
#  WORD REPORT                                                       #
# ================================================================== #

def write_word_report(path, all_results, appendices, load_info, layout_path):
    from docx import Document
    from docx.shared import RGBColor

    doc = Document()
    doc.add_heading("NLB Scratch Lottery - Layout Audit Report", level=0)
    p = doc.add_paragraph()
    p.add_run(f"Layout file: {os.path.basename(layout_path)}\n").italic = True
    p.add_run(f"Generated: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}").italic = True

    doc.add_paragraph(
        f"Blocks per row: {load_info['blocks_per_row']}   |   "
        f"Data rows: {load_info['data_rows']:,}   |   "
        f"VOID tickets: {load_info['void_tickets']:,}   |   "
        f"Malformed: {len(load_info['malformed_serials']):,}   |   "
        f"Duplicates: {len(load_info['duplicate_serials']):,}")

    doc.add_heading("Layout verification", level=2)
    if load_info["layout_warnings"]:
        for wmsg in load_info["layout_warnings"]:
            r = doc.add_paragraph(wmsg).runs[0]
            r.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
    else:
        r = doc.add_paragraph("The file arrangement matches the declared LAYOUT "
                              "(no discrepancies).").runs[0]
        r.font.color.rgb = RGBColor(0x00, 0x80, 0x00)

    for game_key, results in all_results.items():
        cfg = GAME_CONFIG[game_key]
        n_exc = sum(1 for r in results if not r.passed)
        doc.add_page_break()
        doc.add_heading(f'Game {game_key} - "{cfg["name"]}"', level=1)
        run = doc.add_paragraph().add_run(
            "ALL CHECKS PASSED" if n_exc == 0 else f"{n_exc} CHECK(S) WITH EXCEPTIONS")
        run.bold = True
        run.font.color.rgb = RGBColor(0x00, 0x80, 0x00) if n_exc == 0 else RGBColor(0xC0, 0x00, 0x00)

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
            status = "No exceptions were noted." if r.passed else f"Exceptions noted ({len(r.offenders)})."
            run = fc.paragraphs[0].add_run(status)
            run.bold = True
            run.font.color.rgb = RGBColor(0x00, 0x80, 0x00) if r.passed else RGBColor(0xC0, 0x00, 0x00)
            for ln in r.finding:
                fc.add_paragraph(ln)
            if not r.passed and r.offenders:
                fc.add_paragraph("Offending items:")
                MAX_INLINE = 500
                for o in r.offenders[:MAX_INLINE]:
                    fc.add_paragraph("  " + o)
                if len(r.offenders) > MAX_INLINE:
                    fc.add_paragraph(f"  ... {len(r.offenders)-MAX_INLINE:,} more - "
                                     f"see the full list in audit_report.md.")

        apI, apII, apIII = appendices[game_key]

        doc.add_heading("Appendix I - Play symbol distribution", level=2)
        t = doc.add_table(rows=1, cols=5); t.style = "Table Grid"
        for j, h in enumerate(["Play symbol", "Code", "Position 1", "Position 2", "Total"]):
            t.rows[0].cells[j].text = h
        t1 = t2 = tt = 0
        for name, code, p1, p2, tot in apI:
            c = t.add_row().cells
            c[0].text, c[1].text = name, code
            c[2].text, c[3].text, c[4].text = f"{p1:,}", f"{p2:,}", f"{tot:,}"
            t1 += p1; t2 += p2; tt += tot
        c = t.add_row().cells
        c[0].text = "Total"; c[2].text = f"{t1:,}"; c[3].text = f"{t2:,}"; c[4].text = f"{tt:,}"

        doc.add_heading("Appendix II - Prize amount symbol distribution", level=2)
        t = doc.add_table(rows=1, cols=3); t.style = "Table Grid"
        for j, h in enumerate(["Prize amount (LKR)", "Code", "Total"]):
            t.rows[0].cells[j].text = h
        tt = 0
        for amt, code, tot in apII:
            c = t.add_row().cells
            c[0].text = f"{amt:,}"; c[1].text = code; c[2].text = f"{tot:,}"
            tt += tot
        c = t.add_row().cells
        c[0].text = "Total"; c[2].text = f"{tt:,}"

        doc.add_heading("Appendix III - Agent validation code distribution", level=2)
        t = doc.add_table(rows=1, cols=5); t.style = "Table Grid"
        for j, h in enumerate(["Letter", "GLEPS", "Non-GLEPS", "Losing", "Total"]):
            t.rows[0].cells[j].text = h
        cg = cn = cl = ct = 0
        for letter, gl, ng, ls, tot in apIII:
            c = t.add_row().cells
            c[0].text = letter
            c[1].text, c[2].text, c[3].text, c[4].text = f"{gl:,}", f"{ng:,}", f"{ls:,}", f"{tot:,}"
            cg += gl; cn += ng; cl += ls; ct += tot
        c = t.add_row().cells
        c[0].text = "Total"
        c[1].text, c[2].text, c[3].text, c[4].text = f"{cg:,}", f"{cn:,}", f"{cl:,}", f"{ct:,}"

    doc.save(path)


# ================================================================== #
#  MAIN                                                              #
# ================================================================== #

def main():
    if len(sys.argv) < 2:
        print("Usage: python lottery_audit.py <layout_file> [output_dir]")
        sys.exit(1)
    layout_path = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "."
    os.makedirs(out_dir, exist_ok=True)

    print(f"Loading layout file: {layout_path}")
    games, load_info = load_layout(layout_path)
    print(f"  blocks per row     : {load_info['blocks_per_row']}")
    print(f"  data rows          : {load_info['data_rows']:,}")
    print(f"  void tickets       : {load_info['void_tickets']:,}")
    print(f"  malformed serials  : {len(load_info['malformed_serials']):,}")
    print(f"  duplicate serials  : {len(load_info['duplicate_serials']):,}")
    for gkey, chans in load_info["detected_channels"].items():
        print(f"  detected game {gkey}  : channels {chans}")
    if load_info["layout_warnings"]:
        print("  LAYOUT WARNINGS:")
        for w in load_info["layout_warnings"]:
            print(f"    ! {w}")

    all_results = {}
    appendices = {}
    for game_key in GAME_CONFIG:
        # Only audit games that actually appeared in the file.
        if not games[game_key].channels and all(games[game_key].serial[i] is None
                                                 for i in range(min(1, games[game_key].tickets))):
            pass
        print(f"Auditing game {game_key} ({GAME_CONFIG[game_key]['name']}) ...")
        g = games[game_key]
        all_results[game_key] = run_all_checks(g, load_info)
        appendices[game_key] = (build_appendix_I(g),
                                build_appendix_II(g),
                                build_appendix_III(g))

    txt_path = os.path.join(out_dir, "audit_report.md")
    docx_path = os.path.join(out_dir, "audit_report.docx")
    write_text_report(txt_path, all_results, appendices, load_info, layout_path)
    write_word_report(docx_path, all_results, appendices, load_info, layout_path)

    print("\nReports written:")
    print(f"  {txt_path}")
    print(f"  {docx_path}")

    print("\n================ SUMMARY ================")
    if load_info["layout_warnings"]:
        print(f"LAYOUT: {len(load_info['layout_warnings'])} discrepancy(ies) - see report.")
    else:
        print("LAYOUT: matches declaration.")
    for game_key, results in all_results.items():
        exc = [r for r in results if not r.passed]
        print(f"Game {game_key} ({GAME_CONFIG[game_key]['name']}): "
              f"{'ALL PASSED' if not exc else str(len(exc))+' exception(s)'}")
        for r in exc:
            print(f"    - Check {r.index} {r.title}: {len(r.offenders)} offending item(s)")


if __name__ == "__main__":
    main()
