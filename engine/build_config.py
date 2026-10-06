#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BUILD THE SETTINGS FROM THE REVIEWED SPECIFICATION
==================================================

Reads jobs/<job>/spec.md and writes jobs/<job>/job_config.json.

    python build_config.py --job jobs/<job folder>

Two gates, both enforced:

  1. REVIEW   - every item under "## Review items" must be ticked (- [x]).
                An unticked item means the draft has not been reviewed.
  2. VALIDITY - the settings must pass validate_config.  A ticked BLOCKING
                item whose table was not actually corrected fails here.

The specification markdown is the record; the JSON is derived from it and
should never be edited by hand.  If job_config.json already exists and the
new settings differ from it, the differences are listed before overwriting.
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from spec_md import parse, unticked_review_items, SpecError   # noqa: E402
from validate_config import validate                          # noqa: E402


def _diff(a, b, path=""):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            out += _diff(a.get(k, "<absent>"), b.get(k, "<absent>"), f"{path}.{k}")
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            out += _diff(x, y, f"{path}[{i}]")
    elif a != b:
        out.append(f"{path.lstrip('.')}: {a!r} -> {b!r}")
    return out


def main():
    ap = argparse.ArgumentParser(description="Build job_config.json from spec.md")
    ap.add_argument("--job", required=True)
    ap.add_argument("--spec", help="markdown to read (default <job>/spec.md)")
    args = ap.parse_args()

    job_dir = args.job.rstrip("/\\")
    spec = args.spec or os.path.join(job_dir, "spec.md")
    out = os.path.join(job_dir, "job_config.json")
    if not os.path.exists(spec):
        sys.exit(f"{spec} not found - run draft_spec.py first.")
    md = open(spec, encoding="utf-8").read()

    # ---- gate 1: review -----------------------------------------------
    open_items = unticked_review_items(md)
    if open_items:
        print(f"NOT BUILT: {len(open_items)} review item(s) are still unticked "
              f"in {spec}:")
        for i in open_items:
            print(f"  {i}")
        print("\nResolve each item, correct any table it concerns, then tick it (- [x]).")
        sys.exit(1)

    # ---- read the tables ----------------------------------------------
    try:
        cfg = parse(md)
    except (SpecError, KeyError, ValueError) as e:
        sys.exit(f"NOT BUILT: could not read {spec}: {e}\n"
                 "Check that the anchored tables still have their original column "
                 "headings and that numbers are written plainly.")

    # ---- gate 2: validity ---------------------------------------------
    rep = validate(cfg)
    for game, msg in rep.warnings:
        print(f"  ! [{game}] {msg}")
    if not rep.ok:
        print(f"NOT BUILT: the settings in {spec} fail validation:")
        for game, msg in rep.errors:
            print(f"  X [{game}] {msg}")
        print("\nCorrect the tables in the specification and run again.")
        sys.exit(1)

    # ---- write, showing what changed ------------------------------------
    if os.path.exists(out):
        old = json.load(open(out))
        changes = _diff(old, cfg)
        if changes:
            print(f"Updating {out} - {len(changes)} change(s):")
            for c in changes[:40]:
                print(f"  ~ {c}")
            if len(changes) > 40:
                print(f"  ... {len(changes)-40} more")
        else:
            print(f"{out} is already up to date.")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=1)
    print(f"\nBUILT: {out}  ({len(cfg['games'])} game(s), validation passed)")
    print("Next: run probe_layout.py --config to confirm the settings against the "
          "layout file, then audit_engine.py.")


if __name__ == "__main__":
    main()
