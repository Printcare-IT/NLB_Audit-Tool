#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parsers for NLB specification documents.

NLB game specifications follow a fixed template (same headings, same table
layouts, same restriction wording), so the fields are read with targeted
patterns rather than guessed.  Every parser returns what it found PLUS a list
of problems it could not resolve; nothing is silently invented.  Anything a
parser cannot read cleanly becomes a review item in the drafted markdown.

Input is always the flattened text produced by doc_text.flatten().
"""

import re


def _int(s):
    return int(str(s).replace(",", "").strip())


WORD_NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
            "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
            "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30,
            "forty": 40, "fifty": 50, "sixty": 60, "hundred": 100}


def _num_or_word(s):
    s = s.strip().lower()
    if s in WORD_NUM:
        return WORD_NUM[s]
    try:
        return _int(s)
    except ValueError:
        return None


# ------------------------------------------------------------------ #
#  Classification                                                     #
# ------------------------------------------------------------------ #

def classify(flat):
    """Return 'game_spec', 'data_spec' or None."""
    up = flat.upper()
    if "DATA GENERATION SPECIFICATION" in up:
        return "data_spec"
    if "GAME SPECIFICATION" in up and re.search(r"GAME NO:\s*\d{4}", up):
        return "game_spec"
    return None


# ------------------------------------------------------------------ #
#  Game specification                                                 #
# ------------------------------------------------------------------ #

PRIZE_ROW = re.compile(
    r"(?:(?P<num>\d[\d,]*)|(?P<label>[A-Z][A-Za-z ]*?))\s+"
    r"(?P<sys>\d{2})\s+(?:(?P<print>[a-z]{2}|-)\s+)?"
    r"(?P<tier>Low|High)\s+(?P<count>\d[\d,]*)\s+(?P<total>\d[\d,]*)"
    r"(?:\s+\(Rs\.?\s*(?P<post>\d[\d,]*)\))?")

BULLET = re.compile(
    r"(?:(?P<label>[A-Z][A-Za-z ]*?)\s*\(Rs\.?\s*(?P<lamt>\d[\d,]*)\)"
    r"|Rs\.?\s*(?P<amt>\d[\d,]*))\s*-\s*(?P<atl>at least\s+)?"
    r"(?P<n>\d+)\s+winner")

SENTENCE = re.compile(
    r"(Each (?:book|batch of (\d+) books) should .+?)\."
    r"(?=\s+(?:Each|No |Any |A slot|The last)|\s*$)")


def parse_game_spec(flat, source=""):
    g = {"source": source, "problems": [], "evidence": {}}
    P = g["problems"]

    m = re.search(r'GAME NO:\s*(\d{4})\s*-\s*"(.+?)"\s*\(Rs\.?\s*([\d,]+)\)', flat)
    if m:
        g["key"], g["name"], g["ticket_price"] = m.group(1), m.group(2).strip(), _int(m.group(3))
    else:
        P.append("could not read the game number / name / price from the title page")

    m = re.search(r"(SEVANA|SAMURDHI)\s+LOTTERIES\s*\((\d{3})\)", flat, re.I)
    if m:
        g["lottery_name"], g["lottery"] = m.group(1).upper(), m.group(2)
    m = re.search(r"\b1\s+(\d{3})\s+(\d{4})\s+0000001\s+(\d{7})", flat)
    if m:
        g["serial_lottery"], g["serial_game"] = m.group(1), m.group(2)
        g["serial_last"] = _int(m.group(3))

    # header order varies by format ("CONTROL VERSION DATE ISSUED STATUS" in
    # Word, "DATE ISSUED STATUS CONTROL VERSION" in the PDF layout)
    m = re.search(r"STATUS\s+(?:CONTROL VERSION\s+)?([\d.]+)\s+"
                  r"([A-Z][a-z]+ \d{1,2},? \d{4})\s+(\w+)", flat)
    if m:
        g["doc_version"], g["doc_date"], g["doc_status"] = m.group(1), m.group(2), m.group(3)

    # ---- parameters ------------------------------------------------
    def grab(pat, conv=_int):
        mm = re.search(pat, flat)
        return conv(mm.group(1)) if mm else None
    g["tickets"] = grab(r"Tickets:\s*(\d[\d,]*)")
    g["revenue"] = grab(r"Revenue:\s*Rs\.?\s*(\d[\d,]*)")
    g["payout_pct"] = grab(r"Prize payout:\s*([\d.]+)\s*%", float)
    g["pool"] = grab(r"Prize pool:\s*Rs\.?\s*(\d[\d,]*)")
    g["win_ratio"] = grab(r"win ratio:\s*1\s*:\s*([\d.]+)", float)
    tp = grab(r"Ticket price:\s*Rs\.?\s*(\d[\d,]*)")
    if tp and g.get("ticket_price") and tp != g["ticket_price"]:
        P.append(f"title page says Rs.{g['ticket_price']} but parameters say Rs.{tp}")
    for k in ("tickets", "revenue", "payout_pct", "pool", "win_ratio"):
        if g[k] is None:
            P.append(f"could not read '{k}' from the prize parameters")

    # ---- game mechanism --------------------------------------------
    # the sentence under "3.0 Game Play Mechanism"; skip the contents page
    g["mechanism"] = None
    for mm in re.finditer(r"Game Play Mechanism\s+((?:Scratch|Find|Match)[^.]*)\.", flat):
        if "...." not in mm.group(1):
            g["mechanism"] = mm.group(1).strip()
            break
    if not g["mechanism"]:
        P.append("could not find the game play mechanism sentence")

    m = re.search(r"Category\s+Symbols\s+Play Symbols\s+(.+?)\s+Prize Amount Symbols", flat)
    if m:
        g["play_symbol_names"] = [s.strip() for s in
                                  re.split(r",\s*|\s+and\s+", m.group(1)) if s.strip()]
    m = re.search(r"Prize Amount Symbols\s+(.+?)\s+3\.4\s+Serial", flat)
    g["prize_symbol_text"] = m.group(1).strip() if m else None

    # ---- prize table -----------------------------------------------
    sub = flat.find("Sub Total")
    rows = []
    if sub < 0:
        P.append("could not find the prize structure table (no 'Sub Total')")
    else:
        region = flat[max(0, sub - 3000):sub]
        for mm in PRIZE_ROW.finditer(region):
            amt = _int(mm.group("num")) if mm.group("num") else (
                _int(mm.group("post")) if mm.group("post") else None)
            if amt is None:
                continue
            cnt, tot = _int(mm.group("count")), _int(mm.group("total"))
            if amt * cnt != tot:
                continue            # not a genuine prize row
            label = None
            if mm.group("label"):
                label = f"{mm.group('label').strip()} (Rs. {amt:,})"
            pc = mm.group("print")
            rows.append({"sys": mm.group("sys"), "amount": amt,
                         "print": "" if pc in (None, "-") else pc,
                         "tier": mm.group("tier"), "count": cnt,
                         "label": label})
        m = re.search(r"Sub Total\s+(\d[\d,]*)\s+(\d[\d,]*)", flat[sub:sub + 80])
        if m:
            g["subtotal_count"], g["subtotal_amount"] = _int(m.group(1)), _int(m.group(2))
    g["prizes"] = rows
    if sub >= 0 and not rows:
        P.append("found the prize table but could not read any rows")
    if rows and g.get("subtotal_count") and \
            sum(r["count"] for r in rows) != g["subtotal_count"]:
        P.append(f"prize rows sum to {sum(r['count'] for r in rows):,} but the "
                 f"table's Sub Total is {g['subtotal_count']:,} - a row may be "
                 "missing or unreadable")

    m = re.search(r"Non-Win\s+(\d{2,3})\s+(\d[\d,]*)", flat)
    if m:
        code = m.group(1)
        g["loss_code_written"] = code
        g["loss_code"] = code[-2:]           # spec writes 099; data uses 99
        g["loss_count"] = _int(m.group(2))
    else:
        P.append("could not read the Non-Win row")

    # ---- GLEPS and book size ----------------------------------------
    m = re.search(r"GLEPS prize value for each book of (\d+) tickets will be:(.+?)Total", flat)
    if m:
        g["book_size"] = int(m.group(1))
        mm = re.search(r"(\d[\d,]*)\s+(\d+)\s+(\d[\d,]*\.\d{2})", m.group(2))
        if mm and _int(mm.group(1)) * int(mm.group(2)) == float(mm.group(3).replace(",", "")):
            g["gleps_amount"], g["gleps_per_book"] = _int(mm.group(1)), int(mm.group(2))
        else:
            P.append("could not read the GLEPS row")
    else:
        P.append("could not find the GLEPS section")
    bs = set(int(x) for x in re.findall(r"books of (\d+)", flat))
    bs |= set(int(x) for x in re.findall(r"Each book will contain (\d+) tickets", flat))
    if g.get("book_size"):
        bs.add(g["book_size"])
    if len(bs) > 1:
        P.append(f"book size is stated inconsistently: {sorted(bs)}")
    elif bs and not g.get("book_size"):
        g["book_size"] = bs.pop()

    # ---- agent validation -------------------------------------------
    m = re.search(r"Three distinct letters chosen from:\s*([A-Z](?:\s*,\s*[A-Z])+)", flat)
    g["agent_high"] = [x.strip() for x in m.group(1).split(",")] if m else None
    lows = re.findall(r"Third Letter\s+((?:Rs\.?\s*\d[\d,]*\s+[A-Z]\b\s*)+)", flat)
    g["agent_low"] = {}
    for block in lows:
        for a, l in re.findall(r"Rs\.?\s*(\d[\d,]*)\s+([A-Z])\b", block):
            g["agent_low"][_int(a)] = l
    if not g["agent_high"]:
        P.append("could not read the high-tier agent letters")
    if not g["agent_low"]:
        P.append("could not read the low-tier agent letter")

    # ---- restrictions -----------------------------------------------
    region = None
    for mm in re.finditer(r"Restrictions", flat):
        end = flat.find("Play Requirement", mm.end())
        seg = flat[mm.end(): end if end > 0 else mm.end() + 4000]
        if "consecutive" in seg:
            region = seg.strip()
            break
    g["restrictions_text"] = region
    if not region:
        P.append("could not find the restrictions section")
        return g
    g.update(parse_restrictions(region, g.get("tickets"), g.get("book_size")))
    return g


def parse_restrictions(text, tickets, book_size):
    out = {"packing": [], "group_rules": [], "fixed": {},
           "unrecognised": [], "red_missing": []}

    # ---- packing blocks ---------------------------------------------
    heads = []
    for m in re.finditer(r"A slot of (\d[\d,]*) Tickets \((\d+) books\) should contain "
                         r"the following prizes\. There will be (\d+) boxes", text):
        heads.append((m.start(), m.end(), int(m.group(3)), int(m.group(2)), m.group(0)))
    for m in re.finditer(r"The last box containing (\d[\d,]*) Tickets \((\d+) books\) "
                         r"should have:", text):
        heads.append((m.start(), m.end(), 1, int(m.group(2)), m.group(0)))
    for m in re.finditer(r"Each box \((\d[\d,]*) Tickets\) should contain:", text):
        box_t = _int(m.group(1))
        books = box_t // book_size if book_size else None
        slots = tickets // box_t if tickets else None
        if book_size and box_t % book_size:
            out["unrecognised"].append(
                f"box of {box_t:,} tickets is not a whole number of {book_size}-ticket books")
        if tickets and tickets % box_t:
            out["unrecognised"].append(
                f"{tickets:,} tickets is not a whole number of {box_t:,}-ticket boxes")
        heads.append((m.start(), m.end(), slots, books, m.group(0)))
    heads.sort()
    stop = re.compile(r"(?:A slot of|The last box|Each box|Each book|Each batch|No |Any )")
    for i, (s, e, slots, books, _) in enumerate(heads):
        nxt = stop.search(text, e)
        body = text[e: nxt.start() if nxt else len(text)]
        alloc = []
        for b in BULLET.finditer(body):
            amt = _int(b.group("lamt") or b.group("amt"))
            alloc.append({"amount": amt,
                          "mode": "min" if b.group("atl") else "exact",
                          "n": int(b.group("n"))})
        out["packing"].append({"slots": slots, "books": books, "allocation": alloc})

    # ---- per-book / per-batch sentences -----------------------------
    for m in SENTENCE.finditer(text):
        s = m.group(1)
        low = s.lower()
        amounts = [_int(x) for x in re.findall(r"Rs\.?\s*(\d[\d,]*)", s)]
        if "non-gleps" in low:
            out["fixed"]["non_gleps_per_book"] = True
            continue
        if m.group(2):
            if "minimum of one" in low and amounts:
                out["group_rules"].append({"group": "batch", "size": int(m.group(2)),
                                           "amounts": amounts, "mode": "min", "n": 1,
                                           "wording": s})
            else:
                out["unrecognised"].append(s)
            continue
        if "not contain more than one" in low and amounts:
            rule = {"group": "book", "size": 1, "amounts": amounts,
                    "mode": "at_most_each", "n": 1}
        elif "either one prize of" in low and "or both" in low and amounts:
            rule = {"group": "book", "size": 1, "amounts": amounts,
                    "mode": "at_least_one_total", "n": 1}
        elif "either one prize of" in low and amounts:
            rule = {"group": "book", "size": 1, "amounts": amounts,
                    "mode": "exactly_one_total", "n": 1}
        elif re.search(r"contain one prize of", low) and len(amounts) == 1:
            rule = {"group": "book", "size": 1, "amounts": amounts,
                    "mode": "exactly", "n": 1}
        else:
            out["unrecognised"].append(s)
            continue
        rule["wording"] = s
        out["group_rules"].append(rule)

    # ---- the six fixed ("red") restrictions -------------------------
    low = text.lower()
    checks = {
        "non-gleps prize per book": "non-gleps" in low,
        "no consecutive same play patterns":
            "no consecutive tickets with same play patterns" in low,
        "no consecutive same symbols in any rotation":
            "no consecutive tickets with same winning symbols in any rotation" in low,
        "no play pattern / VIRN relationship":
            "no logical relationship between play patterns and virn" in low,
    }
    m = re.search(r"no more than (\w+) consecutive tickets with same prize value", low)
    checks["maximum same prize value run"] = bool(m)
    if m:
        out["fixed"]["max_same_value_run"] = _num_or_word(m.group(1))
    m = re.search(r"multiples of (\w+) tickets starting from ticket number 001", low)
    checks["winner in every block of N tickets"] = bool(m)
    if m:
        out["fixed"]["winner_every_n_tickets"] = _num_or_word(m.group(1))
    out["red_missing"] = [k for k, ok in checks.items() if not ok]
    return out


# ------------------------------------------------------------------ #
#  Winning-rule reading from the mechanism sentence                   #
# ------------------------------------------------------------------ #

def read_win_rule(mechanism):
    """Return (rule, [special symbol NAMES], note)."""
    if not mechanism:
        return None, [], "no mechanism sentence"
    low = mechanism.lower()
    singles = re.findall(r"\ban?\s+\"([^\"]+)\"\s+symbol", mechanism)
    singles += re.findall(r"\ban?\s+'([^']+)'\s+symbol", mechanism)
    pair = re.findall(r"two\s+\"?([A-Z][A-Za-z]*(?: [A-Z][A-Za-z]*)*)\"?\s+symbols", mechanism)
    has_two = "two similar" in low
    if singles and has_two:
        return "match_two_or_special", singles, None
    if singles and not has_two:
        return "special_only", singles, None
    note = None
    if pair:
        note = (f"two '{pair[0]}' symbols is an ordinary matching pair, "
                "not a special-symbol rule")
    return "match_two", [], note


# ------------------------------------------------------------------ #
#  Data generation specification                                      #
# ------------------------------------------------------------------ #

def parse_data_spec(flat, source=""):
    d = {"source": source, "problems": [], "games": {}}
    P = d["problems"]

    m = re.search(r"Version:\s*(V[\d.]+)\s+Date Issued:\s*(.+?\d{4})", flat)
    if m:
        d["doc_version"], d["doc_date"] = m.group(1), m.group(2).strip()

    # how to play, per game
    m = re.search(r"How to Play:\s*(.+?)\s+Number of Play Symbols", flat)
    if m:
        for mm in re.finditer(r"Game (\d{3}) (\d{4})\s*:\s*(.+?)(?=\s+Game \d{3} \d{4}\s*:|$)",
                              m.group(1)):
            d["games"].setdefault(mm.group(2), {})["how_to_play"] = mm.group(3).strip()

    # tables headed "Game LLL GGGG"
    heads = list(re.finditer(r"Game (\d{3}) (\d{4})\s+(Prize Amount LKR|Play Symbol)", flat))
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(flat)
        seg = flat[h.end(): end]
        cut = re.search(r"(Play Symbol Print Codes|Agent Validation|Prize Symbol Print Codes)", seg)
        if cut:
            seg = seg[:cut.start()]
        lot, key = h.group(1), h.group(2)
        entry = {"heading": f"Game {lot} {key}", "heading_lottery": lot}
        if h.group(3) == "Prize Amount LKR":
            seg = re.sub(r"^.*?System Prize Code", "", seg)
            rows = []
            for mm in re.finditer(
                    r"(?:(?P<label>[A-Za-z][A-Za-z ]*?)\s*\((?P<lamt>\d[\d,]*)\)"
                    r"|(?P<amt>\d[\d,]*))\s+(?P<print>[a-z]{2}|-)\s+(?P<sys>\d{2})\b", seg):
                rows.append({"amount": _int(mm.group("lamt") or mm.group("amt")),
                             "print": "" if mm.group("print") == "-" else mm.group("print"),
                             "sys": mm.group("sys")})
            entry["prize_codes"] = rows
            d.setdefault("prize_tables", []).append((key, entry))
        else:
            seg = re.sub(r"^.*?Print Code - Capitals", "", seg)
            syms, name = [], []
            for tok in seg.split():
                if re.fullmatch(r"[A-Z]{2}", tok) and name:
                    syms.append((tok, " ".join(name)))
                    name = []
                else:
                    name.append(tok)
            entry["symbols"] = syms
            d.setdefault("symbol_tables", []).append((key, entry))

    # forbidden patterns
    m = re.search(r"NOT ALLOWED are:\s*(.+?)(?:\s+Agent Validation|$)", flat)
    if m:
        for mm in re.finditer(r"Game (?:\d{3} )?(\d{4})\s*:\s*(.+?)(?=\s+Game (?:\d{3} )?\d{4}\s*:|$)",
                              m.group(1)):
            d["games"].setdefault(mm.group(1), {})["not_allowed"] = mm.group(2).strip()

    # agent codes
    m = re.search(r"Three of either\s*-\s*([A-Z](?:\s*,\s*[A-Z])*(?:\s*,?\s*or\s+[A-Z])?)", flat)
    if m:
        d["agent_high"] = re.findall(r"\b([A-Z])\b", m.group(1))
    d["agent_low"] = {}
    for mm in re.finditer(r"Low Winner\s*-\s*Rs\.?\s*(\d[\d,]*)\s*/?-?\s+([A-Z]) plus two", flat):
        d["agent_low"][_int(mm.group(1))] = mm.group(2)

    m = re.search(r"range (\d{7}) thru (\d{7})", flat)
    if m:
        d["virn_range"] = [int(m.group(1)), int(m.group(2))]

    m = re.search(r"Channel\s+((?:\d+\s*\(\d{4}\)\s*)+)", flat)
    if m:
        d["channel_map"] = {k: int(c) for c, k in re.findall(r"(\d+)\s*\((\d{4})\)", m.group(1))}
    m = re.search(r"Range (\d{6})\s*-\s*(\d{6})", flat)
    if m:
        d["page_range"] = [int(m.group(1)), int(m.group(2))]
    m = re.search(r"(\d+) tickets per page", flat)
    if m:
        d["tickets_per_page"] = int(m.group(1))
    m = re.search(r"preceded by (\w+) pages of void", flat, re.I)
    if m:
        d["leading_void_pages"] = _num_or_word(m.group(1))
    m = re.search(r"Channel Data occurs (\w+) times", flat)
    if m:
        d["channels_stated"] = _num_or_word(m.group(1))
    m = re.search(r"printed in pages of (?:\d+ tickets (?:on|in) )?(\w+) channels", flat)
    if m:
        d["channels_prose"] = _num_or_word(m.group(1))
    return d


def forbidden_from_text(txt):
    if not txt:
        return None
    low = txt.lower()
    if low.startswith("n/a") or low == "none":
        return None
    if "together" in low or low.startswith("two"):
        return "two_special"
    return "unrecognised"
