# -*- coding: utf-8 -*-
"""
Synthetic NLB job for regression tests.

Builds a small but complete job - two games, 400 tickets each, 20 books of 20,
four packing slots - whose layout satisfies EVERY rule.  Tests then inject one
defect at a time and check that exactly the right audit check fails.

Game 0901 "TEST MATCH"   - match_two,   lottery 300, channel 1
Game 0902 "TEST SPECIAL" - special_only (Gold Coin / Diamond), lottery 320,
                           channel 2, two specials together forbidden

Per book: 4 x Rs.50 (GLEPS), 1 x Rs.500; the third book of each 5-book slot
also carries the slot's single Rs.1,000.

The module also writes matching game-spec and data-spec TEXT in the NLB
template's shape, so the drafter can be tested end to end without PDFs.
"""

import copy
import random

HIGH = ["W", "S", "A", "D", "Z", "R"]
VOID = "8" * 15
TICKETS, BOOK, SLOT_BOOKS = 400, 20, 5
ROWS_PER_PAGE, LEAD_VOID_ROWS, TRAIL_VOID_ROWS = 4, 8, 4


def fixture_config():
    def game(key, name, lot, ch, rule, symbols, specials, forbidden):
        return {
            "key": key, "name": name, "lottery": lot, "channel": ch,
            "win_rule": rule, "special_symbols": specials, "forbidden": forbidden,
            "play_symbols": symbols, "has_prize_spot": True,
            "prizes": [
                {"sys": "03", "amount": 50, "print": "dd", "tier": "Low", "count": 80},
                {"sys": "07", "amount": 500, "print": "hh", "tier": "High", "count": 20},
                {"sys": "08", "amount": 1000, "print": "jj", "tier": "High", "count": 4},
            ],
            "loss": {"code": "99", "count": 296},
            "gleps_per_book": 4,
            "packing": [{"slots": 4, "books": 5, "allocation": [
                {"amount": 500, "mode": "exact", "n": 5},
                {"amount": 1000, "mode": "exact", "n": 1}]}],
            "group_rules": [
                {"group": "book", "size": 1, "amounts": [500], "mode": "exactly", "n": 1},
                {"group": "book", "size": 1, "amounts": [1000], "mode": "at_most_each", "n": 1}],
            "expected": {"revenue": 20000, "pool": 18000, "payout_pct": 90.0,
                         "win_ratio": 3.85},
        }
    return {
        "schema_version": "1.0",
        "job": {"id": "TEST_0901-0902", "client": "NLB", "title": "NLB Scratch Lottery",
                "ticket_price": 50, "sources": []},
        "layout": {"block_len": 21, "channels": 2, "lead_columns": 1,
                   "offsets": {"serial": 0, "virn": 1, "bar": 2, "sys": 3, "print": 4,
                               "play_first": 5, "play_count": 6, "play_used": 2,
                               "agent_first": 11, "agent_count": 9, "qa": 20},
                   "void_serial": VOID, "passive_flag": "1",
                   "virn_random_range": [2000000, 6999999],
                   "parity_rule": "digit_sum_mod10"},
        "structure": {"tickets_per_game": TICKETS, "book_size": BOOK},
        "agent": {"high_letters": HIGH, "low_letters": {"50": "T"},
                  "positions": 9, "letters_used": 3},
        "fixed_rules": {"max_same_value_run": 3, "winner_every_n_tickets": 5,
                        "gleps_amount": 50},
        "games": [
            game("0901", "TEST MATCH", "300", 1, "match_two",
                 {"KA": "Face", "LA": "Crown", "NA": "Flag", "PA": "Trophy",
                  "QA": "Key", "UA": "Motor Bicycle"}, [], None),
            game("0902", "TEST SPECIAL", "320", 2, "special_only",
                 {"KB": "Gold Coin", "LB": "Diamond", "NB": "Gift Box", "PB": "Hand",
                  "QB": "Bundle of Money", "UB": "Face"}, ["KB", "LB"], "two_special"),
        ],
    }


# ------------------------------------------------------------------ #
#  Ticket generation                                                  #
# ------------------------------------------------------------------ #

def parity(v):
    return str(sum(int(c) for c in v) % 10)


