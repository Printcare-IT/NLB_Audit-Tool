#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The job specification markdown format.

This module both WRITES the markdown (render) and READS it back (parse), so
the drafter and the settings builder can never disagree about the layout.

Machine-read tables are marked with an invisible anchor on the line above:

    <!-- table:prizes game=0345 -->
    | System code | Amount | ... |

Everything else in the document is prose for the reviewer and is ignored by
the parser, so it can be edited freely.  Edit the VALUES in anchored tables to
change the settings; do not rename their column headings.

Section order follows the standard job record:
  1 Usage · 2 Layout file format · 3 Game mechanics · 4 Prize structures ·
  5 Play symbol codes · 6 Agent validation codes · 7 Ticket and packaging ·
  8 Audit procedures · 9 Tool configuration · 10 Modelling conventions ·
  11 Tool structure and limitations
"""

import datetime
import re

from validate_config import game_channels

TEMPLATE_VERSION = "1"

WIN_RULE_TEXT = {
    "match_two": "two identical play symbols win",
    "match_two_or_special": "two identical play symbols win, or a single special symbol wins",
    "special_only": "a single special symbol wins; a matching pair does NOT win",
}
MODE_TEXT = {
    "exactly": "exactly N of each",
    "min": "at least N in total",
    "at_most_each": "at most N of each",
    "at_least_one_total": "at least one of the set, at most N of each",
    "exactly_one_total": "exactly one of the set in total",
}


# ------------------------------------------------------------------ #
#  Small helpers                                                      #
# ------------------------------------------------------------------ #

def _n(x):
    return f"{x:,}" if isinstance(x, int) else str(x)


def _table(anchor, headers, rows):
    out = [f"<!-- table:{anchor} -->",
           "| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def _cell_int(s):
    s = s.strip().replace(",", "").replace("Rs.", "").replace("Rs", "").strip()
    return int(s)


def _cell_list(s):
    s = s.strip()
    if s in ("", "-", "none", "None"):
        return []
    return [x.strip() for x in s.split(",") if x.strip()]


def _blank(s):
    return s.strip() in ("", "-", "none", "None")


# ------------------------------------------------------------------ #
#  RENDER                                                             #
# ------------------------------------------------------------------ #

def render(cfg, review, evidence, meta):
    """cfg      - settings dict (the same shape as job_config.json)
       review   - list of {id, game, severity, text}
       evidence - dict: key -> list of prose lines (keys: 'layout',
                  'agent', 'packing', ('mech', game), ('prize', game), ...)
       meta     - {'generated', 'sources_detail', 'tool'}"""
    J = cfg["job"]
    L = cfg["layout"]
    O = L["offsets"]
    S = cfg["structure"]
    A = cfg["agent"]
    F = cfg["fixed_rules"]
    games = sorted(cfg["games"], key=lambda g: game_channels(g)[0])
    E = lambda k: evidence.get(k, [])
    W = []
    add = W.append

    add(f"# NLB Job Specification - {J['id']}")
    add(f"<!-- spec-template: {TEMPLATE_VERSION} -->")
    add("")
    add(f"> **Draft generated** {meta['generated']} by `draft_spec.py` from the "
        "documents listed below and the measurements in `measured_facts.json`. "
        "Review every section against the specification documents, resolve the "
        "review items, then run `build_config.py`. It will not produce settings "
        "while any review item is unticked or the settings fail validation.")
    add("")
    add(_table("job", ["Setting", "Value"], [
        ["Job ID", J["id"]], ["Client", J["client"]], ["Title", J["title"]]]))
    add("")
    add("**Sources**")
    add("")
    add("<!-- list:sources -->")
    for s in J["sources"]:
        add(f"- {s}")
    add("")

    # ---- review items ------------------------------------------------
    add("## Review items")
    add("")
    if review:
        add("Tick each item (`- [x]`) once it is resolved. Items marked "
            "**BLOCKING** also need the relevant table corrected - ticking alone "
            "will not get past validation. Items marked **LAYOUT** are places where "
            "the layout file disagrees with the specification: confirm the tables "
            "follow the specification (not the file) and tick - the audit reports "
            "the difference as a layout-file error.")
        add("")
        for r in review:
            tag = {"blocking": "BLOCKING", "layout": "LAYOUT"}.get(r["severity"], "check")
            where = f"{r['game']} · " if r.get("game") else ""
            add(f"- [ ] **{r['id']} · {where}{tag}** - {r['text']}")
    else:
        add("No review items. The specifications, the data specification and the "
            "measured layout file agree on every point the drafter checks.")
    add("")

    # ---- 1 usage ----------------------------------------------------
    add("## 1. Usage")
    add("")
    add("```")
    add(f"python engine/build_config.py  --job jobs/{J['id']}")
    add(f"python engine/probe_layout.py  <layout file> --config jobs/{J['id']}/job_config.json")
    add(f"python engine/audit_engine.py  --config jobs/{J['id']}/job_config.json "
        f"--layout <layout file> --out jobs/{J['id']}/out")
    add("```")
    add("")

    # ---- 2 layout ---------------------------------------------------
    add("## 2. Layout file format")
    add("")
    lo, hi = L["virn_random_range"]
    add(_table("layout", ["Setting", "Value"], [
        ["Channels", L["channels"]],
        ["Lead columns", L["lead_columns"]],
        ["Block length", L["block_len"]],
        ["Serial offset", O["serial"]], ["VIRN offset", O["virn"]],
        ["Barcode offset", O["bar"]], ["System prize code offset", O["sys"]],
        ["Prize print code offset", O["print"]],
        ["First play offset", O["play_first"]], ["Play fields", O["play_count"]],
        ["Play fields used", O["play_used"]],
        ["First agent offset", O["agent_first"]], ["Agent fields", O["agent_count"]],
        ["QA offset", O["qa"]],
        ["Void serial", L["void_serial"]], ["Passive flag", L["passive_flag"]],
        ["VIRN random range", f"{lo:,} - {hi:,}"],
        ["Parity rule", L["parity_rule"]],
    ]))
    add("")
    for line in E("layout"):
        add(f"- {line}")
    add("")
    add(_table("games", ["Channel", "Game", "Lottery", "Name"],
               [[" / ".join(str(c) for c in game_channels(g)), g["key"],
                 g["lottery"], g["name"]] for g in games]))
    add("")

    # ---- 3 mechanics ------------------------------------------------
    add("## 3. Game mechanics")
    add("")
    add(_table("mechanics", ["Game", "Win rule", "Special symbols", "Forbidden", "Prize spot"], [
        [g["key"], g["win_rule"], ", ".join(g.get("special_symbols") or []) or "-",
         g.get("forbidden") or "-", "yes" if g.get("has_prize_spot", True) else "no"]
        for g in games]))
    add("")
    add("Win rules: " + "; ".join(f"`{k}` - {v}" for k, v in WIN_RULE_TEXT.items()) +
        ". Forbidden `two_special` rejects any ticket carrying two special symbols.")
    add("")
    for g in games:
        add(f"**{g['key']} {g['name']}**")
        add("")
        for line in E(("mech", g["key"])):
            add(f"- {line}")
        add("")

    # ---- 4 prizes ---------------------------------------------------
    add("## 4. Prize structures")
    add("")
    for g in games:
        add(f"### {g['lottery']}-{g['key']} {g['name']}")
        add("")
        rows = []
        for p in sorted(g["prizes"], key=lambda p: p["amount"]):
            rows.append([p["sys"], _n(p["amount"]), p.get("label") or "-",
                         p.get("print") or "-", p["tier"], _n(p["count"]),
                         p.get("symbol") or "-"])
        rows.append([g["loss"]["code"], "-", "Non-win", "-", "Loss",
                     _n(g["loss"]["count"]), "-"])
        add(_table(f"prizes game={g['key']}",
                   ["System code", "Amount", "Label", "Print code", "Tier", "Count", "Symbol"],
                   rows))
        add("")
        for line in E(("prize", g["key"])):
            add(f"- {line}")
        add("")
    add("**Declared parameters** (checked by the validator, never used to compute):")
    add("")
    add(_table("expected", ["Game", "Revenue", "Pool", "Payout %", "Win ratio"], [
        [g["key"], _n(g["expected"]["revenue"]), _n(g["expected"]["pool"]),
         f"{g['expected']['payout_pct']:.1f}", f"{g['expected']['win_ratio']:.2f}"]
        for g in games]))
    add("")

    # ---- 5 symbols --------------------------------------------------
    add("## 5. Play symbol codes")
    add("")
    add("Play codes are capitals; prize print codes are smalls.")
    add("")
    for g in games:
        add(f"**{g['key']} {g['name']}**")
        add("")
        add(_table(f"symbols game={g['key']}", ["Code", "Symbol"],
                   [[c, n] for c, n in g["play_symbols"].items()]))
        add("")
        for line in E(("sym", g["key"])):
            add(f"- {line}")
        if E(("sym", g["key"])):
            add("")

    # ---- 6 agent ----------------------------------------------------
    add("## 6. Agent validation codes")
    add("")
    rows = [["High-tier letters", ", ".join(A["high_letters"])]]
    for amt, letter in sorted(A["low_letters"].items(), key=lambda kv: int(kv[0])):
        rows.append([f"Low-tier letter (Rs. {int(amt):,})", letter])
    rows += [["Positions", A["positions"]], ["Letters per ticket", A["letters_used"]]]
    add(_table("agent", ["Setting", "Value"], rows))
    add("")
    add("Non-winning and high-tier winning tickets carry three distinct high-tier "
        "letters; low-tier winners carry the low-tier letter plus two distinct "
        "high-tier letters.")
    add("")
    for line in E("agent"):
        add(f"- {line}")
    add("")

    # ---- 7 ticket and packaging --------------------------------------
    add("## 7. Ticket and packaging")
    add("")
    add(_table("ticket", ["Setting", "Value"], [
        ["Ticket price", _n(J["ticket_price"])],
        ["Tickets per game", _n(S["tickets_per_game"])],
        ["Book size", S["book_size"]]]))
    add("")
    add(_table("gleps", ["Game", "GLEPS per book"],
               [[g["key"], g.get("gleps_per_book", "-")] for g in games]))
    add("")
    add("Packing: each slot group is a run of identical slots covering whole "
        "books, in serial order. Mode `exact` must match; `min` is a floor.")
    add("")
    for g in games:
        add(f"**{g['key']} {g['name']}**")
        add("")
        rows = []
        for i, s in enumerate(g.get("packing") or [], 1):
            if not s["allocation"]:
                rows.append([i, s["slots"], s["books"], "-", "-", "-"])
            for a in s["allocation"]:
                rows.append([i, s["slots"], s["books"], _n(a["amount"]), a["mode"], a["n"]])
        add(_table(f"packing game={g['key']}",
                   ["Slot group", "Slots", "Books per slot", "Amount", "Mode", "N"], rows))
        add("")
        for line in E(("pack", g["key"])):
            add(f"- {line}")
        if E(("pack", g["key"])):
            add("")

    # ---- 8 audit procedures ----------------------------------------
    add("## 8. Audit procedures")
    add("")
    add("The six restrictions identical in every NLB game specification are built "
        "into the engine. Their two embedded numbers are settings:")
    add("")
    add(_table("fixed", ["Setting", "Value"], [
        ["Max same-value run", F["max_same_value_run"]],
        ["Winner every N tickets", F["winner_every_n_tickets"]],
        ["GLEPS amount", _n(F["gleps_amount"])]]))
    add("")
    for line in E("fixed"):
        add(f"- {line}")
    if E("fixed"):
        add("")
    add("Per-game prize promises (per book, or per batch of books). Separate "
        "several amounts with ` / `. Modes: " +
        "; ".join(f"`{k}` - {v}" for k, v in MODE_TEXT.items()) + ".")
    add("")
    for g in games:
        add(f"**{g['key']} {g['name']}**")
        add("")
        rows = []
        for gr in g.get("group_rules") or []:
            rows.append([gr["group"], gr.get("size", 1),
                         " / ".join(_n(a) for a in gr["amounts"]),
                         gr["mode"], gr.get("n", 1), gr.get("note", "") or "-"])
        if not rows:
            rows.append(["none", "-", "-", "-", "-", "-"])
        add(_table(f"groups game={g['key']}",
                   ["Group", "Size (books)", "Amounts", "Mode", "N", "Note"], rows))
        add("")
        for line in E(("group", g["key"])):
            add(f"- {line}")
        if E(("group", g["key"])):
            add("")
    add("Procedures run per game: 1 play positions · 2 prize box · 3 serial "
        "numbers · 4 VIRN and barcode · 5 agent codes · 6 prize structure · "
        "7 GLEPS per book · 8 packing allocation · 9 per-group promises · "
        "10 NON-GLEPS per book · 11 consecutive play pattern · 12 consecutive "
        "symbols in any rotation · 13 winner in every block of N · 14 prize "
        "value run length · 15 VIRN independence.")
    add("")

    # ---- 9-11 ------------------------------------------------------
    add("## 9. Tool configuration")
    add("")
    add("`job_config.json` is generated from this document by `build_config.py`. "
        "Do not edit the JSON by hand: change the anchored tables here and "
        "rebuild, so this document stays the record of what was audited.")
    add("")
    add("## 10. Modelling conventions")
    add("")
    add("- Consecutive tickets means consecutive serial numbers within a game.")
    add("- Book = (serial - 1) // book size + 1; slots are counted in whole books "
        "from serial 1.")
    add("- `min` rules pass when the actual count meets or exceeds the floor; "
        "the actual figure is always reported.")
    add("- VOID rows are identified by serial value, not position; padding at "
        "either end of the file is expected.")
    add("- The prize-value run-length rule applies to winning tickets only.")
    add("- The QA sample code is not audited.")
    add("")
    add("## 11. Tool structure and limitations")
    add("")
    add("- `draft_spec.py` reads NLB specifications with patterns written for the "
        "NLB template. A specification that departs from that template produces "
        "review items rather than guesses, but read every table regardless.")
    add("- Nothing in the pipeline compares the settings against the written "
        "specification except this review.")
    add("- The whole layout file is held in memory during the audit.")
    add("")
    return "\n".join(W)


# ------------------------------------------------------------------ #
#  PARSE                                                              #
# ------------------------------------------------------------------ #

class SpecError(Exception):
    pass


ANCHOR = re.compile(r"<!--\s*(table|list):(\w+)(?:\s+game=(\w+))?\s*-->")


def _read_tables(md):
    lines = md.splitlines()
    tables, lists = {}, {}
    for i, line in enumerate(lines):
        m = ANCHOR.search(line)
        if not m:
            continue
        kind, name, game = m.groups()
        key = (name, game)
        j = i + 1
        if kind == "list":
            items = []
            while j < len(lines) and lines[j].strip().startswith("- "):
                items.append(lines[j].strip()[2:].strip())
                j += 1
            lists[key] = items
            continue
        while j < len(lines) and not lines[j].strip():
            j += 1
        rows = []
        while j < len(lines) and lines[j].strip().startswith("|"):
            cells = [c.strip().replace("**", "").replace("`", "")
                     for c in lines[j].strip().strip("|").split("|")]
            rows.append(cells)
            j += 1
        if len(rows) < 2:
            raise SpecError(f"table '{name}'{' for game '+game if game else ''} "
                            "is empty or malformed")
        header = rows[0]
        body = [dict(zip(header, r)) for r in rows[2:]]
        tables[key] = (header, body)
    return tables, lists


def _kv(tables, name):
    if (name, None) not in tables:
        raise SpecError(f"missing table '{name}'")
    return {r["Setting"]: r["Value"] for r in tables[(name, None)][1]}


def unticked_review_items(md):
    m = re.search(r"^## Review items\s*$(.*?)^## ", md, re.S | re.M)
    if not m:
        return []
    return [l.strip() for l in m.group(1).splitlines()
            if re.match(r"\s*- \[ \]", l)]


def parse(md):
    """Return the settings dict described by a spec markdown document."""
    t, lists = _read_tables(md)

    job = _kv(t, "job")
    tick = _kv(t, "ticket")
    lay = _kv(t, "layout")
    agent = _kv(t, "agent")
    fixed = _kv(t, "fixed")

    lo, hi = [int(x.replace(",", "")) for x in lay["VIRN random range"].split("-")]
    cfg = {
        "schema_version": "1.0",
        "job": {"id": job["Job ID"], "client": job["Client"], "title": job["Title"],
                "ticket_price": _cell_int(tick["Ticket price"]),
                "sources": lists.get(("sources", None), [])},
        "layout": {
            "block_len": _cell_int(lay["Block length"]),
            "channels": _cell_int(lay["Channels"]),
            "lead_columns": _cell_int(lay["Lead columns"]),
            "offsets": {
                "serial": _cell_int(lay["Serial offset"]),
                "virn": _cell_int(lay["VIRN offset"]),
                "bar": _cell_int(lay["Barcode offset"]),
                "sys": _cell_int(lay["System prize code offset"]),
                "print": _cell_int(lay["Prize print code offset"]),
                "play_first": _cell_int(lay["First play offset"]),
                "play_count": _cell_int(lay["Play fields"]),
                "play_used": _cell_int(lay["Play fields used"]),
                "agent_first": _cell_int(lay["First agent offset"]),
                "agent_count": _cell_int(lay["Agent fields"]),
                "qa": _cell_int(lay["QA offset"]),
            },
            "void_serial": lay["Void serial"],
            "passive_flag": lay["Passive flag"],
            "virn_random_range": [lo, hi],
            "parity_rule": lay["Parity rule"],
        },
        "structure": {"tickets_per_game": _cell_int(tick["Tickets per game"]),
                      "book_size": _cell_int(tick["Book size"])},
        "agent": {
            "high_letters": _cell_list(agent["High-tier letters"]),
            "low_letters": {},
            "positions": _cell_int(agent["Positions"]),
            "letters_used": _cell_int(agent["Letters per ticket"]),
        },
        "fixed_rules": {
            "max_same_value_run": _cell_int(fixed["Max same-value run"]),
            "winner_every_n_tickets": _cell_int(fixed["Winner every N tickets"]),
            "gleps_amount": _cell_int(fixed["GLEPS amount"]),
        },
        "games": [],
    }
    for k, v in agent.items():
        m = re.match(r"Low-tier letter \(Rs\.?\s*([\d,]+)\)", k)
        if m:
            cfg["agent"]["low_letters"][str(int(m.group(1).replace(",", "")))] = v.strip()

    if ("games", None) not in t:
        raise SpecError("missing table 'games'")
    mech = {r["Game"]: r for r in t.get(("mechanics", None), (None, []))[1]}
    exp = {r["Game"]: r for r in t.get(("expected", None), (None, []))[1]}
    gleps = {r["Game"]: r for r in t.get(("gleps", None), (None, []))[1]}

    for row in t[("games", None)][1]:
        key = row["Game"]
        if key not in mech:
            raise SpecError(f"game {key} has no row in the mechanics table")
        mrow = mech[key]
        g = {"key": key, "name": row["Name"], "lottery": row["Lottery"],
             "channels": [_cell_int(c) for c in row["Channel"].split("/")],
             "win_rule": mrow["Win rule"],
             "special_symbols": _cell_list(mrow["Special symbols"]),
             "forbidden": None if _blank(mrow["Forbidden"]) else mrow["Forbidden"],
             "has_prize_spot": mrow["Prize spot"].strip().lower() in ("yes", "y", "true")}

        if ("symbols", key) not in t:
            raise SpecError(f"game {key} has no play symbol table")
        g["play_symbols"] = {r["Code"]: r["Symbol"] for r in t[("symbols", key)][1]}

        if ("prizes", key) not in t:
            raise SpecError(f"game {key} has no prize table")
        prizes, loss = [], None
        for r in t[("prizes", key)][1]:
            if r["Tier"].strip().lower() == "loss":
                loss = {"code": r["System code"], "count": _cell_int(r["Count"])}
                continue
            p = {"sys": r["System code"], "amount": _cell_int(r["Amount"]),
                 "print": "" if _blank(r["Print code"]) else r["Print code"],
                 "tier": r["Tier"], "count": _cell_int(r["Count"])}
            if not _blank(r.get("Symbol", "")):
                p["symbol"] = r["Symbol"]
            if not _blank(r.get("Label", "")):
                p["label"] = r["Label"]
            prizes.append(p)
        if loss is None:
            raise SpecError(f"game {key}: prize table has no Loss row")
        g["prizes"], g["loss"] = prizes, loss

        if key in gleps and not _blank(gleps[key]["GLEPS per book"]):
            g["gleps_per_book"] = _cell_int(gleps[key]["GLEPS per book"])

        packing = []
        for r in t.get(("packing", key), (None, []))[1]:
            grp = _cell_int(r["Slot group"])
            while len(packing) < grp:
                packing.append(None)
            if packing[grp - 1] is None:
                packing[grp - 1] = {"slots": _cell_int(r["Slots"]),
                                    "books": _cell_int(r["Books per slot"]),
                                    "allocation": []}
            if not _blank(r["Amount"]):
                packing[grp - 1]["allocation"].append(
                    {"amount": _cell_int(r["Amount"]), "mode": r["Mode"],
                     "n": _cell_int(r["N"])})
        if any(p is None for p in packing):
            raise SpecError(f"game {key}: packing slot groups must be numbered 1, 2, 3 ...")
        g["packing"] = packing

        rules = []
        for r in t.get(("groups", key), (None, []))[1]:
            if r["Group"].strip().lower() == "none":
                continue
            gr = {"group": r["Group"], "size": _cell_int(r["Size (books)"]),
                  "amounts": [_cell_int(a) for a in r["Amounts"].split("/")
                              if not _blank(a)],
                  "mode": r["Mode"], "n": _cell_int(r["N"])}
            if not _blank(r.get("Note", "")):
                gr["note"] = r["Note"]
            rules.append(gr)
        g["group_rules"] = rules

        if key in exp:
            e = exp[key]
            g["expected"] = {"revenue": _cell_int(e["Revenue"]),
                             "pool": _cell_int(e["Pool"]),
                             "payout_pct": float(e["Payout %"]),
                             "win_ratio": float(e["Win ratio"])}
        cfg["games"].append(g)
    cfg["games"].sort(key=lambda g: g["channels"][0])
    return cfg
