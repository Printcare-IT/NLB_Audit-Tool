#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LOTTERY AUDIT TOOL - MODULE ENTRY POINT
=======================================

One command for a host platform (or a person) to drive the whole pipeline.
It adds no checking logic of its own: every step runs the engine script that
the README documents, so the engine's output and gates are unchanged.

    python audit_tool.py status  --job <job>
    python audit_tool.py new     --job <job>
    python audit_tool.py probe   --job <job> [--layout <file>]
    python audit_tool.py draft   --job <job> [--layout <file>]
    python audit_tool.py build   --job <job>
    python audit_tool.py verify  --job <job> [--layout <file>]
    python audit_tool.py audit   --job <job> [--layout <file>]
    python audit_tool.py run     --job <job> [--layout <file>]   build + verify + audit
    python audit_tool.py test    [--layouts <folder>]

<job> is a folder name under jobs/ (e.g. 2026.Sep.NLB.1G) or a path.

--json   send progress to stderr and print one JSON result object on stdout.

Layout file: --layout, else the first *LAYOUT*.TXT found in jobs/<job>/inputs,
jobs/<job>, or the folder named by the AUDIT_LAYOUTS_DIR environment variable
(a file whose name starts with the job's first game number is preferred there).

EXIT CODES
  0  step succeeded (for audit/run: every check passed)
  1  step refused or failed - a gate, a missing file, or an engine error
  2  audit completed, but exceptions were found in the layout file
  3  stopped at a human gate - spec.md has unticked review items
"""

import argparse
import glob
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(ROOT, "engine")
JOBS = os.path.join(ROOT, "jobs")
sys.path.insert(0, ENGINE)

OK, FAILED, EXCEPTIONS, NEEDS_REVIEW = 0, 1, 2, 3
DOC_EXT = (".pdf", ".docx", ".doc")

LOG = sys.stdout          # switched to stderr under --json


def log(msg=""):
    print(msg, file=LOG, flush=True)


# ------------------------------------------------------------------ #
#  Job folder helpers                                                 #
# ------------------------------------------------------------------ #

def job_dir(job):
    if os.path.isdir(job) or os.sep in job or "/" in job:
        return os.path.abspath(job)
    return os.path.join(JOBS, job)


def spec_docs(jd):
    d = os.path.join(jd, "inputs")
    if not os.path.isdir(d):
        return []
    return sorted(p for p in glob.glob(os.path.join(d, "*"))
                  if p.lower().endswith(DOC_EXT)
                  and not os.path.basename(p).startswith("~$"))


def find_layout(jd, explicit=None):
    if explicit:
        return os.path.abspath(explicit) if os.path.isfile(explicit) else None
    for d in (os.path.join(jd, "inputs"), jd):
        hits = sorted(glob.glob(os.path.join(d, "*LAYOUT*.TXT"))
                      + glob.glob(os.path.join(d, "*LAYOUT*.txt")))
        if hits:
            return hits[0]
    share = os.environ.get("AUDIT_LAYOUTS_DIR")
    if share and os.path.isdir(share):
        hits = sorted(glob.glob(os.path.join(share, "*LAYOUT*.TXT"))
                      + glob.glob(os.path.join(share, "*LAYOUT*.txt")))
        cfg = os.path.join(jd, "job_config.json")
        if os.path.exists(cfg):
            first = json.load(open(cfg))["games"][0]["key"]
            hits = [h for h in hits if os.path.basename(h).startswith(first)]
        if len(hits) == 1:                  # never guess between several
            return hits[0]
    return None


def engine(script, *args):
    """Run an engine script, streaming its output to the log. Returns exit code."""
    cmd = [sys.executable, os.path.join(ENGINE, script), *args]
    log(f"$ {' '.join(cmd[1:])}")
    return subprocess.run(cmd, cwd=ROOT, stdout=LOG, stderr=LOG).returncode


def mtime(p):
    return os.path.getmtime(p) if os.path.exists(p) else 0


# ------------------------------------------------------------------ #
#  Status - where a job is in the process                             #
# ------------------------------------------------------------------ #

def job_status(jd, layout_arg=None):
    """Return a dict describing the job's stage and the next action."""
    from spec_md import parse, unticked_review_items, SpecError

    st = {"job": os.path.basename(jd), "path": jd}
    p = lambda *a: os.path.join(jd, *a)                       # noqa: E731
    spec, cfg, facts = p("spec.md"), p("job_config.json"), p("measured_facts.json")
    summary = p("out", "audit_summary.json")
    layout = find_layout(jd, layout_arg)
    st["layout"] = layout
    st["inputs"] = [os.path.basename(x) for x in spec_docs(jd)]

    def stage(name, nxt, **extra):
        st.update(stage=name, next=nxt, **extra)
        return st

    if not os.path.isdir(jd):
        return stage("missing", f"audit_tool.py new --job {st['job']}")
    if os.path.exists(p("spec.draft.md")) and mtime(p("spec.draft.md")) > mtime(spec):
        st["pending_redraft"] = "spec.draft.md is newer than spec.md - merge it by hand"
    if not os.path.exists(spec):
        if not os.path.isdir(p("inputs")) and glob.glob(p("**", "*.py"), recursive=True):
            return stage("legacy", "none - audited with a one-off script before the "
                         "engine existed; keep as an archive, do not convert")
        if not st["inputs"]:
            return stage("needs_inputs",
                         "copy game specs + data spec (.pdf/.docx/.doc) into inputs/")
        if not os.path.exists(facts) and not layout:
            return stage("needs_layout",
                         "put the *LAYOUT*.TXT in inputs/ or pass --layout")
        return stage("needs_draft", f"audit_tool.py draft --job {st['job']}")

    md = open(spec, encoding="utf-8").read()
    open_items = unticked_review_items(md)
    if open_items:
        return stage("needs_review", "a person resolves and ticks every review item in spec.md",
                     review_items=open_items)
    try:
        want = json.loads(json.dumps(parse(md)))     # as build_config writes it
    except (SpecError, KeyError, ValueError) as e:
        return stage("spec_unreadable", "fix the anchored tables in spec.md", error=str(e))
    have = json.load(open(cfg)) if os.path.exists(cfg) else None
    if have != want:
        return stage("needs_build", f"audit_tool.py build --job {st['job']}",
                     reason="job_config.json missing" if have is None
                     else "job_config.json differs from spec.md")
    if not os.path.exists(summary) or mtime(summary) < mtime(cfg):
        if not layout:
            return stage("needs_layout", "put the *LAYOUT*.TXT in inputs/ or pass --layout")
        return stage("ready_to_audit", f"audit_tool.py run --job {st['job']}")
    s = json.load(open(summary))
    return stage("audited", "review out/audit_report.md and sign off",
                 all_passed=s["all_passed"], exceptions=s["exceptions"])


# ------------------------------------------------------------------ #
#  Commands                                                           #
# ------------------------------------------------------------------ #

def need_layout(jd, a):
    lay = find_layout(jd, a.layout)
    if not lay:
        log("No layout file: pass --layout, put *LAYOUT*.TXT in "
            f"{os.path.join(jd, 'inputs')}, or set AUDIT_LAYOUTS_DIR.")
    return lay


def cmd_status(jd, a):
    st = job_status(jd, a.layout)
    for k, v in st.items():
        if k == "review_items":
            log(f"review_items ({len(v)}):")
            for i in v:
                log(f"   {i}")
        else:
            log(f"{k:15}: {v}")
    code = NEEDS_REVIEW if st["stage"] == "needs_review" else \
        EXCEPTIONS if st["stage"] == "audited" and not st["all_passed"] else OK
    return code, st


def cmd_new(jd, a):
    os.makedirs(os.path.join(jd, "inputs"), exist_ok=True)
    os.makedirs(os.path.join(jd, "out"), exist_ok=True)
    log(f"Created {jd}\\inputs and out. Copy the game specs, the data spec "
        "and the layout file into inputs/.")
    return OK, {"path": jd}


def cmd_probe(jd, a):
    lay = need_layout(jd, a)
    if not lay:
        return FAILED, {}
    rc = engine("probe_layout.py", lay, "--out", os.path.join(jd, "measured_facts.json"))
    return (OK if rc == 0 else FAILED), {"layout": lay}


def cmd_draft(jd, a):
    args = ["--job", jd]
    lay = find_layout(jd, a.layout)
    if lay:
        args += ["--layout", lay]
    rc = engine("draft_spec.py", *args)
    st = job_status(jd, a.layout)
    return (FAILED if rc else NEEDS_REVIEW if st["stage"] == "needs_review" else OK), st


def cmd_build(jd, a):
    rc = engine("build_config.py", "--job", jd)
    if rc == 0:
        return OK, {"config": os.path.join(jd, "job_config.json")}
    st = job_status(jd)
    return (NEEDS_REVIEW if st["stage"] == "needs_review" else FAILED), st


def cmd_verify(jd, a):
    lay = need_layout(jd, a)
    if not lay:
        return FAILED, {}
    rc = engine("probe_layout.py", lay, "--config", os.path.join(jd, "job_config.json"))
    return (OK if rc == 0 else FAILED), {"layout": lay, "settings_match_data": rc == 0}


def cmd_audit(jd, a):
    lay = need_layout(jd, a)
    if not lay:
        return FAILED, {}
    out = os.path.abspath(a.out) if a.out else os.path.join(jd, "out")
    rc = engine("audit_engine.py", "--config", os.path.join(jd, "job_config.json"),
                "--layout", lay, "--out", out)
    if rc:
        return FAILED, {"layout": lay}
    s = json.load(open(os.path.join(out, "audit_summary.json")))
    s["out"] = out
    return (OK if s["all_passed"] else EXCEPTIONS), s


def cmd_run(jd, a):
    code, res = cmd_build(jd, a)
    if code != OK:
        return code, dict(res, stopped_at="build")
    code, res = cmd_verify(jd, a)
    if code != OK and not a.force_audit:
        log("\nThe settings disagree with the layout file. If every disagreement is "
            "a LAYOUT review item already ticked in spec.md, that is expected (the "
            "audit reports it as a layout-file error): rerun with --force-audit.")
        return code, dict(res, stopped_at="verify")
    return cmd_audit(jd, a)


def cmd_test(_jd, a):
    args = ["--layouts", a.layouts] if a.layouts else ["--unit-only"]
    cmd = [sys.executable, os.path.join(ROOT, "tests", "run_regression.py"), *args]
    log(f"$ {' '.join(cmd[1:])}")
    rc = subprocess.run(cmd, cwd=ROOT, stdout=LOG, stderr=LOG).returncode
    return (OK if rc == 0 else FAILED), {"passed": rc == 0}


COMMANDS = {"status": cmd_status, "new": cmd_new, "probe": cmd_probe,
            "draft": cmd_draft, "build": cmd_build, "verify": cmd_verify,
            "audit": cmd_audit, "run": cmd_run, "test": cmd_test}


def main():
    global LOG
    ap = argparse.ArgumentParser(description="Lottery layout audit - module entry point")
    ap.add_argument("command", choices=COMMANDS)
    ap.add_argument("--job", help="folder name under jobs/, or a path")
    ap.add_argument("--layout", help="layout file (default: auto-discovered)")
    ap.add_argument("--out", help="audit output folder (default <job>/out)")
    ap.add_argument("--layouts", help="test: folder of layout files for golden runs")
    ap.add_argument("--force-audit", action="store_true",
                    help="run: audit even when verify reports disagreements")
    ap.add_argument("--json", action="store_true",
                    help="progress to stderr, one JSON result object to stdout")
    a = ap.parse_args()

    if a.json:
        LOG = sys.stderr
    if a.command not in ("test",) and not a.job:
        ap.error("--job is required")
    jd = job_dir(a.job) if a.job else None
    if jd and a.command not in ("new", "status") and not os.path.isdir(jd):
        log(f"No job folder {jd} - run: audit_tool.py new --job {a.job}")
        code, res = FAILED, {}
    else:
        code, res = COMMANDS[a.command](jd, a)

    if a.json:
        res = {"command": a.command, "job": a.job, "exit_code": code, **res}
        print(json.dumps(res, indent=1, default=str))
    sys.exit(code)


if __name__ == "__main__":
    main()
