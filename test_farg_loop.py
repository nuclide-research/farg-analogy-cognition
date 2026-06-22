#!/usr/bin/env python3
"""
test_farg_loop.py - the adversarial verification verdict, frozen as regression tests.

The 5-agent verification panel (see VERIFICATION.md) confirmed the prototype is
genuine and caught one real overclaim. Rather than let those findings live only in a
markdown file, every load-bearing claim and every ablation is encoded here as an
executable test. Run:  python3 -m unittest test_farg_loop -v   (stdlib only).

Grouped by what they protect:
  TestNotRigged      - no answer is hardcoded in the decision path
  TestEmergence      - the answer comes from the slip dynamics, symmetrically
  TestAblations      - the panel's ablations: remove a part, prove it mattered
  TestFreezeBar      - aspiration-coupled cooling recovers the elegant answer
  TestDeterminism    - fixed seeds reproduce, even across PYTHONHASHSEED
  TestGiveUp         - the snag-loop give-up detector stops a dead executor
  TestParsing        - the LLM reply parser validates and rejects honestly
  TestControlLaw     - the temperature law matches its stated formula
"""
import os
import sys
import subprocess
import unittest
from collections import Counter

import farg_loop as F

XYZ = lambda: F.Problem("abc", "abd", "xyz")
ANSWER_STRINGS = ("wyz", "xyy", "yyz")          # the OUTPUTS, not inputs (abc/abd are inputs)


class TestNotRigged(unittest.TestCase):
    """The decision-path functions contain no answer-output literal. We inspect the
    compiled code objects directly (co_consts), so this cannot be fooled by where the
    strings sit in the source. Docstrings are excluded; we only forbid the three
    ANSWER strings, never the inputs abc/abd which legitimately appear in docstrings."""

    DECISION_FUNCS = [
        F.solve, F.coherence_of, F.rule_support, F.apply_rule, F.infer_rule,
        F._index, F.softmax_choice, F.Slipnet.slip, F.ScriptedProposer.propose,
    ]

    def _consts(self, fn):
        out = []
        code = fn.__code__
        stack = list(code.co_consts)
        while stack:
            c = stack.pop()
            if isinstance(c, str):
                out.append(c)
            elif hasattr(c, "co_consts"):       # nested code object
                stack.extend(c.co_consts)
        return out

    def test_no_answer_literal_in_decision_path(self):
        for fn in self.DECISION_FUNCS:
            consts = self._consts(fn)
            # drop the function's own docstring (consts[0] if it is the docstring)
            doc = fn.__doc__
            consts = [c for c in consts if c != doc]
            joined = " ".join(consts).lower()
            for ans in ANSWER_STRINGS:
                self.assertNotIn(
                    ans, joined,
                    f"answer literal {ans!r} found in {fn.__qualname__} code consts",
                )

    def test_rule_support_signature_cannot_see_the_answer(self):
        # rule_support is the discriminating coherence term; it takes only (rule, base)
        import inspect
        params = list(inspect.signature(F.rule_support).parameters)
        self.assertEqual(params, ["rule", "base"])


