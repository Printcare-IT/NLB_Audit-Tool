# -*- coding: utf-8 -*-
"""
Audit-check regression tests.

Each test starts from a clean synthetic job that passes every check, injects
ONE defect, and asserts that exactly the expected checks fail - no more, no
fewer.  Where a defect can only be placed at certain tickets without side
effects (e.g. without accidentally creating a consecutive-pattern repeat),
the test tries candidate positions until one is clean; the defect itself is
always genuine, so a check that stops firing still fails the test.

Check numbers: 1 play positions · 2 prize box · 3 serial · 4 VIRN/barcode ·
5 agent codes · 6 prize structure · 7 GLEPS · 8 packing · 9 group promises ·
10 non-GLEPS · 11 consecutive pattern · 12 rotation · 13 winner per block ·
14 value run · 15 VIRN independence
"""

import copy
import os
import random
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, "..", "engine")]
import fixtures as F                                          # noqa: E402
from audit_engine import Job, load_layout, run_all_checks     # noqa: E402

A, B = "0901", "0902"


def audit(cfg, tickets):
    path = os.path.join(tempfile.mkdtemp(), "layout.TXT")
    F.write_layout(path, cfg, tickets)
    job = Job(cfg)
    games, info = load_layout(job, path)
    return {k: {r.index for r in run_all_checks(job, g, info) if not r.passed}
            for k, g in games.items()}


def gcfg(cfg, key):
    return next(g for g in cfg["games"] if g["key"] == key)


def winners(tix, amount=None):
    return [i for i, t in enumerate(tix) if t and t["amount"] is not None
            and (amount is None or t["amount"] == amount)]


def losers(tix):
    return [i for i, t in enumerate(tix) if t and t["amount"] is None]


def swap_content(x, y):
    for k in ("amount", "sys", "print", "agent", "p1", "p2"):
        x[k], y[k] = y[k], x[k]


