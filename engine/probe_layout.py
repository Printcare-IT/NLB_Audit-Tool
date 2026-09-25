#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NLB LAYOUT FILE MEASURING SCRIPT
================================

Reads a layout file and reports WHAT IS ACTUALLY IN IT.  It takes no settings
file and assumes as little as possible: the block structure, the channel-to-game
map, the prize counts, the void convention and the parity rule are all worked
out from the data itself.

    python probe_layout.py <layout file> [--out measured_facts.json]
                           [--config <job_config.json>]

Two uses:

  1. NEW JOB - run it on its own.  The output is the evidence base for drafting
     the markdown specification, so that every figure in the draft is either
     quoted from a specification document or measured here.  Nothing is guessed.

  2. EXISTING JOB - pass --config as well.  The script then compares what it
     measured against what the settings claim, and lists every disagreement.
     This catches a settings file that has drifted from the delivered data.

The script deliberately duplicates nothing from the audit engine: it is a
second, independent reading of the same file.  When the two agree, that
agreement means something.
"""

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict


VOID_CANDIDATE = re.compile(r"^(\d)\1{10,}$")     # e.g. 888888888888888


# ------------------------------------------------------------------ #
#  Structure discovery                                                #
# ------------------------------------------------------------------ #

def sniff_structure(path):
    """Work out the row shape from the header and the first data rows."""
    with open(path, "r", newline="") as f:
        header = f.readline().rstrip("\r\n").split(",")
        rows = []
        for _ in range(200):
            line = f.readline()
            if not line:
                break
            rows.append(line.rstrip("\r\n").split(","))

    n_fields = len(header)
    names = [h.strip() for h in header]

    # Lead columns = fields before the first repeating block.  We find the
    # block length by locating repeated base names (SerialNo1_01, SerialNo2_01…)
    base = []
    for nm in names:
        b = re.sub(r"\d+_\d+$", "", nm)          # strip the channel/block tag
        b = re.sub(r"\d+$", "", b)
        base.append(b)

    first_serial = next((i for i, b in enumerate(base)
                         if b.lower().startswith("serial")), None)
    lead = first_serial if first_serial is not None else 0

    serial_cols = [i for i, b in enumerate(base)
                   if b.lower().startswith("serial")]
    if len(serial_cols) >= 2:
        block_len = serial_cols[1] - serial_cols[0]
        channels = len(serial_cols)
    else:
        block_len = n_fields - lead
        channels = 1

    # Field offsets within a block, by header name
    off = {}
    if serial_cols:
        s0 = serial_cols[0]
        for i in range(s0, min(s0 + block_len, n_fields)):
            b = base[i].lower()
            rel = i - s0
            if b.startswith("serial"):   off.setdefault("serial", rel)
            elif b.startswith("virn"):   off.setdefault("virn", rel)
            elif b.startswith("bar"):    off.setdefault("bar", rel)
            elif "systemprize" in b or b.startswith("sys"): off.setdefault("sys", rel)
            elif "prizeprint" in b:      off.setdefault("print", rel)
            elif b.startswith("play"):
                off.setdefault("play_first", rel)
                off["play_count"] = off.get("play_count", 0) + 1
            elif "agent" in b:
                off.setdefault("agent_first", rel)
                off["agent_count"] = off.get("agent_count", 0) + 1
            elif "qa" in b:              off.setdefault("qa", rel)

    return {
        "fields_per_row": n_fields,
        "lead_columns": lead,
        "lead_names": names[:lead],
        "block_len": block_len,
        "channels": channels,
        "offsets": off,
        "header_names_block1": names[lead:lead + block_len],
        "sample_rows": rows[:3],
    }


def find_void_serial(path, struct, limit=5000):
    """A void/filler serial is a repeated-digit string appearing many times."""
    O = struct["offsets"]
    c = Counter()
    with open(path, "r", newline="") as f:
        f.readline()
        for n, line in enumerate(f):
            if n >= limit:
                break
            row = line.rstrip("\r\n").split(",")
            if len(row) != struct["fields_per_row"]:
                continue
            for ch in range(struct["channels"]):
                base = struct["lead_columns"] + ch * struct["block_len"]
                s = row[base + O.get("serial", 0)]
                if VOID_CANDIDATE.match(s):
                    c[s] += 1
    return c.most_common(1)[0][0] if c else None


# ------------------------------------------------------------------ #
#  Full pass                                                          #
# ------------------------------------------------------------------ #

def measure(path, struct, void_serial):
    O = struct["offsets"]
    lead = struct["lead_columns"]
    blk = struct["block_len"]
    nch = struct["channels"]
    play_first = O.get("play_first", 5)
    play_count = O.get("play_count", 6)
    agent_first = O.get("agent_first", 11)
    agent_count = O.get("agent_count", 9)

    per_ch = defaultdict(lambda: {
        "game": None, "lottery": None, "passive": None,
        "tickets": 0, "serial_min": None, "serial_max": None,
        "serial_ascending": True, "serial_prev": 0, "serial_gaps": 0,
        "duplicates": 0, "seen": set(),
        "sys_counts": Counter(), "print_counts": Counter(),
        "play_pos_counts": [Counter() for _ in range(play_count)],
        "play_used_positions": 0,
        "agent_letter_counts": Counter(),
        "agent_letters_per_ticket": Counter(),
        "agent_positions_used": Counter(),
        "qa_counts": Counter(),
        "virn_min": None, "virn_max": None, "virn_dupes": 0, "virn_seen": set(),
        "parity_ok": 0, "parity_bad": 0,
        "sys_by_pattern": defaultdict(Counter),
        "sys_by_serial": {},          # ticket number -> system prize code
        "consec_same_ordered": 0, "consec_same_unordered": 0,
        "prev_pair": None,
    })

    rows = 0
    void_tickets = 0
    void_rows_leading = 0
    void_rows_trailing = 0
    pages = Counter()
    bad_field_rows = 0
    seen_live = False
    trailing = 0

    with open(path, "r", newline="") as f:
        f.readline()
        for line in f:
            row = line.rstrip("\r\n").split(",")
            rows += 1
            if len(row) != struct["fields_per_row"]:
                bad_field_rows += 1
                continue
            if lead:
                pages[row[0]] += 1
            live_here = False
            for ch in range(nch):
                base = lead + ch * blk
                s = row[base + O.get("serial", 0)]
                if s == void_serial:
                    void_tickets += 1
                    continue
                live_here = True
                d = per_ch[ch + 1]
                if len(s) == 15 and s.isdigit():
                    if d["passive"] is None:
                        d["passive"] = s[0]
                        d["lottery"] = s[1:4]
                        d["game"] = s[4:8]
                    tn = int(s[8:])
                    if d["serial_min"] is None or tn < d["serial_min"]:
                        d["serial_min"] = tn
                    if d["serial_max"] is None or tn > d["serial_max"]:
                        d["serial_max"] = tn
                    if tn in d["seen"]:
                        d["duplicates"] += 1
                    else:
                        d["seen"].add(tn)
                    if tn != d["serial_prev"] + 1:
                        if d["serial_prev"] != 0:
                            d["serial_gaps"] += 1
                        d["serial_ascending"] = False if d["serial_prev"] and tn <= d["serial_prev"] else d["serial_ascending"]
                    d["serial_prev"] = tn
                d["tickets"] += 1

                v = row[base + O.get("virn", 1)]
                if len(v) == 15 and v.isdigit():
                    rnd = int(v[8:])
                    if d["virn_min"] is None or rnd < d["virn_min"]:
                        d["virn_min"] = rnd
                    if d["virn_max"] is None or rnd > d["virn_max"]:
                        d["virn_max"] = rnd
                    if v in d["virn_seen"]:
                        d["virn_dupes"] += 1
                    else:
                        d["virn_seen"].add(v)
                    if "bar" in O:
                        b = row[base + O["bar"]]
                        if b == v + str(sum(int(x) for x in v) % 10):
                            d["parity_ok"] += 1
                        else:
                            d["parity_bad"] += 1

                sysc = row[base + O.get("sys", 3)]
                d["sys_counts"][sysc] += 1
                if len(s) == 15 and s.isdigit():
                    d["sys_by_serial"][int(s[8:])] = sysc
                if "print" in O:
                    d["print_counts"][row[base + O["print"]].strip() or "(blank)"] += 1

                plays = [row[base + play_first + k].strip() for k in range(play_count)]
                for k, p in enumerate(plays):
                    if p:
                        d["play_pos_counts"][k][p] += 1
                used = sum(1 for p in plays if p)
                d["play_used_positions"] = max(d["play_used_positions"], used)
                pair = tuple(plays[:2])
                d["sys_by_pattern"][sysc][pair] += 1
                if d["prev_pair"] is not None:
                    if pair == d["prev_pair"]:
                        d["consec_same_ordered"] += 1
                    if set(pair) == set(d["prev_pair"]):
                        d["consec_same_unordered"] += 1
                d["prev_pair"] = pair

                letters = [row[base + agent_first + k].strip()
                           for k in range(agent_count)]
                filled = [x for x in letters if x]
                d["agent_letters_per_ticket"][len(filled)] += 1
                for k, x in enumerate(letters):
                    if x:
                        d["agent_letter_counts"][x] += 1
                        d["agent_positions_used"][k + 1] += 1
                if "qa" in O:
                    d["qa_counts"][row[base + O["qa"]].strip() or "(blank)"] += 1

            if live_here:
                seen_live = True
                trailing = 0
            elif seen_live:
                trailing += 1
                void_rows_trailing = trailing
            else:
                void_rows_leading += 1

    # tidy up: drop the big sets, derive summaries
    out_ch = {}
    for ch, d in sorted(per_ch.items()):
        n = d["tickets"]
        missing = (d["serial_max"] - d["serial_min"] + 1 - len(d["seen"])
                   if d["serial_min"] is not None else 0)
        out_ch[ch] = {
            "game": d["game"], "lottery": d["lottery"], "passive_flag": d["passive"],
            "tickets": n,
            "serial_range": [d["serial_min"], d["serial_max"]],
            "serial_complete": missing == 0,
            "serial_missing": missing,
            "serial_duplicates": d["duplicates"],
            "serial_strictly_ascending_in_file": d["serial_gaps"] == 0,
            "virn_random_range": [d["virn_min"], d["virn_max"]],
            "virn_duplicates": d["virn_dupes"],
            "parity_digit_sum_mod10": {"ok": d["parity_ok"], "bad": d["parity_bad"]},
            "system_prize_codes": dict(sorted(d["sys_counts"].items())),
            "prize_print_codes": dict(sorted(d["print_counts"].items())),
            "play_symbols": sorted(set().union(*[set(c) for c in d["play_pos_counts"] if c])) if any(d["play_pos_counts"]) else [],
            "play_positions_used": d["play_used_positions"],
            "play_symbol_by_position": [dict(sorted(c.items())) for c in d["play_pos_counts"] if c],
            "agent_letters": dict(sorted(d["agent_letter_counts"].items())),
            "agent_letters_per_ticket": dict(sorted(d["agent_letters_per_ticket"].items())),
            "agent_positions_used": dict(sorted(d["agent_positions_used"].items())),
            "qa_sample_code": dict(sorted(d["qa_counts"].items())),
            "consecutive_same_ordered_pair": d["consec_same_ordered"],
            "consecutive_same_unordered_pair": d["consec_same_unordered"],
            "win_pattern_by_prize_code": {
                code: {"distinct_patterns": len(pats), "tickets": sum(pats.values())}
                for code, pats in sorted(d["sys_by_pattern"].items())
            },
            "_patterns": d["sys_by_pattern"],
            "_sys_by_serial": d["sys_by_serial"],
        }
    return {
        "rows": rows,
        "bad_field_count_rows": bad_field_rows,
        "pages": len(pages),
        "rows_per_page": (Counter(pages.values()).most_common(1)[0][0]
                          if pages else None),
        "void_serial": void_serial,
        "void_tickets": void_tickets,
        "void_rows_leading": void_rows_leading,
        "void_rows_trailing": void_rows_trailing,
        "channels": out_ch,
    }


# ------------------------------------------------------------------ #
#  Win-rule inference                                                 #
# ------------------------------------------------------------------ #

def infer_win_rule(chdata, loss_code="99"):
    """Work out the winning rule from the relationship between play patterns
    and winner status.  Returns a plain-English description plus evidence."""
    pats = chdata["_patterns"]
    win_pairs = Counter()
    lose_pairs = Counter()
    for code, pp in pats.items():
        tgt = lose_pairs if code == loss_code else win_pairs
        for pair, n in pp.items():
            tgt[pair] += n

    def matched(p):
        return p[0] == p[1] and p[0] != ""

    win_matched = sum(n for p, n in win_pairs.items() if matched(p))
    win_unmatched = sum(n for p, n in win_pairs.items() if not matched(p))
    lose_matched = sum(n for p, n in lose_pairs.items() if matched(p))

    # symbols that appear on winners but never on a losing ticket
    win_syms = Counter()
    for p, n in win_pairs.items():
        for s in p:
            if s:
                win_syms[s] += n
    lose_syms = Counter()
    for p, n in lose_pairs.items():
        for s in p:
            if s:
                lose_syms[s] += n
    specials = sorted(s for s in win_syms if lose_syms.get(s, 0) == 0)

    if win_unmatched == 0:
        rule = "match_two"
        desc = "two identical play symbols win"
    elif win_matched == 0:
        rule = "special_only"
        desc = ("a single special symbol wins; a matching pair does NOT win"
                if specials else "winners never show a matching pair")
    else:
        rule = "match_two_or_special"
        desc = "two identical symbols win, or a single special symbol wins"

    # forbidden combinations: pairs of specials that never occur at all
    forbidden = None
    if len(specials) >= 1:
        both = sum(n for p, n in list(win_pairs.items()) + list(lose_pairs.items())
                   if p[0] in specials and p[1] in specials)
        if both == 0:
            forbidden = ("two special symbols never appear together "
                         "on the same ticket")
    return {
        "inferred_rule": rule,
        "description": desc,
        "special_symbols": specials,
        "forbidden": forbidden,
        "evidence": {
            "winners_with_matching_pair": win_matched,
            "winners_without_matching_pair": win_unmatched,
            "losers_with_matching_pair": lose_matched,
        },
    }


# ------------------------------------------------------------------ #
#  Book / group structure inference                                   #
# ------------------------------------------------------------------ #

def infer_book_size(chdata, candidates=(20, 25, 40, 50, 100)):
    """Guess the book size from which divisor makes the low-tier prize count
    a whole number per book."""
    sysc = chdata["system_prize_codes"]
    total = sum(sysc.values())
    out = []
    for b in candidates:
        if total % b:
            continue
        books = total // b
        fits = {code: n / books for code, n in sysc.items()
                if n and n % books == 0 and n // books >= 1}
        if fits:
            out.append({"book_size": b, "books": books,
                        "codes_with_whole_number_per_book":
                            {c: int(n) for c, n in
                             ((c, sysc[c] // books) for c in fits)}})
    return out


# ------------------------------------------------------------------ #
#  Comparison against a settings file                                 #
# ------------------------------------------------------------------ #

def _book_counts(chdata, book_size, amount_by_code):
    """Return (list of per-book Counters keyed by prize AMOUNT, n_books).
    Built from the measured serial -> prize code map, so it reflects the
    delivered data and not the settings."""
    m = chdata.get("_sys_by_serial") or {}
    if not m:
        return [], 0
    top = max(m)
    n_books = -(-top // book_size)
    books = [Counter() for _ in range(n_books)]
    for tn, code in m.items():
        amt = amount_by_code.get(code)
        if amt is not None:
            books[(tn - 1) // book_size][amt] += 1
    return books, n_books


def compare(meas, cfg):
    diffs = []
    L = cfg["layout"]
    struct_book = cfg["structure"]["book_size"]
    gleps_amount = cfg["fixed_rules"]["gleps_amount"]
    if meas["channels"] and len(meas["channels"]) != L["channels"]:
        diffs.append(f"channels: measured {len(meas['channels'])}, "
                     f"settings say {L['channels']}")
    if meas["void_serial"] != L["void_serial"]:
        diffs.append(f"void serial: measured {meas['void_serial']}, "
                     f"settings say {L['void_serial']}")
    by_game = {g["key"]: g for g in cfg["games"]}
    for ch, d in meas["channels"].items():
        key = d["game"]
        g = by_game.get(key)
        if g is None:
            diffs.append(f"channel {ch}: game {key} is not in the settings")
            continue
        if g["channel"] != ch:
            diffs.append(f"game {key}: measured on channel {ch}, "
                         f"settings say channel {g['channel']}")
        if g["lottery"] != d["lottery"]:
            diffs.append(f"game {key}: measured lottery {d['lottery']}, "
                         f"settings say {g['lottery']}")
        want = {p["sys"]: p["count"] for p in g["prizes"]}
        want[g["loss"]["code"]] = g["loss"]["count"]
        got = d["system_prize_codes"]
        for code in sorted(set(want) | set(got)):
            if want.get(code, 0) != got.get(code, 0):
                diffs.append(f"game {key} code {code}: measured "
                             f"{got.get(code,0):,}, settings say "
                             f"{want.get(code,0):,}")
        msym = set(d["play_symbols"])
        csym = set(g["play_symbols"])
        if msym - csym:
            diffs.append(f"game {key}: symbols in data but not settings: "
                         f"{sorted(msym-csym)}")
        if csym - msym:
            diffs.append(f"game {key}: symbols in settings but not data: "
                         f"{sorted(csym-msym)}")
        inf = infer_win_rule(d, g["loss"]["code"])
        if inf["inferred_rule"] != g["win_rule"]:
            diffs.append(f"game {key}: data suggests win rule "
                         f"'{inf['inferred_rule']}', settings say "
                         f"'{g['win_rule']}'")
        sp_meas = set(inf["special_symbols"])
        sp_cfg = set(g.get("special_symbols") or [])
        if g["win_rule"] != "match_two" and sp_meas != sp_cfg:
            diffs.append(f"game {key}: special symbols measured {sorted(sp_meas)}, "
                         f"settings say {sorted(sp_cfg)}")
        if d["parity_digit_sum_mod10"]["bad"]:
            diffs.append(f"game {key}: {d['parity_digit_sum_mod10']['bad']:,} "
                         "barcode parity mismatches")

        # ---- book size plausible against the data --------------------
        cands = {c["book_size"] for c in infer_book_size(d)}
        if cands and struct_book not in cands:
            diffs.append(f"game {key}: configured book size {struct_book} does "
                         f"not divide the data evenly; sizes that do: "
                         f"{sorted(cands)}")

        amount_by_code = {p["sys"]: p["amount"] for p in g["prizes"]}
        books, n_books = _book_counts(d, struct_book, amount_by_code)
        if not books:
            continue

        # ---- GLEPS promise holds in the data -------------------------
        want_gl = g.get("gleps_per_book")
        if want_gl is not None:
            seen = Counter(b.get(gleps_amount, 0) for b in books)
            if set(seen) != {want_gl}:
                worst = ", ".join(f"{k} in {v:,} book(s)"
                                  for k, v in sorted(seen.items())[:4])
                diffs.append(f"game {key}: GLEPS configured as {want_gl} x "
                             f"Rs.{gleps_amount:,} per book, but the data shows "
                             f"{worst}")

        # ---- packing schedule against the data -----------------------
        sched = g.get("packing") or []
        sched_books = sum(s["slots"] * s["books"] for s in sched)
        if sched and sched_books != n_books:
            diffs.append(f"game {key}: packing schedule covers {sched_books:,} "
                         f"books but the data holds {n_books:,}")
        cursor = 0
        slot_no = 0
        failing = 0
        first_fail = None
        for s in sched:
            for _ in range(s["slots"]):
                slot_no += 1
                seg = books[cursor:cursor + s["books"]]
                cursor += s["books"]
                if not seg:
                    continue
                tot = Counter()
                for b in seg:
                    tot.update(b)
                for a in s["allocation"]:
                    n = tot.get(a["amount"], 0)
                    bad = (a["mode"] == "exact" and n != a["n"]) or \
                          (a["mode"] == "min" and n < a["n"])
                    if bad:
                        failing += 1
                        if first_fail is None:
                            first_fail = (slot_no, a["amount"], n, a["mode"], a["n"])
        if failing:
            sn, amt, n, mode, need = first_fail
            diffs.append(f"game {key}: {failing} packing-slot allocation(s) not "
                         f"met in the data (first: slot {sn}, Rs.{amt:,} "
                         f"found {n}, {mode} {need})")
    return diffs


# ------------------------------------------------------------------ #
#  Reporting                                                          #
# ------------------------------------------------------------------ #

def human_report(path, struct, meas):
    L = []
    W = L.append
    W("=" * 70)
    W("LAYOUT FILE MEASUREMENT")
    W("=" * 70)
    W(f"File        : {os.path.basename(path)}")
    W(f"Size        : {os.path.getsize(path)/1e6:.1f} MB")
    W("")
    W("--- ROW STRUCTURE ---")
    W(f"  fields per row     : {struct['fields_per_row']}")
    W(f"  lead columns       : {struct['lead_columns']} {struct['lead_names']}")
    W(f"  channels (blocks)  : {struct['channels']}")
    W(f"  fields per block   : {struct['block_len']}")
    W(f"  block offsets      : {struct['offsets']}")
    W(f"  data rows          : {meas['rows']:,}")
    W(f"  rows with wrong field count : {meas['bad_field_count_rows']:,}")
    if meas["pages"]:
        W(f"  pages              : {meas['pages']:,} "
          f"({meas['rows_per_page']} rows per page -> "
          f"{meas['rows_per_page']*struct['channels']} tickets per page)")
    W("")
    W("--- VOID PADDING ---")
    W(f"  void serial        : {meas['void_serial']}")
    W(f"  void tickets       : {meas['void_tickets']:,}")
    W(f"  leading void rows  : {meas['void_rows_leading']:,}")
    W(f"  trailing void rows : {meas['void_rows_trailing']:,}")
    W("")
    for ch, d in meas["channels"].items():
        W("=" * 70)
        W(f"CHANNEL {ch}  ->  lottery {d['lottery']}, game {d['game']}")
        W("=" * 70)
        W(f"  live tickets       : {d['tickets']:,}")
        W(f"  serial range       : {d['serial_range'][0]:,} .. {d['serial_range'][1]:,}")
        complete = ("yes" if d["serial_complete"]
                    else f"NO ({d['serial_missing']:,} missing)")
        W(f"  complete           : {complete}")
        W(f"  duplicates         : {d['serial_duplicates']:,}")
        W(f"  ascending in file  : {'yes' if d['serial_strictly_ascending_in_file'] else 'no (interleaved or out of order)'}")
        W(f"  VIRN random range  : {d['virn_random_range'][0]:,} .. {d['virn_random_range'][1]:,}")
        W(f"  VIRN duplicates    : {d['virn_duplicates']:,}")
        p = d["parity_digit_sum_mod10"]
        W(f"  barcode parity     : {p['ok']:,} correct, {p['bad']:,} wrong "
          f"(rule: digit sum of VIRN mod 10)")
        W("")
        W("  system prize codes:")
        tot = sum(d["system_prize_codes"].values())
        for code, n in d["system_prize_codes"].items():
            W(f"    {code}: {n:>9,}  ({n/tot*100:5.2f}%)")
        if d["prize_print_codes"]:
            W("  prize print codes:")
            for code, n in d["prize_print_codes"].items():
                W(f"    {code:>8}: {n:>9,}")
        W("")
        W(f"  play symbols ({len(d['play_symbols'])}): {', '.join(d['play_symbols'])}")
        W(f"  play positions carrying a symbol : {d['play_positions_used']} "
          f"of {len(d['play_symbol_by_position'])}")
        W("")
        W("  agent validation:")
        W(f"    letters used     : {', '.join(sorted(d['agent_letters']))}")
        W(f"    letters/ticket   : {d['agent_letters_per_ticket']}")
        W(f"    positions used   : {sorted(d['agent_positions_used'])}")
        W("  agent letter totals:")
        for x, n in sorted(d["agent_letters"].items()):
            W(f"    {x}: {n:>9,}")
        if d["qa_sample_code"]:
            W(f"  QA sample code     : {d['qa_sample_code']}")
        W("")
        inf = infer_win_rule(d)
        W("  WIN RULE (inferred from the data):")
        W(f"    {inf['inferred_rule']}  -  {inf['description']}")
        if inf["special_symbols"]:
            W(f"    special symbols  : {', '.join(inf['special_symbols'])} "
              "(appear on winners, never on a loser)")
        if inf["forbidden"]:
            W(f"    note             : {inf['forbidden']}")
        e = inf["evidence"]
        W(f"    winners with a matching pair    : {e['winners_with_matching_pair']:,}")
        W(f"    winners without a matching pair : {e['winners_without_matching_pair']:,}")
        W(f"    losers with a matching pair     : {e['losers_with_matching_pair']:,}")
        W("")
        W("  BOOK SIZE (candidates that divide evenly):")
        for cand in infer_book_size(d):
            W(f"    {cand['book_size']:>3} tickets -> {cand['books']:,} books; "
              f"whole prizes per book: {cand['codes_with_whole_number_per_book']}")
        W("")
        W("  consecutive-ticket observations (serial order):")
        W(f"    same ordered pair   : {d['consecutive_same_ordered_pair']:,}")
        W(f"    same unordered pair : {d['consecutive_same_unordered_pair']:,}")
        W("")
    return "\n".join(L)


def to_facts(struct, meas):
    """The JSON-safe measured facts, exactly as written to measured_facts.json
    (the raw pattern maps use tuple keys and are left out)."""
    clean = {k: v for k, v in meas.items() if k != "channels"}
    clean["channels"] = {}
    for ch_id, ch in meas["channels"].items():
        c = {k: v for k, v in ch.items() if not k.startswith("_")}
        c["inferred_win_rule"] = infer_win_rule(ch)
        c["book_size_candidates"] = infer_book_size(ch)
        clean["channels"][str(ch_id)] = c
    clean["structure"] = {k: v for k, v in struct.items() if k != "sample_rows"}
    return json.loads(json.dumps(clean, default=str))


def main():
    ap = argparse.ArgumentParser(description="Measure an NLB layout file")
    ap.add_argument("layout")
    ap.add_argument("--out", default=None,
                    help="write measured facts as JSON to this path")
    ap.add_argument("--config", default=None,
                    help="compare the measurements against a settings file")
    args = ap.parse_args()

    print(f"Sniffing structure of {args.layout} ...")
    struct = sniff_structure(args.layout)
    print(f"  {struct['fields_per_row']} fields = {struct['lead_columns']} lead "
          f"+ {struct['channels']} x {struct['block_len']}")
    void = find_void_serial(args.layout, struct)
    print(f"  void serial: {void}")
    print("Measuring (one full pass) ...")
    meas = measure(args.layout, struct, void)

    report = human_report(args.layout, struct, meas)
    print()
    print(report)

    if args.out:
        with open(args.out, "w") as f:
            json.dump(to_facts(struct, meas), f, indent=1, default=str)
        print(f"\nMeasured facts written to {args.out}")

    if args.config:
        cfg = json.load(open(args.config))
        diffs = compare(meas, cfg)
        print("\n" + "=" * 70)
        print("COMPARISON AGAINST SETTINGS")
        print("=" * 70)
        if diffs:
            print(f"{len(diffs)} disagreement(s):")
            for d in diffs:
                print(f"  X {d}")
            sys.exit(1)
        else:
            print("No disagreements: the settings match the delivered data.")


if __name__ == "__main__":
    main()