class TestEmergence(unittest.TestCase):
    def test_answer_emerges_from_opposites(self):
        # the reframe rule is literally OPPOSITES applied to the base rule's parts
        base = XYZ().base_rule                         # (rightmost, successor)
        self.assertEqual(F.OPPOSITES[base.pos], "leftmost")
        self.assertEqual(F.OPPOSITES[base.op], "predecessor")
        reframe = F.Rule("leftmost", "predecessor")
        res, _ = F.apply_rule(reframe, "xyz")
        self.assertEqual(res, "wyz")

    def test_mirror_case_is_symmetric(self):
        # The mirror of xyz. Base example bcd->acd reads as (leftmost, predecessor).
        # On target abc the leftmost 'a' has no predecessor: the LEFT wall, the mirror
        # of xyz's right wall. It must double-slip to (rightmost, successor) and yield
        # abd. Same machinery, mirrored, no special-casing of xyz.
        prob = F.Problem("bcd", "acd", "abc")          # index0 b->a: leftmost, predecessor
        self.assertEqual(str(prob.base_rule), "(leftmost, predecessor)")
        t = Counter()
        for s in range(120):
            r, _, _ = F.solve(prob, seed=s, freeze_bar=0.99)
            t[r] += 1
        # the elegant double-slip yields abd; it should be the plurality at a high bar
        self.assertEqual(max(t, key=t.get), "abd",
                         f"mirror case did not converge on abd: {dict(t)}")

    def test_clean_case_never_snags(self):
        prob = F.Problem("abc", "abd", "ijk")
        r, rule, trace = F.solve(prob, seed=1)
        self.assertEqual(r, "ijl")
        self.assertFalse(any(t[6].startswith("SNAG") for t in trace))


class TestAblations(unittest.TestCase):
    """The panel's three ablations, as tests. Each removes one part and proves the
    answer depended on it."""

    class _BaseOnly:
        """A proposer that offers only the base rule: no slip path at all."""
        def propose(self, prob, net):
            return [prob.base_rule]

    def test_no_slip_path_fails(self):
        # base rule always snags on xyz; with no slip candidate ever, it must give up
        for s in range(20):
            r, _, _ = F.solve(XYZ(), proposer=self._BaseOnly(), seed=s)
            self.assertIsNone(r, "with no slip path the loop must not produce an answer")

    def test_reheat_off_still_solves(self):
        # the panel's MEDIUM finding: the reframe is gated by `opposite`, not the heat.
        # turn the re-heat into a no-op; the loop must still solve.
        orig = F.Temperature.snag
        F.Temperature.snag = lambda self: None
        try:
            solved = sum(F.solve(XYZ(), seed=s)[0] is not None for s in range(60))
            self.assertEqual(solved, 60, "reheat-off should still solve every run")
        finally:
            F.Temperature.snag = orig

    def test_opposite_blocked_fails(self):
        # block the slip (opposite never licenses a reframe); the scaffold can only
        # ever offer the base rule, which snags -> no answer.
        orig = F.Slipnet.slip
        F.Slipnet.slip = lambda self, concept: concept     # identity: never slips
        try:
            anysolved = any(F.solve(XYZ(), seed=s)[0] == "wyz" for s in range(60))
            self.assertFalse(anysolved, "with slip blocked, wyz must never appear")
        finally:
            F.Slipnet.slip = orig


class TestFreezeBar(unittest.TestCase):
    def _wyz_count(self, bar, n=300):
        return sum(F.solve(XYZ(), seed=1000 + s, freeze_bar=bar)[0] == "wyz"
                   for s in range(n))

    def test_raising_bar_recovers_wyz(self):
        low = self._wyz_count(0.90)
        high = self._wyz_count(0.99)
        self.assertGreater(high, low, "raising the freeze bar should increase wyz")
        self.assertGreater(high, 280, f"bar 0.99 should be near-total wyz, got {high}/300")

    def test_default_bar_unchanged_canonical(self):
        # lock the canonical deterministic distribution; guards against drift
        t = Counter()
        for s in range(300):
            t[F.solve(XYZ(), seed=1000 + s)[0]] += 1
        self.assertEqual(dict(t), {"wyz": 143, "xyy": 83, "yyz": 74})


