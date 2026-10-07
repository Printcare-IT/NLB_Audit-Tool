# -*- coding: utf-8 -*-
"""
Module entry-point tests (audit_tool.py).

The platform drives the tool only through audit_tool.py, its exit codes and
its --json result, so those are a contract.  These tests run the real command
on a synthetic job folder and check the stage it reports, the gate it stops
at, and the exit code for a clean and a defective layout file.
"""

import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path[:0] = [HERE, os.path.join(ROOT, "engine")]
import fixtures as F                                          # noqa: E402
from spec_md import render                                    # noqa: E402

TOOL = os.path.join(ROOT, "audit_tool.py")
A = "0901"


def tool(*args):
    r = subprocess.run([sys.executable, TOOL, *args, "--json"],
                       capture_output=True, text=True, cwd=ROOT)
    return r.returncode, json.loads(r.stdout)


class ModuleEntryPoint(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.job = os.path.join(self.tmp, "TEST.JOB")
        self.cfg, self.tix = F.make_job()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def make(self, review=(), tickets=None):
        tool("new", "--job", self.job)
        with open(os.path.join(self.job, "spec.md"), "w", encoding="utf-8") as f:
            f.write(render(self.cfg, list(review), {}, {"generated": "t"}))
        F.write_layout(os.path.join(self.job, "inputs", "0901-0902-LAYOUT.TXT"),
                       self.cfg, tickets or self.tix)

    def test_status_of_a_missing_job(self):
        code, res = tool("status", "--job", self.job)
        self.assertEqual((code, res["stage"]), (0, "missing"))

    def test_run_stops_at_the_review_gate(self):
        self.make(review=[{"id": "R1", "game": A, "severity": "check",
                           "text": "worth a look"}])
        code, res = tool("status", "--job", self.job)
        self.assertEqual((code, res["stage"]), (3, "needs_review"))
        self.assertEqual(len(res["review_items"]), 1)
        code, res = tool("run", "--job", self.job)
        self.assertEqual((code, res["stopped_at"]), (3, "build"))
        self.assertFalse(os.path.exists(os.path.join(self.job, "job_config.json")))

    def test_clean_job_runs_to_audited(self):
        self.make()
        self.assertEqual(tool("status", "--job", self.job)[1]["stage"], "needs_build")
        code, res = tool("run", "--job", self.job)
        self.assertEqual(code, 0, res)
        self.assertTrue(res["all_passed"])
        self.assertTrue(os.path.exists(os.path.join(res["out"], "audit_report.md")))
        code, st = tool("status", "--job", self.job)
        self.assertEqual((code, st["stage"], st["all_passed"]), (0, "audited", True))

    def test_defective_layout_exits_with_exceptions(self):
        tix = {k: [dict(t) if t else t for t in v] for k, v in self.tix.items()}
        loser = random.Random(1).choice(
            [i for i, t in enumerate(tix[A]) if t and t["amount"] is None])
        tix[A][loser]["p1"] = "ZZ"                    # not a play symbol: check 1
        self.make(tickets=tix)
        code, res = tool("run", "--job", self.job, "--force-audit")
        self.assertEqual(code, 2, res)
        game = next(g for g in res["games"] if g["key"] == A)
        self.assertEqual([c["index"] for c in game["checks"] if not c["passed"]], [1])
        self.assertEqual(tool("status", "--job", self.job)[0], 2)


if __name__ == "__main__":
    unittest.main()