def set_prize(t, g, amount):
    """Make ticket t a winner of `amount`, or a loser if amount is None.
    Sets system code, print code and agent letters consistently."""
    rng = t.setdefault("_rng", random.Random(t["serial"]))
    t["amount"] = amount
    if amount is None:
        t["sys"] = g["loss"]["code"]
        t["print"] = rng.choice([p["print"] for p in g["prizes"]])   # decoy
        letters = rng.sample(HIGH, 3)
    else:
        p = next(p for p in g["prizes"] if p["amount"] == amount)
        t["sys"], t["print"] = p["sys"], p["print"]
        letters = (["T"] + rng.sample(HIGH, 2)) if amount == 50 else rng.sample(HIGH, 3)
    rng.shuffle(letters)
    agent = [""] * 9
    for pos, letter in zip(sorted(rng.sample(range(9), 3)), letters):
        agent[pos] = letter
    t["agent"] = agent


def assign_symbols(tix, g, rng):
    """Play symbols consistent with each ticket's status, with no two
    consecutive tickets sharing a symbol set (so no pattern or rotation repeat)."""
    syms = list(g["play_symbols"])
    sp = set(g.get("special_symbols") or [])
    nonsp = [s for s in syms if s not in sp]
    prev = None
    for t in tix:
        if t is None:
            prev = None
            continue
        for _ in range(200):
            if g["win_rule"] == "match_two":
                if t["amount"]:
                    s = rng.choice(syms)
                    pair = (s, s)
                else:
                    pair = tuple(rng.sample(syms, 2))
            else:                                      # special_only
                if t["amount"]:
                    a, b = rng.choice(sorted(sp)), rng.choice(nonsp)
                    pair = (a, b) if rng.random() < 0.5 else (b, a)
                else:
                    pair = (rng.choice(nonsp), rng.choice(nonsp))   # a pair still loses
            if set(pair) != prev:
                break
        t["p1"], t["p2"] = pair
        prev = set(pair)


def _book_layout(b, rng):
    """Winner positions for book b: first and last ticket are losers (so no run
    crosses a book boundary), every block of 5 has a winner, no run of more
    than three consecutive same-value winners."""
    items = [50] * 4 + [500] + ([1000] if b % SLOT_BOOKS == 2 else [])
    while True:
        pos = sorted(rng.sample(range(1, BOOK - 1), len(items)))
        if not all(any(s <= p < s + 5 for p in pos) for s in range(0, BOOK, 5)):
            continue
        vals = items[:]
        rng.shuffle(vals)
        assign = dict(zip(pos, vals))
        run, prev, ok = 0, None, True
        for i in range(BOOK):
            v = assign.get(i)
            if v is None:
                run, prev = 0, None
                continue
            run = run + 1 if v == prev else 1
            prev = v
            if run > 3:
                ok = False
                break
        if ok:
            return assign


