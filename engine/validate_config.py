#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NLB job-settings validator.

Checks a job_config.json against itself BEFORE any audit is run.  Every test
here is pure arithmetic on the settings - no layout file is needed.  This is
what catches a mistyped prize table or an impossible restriction early, rather
than after 50 seconds of auditing several million tickets.

Usage:  python validate_config.py <job_config.json>

Exit code 0 = all good, 1 = problems found.
"""

import json
import sys

WIN_RULES = {"match_two", "match_two_or_special", "special_only"}
GROUP_MODES = {"exactly", "min", "at_most_each", "at_least_one_total",
               "exactly_one_total"}
ALLOC_MODES = {"exact", "min"}


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.notes = []

    def error(self, game, msg):
        self.errors.append((game, msg))

    def warn(self, game, msg):
        self.warnings.append((game, msg))

    def note(self, game, msg):
        self.notes.append((game, msg))

    @property
    def ok(self):
        return not self.errors


def game_channels(g):
    """The channels a game is printed on.  Settings carry a list ("channels");
    older settings files carry a single number ("channel")."""
    return list(g["channels"]) if "channels" in g else [g["channel"]]


def validate(cfg):
    r = Report()
    struct = cfg["structure"]
    tickets = struct["tickets_per_game"]
    book_size = struct["book_size"]
    books = tickets // book_size
    price = cfg["job"]["ticket_price"]
    gleps_amt = cfg["fixed_rules"]["gleps_amount"]

    if tickets % book_size:
        r.error("job", f"{tickets:,} tickets is not a whole number of "
                       f"{book_size}-ticket books.")

    # every channel 1..N belongs to exactly one game; a game may own several
    n_ch = cfg["layout"]["channels"]
    owner = {}
    for g in cfg["games"]:
        chans = game_channels(g)
        if not chans:
            r.error(g["key"], "no channel assigned.")
        for ch in chans:
            if not 1 <= ch <= n_ch:
                r.error(g["key"], f"channel {ch} is outside 1..{n_ch}.")
            elif ch in owner:
                r.error("job", f"channel {ch} is assigned to both game "
                               f"{owner[ch]} and game {g['key']}.")
            else:
                owner[ch] = g["key"]
    free = [ch for ch in range(1, n_ch + 1) if ch not in owner]
    if free:
        r.error("job", f"layout declares {n_ch} channels but channel(s) "
                       f"{', '.join(map(str, free))} belong to no game.")

    for g in cfg["games"]:
        key = g["key"]
        prizes = g["prizes"]
        by_amount = {}
        for p in prizes:
            by_amount.setdefault(p["amount"], 0)
            by_amount[p["amount"]] += p["count"]

        # ---- 1. counts reconcile -------------------------------------
        winners = sum(p["count"] for p in prizes)
        losers = g["loss"]["count"]
        total = winners + losers
        if total != tickets:
            r.error(key, f"winners {winners:,} + losers {losers:,} = "
                         f"{total:,}, expected {tickets:,}.")

        # ---- 2. pool and payout --------------------------------------
        pool = sum(p["amount"] * p["count"] for p in prizes)
        exp = g.get("expected", {})
        if "pool" in exp and pool != exp["pool"]:
            r.error(key, f"prize pool computes to {pool:,} but the spec states "
                         f"{exp['pool']:,}.")
        revenue = tickets * price
        if "revenue" in exp and revenue != exp["revenue"]:
            r.error(key, f"revenue computes to {revenue:,} but the spec states "
                         f"{exp['revenue']:,}.")
        if "payout_pct" in exp and revenue:
            pct = pool / revenue * 100
            if abs(pct - exp["payout_pct"]) > 0.05:
                r.error(key, f"payout computes to {pct:.2f}% but the spec "
                             f"states {exp['payout_pct']}%.")
        if "win_ratio" in exp and winners:
            ratio = tickets / winners
            if abs(ratio - exp["win_ratio"]) > 0.005:
                r.warn(key, f"win ratio computes to 1:{ratio:.3f} but the spec "
                            f"states 1:{exp['win_ratio']}.")

        # ---- 3. GLEPS reconciles -------------------------------------
        gl = g.get("gleps_per_book")
        if gl is not None:
            want = gl * books
            got = by_amount.get(gleps_amt, 0)
            if want != got:
                r.error(key, f"GLEPS: {gl} x Rs.{gleps_amt} per book over "
                             f"{books:,} books = {want:,}, but the prize table "
                             f"has {got:,}.")

        # ---- 4. win rule / symbols coherent ---------------------------
        rule = g["win_rule"]
        if rule not in WIN_RULES:
            r.error(key, f"unknown win rule '{rule}'.")
        symbols = set(g["play_symbols"])
        for s in g.get("special_symbols") or []:
            if s not in symbols:
                r.error(key, f"special symbol '{s}' is not in the play-symbol table.")
        if rule in ("match_two_or_special", "special_only") and not g.get("special_symbols"):
            r.error(key, f"win rule '{rule}' needs at least one special symbol.")
        for p in prizes:
            if "symbol" in p and p["symbol"] not in symbols:
                r.error(key, f"prize {p['sys']} references symbol "
                             f"'{p['symbol']}' which is not in the table.")
        if g.get("has_prize_spot"):
            for p in prizes:
                if not p.get("print"):
                    r.error(key, f"prize {p['sys']} has no print code but this "
                                 "game has a prize spot.")
        else:
            for p in prizes:
                if p.get("print"):
                    r.error(key, f"prize {p['sys']} carries print code "
                                 f"'{p['print']}' but this game has no prize spot.")

        # ---- 5. packing schedule reconciles ---------------------------
        sched = g.get("packing") or []
        sched_books = sum(s["slots"] * s["books"] for s in sched)
        if sched_books != books:
            r.error(key, f"packing schedule covers {sched_books:,} books but "
                         f"the game has {books:,}.")
        alloc_tot = {}
        alloc_exact = {}
        for s in sched:
            for a in s["allocation"]:
                if a["mode"] not in ALLOC_MODES:
                    r.error(key, f"unknown allocation mode '{a['mode']}'.")
                alloc_tot[a["amount"]] = alloc_tot.get(a["amount"], 0) + a["n"] * s["slots"]
                if a["mode"] == "exact":
                    alloc_exact.setdefault(a["amount"], True)
                else:
                    alloc_exact[a["amount"]] = False
        for amt, need in alloc_tot.items():
            have = by_amount.get(amt, 0)
            if amt not in by_amount:
                r.error(key, f"packing references Rs.{amt:,} which is not a prize "
                             "in this game.")
            elif alloc_exact.get(amt) and need != have:
                r.error(key, f"Rs.{amt:,}: packing requires exactly {need:,} "
                             f"but the prize table has {have:,}.")
            elif not alloc_exact.get(amt) and need > have:
                r.error(key, f"Rs.{amt:,}: packing requires at least {need:,} "
                             f"but the prize table has only {have:,}.")
            elif not alloc_exact.get(amt):
                r.note(key, f"Rs.{amt:,}: packing minimum {need:,}, prize table "
                            f"{have:,} (slack {have-need:,}).")

        # ---- 6. group rules are achievable ----------------------------
        for gr in g.get("group_rules") or []:
            mode = gr["mode"]
            if mode not in GROUP_MODES:
                r.error(key, f"unknown group mode '{mode}'.")
                continue
            size_books = gr.get("size", 1)
            n_groups = -(-books // size_books)
            pool_amt = sum(by_amount.get(a, 0) for a in gr["amounts"])
            label = "/".join(f"Rs.{a:,}" for a in gr["amounts"])
            if mode in ("exactly", "min", "at_least_one_total"):
                need = n_groups * gr.get("n", 1)
                if need > pool_amt:
                    r.error(key, f"{label}: '{mode}' over {n_groups:,} group(s) "
                                 f"of {size_books} book(s) needs {need:,} prizes "
                                 f"but only {pool_amt:,} exist - IMPOSSIBLE.")
                elif mode == "exactly" and need != pool_amt:
                    r.error(key, f"{label}: 'exactly {gr.get('n',1)}' per group "
                                 f"over {n_groups:,} groups needs exactly "
                                 f"{need:,} but {pool_amt:,} exist.")
            elif mode == "exactly_one_total":
                if pool_amt != n_groups:
                    r.error(key, f"{label}: 'exactly one in total' per group "
                                 f"needs exactly {n_groups:,} prizes but "
                                 f"{pool_amt:,} exist.")
            elif mode == "at_most_each":
                for a in gr["amounts"]:
                    if by_amount.get(a, 0) > n_groups * gr.get("n", 1):
                        r.error(key, f"Rs.{a:,}: 'at most {gr.get('n',1)} per "
                                     f"group' allows {n_groups*gr.get('n',1):,} "
                                     f"but {by_amount.get(a,0):,} exist.")
            if gr.get("note"):
                r.note(key, gr["note"])
            if books % size_books:
                r.warn(key, f"{label}: group of {size_books} books does not "
                            f"divide {books:,} books evenly "
                            f"({books/size_books:.2f} groups).")

        # ---- 7. agent low-tier letter exists --------------------------
        low_map = cfg["agent"]["low_letters"]
        low_amounts = [p["amount"] for p in prizes if p["tier"] == "Low"]
        for a in low_amounts:
            if str(a) not in low_map:
                r.error(key, f"low-tier prize Rs.{a:,} has no agent letter "
                             "configured.")
    return r


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_config.py <job_config.json>")
        sys.exit(1)
    cfg = json.load(open(sys.argv[1]))
    r = validate(cfg)

    print(f"Validating: {cfg['job']['id']}")
    print(f"  {len(cfg['games'])} game(s), "
          f"{cfg['structure']['tickets_per_game']:,} tickets each, "
          f"books of {cfg['structure']['book_size']}\n")

    for tag, items, sym in (("ERROR", r.errors, "X"),
                            ("WARNING", r.warnings, "!"),
                            ("note", r.notes, "-")):
        if items:
            print(f"{tag}S:" if tag != "note" else "Notes:")
            for game, msg in items:
                print(f"  {sym} [{game}] {msg}")
            print()

    if r.ok:
        print("RESULT: settings are internally consistent.")
    else:
        print(f"RESULT: {len(r.errors)} error(s) - do not run the audit until resolved.")
    sys.exit(0 if r.ok else 1)


if __name__ == "__main__":
    main()