class TestDeterminism(unittest.TestCase):
    def test_same_seed_same_answer(self):
        for s in (3, 11, 42, 99):
            a = F.solve(XYZ(), seed=s)[0]
            b = F.solve(XYZ(), seed=s)[0]
            self.assertEqual(a, b)

    def test_distribution_independent_of_pythonhashseed(self):
        # the bug we fixed: set-iteration order under hash randomization made the
        # "fixed seed" distribution drift. Run the demo under two hash seeds; identical.
        snippet = (
            "import farg_loop as F;"
            "from collections import Counter;"
            "t=Counter();"
            "[t.update([F.solve(F.Problem('abc','abd','xyz'),seed=1000+s)[0]]) for s in range(300)];"
            "print(sorted(t.items()))"
        )
        env0 = {**os.environ, "PYTHONHASHSEED": "0"}
        env1 = {**os.environ, "PYTHONHASHSEED": "12345"}
        here = os.path.dirname(os.path.abspath(__file__))
        out0 = subprocess.run([sys.executable, "-c", snippet], cwd=here, env=env0,
                              capture_output=True, text=True).stdout
        out1 = subprocess.run([sys.executable, "-c", snippet], cwd=here, env=env1,
                              capture_output=True, text=True).stdout
        self.assertEqual(out0, out1)
        self.assertIn("143", out0)


class TestGiveUp(unittest.TestCase):
    def test_dead_executor_gives_up(self):
        def dead(prompt):
            raise RuntimeError("no executor")
        prop = F.LLMProposer(dead, scaffold=False)
        r, rule, trace = F.solve(XYZ(), proposer=prop, seed=7, max_cycles=40, max_snags=6)
        self.assertIsNone(r)
        self.assertLessEqual(len(trace), 8, "should give up early, not spin to max_cycles")
        self.assertTrue(trace[-1][6].startswith("GIVE-UP"))

    def test_healthy_run_never_gives_up(self):
        for s in range(60):
            r, _, trace = F.solve(XYZ(), seed=s)
            self.assertFalse(any(t[6].startswith("GIVE-UP") for t in trace))


class TestParsing(unittest.TestCase):
    def test_parses_plain_array(self):
        rules = F._parse_rules('[{"pos":"leftmost","op":"predecessor"}]')
        self.assertEqual(rules, [F.Rule("leftmost", "predecessor")])

    def test_parses_fenced_json(self):
        raw = '```json\n[{"pos":"rightmost","op":"successor"}]\n```'
        self.assertEqual(F._parse_rules(raw), [F.Rule("rightmost", "successor")])

    def test_drops_out_of_vocabulary(self):
        raw = '[{"pos":"banana","op":"successor"},{"pos":"leftmost","op":"predecessor"}]'
        self.assertEqual(F._parse_rules(raw), [F.Rule("leftmost", "predecessor")])

    def test_garbage_returns_empty(self):
        self.assertEqual(F._parse_rules("the answer is wyz, trust me"), [])
        self.assertEqual(F._parse_rules(""), [])

    def test_dedups(self):
        raw = '[{"pos":"leftmost","op":"successor"},{"pos":"leftmost","op":"successor"}]'
        self.assertEqual(len(F._parse_rules(raw)), 1)


class TestControlLaw(unittest.TestCase):
    def test_temperature_matches_formula(self):
        temp = F.Temperature()
        for c in (0.0, 0.3, 0.5, 0.93, 1.0):
            t = F.Temperature()
            got = t.update(c)
            want = t.T_floor + (t.T_max - t.T_floor) * (1.0 - c) ** t.gamma
            self.assertAlmostEqual(got, want, places=12)

    def test_floor_never_zero(self):
        t = F.Temperature()
        self.assertGreater(t.update(1.0), 0.0, "temperature floor must stay above 0")

    def test_tau_monotonic_in_temperature(self):
        t = F.Temperature()
        t.value = 0.1
        cold = t.tau()
        t.value = 0.9
        hot = t.tau()
        self.assertGreater(hot, cold)

    def test_wall_primitives(self):
        self.assertIsNone(F.successor("z"))
        self.assertIsNone(F.predecessor("a"))
        self.assertEqual(F.successor("a"), "b")
        self.assertEqual(F.predecessor("z"), "y")


if __name__ == "__main__":
    unittest.main(verbosity=2)