class AuditChecks(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cfg, cls.base = F.make_job(seed=7)

    def fresh(self):
        return copy.deepcopy(self.cfg), F.clone(self.base)

    def expect(self, mutate, game, expected, attempts=80):
        """Apply `mutate(cfg, tickets, rng)` to fresh copies until the result
        is exactly `expected` failed checks in `game` and none elsewhere."""
        last = None
        for a in range(attempts):
            cfg, tix = self.fresh()
            if mutate(cfg, tix, random.Random(a)) is False:
                continue
            got = audit(cfg, tix)
            want = {k: set() for k in got}
            want[game] = set(expected)
            if got == want:
                return
            last = got
        self.fail(f"no placement gave exactly {sorted(expected)} in {game}; last: {last}")

    # ---- baseline -----------------------------------------------------
    def test_00_clean_job_passes_every_check(self):
        cfg, tix = self.fresh()
        self.assertEqual(audit(cfg, tix), {A: set(), B: set()})

    def test_00_clean_job_contains_long_loser_runs(self):
        """Guards the check-14 fix: runs of LOSERS must never count as a
        same-prize-value run.  The clean data has them and still passes."""
        best = cur = 0
        for t in self.base[A]:
            cur = cur + 1 if t["amount"] is None else 0
            best = max(best, cur)
        self.assertGreaterEqual(best, 4)

    # ---- 1 play positions ------------------------------------------------
    def test_01_invalid_play_symbol(self):
        def m(cfg, t, r):
            t[A][r.choice(losers(t[A]))]["p1"] = "ZZ"
        self.expect(m, A, {1})

    def test_01_loser_showing_a_matching_pair(self):
        def m(cfg, t, r):
            i = r.choice(losers(t[A]))
            s = r.choice(list(gcfg(cfg, A)["play_symbols"]))
            t[A][i]["p1"] = t[A][i]["p2"] = s
        self.expect(m, A, {1})

    def test_01_two_special_symbols_forbidden(self):
        def m(cfg, t, r):
            i = r.choice(losers(t[B]))
            t[B][i]["p1"], t[B][i]["p2"] = "KB", "LB"
        self.expect(m, B, {1})

    def test_01_special_only_game_pair_must_not_win(self):
        """0346-style rule: a winner showing a matching pair and no special
        symbol is wrong."""
        def m(cfg, t, r):
            i = r.choice(winners(t[B]))
            t[B][i]["p1"] = t[B][i]["p2"] = r.choice(["NB", "PB", "QB", "UB"])
        self.expect(m, B, {1})

    # ---- 2 prize box ---------------------------------------------------
    def test_02_wrong_print_code_on_winner(self):
        def m(cfg, t, r):
            t[A][r.choice(winners(t[A], 500))]["print"] = "dd"
        self.expect(m, A, {2})

    # ---- 3 serial numbers ------------------------------------------------
    def test_03_missing_ticket(self):
        def m(cfg, t, r):
            t[A][r.choice(losers(t[A]))] = None
        self.expect(m, A, {3, 6})

    def test_03_duplicate_serial(self):
        def m(cfg, t, r):
            i = r.choice([i for i in losers(t[A]) if i > 0])
            t[A][i]["serial"] = t[A][i - 1]["serial"]
        self.expect(m, A, {3, 6})

    def test_03_malformed_serial(self):
        def m(cfg, t, r):
            t[A][r.choice(losers(t[A]))]["serial"] = "X" * 15
        self.expect(m, A, {3, 6})

    # ---- 4 VIRN and barcode ------------------------------------------------
    def test_04_wrong_parity_digit(self):
        def m(cfg, t, r):
            x = t[A][r.choice(losers(t[A]))]
            x["bar"] = x["bar"][:-1] + str((int(x["bar"][-1]) + 1) % 10)
        self.expect(m, A, {4})

    def test_04_virn_out_of_range(self):
        def m(cfg, t, r):
            x = t[A][r.choice(losers(t[A]))]
            x["virn"] = x["virn"][:8] + "1999999"
            x["bar"] = x["virn"] + F.parity(x["virn"])
        self.expect(m, A, {4})

    def test_04_duplicate_virn(self):
        def m(cfg, t, r):
            i, j = r.sample(losers(t[A]), 2)
            t[A][j]["virn"], t[A][j]["bar"] = t[A][i]["virn"], t[A][i]["bar"]
        self.expect(m, A, {4})

    # ---- 5 agent codes ---------------------------------------------------
    def test_05_low_winner_without_its_letter(self):
        def m(cfg, t, r):
            x = t[A][r.choice(winners(t[A], 50))]
            x["agent"] = [("W" if c == "T" else c) if c else "" for c in x["agent"]]
            if len({c for c in x["agent"] if c}) != 3:
                return False
        self.expect(m, A, {5})

    def test_05_loser_carrying_the_low_tier_letter(self):
        def m(cfg, t, r):
            x = t[A][r.choice(losers(t[A]))]
            k = next(i for i, c in enumerate(x["agent"]) if c)
            x["agent"][k] = "T"
        self.expect(m, A, {5})

    def test_05_wrong_number_of_letters(self):
        def m(cfg, t, r):
            x = t[A][r.choice(losers(t[A]))]
            x["agent"][next(i for i, c in enumerate(x["agent"]) if not c)] = "Z" \
                if "Z" not in x["agent"] else "R"
        self.expect(m, A, {5})

    # ---- 6 prize structure -----------------------------------------------
    def test_06_prize_count_differs_from_settings(self):
        def m(cfg, t, r):
            gcfg(cfg, A)["loss"]["count"] += 1        # settings, not data
        self.expect(m, A, {6})

    # ---- 7 GLEPS -----------------------------------------------------------
    def test_07_gleps_moved_between_books(self):
        def m(cfg, t, r):
            i = r.choice([i for i in winners(t[A], 50) if i // F.BOOK == 3])
            j = r.choice([j for j in losers(t[A]) if j // F.BOOK == 4])
            swap_content(t[A][i], t[A][j])
        self.expect(m, A, {7})

    # ---- 8 packing ---------------------------------------------------------
    def test_08_top_prize_moved_to_another_slot(self):
        def m(cfg, t, r):
            i = winners(t[A], 1000)[0]                  # slot 1
            j = r.choice([j for j in losers(t[A])
                          if (j // F.BOOK) in (5, 6, 8, 9)])   # slot 2, not its top-prize book
            swap_content(t[A][i], t[A][j])
        self.expect(m, A, {8})

    # ---- 9 group promises --------------------------------------------------
    def test_09_book_with_two_rs500(self):
        def m(cfg, t, r):
            i = next(i for i in winners(t[A], 500) if i // F.BOOK == 2)   # keeps its Rs.1,000
            j = r.choice([j for j in losers(t[A]) if j // F.BOOK == 0])
            swap_content(t[A][i], t[A][j])
        self.expect(m, A, {9})

    # ---- 10 non-GLEPS ------------------------------------------------------
    def test_10_book_without_a_non_gleps_prize(self):
        """Removing book 1's only non-GLEPS prize necessarily also breaks its
        Rs.500 promise and the slot totals."""
        def m(cfg, t, r):
            i = next(i for i in winners(t[A], 500) if i // F.BOOK == 0)
            j = r.choice([j for j in losers(t[A]) if j // F.BOOK == 6])
            swap_content(t[A][i], t[A][j])
        self.expect(m, A, {8, 9, 10})

    # ---- 11 / 12 consecutive tickets --------------------------------------
    def test_11_consecutive_same_play_pattern(self):
        def m(cfg, t, r):
            i = r.choice([i for i in losers(t[A]) if i + 1 < len(t[A])
                          and t[A][i + 1] and t[A][i + 1]["amount"] is None])
            t[A][i + 1]["p1"], t[A][i + 1]["p2"] = t[A][i]["p1"], t[A][i]["p2"]
        self.expect(m, A, {11, 12})

    def test_12_same_symbols_rotated(self):
        def m(cfg, t, r):
            i = r.choice([i for i in losers(t[A]) if i + 1 < len(t[A])
                          and t[A][i + 1] and t[A][i + 1]["amount"] is None])
            t[A][i + 1]["p1"], t[A][i + 1]["p2"] = t[A][i]["p2"], t[A][i]["p1"]
        self.expect(m, A, {12})

    # ---- 13 winner in every block of five ---------------------------------
    def test_13_block_of_five_without_a_winner(self):
        def m(cfg, t, r):
            b = r.randrange(F.TICKETS // F.BOOK)
            base = b * F.BOOK
            blocks = [[i for i in range(base + s, base + s + 5) if t[A][i]["amount"]]
                      for s in range(0, F.BOOK, 5)]
            lone = [bl[0] for bl in blocks if len(bl) == 1]
            if not lone:
                return False
            i = r.choice(lone)
            j = r.choice([j for j in range(base + 1, base + F.BOOK - 1)
                          if t[A][j]["amount"] is None and (j - base) // 5 != (i - base) // 5])
            swap_content(t[A][i], t[A][j])
        self.expect(m, A, {13})

    # ---- 14 prize value run ------------------------------------------------
    def test_14_four_consecutive_winners_same_value(self):
        def m(cfg, t, r):
            g = gcfg(cfg, A)
            base = 2 * F.BOOK                                   # book 3 has 6 winners
            plan = {3: 50, 4: 50, 5: 50, 6: 50, 11: 500, 16: 1000}
            for k in range(F.BOOK):
                F.set_prize(t[A][base + k], g, plan.get(k))
            F.assign_symbols(t[A], g, r)
        self.expect(m, A, {14})

    # ---- 15 VIRN independence ---------------------------------------------
    def test_15_virn_correlated_with_winning(self):
        def m(cfg, t, r):
            virns = sorted(x["virn"] for x in t[A])
            order = winners(t[A]) + losers(t[A])        # winners get the lowest VIRNs
            for v, i in zip(virns, order):
                t[A][i]["virn"], t[A][i]["bar"] = v, v + F.parity(v)
        self.expect(m, A, {15}, attempts=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