def make_game(g, seed):
    rng = random.Random(seed)
    tix = []
    used = set()
    for b in range(TICKETS // BOOK):
        assign = _book_layout(b, rng)
        for i in range(BOOK):
            n = b * BOOK + i + 1
            t = {"serial": f"1{g['lottery']}{g['key']}{n:07d}", "_rng": random.Random(seed * 100003 + n)}
            while True:
                v = f"1{g['lottery']}{g['key']}{rng.randint(2000000, 6999999):07d}"
                if v not in used:
                    used.add(v)
                    break
            t["virn"], t["bar"] = v, v + parity(v)
            t["qa"] = "$"
            set_prize(t, g, assign.get(i))
            tix.append(t)
    assign_symbols(tix, g, rng)
    return tix


def make_job(seed=7):
    cfg = fixture_config()
    return cfg, {g["key"]: make_game(g, seed + i) for i, g in enumerate(cfg["games"])}


def clone(tickets):
    """Deep copy (agent letters are lists - a shallow copy lets one test's
    edits leak into every later test)."""
    return {k: [None if t is None else copy.deepcopy({kk: vv for kk, vv in t.items()
                                                      if kk != "_rng"})
                for t in v] for k, v in tickets.items()}


# ------------------------------------------------------------------ #
#  Layout writer                                                      #
# ------------------------------------------------------------------ #

def _block(t):
    return [t["serial"], t["virn"], t["bar"], t["sys"], t["print"], t["p1"], t["p2"],
            "", "", "", ""] + t["agent"] + [t["qa"]]


def _void_block(g):
    s = list(g["play_symbols"])
    return [VOID, VOID, "8" * 16, "99", g["prizes"][0]["print"], s[0], s[1],
            "", "", "", "", "W", "", "S", "", "A", "", "", "", "", "$"]


def write_layout(path, cfg, tickets):
    games = sorted(cfg["games"], key=lambda g: g["channel"])
    header = ["PageNo"]
    for ch in range(1, len(games) + 1):
        header += [f"SerialNo{ch}_01", f"VIRN{ch}_01", f"BAR{ch}_01",
                   f"SystemPrizeCode{ch}_01", f"PrizePrintCode{ch}_01"]
        header += [f"Play{ch}{k}_01" for k in range(1, 7)]
        header += [f"Agent_ValCode{ch}{k}_01" for k in range(1, 10)]
        header += [f"QA_SampleCode{ch}_01"]
    rows = []
    rows += [[_void_block(g) for g in games] for _ in range(LEAD_VOID_ROWS)]
    for i in range(TICKETS):
        rows.append([_block(tickets[g["key"]][i]) if tickets[g["key"]][i] is not None
                     else _void_block(g) for g in games])
    rows += [[_void_block(g) for g in games] for _ in range(TRAIL_VOID_ROWS)]
    with open(path, "w", newline="") as f:
        f.write(",".join(header) + "\r\n")
        for r, blocks in enumerate(rows):
            fields = [f"{r // ROWS_PER_PAGE + 1:06d}"]
            for b in blocks:
                fields += b
            f.write(",".join(fields) + "\r\n")
    return len(rows)


# ------------------------------------------------------------------ #
#  Specification text in the NLB template's flattened shape           #
# ------------------------------------------------------------------ #

TOC = ("CONTENTS 1 INTRODUCTION ........................ 4 1.1 Game Mechanism "
       "........................ 4 3 GAME SPECIFICATIONS ........................ 5 "
       "3.0 Game Play Mechanism ........................ 5 3.3 Play Symbols "
       "........................ 5 3.4 Serial Numbering ........................ 5 "
       "4.1 Prize Structure ........................ 7 5.0 Restrictions "
       "........................ 8 5.1 Play Requirement ........................ 8 ")

MECH = {
    "0901": "Scratch and find two similar symbols and win the corresponding prize",
    "0902": 'Scratch and find a "Gold Coin" symbol or a "Diamond" symbol and win that corresponding prize',
}


def game_spec_text(cfg, key, extra_restrictions=""):
    g = next(x for x in cfg["games"] if x["key"] == key)
    lname = {"300": "SEVANA", "320": "SAMURDHI"}[g["lottery"]]
    names = list(g["play_symbols"].values())
    rows = " ".join(f"{p['amount']:,} {p['sys']} {p['print'] or '-'} {p['tier']} "
                    f"{p['count']:,} {p['amount']*p['count']:,}" for p in g["prizes"])
    sub = sum(p["count"] for p in g["prizes"])
    pool = sum(p["amount"] * p["count"] for p in g["prizes"])
    return (
        "PRINTCARE SECURE LIMITED (PSL) GAME SPECIFICATION FOR NATIONAL LOTTERIES "
        f"BOARD (NLB) {lname} LOTTERIES ({g['lottery']}) GAME NO: {key} - \"{g['name']}\" "
        f"(Rs. 50) PO REF: Quantity: {TICKETS} Tickets CONFIDENTIAL DOCUMENT CONTROL "
        "VERSION DATE ISSUED STATUS 1.0 June 23, 2026 Final Prepared by Checked by "
        + TOC +
        f"1 INTRODUCTION 1.1 Game Mechanism This lottery will consist of {TICKETS} tickets. "
        f"Players will be required to {MECH[key][0].lower()}{MECH[key][1:]}. "
        f"Finish: Tickets are to be perforated and fan folded five to view in books of {BOOK}. "
        f"3 GAME SPECIFICATIONS 3.0 Game Play Mechanism {MECH[key]}. "
        "3.1 Game Classification (Perfect or Non-Perfect) The complete game is a Perfect Game. "
        "3.3 Play Symbols This game will use following symbols. Category Symbols Play Symbols "
        f"{', '.join(names[:-1])} and {names[-1]} Prize Amount Symbols Rs. 50, Rs. 500 and "
        "Rs. 1,000 3.4 Serial Numbering Each ticket will contain a unique number. Passive/ "
        "Scratch Lottery Code Game Number Start Serial Number End Serial Number "
        f"1 {g['lottery']} {key} 0000001 {TICKETS:07d} 3.5 Validation "
        "Non-winning and High-Tier Winning Tickets Three distinct letters chosen from: "
        "W, S, A, D, Z, R Low-Tier Winning Tickets Two distinct letters chosen from: "
        "W, S, A, D, Z, R plus one additional letter based on the prize: Prize Agent Code "
        "Third Letter Rs. 50 T 4 PRIZE STRUCTURE 4.0 Parameters Ticket price: Rs. 50 "
        f"Tickets: {TICKETS} Revenue: Rs. {TICKETS*50:,} Prize payout: "
        f"{pool/(TICKETS*50)*100:.1f}% Prize pool: Rs. {pool:,} Guaranteed win ratio: "
        f"1:{TICKETS/sub:.2f} 4.1 Prize Structure Prize Amount (Rs) Prize System Code Play "
        f"Symbol Code Prize Tier Number Prizes Prize Total (Rs) {rows} Sub Total {sub:,} "
        f"{pool:,} Non-Win 099 {g['loss']['count']:,} Game Total {TICKETS:,} {pool:,} "
        "4.2 Guaranteed Low End Prize Structure (GLEPS) The GLEPS prize value for each "
        f"book of {BOOK} tickets will be: Prize Amount (Rs) Number of Prizes Prize Value "
        f"per Book (Rs) 50 4 200.00 Total 4 200.00 5 GAME RESTRICTIONS AND PLAY "
        f"REQUIREMENTS 5.0 Restrictions A slot of {SLOT_BOOKS*BOOK} Tickets ({SLOT_BOOKS} "
        f"books) should contain the following prizes. There will be "
        f"{TICKETS//(SLOT_BOOKS*BOOK)} boxes with this prize allocation. "
        "• Rs. 500 - 5 winners • Rs. 1,000 - 1 winner "
        "Each book should contain one prize of Rs. 500. "
        "Each book should not contain more than one prize of Rs. 1,000. "
        + extra_restrictions +
        'Each book should contain at least one "NON-GLEPS" prize. '
        "No consecutive tickets with same play patterns. No consecutive tickets with same "
        "winning symbols in any rotation. No logical relationship between play patterns "
        "and VIRN. No more than three consecutive tickets with same prize value. Any "
        "multiples of 5 tickets starting from ticket number 001 in a book should contain "
        "at least one winner. 5.1 Play Requirement Not applicable for this game. "
        f"7.0 Books Each book will contain {BOOK} tickets.")


def data_spec_text(cfg, heading_override=None):
    """heading_override: {game key: wrong 'LLL GGGG'} to mislabel a symbol table."""
    heading_override = heading_override or {}
    games = sorted(cfg["games"], key=lambda g: g["channel"])
    how = " ".join(f"Game {g['lottery']} {g['key']}: {MECH[g['key']]}" for g in games)
    pz = " ".join(
        f"Game {g['lottery']} {g['key']} Prize Amount LKR Print Code - Smalls System Prize "
        f"Code " + " ".join(f"{p['amount']:,} {p['print'] or '-'} {p['sys']}" for p in g["prizes"])
        for g in games)
    sy = " ".join(
        f"Game {heading_override.get(g['key'], g['lottery'] + ' ' + g['key'])} Play Symbol "
        "Print Code - Capitals " + " ".join(f"{n} {c}" for c, n in g["play_symbols"].items())
        for g in games)
    na = " ".join(f"Game {g['key']}: " + ('"Gold Coin" and "Diamond" symbols together'
                                          if g.get("forbidden") else "N/A") for g in games)
    chans = " ".join(f"{g['channel']} ({g['key']})" for g in games)
    pages = (LEAD_VOID_ROWS + TICKETS + TRAIL_VOID_ROWS) // ROWS_PER_PAGE
    return (
        "PRINTCARE SECURE LIMITED INSTANT SCRATCH LOTTERY DATA GENERATION SPECIFICATION "
        "Document Control Original Version: V1.0 Date Issued: 20 July 2026 "
        f"How to Play: {how} Number of Play Symbols: Six "
        f"Prize Symbol Print Codes: {pz} Play Symbol Print Codes: {sy} "
        "Agent Validation Codes: Ticket Status Codes High Winner and Loser Tickets Three of "
        "either - W, S, A, D, Z or R Req'd Low Winner - Rs50/- T plus two of above six "
        "codes Req'd VIRN n(15), n is 1 next nnn is Lottery Code and nnnnnnn is unique "
        "random numbers in range 2000000 thru 6999999 Game play symbol patterns NOT "
        f"ALLOWED are: {na} Agent Validation Codes X,X,X,X,X,X,X,X,X "
        f"Print Layout Pages Tickets will be printed in pages of "
        f"{ROWS_PER_PAGE*len(games)} tickets on two channels across the press web. "
        f"Channel {chans} Colour Scheme A B Page Number: nnnnnn (Range 000001 - "
        f"{pages:06d}) Channel Data occurs two times: Ticket Data occurs four times per "
        f"channel per page meaning that there are {ROWS_PER_PAGE*len(games)} tickets per "
        "page. Live data will be preceded by two pages of void losing tickets.")
