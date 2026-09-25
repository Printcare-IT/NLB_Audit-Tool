#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REGRESSION RUNNER
=================

Run after ANY change to the engine, before auditing a new job.

    python tests/run_regression.py --layouts <folder with layout files>
    python tests/run_regression.py --unit-only          (seconds; no layouts)
    python tests/run_regression.py --record --layouts <folder>

Two layers:

  1. Unit tests (tests/test_*.py) on a small synthetic job - every audit
     check, the validator, the parsers, the markdown format, the drafter and
     the build gates.  Under a second.  Always run.

  2. Golden results for each real job that has tests/golden/<job>.json:
       a. job_config.json is still exactly what spec.md produces
       b. the settings still validate
       c. the drafter still reads the job's documents exactly as before
          (needs jobs/<job>/inputs and measured_facts.json)
       d. with the layout file present: the probe still agrees with the
          settings, and every check reports the same offender count as
          recorded.  Several minutes per job.

--record writes the golden files from the CURRENT results.  Only do that
after confirming a change in results is intended - it redefines "correct".
"""

import argparse
import copy
import datetime
import glob
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
ENGINE = os.path.join(ROOT, "engine")
sys.path[:0] = [ENGINE]
from spec_md import parse                                     # noqa: E402
from validate_config import validate                          # noqa: E402
import probe_layout as P                                      # noqa: E402
import draft_spec                                             # noqa: E402
from doc_text import to_text, flatten                         # noqa: E402
from audit_engine import Job, load_layout, run_all_checks     # noqa: E402

GOLDEN = os.path.join(HERE, "golden")


def say(ok, msg):
    print(f"   {'PASS' if ok else 'FAIL'}  {msg}")
    return ok


def find_layout(name, job_dir, extra_dirs):
    for d in list(extra_dirs) + [job_dir, os.path.join(job_dir, "inputs")]:
        p = os.path.join(d, name)
        if os.path.isfile(p):
            return p
    return None


def diff(a, b, path=""):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            out += diff(a.get(k, "<absent>"), b.get(k, "<absent>"), f"{path}.{k}")
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, f"{path}[{i}]")
    elif a != b:
        out.append(f"{path.lstrip('.')}: {a!r} -> {b!r}")
    return out


def draft_now(job_dir):
    ins = sorted(p for e in ("pdf", "docx", "doc")
                 for p in glob.glob(os.path.join(job_dir, "inputs", f"*.{e}")))
    facts_p = os.path.join(job_dir, "measured_facts.json")
    if not ins or not os.path.exists(facts_p):
        return None
    docs = [(p, flatten(to_text(p))) for p in ins]
    cfg, D = draft_spec.build(os.path.basename(job_dir), docs, json.load(open(facts_p)))
    return {"review": [f"{r['severity']}: {r['text']}" for r in D.review],
            "config": json.loads(json.dumps(cfg))}


def audit_now(cfg, layout):
    job = Job(cfg)
    games, info = load_layout(job, layout)
    res = {k: {str(r.index): len(r.offenders) if not r.passed else 0
               for r in run_all_checks(job, g, info)} for k, g in games.items()}
    load = {"rows": info["rows"], "void_tickets": info["void_tickets"],
            "live_tickets": info["rows"] * job.channels - info["void_tickets"],
            "malformed": len(info["malformed"]), "duplicates": len(info["duplicates"])}
    st = P.sniff_structure(layout)
    meas = P.measure(layout, st, P.find_void_serial(layout, st))
    return res, load, P.compare(meas, cfg)


def check_job(job_dir, golden, layouts, record):
    name = os.path.basename(job_dir)
    print(f"\n== {name} ==")
    ok = True
    spec_p = os.path.join(job_dir, "spec.md")
    cfg_p = os.path.join(job_dir, "job_config.json")
    if not (os.path.exists(spec_p) and os.path.exists(cfg_p)):
        return say(False, "spec.md and job_config.json are both required")

    # a. settings derived from the spec
    from_spec = parse(open(spec_p, encoding="utf-8").read())
    stored = json.load(open(cfg_p))
    d = diff(stored, from_spec)
    ok &= say(not d, "job_config.json matches spec.md" if not d else
              f"job_config.json differs from spec.md ({len(d)}): {d[:3]} - run build_config.py")
    # b. validation
    rep = validate(stored)
    ok &= say(rep.ok, "settings validate" if rep.ok else f"validation errors: {rep.errors[:3]}")

    # c. drafter
    t = time.time()
    dr = draft_now(job_dir)
    if dr is None:
        print("   skip  drafter: no inputs/ or measured_facts.json")
    elif record:
        golden["draft"] = dr
        print(f"   REC   drafter: {len(dr['review'])} review item(s) recorded ({time.time()-t:.0f}s)")
    elif "draft" in golden:
        d1 = diff(golden["draft"]["config"], dr["config"])
        ok &= say(not d1, "drafter reads the documents as recorded" if not d1 else
                  f"drafted settings changed ({len(d1)}): {d1[:4]}")
        same = golden["draft"]["review"] == dr["review"]
        ok &= say(same, f"drafter raises the same {len(dr['review'])} review item(s)"
                  if same else f"review items changed: was {golden['draft']['review']}, "
                               f"now {dr['review']}")

    # d. layout: probe + audit
    lname = golden.get("layout_file") or (record and None)
    layout = find_layout(lname, job_dir, layouts) if lname else None
    if layout is None:
        print(f"   skip  audit: layout file {lname or '(unknown)'} not found "
              "(pass --layouts <folder>)")
        return ok
    t = time.time()
    res, load, probe_diffs = audit_now(stored, layout)
    ok &= say(not probe_diffs, "probe agrees with the settings" if not probe_diffs
              else f"probe disagreements: {probe_diffs[:3]}")
    if record:
        golden["audit"], golden["load"] = res, load
        print(f"   REC   audit results recorded ({time.time()-t:.0f}s)")
        return ok
    d2 = diff(golden.get("load", {}), load)
    ok &= say(not d2, f"load figures unchanged ({load['live_tickets']:,} live tickets)"
              if not d2 else f"load figures changed: {d2}")
    d3 = diff(golden.get("audit", {}), res)
    summary = ", ".join(f"{k}: " + (", ".join(f"#{c}={n:,}" for c, n in v.items() if n) or "clean")
                        for k, v in res.items())
    ok &= say(not d3, f"every check unchanged [{summary}] ({time.time()-t:.0f}s)" if not d3
              else "check results changed (game.check: was -> now):\n          " +
              "\n          ".join(d3))
    return ok


def main():
    ap = argparse.ArgumentParser(description="NLB audit tool regression runner")
    ap.add_argument("--layouts", action="append", default=[],
                    help="folder holding layout files (repeatable)")
    ap.add_argument("--unit-only", action="store_true")
    ap.add_argument("--record", action="store_true",
                    help="write golden results from the current state")
    ap.add_argument("--job", action="append", default=[], help="limit to these job folders")
    args = ap.parse_args()

    print("== unit tests ==")
    r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", HERE, "-t", ROOT],
                       capture_output=True, text=True, cwd=ROOT)
    last = r.stderr.strip().splitlines()
    print("   " + (last[-3] if len(last) >= 3 else "") + " -> " + (last[-1] if last else ""))
    if r.returncode != 0:
        print(r.stderr)
        print("UNIT TESTS FAILED - fix these before trusting any audit.")
        sys.exit(1)
    if args.unit_only:
        print("\nALL PASSED (unit tests only)")
        return

    os.makedirs(GOLDEN, exist_ok=True)
    jobs_root = os.path.join(ROOT, "jobs")
    names = args.job or sorted(os.listdir(jobs_root)) if os.path.isdir(jobs_root) else []
    all_ok, ran = True, 0
    for name in names:
        job_dir = os.path.join(jobs_root, os.path.basename(name))
        gp = os.path.join(GOLDEN, f"{os.path.basename(job_dir)}.json")
        if not os.path.isdir(job_dir):
            continue
        if args.record:
            golden = json.load(open(gp)) if os.path.exists(gp) else {}
            golden.setdefault("layout_file", _guess_layout(job_dir, args.layouts))
            golden["recorded"] = f"{datetime.datetime.now():%Y-%m-%d %H:%M}"
            all_ok &= check_job(job_dir, golden, args.layouts, record=True)
            json.dump(golden, open(gp, "w"), indent=1)
            print(f"   wrote {os.path.relpath(gp, ROOT)}")
        elif os.path.exists(gp):
            all_ok &= check_job(job_dir, json.load(open(gp)), args.layouts, record=False)
        else:
            continue
        ran += 1
    if not ran:
        print("\nno jobs with golden results (tests/golden/<job>.json) - "
              "use --record once to create them")
    print("\nALL PASSED" if all_ok else "\nREGRESSION FAILED - do not use the tool until "
          "every difference is explained")
    sys.exit(0 if all_ok else 1)


def _guess_layout(job_dir, dirs):
    """At record time, find the layout whose name matches the job's games."""
    cfg = json.load(open(os.path.join(job_dir, "job_config.json")))
    stem = "-".join(g["key"] for g in sorted(cfg["games"], key=lambda g: g["channel"]))
    for d in list(dirs) + [job_dir, os.path.join(job_dir, "inputs")]:
        for p in glob.glob(os.path.join(d, "*")):
            if os.path.basename(p).upper().startswith(stem) and p.upper().endswith(".TXT"):
                return os.path.basename(p)
    return None


if __name__ == "__main__":
    main()
