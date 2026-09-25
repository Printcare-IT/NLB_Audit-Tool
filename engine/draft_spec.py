#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DRAFT THE JOB SPECIFICATION MARKDOWN
====================================

Reads the NLB game specifications, the data generation specification and the
layout measurements, cross-checks them against one another, and writes
spec.md for review.

    python draft_spec.py --job jobs/<job folder> [--layout <layout file>]

Expected job folder:
    jobs/<job>/inputs/          game specs and data spec (.pdf / .docx / .doc)
    jobs/<job>/measured_facts.json   from probe_layout.py (created for you if
                                     --layout is given and the file is missing)

Output: jobs/<job>/spec.md, or spec.draft.md if spec.md already exists - a
reviewed specification is never overwritten.

Every figure in the draft comes from a specification document or from the
measurements.  Where three sources can speak to the same fact (game spec,
data spec, measured data) they are compared, and each disagreement becomes a
review item.  Nothing is guessed silently: if a value cannot be read, the
draft says so.
"""

import argparse
import datetime
import glob
import json
import os
import re
import subprocess
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from doc_text import to_text, flatten                          # noqa: E402
from spec_parse import (classify, parse_game_spec, parse_data_spec,  # noqa: E402
                        read_win_rule, forbidden_from_text)
from spec_md import render                                     # noqa: E402
from validate_config import validate                           # noqa: E402


class Draft:
    def __init__(self):
        self.review = []
        self.ev = defaultdict(list)

    def item(self, severity, text, game=None):
        self.review.append({"id": f"R{len(self.review)+1}", "game": game,
                            "severity": severity, "text": text})

    def note(self, key, text):
        self.ev[key].append(text)


def _amount_in(name):
    m = re.search(r"(\d[\d,]*)", name or "")
    return int(m.group(1).replace(",", "")) if m else None


def _agree(values):
    vals = [v for v in values if v is not None]
    return (vals[0], len(set(map(str, vals))) == 1) if vals else (None, True)


# ------------------------------------------------------------------ #

def build(job_id, docs, facts):
    D = Draft()
    game_specs, data_specs, unknown = {}, [], []
    for path, flat in docs:
        kind = classify(flat)
        name = os.path.basename(path)
        if kind == "game_spec":
            g = parse_game_spec(flat, name)
            if g.get("key") in game_specs:
                D.item("blocking", f"two game specifications for game {g['key']}: "
                       f"{game_specs[g['key']]['source']} and {name}.")
            game_specs[g.get("key") or name] = g
        elif kind == "data_spec":
            data_specs.append(parse_data_spec(flat, name))
        else:
            unknown.append(name)
    for n in unknown:
        D.item("check", f"`{n}` is neither a game specification nor a data "
               "specification and was ignored.")
    if not game_specs:
        raise SystemExit("No NLB game specifications found in the inputs.")
    if not data_specs:
        D.item("blocking", "no data generation specification was supplied: symbol "
               "names, print codes, forbidden patterns and the channel map could "
               "not be cross-checked.")
    elif len(data_specs) > 1:
        D.item("check", "more than one data specification supplied; the first "
               f"({data_specs[0]['source']}) was used.")
    ds = data_specs[0] if data_specs else {"games": {}}

    # ---- measured facts ----------------------------------------------
    M = facts or {}
    mch = {}
    for ch, d in (M.get("channels") or {}).items():
        mch[d["game"]] = dict(d, channel=int(ch))
    if not facts:
        D.item("blocking", "no measured_facts.json: nothing in this draft has been "
               "checked against the layout file. Run probe_layout.py first.")

    for key in sorted(set(game_specs) - set(mch)):
        if facts:
            D.item("blocking", f"game {key} has a specification but does not appear "
                   "in the layout file.", key)
    for key in sorted(set(mch) - set(game_specs)):
        D.item("blocking", f"game {key} appears in the layout file (channel "
               f"{mch[key]['channel']}) but no game specification was supplied.", key)

    # ---- data-spec symbol tables, resolving mislabelled headings ------
    sym_tables = {}
    for key, entry in ds.get("symbol_tables", []):
        sym_tables.setdefault(key, []).append(entry)
    for key in list(sym_tables):
        if key in game_specs:
            continue
        for entry in sym_tables.pop(key):
            codes = {c for c, _ in entry["symbols"]}
            match = [k for k, d in mch.items() if set(d.get("play_symbols", [])) == codes]
            if len(match) == 1 and match[0] not in sym_tables:
                sym_tables[match[0]] = [entry]
                D.item("check", f"the data specification's play symbol table headed "
                       f"'{entry['heading']}' names a game not in this job; its codes "
                       f"({', '.join(sorted(codes))}) match the measured symbols of "
                       f"game {match[0]}, so it was used for {match[0]}. Correct the "
                       "heading in the data specification.", match[0])
            else:
                D.item("blocking", f"the data specification's play symbol table "
                       f"headed '{entry['heading']}' matches no game in this job.")
    prize_tables = {k: e for k, e in ds.get("prize_tables", [])}

    # ---- job-level values, compared across games ----------------------
    specs = [game_specs[k] for k in sorted(game_specs)]

    def job_value(field, label):
        vals = {g.get("key"): g.get(field) for g in specs}
        v, ok = _agree(vals.values())
        if not ok:
            D.item("blocking", f"{label} differs between games: " +
                   ", ".join(f"{k}={vv}" for k, vv in vals.items()) +
                   ". This tool expects one value per job.")
        if v is None:
            D.item("blocking", f"could not read the {label} from any game specification.")
        return v

    price = job_value("ticket_price", "ticket price")
    tickets = job_value("tickets", "tickets per game")
    book = job_value("book_size", "book size")
    gleps_amt = job_value("gleps_amount", "GLEPS prize amount")

    high = job_value("agent_high", "high-tier agent letter set")
    if ds.get("agent_high") and high and ds["agent_high"] != high:
        D.item("check", f"high-tier agent letters: game specs say {', '.join(high)}, "
               f"data spec says {', '.join(ds['agent_high'])}.")
    low = {}
    for g in specs:
        for a, l in (g.get("agent_low") or {}).items():
            if a in low and low[a] != l:
                D.item("blocking", f"low-tier letter for Rs.{a} differs between games.")
            low[a] = l
    for a, l in (ds.get("agent_low") or {}).items():
        if a in low and low[a] != l:
            D.item("check", f"low-tier letter for Rs.{a}: game specs say {low[a]}, "
                   f"data spec says {l}.")
        low.setdefault(a, l)

    fixed = {}
    for field, label, default in (("max_same_value_run", "maximum same-value run", 3),
                                  ("winner_every_n_tickets", "winner-every-N block", 5)):
        vals = {g.get("key"): (g.get("fixed") or {}).get(field) for g in specs}
        v, ok = _agree(vals.values())
        if not ok:
            D.item("blocking", f"{label} differs between games: {vals}.")
        if v is None:
            D.item("blocking", f"could not read the {label}; defaulted to {default}.")
            v = default
        fixed[field] = v
    for g in specs:
        for miss in g.get("red_missing") or []:
            D.item("blocking", f"standard restriction not found in the "
                   f"specification: '{miss}'. The engine will still check it.", g.get("key"))
    D.note("fixed", "All six standard restrictions were found word for word in "
           "every game specification." if not any(g.get("red_missing") for g in specs)
           else "Some standard restrictions were not found - see review items.")

    # ---- layout from the measurements ---------------------------------
    st = M.get("structure", {})
    off = st.get("offsets", {})
    used = max((d.get("play_positions_used", 0) for d in mch.values()), default=2)
    per_ticket = [int(k) for d in mch.values()
                  for k, v in (d.get("agent_letters_per_ticket") or {}).items() if v]
    layout = {
        "block_len": st.get("block_len", 21),
        "channels": st.get("channels", len(game_specs)),
        "lead_columns": st.get("lead_columns", 1),
        "offsets": {
            "serial": off.get("serial", 0), "virn": off.get("virn", 1),
            "bar": off.get("bar", 2), "sys": off.get("sys", 3),
            "print": off.get("print", 4),
            "play_first": off.get("play_first", 5),
            "play_count": off.get("play_count", 6), "play_used": used,
            "agent_first": off.get("agent_first", 11),
            "agent_count": off.get("agent_count", 9), "qa": off.get("qa", 20)},
        "void_serial": M.get("void_serial") or "888888888888888",
        "passive_flag": next((d.get("passive_flag") for d in mch.values()), "1"),
        "virn_random_range": ds.get("virn_range") or [2000000, 6999999],
        "parity_rule": "digit_sum_mod10",
    }
    if not ds.get("virn_range"):
        D.item("check", "VIRN random range not found in the data specification; "
               "using 2,000,000 - 6,999,999.")

    if facts:
        rpp = M.get("rows_per_page")
        D.note("layout", f"Measured: {M.get('rows', 0):,} data rows, "
               f"{st.get('fields_per_row')} fields per row "
               f"({layout['lead_columns']} lead + {layout['channels']} x "
               f"{layout['block_len']}), {M.get('pages', 0):,} pages of "
               f"{rpp} rows = {(rpp or 0)*layout['channels']} tickets per page.")
        D.note("layout", f"Measured: {M.get('void_tickets', 0):,} void tickets - "
               f"{M.get('void_rows_leading', 0):,} leading rows and "
               f"{M.get('void_rows_trailing', 0):,} trailing rows.")
        bad_par = sum(d["parity_digit_sum_mod10"]["bad"] for d in mch.values())
        ok_par = sum(d["parity_digit_sum_mod10"]["ok"] for d in mch.values())
        D.note("layout", f"Measured: barcode parity (digit sum of VIRN mod 10) "
               f"correct on {ok_par:,} tickets, wrong on {bad_par:,}.")
        if bad_par:
            D.item("blocking", f"{bad_par:,} barcodes fail the digit-sum-mod-10 "
                   "parity rule in the layout file.")
        if ds.get("channels_stated") and ds["channels_stated"] != layout["channels"]:
            D.item("check", f"data spec says channel data occurs "
                   f"{ds['channels_stated']} times; the file has {layout['channels']}.")
        if ds.get("channels_prose") and ds["channels_prose"] != layout["channels"]:
            D.item("check", f"data spec prose says pages of {ds['channels_prose']} "
                   f"channels; the file has {layout['channels']}.")
        if ds.get("tickets_per_page") and rpp and \
                ds["tickets_per_page"] != rpp * layout["channels"]:
            D.item("check", f"data spec says {ds['tickets_per_page']} tickets per "
                   f"page; the file has {rpp * layout['channels']}.")
        if ds.get("page_range") and M.get("pages") and ds["page_range"][1] != M["pages"]:
            D.item("check", f"data spec gives the page range as "
                   f"{ds['page_range'][0]:06d} - {ds['page_range'][1]:06d}; the file "
                   f"has {M['pages']:,} pages "
                   f"({M['pages'] - ds['page_range'][1]:+,} pages).")
        if ds.get("leading_void_pages") and rpp and \
                ds["leading_void_pages"] * rpp != M.get("void_rows_leading"):
            D.item("check", f"data spec says {ds['leading_void_pages']} leading void "
                   f"pages ({ds['leading_void_pages']*rpp} rows); the file has "
                   f"{M.get('void_rows_leading'):,} leading void rows.")
        if M.get("void_rows_trailing"):
            D.note("layout", "Trailing void padding is normal: it completes the "
                   "final page and is not an exception.")
        if book:
            for key, d in mch.items():
                cands = {c["book_size"] for c in d.get("book_size_candidates", [])}
                if cands and book not in cands:
                    D.item("blocking", f"book size {book} does not divide game "
                           f"{key}'s data evenly (sizes that do: {sorted(cands)}).", key)

    # ---- games ----------------------------------------------------------
    games = []
    order = sorted(game_specs, key=lambda k: mch.get(k, {}).get("channel", 99))
    for n, key in enumerate(order, 1):
        s = game_specs[key]
        m = mch.get(key, {})
        for p in s["problems"]:
            D.item("blocking", f"reading {s['source']}: {p}.", key)

        channel = m.get("channel") or (ds.get("channel_map") or {}).get(key) or n
        dch = (ds.get("channel_map") or {}).get(key)
        if dch and m and dch != m["channel"]:
            D.item("check", f"data spec puts game {key} on channel {dch}; the file "
                   f"has it on channel {m['channel']}. The measured channel is used.", key)

        lottery = s.get("lottery")
        for other, label in ((s.get("serial_lottery"), "serial number table"),
                             (m.get("lottery"), "layout file")):
            if other and lottery and other != lottery:
                D.item("blocking", f"lottery code is {lottery} in the title but "
                       f"{other} in the {label}.", key)
        sym_entry = (sym_tables.get(key) or [None])[0]
        if sym_entry and sym_entry.get("heading_lottery") and lottery and \
                sym_entry["heading_lottery"] != lottery and sym_entry["heading"].endswith(key):
            D.item("check", f"data spec heading '{sym_entry['heading']}' gives lottery "
                   f"{sym_entry['heading_lottery']}; the game spec says {lottery}.", key)

        # symbols
        if sym_entry:
            symbols = {c: nm for c, nm in sym_entry["symbols"]}
        else:
            symbols = {c: "?" for c in m.get("play_symbols", [])}
            D.item("blocking", "no play symbol table in the data specification; codes "
                   "taken from the layout file - fill in the symbol names.", key)
        if m:
            meas = set(m.get("play_symbols", []))
            if meas and set(symbols) != meas:
                D.item("blocking", f"play symbols: data spec has "
                       f"{', '.join(sorted(symbols))}; the file has "
                       f"{', '.join(sorted(meas))}.", key)
        if s.get("play_symbol_names"):
            names = {x.lower() for x in s["play_symbol_names"]}
            if names != {v.lower() for v in symbols.values()}:
                D.item("check", "symbol names in the game specification "
                       f"({', '.join(s['play_symbol_names'])}) do not match the data "
                       f"specification ({', '.join(symbols.values())}).", key)

        # win rule
        rule, names, rnote = read_win_rule(s.get("mechanism"))
        by_name = {v.lower(): c for c, v in symbols.items()}
        specials = []
        for nm in names:
            c = by_name.get(nm.lower())
            if c:
                specials.append(c)
            else:
                D.item("blocking", f"special symbol '{nm}' named in the mechanism is "
                       "not in the play symbol table.", key)
        how = ds.get("games", {}).get(key, {}).get("how_to_play")
        if how:
            r2, n2, _ = read_win_rule(how)
            if r2 != rule or {x.lower() for x in n2} != {x.lower() for x in names}:
                D.item("check", f"game spec mechanism reads as '{rule}'"
                       f"{' '+str(names) if names else ''} but the data spec's "
                       f"how-to-play reads as '{r2}'{' '+str(n2) if n2 else ''}.", key)
        inf = m.get("inferred_win_rule") or {}
        if inf:
            ev = inf.get("evidence", {})
            if inf.get("inferred_rule") != rule:
                D.item("blocking", f"the specification describes '{rule}' but the "
                       f"layout file behaves as '{inf.get('inferred_rule')}' "
                       f"({ev.get('winners_with_matching_pair', 0):,} winners with a "
                       f"matching pair, {ev.get('winners_without_matching_pair', 0):,} "
                       "without).", key)
            elif rule != "match_two" and set(inf.get("special_symbols", [])) != set(specials):
                D.item("blocking", f"special symbols: specification gives "
                       f"{specials}, the layout file behaves as "
                       f"{inf.get('special_symbols')}.", key)
        D.note(("mech", key), f"Specification: \"{s.get('mechanism')}\"")
        if how and how != s.get("mechanism"):
            D.note(("mech", key), f"Data specification: \"{how}\"")
        if rnote:
            D.note(("mech", key), f"Reading: {rnote}.")
        if inf:
            ev = inf.get("evidence", {})
            D.note(("mech", key), f"Measured: behaves as `{inf.get('inferred_rule')}`"
                   f"{' with special ' + ', '.join(inf['special_symbols']) if inf.get('special_symbols') else ''}"
                   f" - {ev.get('winners_with_matching_pair', 0):,} winners with a "
                   f"matching pair, {ev.get('winners_without_matching_pair', 0):,} "
                   f"without, {ev.get('losers_with_matching_pair', 0):,} losers with one.")

        na = ds.get("games", {}).get(key, {}).get("not_allowed")
        forbidden = forbidden_from_text(na)
        if forbidden == "unrecognised":
            D.item("blocking", f"could not interpret the NOT ALLOWED pattern "
                   f"'{na}'.", key)
            forbidden = None
        if rule == "match_two":
            forbidden = None
        if na:
            D.note(("mech", key), f"Not allowed (data spec): \"{na}\".")
        if forbidden and inf and specials and not inf.get("forbidden"):
            D.item("check", "the specification forbids two special symbols together, "
                   "but the measurements did not confirm their absence.", key)

        # prizes
        ptab = {r["sys"]: r for r in (prize_tables.get(key) or {}).get("prize_codes", [])}
        prizes = []
        amount_symbol = {}
        for c, nm in symbols.items():
            a = _amount_in(nm)
            if a:
                amount_symbol[a] = c
        for r in s.get("prizes", []):
            p = {"sys": r["sys"], "amount": r["amount"], "print": r["print"],
                 "tier": r["tier"], "count": r["count"]}
            if r.get("label"):
                p["label"] = r["label"]
            if r["amount"] in amount_symbol and len(amount_symbol) == len(symbols):
                p["symbol"] = amount_symbol[r["amount"]]
            t = ptab.get(r["sys"])
            if ptab and not t:
                D.item("check", f"prize code {r['sys']} (Rs.{r['amount']:,}) is not in "
                       "the data specification's print-code table.", key)
            elif t and (t["amount"] != r["amount"] or t["print"] != r["print"]):
                D.item("blocking", f"prize code {r['sys']}: game spec says Rs."
                       f"{r['amount']:,} print '{r['print'] or '-'}', data spec says "
                       f"Rs.{t['amount']:,} print '{t['print'] or '-'}'.", key)
            prizes.append(p)
        has_spot = any(p["print"] for p in prizes)
        if m:
            codes = set(m.get("prize_print_codes", {})) - {"(blank)"}
            if has_spot != bool(codes):
                D.item("blocking", f"prize spot: specification implies "
                       f"{'a prize spot' if has_spot else 'no prize spot'}, the file "
                       f"carries {'print codes' if codes else 'none'}.", key)
        loss = {"code": s.get("loss_code", "99"), "count": s.get("loss_count", 0)}
        if s.get("loss_code_written") and s["loss_code_written"] != loss["code"]:
            D.note(("prize", key), f"The specification writes the non-win code as "
                   f"{s['loss_code_written']}; the two-digit field holds "
                   f"{loss['code']}.")
        if m:
            got = m.get("system_prize_codes", {})
            want = {p["sys"]: p["count"] for p in prizes}
            want[loss["code"]] = loss["count"]
            diffs = [c for c in sorted(set(want) | set(got)) if want.get(c, 0) != got.get(c, 0)]
            for c in diffs:
                D.item("blocking", f"prize code {c}: specification says "
                       f"{want.get(c, 0):,}, the layout file holds {got.get(c, 0):,}.", key)
            if not diffs:
                D.note(("prize", key), f"Measured: every prize count and the loser "
                       f"count match the file exactly ({m.get('tickets', 0):,} tickets, "
                       f"serials {'complete' if m.get('serial_complete') else 'INCOMPLETE'}, "
                       f"{m.get('serial_duplicates', 0)} duplicates).")
        if s.get("doc_version"):
            D.note(("prize", key), f"Source: {s['source']}, version {s['doc_version']} "
                   f"{s.get('doc_status', '')}, {s.get('doc_date', '')}.")

        for u in s.get("unrecognised") or []:
            D.item("blocking", f"restriction not understood - add it to the tables "
                   f"by hand or confirm it needs no check: \"{u}\".", key)
        rules = []
        for gr in s.get("group_rules") or []:
            rules.append({k: v for k, v in gr.items() if k != "wording"})
            D.note(("group", key), f"\"{gr['wording']}.\" -> `{gr['mode']}`")
        for i, pk in enumerate(s.get("packing") or [], 1):
            D.note(("pack", key), f"Slot group {i}: {pk['slots']} x {pk['books']} "
                   "books, from the specification's restrictions.")

        games.append({
            "key": key, "name": s.get("name", key), "lottery": lottery or "?",
            "channel": channel, "win_rule": rule or "match_two",
            "special_symbols": specials, "forbidden": forbidden,
            "play_symbols": symbols, "has_prize_spot": has_spot,
            "prizes": prizes, "loss": loss,
            "gleps_per_book": s.get("gleps_per_book"),
            "packing": s.get("packing") or [], "group_rules": rules,
            "expected": {"revenue": s.get("revenue") or 0, "pool": s.get("pool") or 0,
                         "payout_pct": s.get("payout_pct") or 0.0,
                         "win_ratio": s.get("win_ratio") or 0.0},
        })

    sources = [f"{g['source']} - game {g.get('key')}, version "
               f"{g.get('doc_version', '?')} {g.get('doc_status', '')}, "
               f"{g.get('doc_date', '?')}".replace("  ", " ")
               for g in (game_specs[k] for k in order)]
    for d in data_specs:
        sources.append(f"{d['source']} - data specification, "
                       f"{d.get('doc_version', '?')}, {d.get('doc_date', '?')}")
    if facts:
        sources.append("measured_facts.json - produced by probe_layout.py")

    cfg = {
        "schema_version": "1.0",
        "job": {"id": job_id, "client": "NLB", "title": "NLB Scratch Lottery",
                "ticket_price": price or 0, "sources": sources},
        "layout": layout,
        "structure": {"tickets_per_game": tickets or 0, "book_size": book or 0},
        "agent": {"high_letters": high or [],
                  "low_letters": {str(a): l for a, l in sorted(low.items())},
                  "positions": layout["offsets"]["agent_count"],
                  "letters_used": max(per_ticket) if per_ticket else 3},
        "fixed_rules": dict(fixed, gleps_amount=gleps_amt or 0),
        "games": games,
    }
    D.note("agent", f"High-tier letters from the game specifications; low-tier "
           f"letters: {', '.join(f'Rs.{a}={l}' for a, l in sorted(low.items()))}.")

    # ---- finally, validate the drafted settings -------------------------
    try:
        rep = validate(cfg)
        for game, msg in rep.errors:
            D.item("blocking", f"validation: {msg}", game if game != "job" else None)
        for game, msg in rep.warnings:
            D.item("check", f"validation: {msg}", game if game != "job" else None)
        for game, msg in rep.notes:
            D.note(("pack", game) if game != "job" else "layout", msg)
    except Exception as e:                      # a malformed draft must still render
        D.item("blocking", f"validation could not run: {e}")
    return cfg, D


def main():
    ap = argparse.ArgumentParser(description="Draft the NLB job specification markdown")
    ap.add_argument("--job", required=True, help="job folder, e.g. jobs/2026-07_NLB_0345-0347")
    ap.add_argument("--layout", help="layout file (used to create measured_facts.json if missing)")
    ap.add_argument("--inputs", help="folder of specification documents "
                                     "(default: <job>/inputs)")
    args = ap.parse_args()

    job_dir = args.job.rstrip("/\\")
    job_id = os.path.basename(job_dir)
    in_dir = args.inputs or os.path.join(job_dir, "inputs")
    paths = sorted(p for ext in ("pdf", "docx", "doc")
                   for p in glob.glob(os.path.join(in_dir, f"*.{ext}")))
    paths = [p for p in paths if not os.path.basename(p).startswith("~$")]
    if not paths:
        raise SystemExit(f"No .pdf/.docx/.doc files found in {in_dir}")

    facts_path = os.path.join(job_dir, "measured_facts.json")
    if not os.path.exists(facts_path) and args.layout:
        print("measured_facts.json not found - running probe_layout.py ...")
        subprocess.run([sys.executable, os.path.join(HERE, "probe_layout.py"),
                        args.layout, "--out", facts_path], check=True,
                       stdout=subprocess.DEVNULL)
    facts = json.load(open(facts_path)) if os.path.exists(facts_path) else None

    docs = []
    for p in paths:
        print(f"reading {os.path.basename(p)}")
        docs.append((p, flatten(to_text(p))))

    cfg, D = build(job_id, docs, facts)
    md = render(cfg, D.review, D.ev,
                {"generated": f"{datetime.datetime.now():%Y-%m-%d %H:%M}"})
    out = os.path.join(job_dir, "spec.md")
    if os.path.exists(out):
        out = os.path.join(job_dir, "spec.draft.md")
        print("spec.md already exists - writing spec.draft.md instead "
              "(a reviewed specification is never overwritten)")
    with open(out, "w", encoding="utf-8") as f:
        f.write(md)

    blocking = sum(1 for r in D.review if r["severity"] == "blocking")
    print(f"\nDraft written: {out}")
    print(f"  {len(cfg['games'])} game(s), {len(D.review)} review item(s) "
          f"({blocking} blocking)")
    for r in D.review:
        print(f"  {'X' if r['severity']=='blocking' else '?'} {r['id']} "
              f"{('['+r['game']+'] ') if r.get('game') else ''}{r['text']}")


if __name__ == "__main__":
    main()
