#!/usr/bin/env python3
"""
test_domain_music.py - regression tests for the SECOND domain (diatonic melody).

These mirror the letter suite's verification verdict in the new surface, and add the
load-bearing cross-domain checks: that the music domain REUSES the imported control law
(it does not re-implement it) and that the scripted distributions match the letter
domain to the count (the loop is surface-blind by construction). Stdlib unittest, no
network, no model.
"""
import io
import unittest
from collections import Counter
from contextlib import redirect_stdout

import farg_loop as F
import domain_music as M


def _all_consts(fn):
    """Flatten co_consts of a function and any nested code objects to a set of reprs,
    so a forbidden answer literal cannot hide in a comprehension/closure."""
    import types
    out, stack = set(), [fn.__code__]
    while stack:
        code = stack.pop()
        for c in code.co_consts:
            if isinstance(c, types.CodeType):
                stack.append(c)
            else:
                out.add(repr(c))
    return out


class TestNotRigged(unittest.TestCase):
    """The answer is never a literal on the decision path; it must be computed."""

    DECISION_FNS = [M.apply_rule_music, M.infer_rule_music,
                    M.rule_support_music, M.coherence_music]

    def test_no_answer_string_in_decision_path(self):
        for fn in self.DECISION_FNS:
            consts = _all_consts(fn)
            for forbidden in ("'F A B'", "'FAB'", "'F'", "'A B'"):
                self.assertNotIn(forbidden, consts,
                                 f"{fn.__name__} contains answer literal {forbidden}")

    def test_no_answer_degrees_in_decision_path(self):
        # the elegant answer is degrees (3,5,6); it must never appear as a literal tuple
        for fn in self.DECISION_FNS:
            self.assertNotIn("(3, 5, 6)", _all_consts(fn),
                             f"{fn.__name__} hardcodes the answer degrees")

    def test_rule_support_signature_is_generic(self):
        # critic must score a rule against the BASE rule, not against a stored answer
        import inspect
        params = list(inspect.signature(M.rule_support_music).parameters)
        self.assertEqual(params, ["rule", "base"])


class TestEmergence(unittest.TestCase):
    """The reframe emerges from opposite-gated slips, not from a special case."""

    def test_plurality_is_the_double_slip(self):
        tally = Counter()
        for s in range(300):
            res, rule, _ = F.solve(M.MusicProblem("C D E", "C D F", "G A B"), seed=1000 + s)
            tally[(res, str(rule))] += 1
        top, _ = tally.most_common(1)[0]
        self.assertEqual(top, ("F A B", "(leftmost, down)"),
                         "elegant double-slip F A B should be the plurality")

    def test_answer_comes_from_opposite_concept(self):
        # block the opposite slip (identity) -> the reframe can never form -> give up
        orig = F.Slipnet.slip
        F.Slipnet.slip = lambda self, c: c            # opposite never fires
        try:
            res, _, _ = F.solve(M.MusicProblem("C D E", "C D F", "G A B"), seed=7)
        finally:
            F.Slipnet.slip = orig
        self.assertIsNone(res, "without the opposite-gated slip there is no reframe")

    def test_mirror_case_is_symmetric(self):
        # an example that LOWERS the leftmost note, with a target on the FLOOR (C), must
        # double-slip the OTHER way: (leftmost, down) walls -> (rightmost, up).
        tally = Counter()
        for s in range(300):
            res, rule, _ = F.solve(M.MusicProblem("D E F", "C E F", "C E G"), seed=1000 + s)
            tally[(res, str(rule))] += 1
        top, _ = tally.most_common(1)[0]
        self.assertEqual(top, ("C E A", "(rightmost, up)"),
                         "mirror case should resolve symmetrically to C E A")

    def test_clean_case_never_snags(self):
        # target whose rightmost note is not the ceiling: base rule applies cleanly
        _, _, trace = F.solve(M.MusicProblem("C D E", "C D F", "C E G"), seed=3)
        self.assertFalse(any("SNAG" in t[6] for t in trace),
                         "a non-ceiling target must not snag")


class TestWall(unittest.TestCase):
    """The register boundary is the snag; it is a real wall, not a flag."""

    def test_ceiling_walls_the_base_rule(self):
        prob = M.MusicProblem("C D E", "C D F", "G A B")
        result, snag = M.apply_rule_music(prob.base_rule, prob.target_degs)
        self.assertIsNone(result)
        self.assertIn("register", snag)

    def test_floor_walls_down_at_C(self):
        # down at C leaves the register
        result, snag = M.apply_rule_music(F.Rule("leftmost", "down"), M.degs("C E G"))
        self.assertIsNone(result)

    def test_no_wall_in_the_middle_of_the_scale(self):
        result, snag = M.apply_rule_music(F.Rule("rightmost", "up"), M.degs("C E G"))
        self.assertEqual(result, M.degs("C E A"))
        self.assertIsNone(snag)


class TestFreezeBar(unittest.TestCase):
    """Aspiration-coupled cooling steers the answer, same as the letter domain."""

    def test_default_bar_distribution_locks(self):
        tally = Counter()
        for s in range(300):
            res, _, _ = F.solve(M.MusicProblem("C D E", "C D F", "G A B"),
                                seed=1000 + s, freeze_bar=0.90)
            tally[res] += 1
        # the canonical 143/83/74 split, identical to the letter domain by construction
        self.assertEqual(tally["F A B"], 143)
        self.assertEqual(tally["G A A"], 83)
        self.assertEqual(tally["A A B"], 74)

    def test_raised_bar_recovers_the_reframe(self):
        tally = Counter()
        for s in range(300):
            res, _, _ = F.solve(M.MusicProblem("C D E", "C D F", "G A B"),
                                seed=1000 + s, freeze_bar=0.99)
            tally[res] += 1
        self.assertGreater(tally["F A B"], 280,
                           "raising the bar should recover the elegant answer for nearly all seeds")


class TestReusesControlLaw(unittest.TestCase):
    """The whole point: the music domain DRIVES the imported control law, it does not
    re-implement it. If these identities break, the generalization claim is void."""

    def test_solve_is_the_same_object(self):
        self.assertIs(M.solve, F.solve)

    def test_scripted_proposer_is_the_same_object(self):
        self.assertIs(M.ScriptedProposer, F.ScriptedProposer)

    def test_music_problem_is_not_the_letter_problem(self):
        self.assertIsNot(M.MusicProblem, F.Problem)

    def test_scripted_distribution_matches_letters_to_the_count(self):
        """The loop cannot see the surface, so under identical seeds and coherence
        values the music distribution must equal the letter distribution under the
        label map wyz<->F A B, xyy<->G A A, yyz<->A A B."""
        label = {"wyz": "F A B", "xyy": "G A A", "yyz": "A A B"}
        lt, mt = Counter(), Counter()
        for s in range(300):
            lr, _, _ = F.solve(F.Problem("abc", "abd", "xyz"), seed=1000 + s)
            mr, _, _ = F.solve(M.MusicProblem("C D E", "C D F", "G A B"), seed=1000 + s)
            lt[lr] += 1
            mt[mr] += 1
        for letter_ans, music_ans in label.items():
            self.assertEqual(lt[letter_ans], mt[music_ans],
                             f"{letter_ans} ({lt[letter_ans]}) != {music_ans} ({mt[music_ans]})")


class TestParsing(unittest.TestCase):
    """The shared LLM parser, gated to the music op vocabulary."""

    def test_accepts_music_ops(self):
        rules = F._parse_rules('[{"pos":"leftmost","op":"down"},{"pos":"rightmost","op":"up"}]',
                               valid_op=M._MUSIC_VALID_OP)
        self.assertIn(F.Rule("leftmost", "down"), rules)
        self.assertIn(F.Rule("rightmost", "up"), rules)

    def test_rejects_letter_ops_in_music_vocab(self):
        # 'successor' is a letter op; under the music vocab it must be dropped
        rules = F._parse_rules('[{"pos":"rightmost","op":"successor"}]',
                               valid_op=M._MUSIC_VALID_OP)
        self.assertEqual(rules, [])


class TestDeterminism(unittest.TestCase):
    def test_same_seed_reproduces(self):
        a = F.solve(M.MusicProblem("C D E", "C D F", "G A B"), seed=42)[0]
        b = F.solve(M.MusicProblem("C D E", "C D F", "G A B"), seed=42)[0]
        self.assertEqual(a, b)


class TestDemosRun(unittest.TestCase):
    def test_offline_demos_run_clean(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            M._run_offline_demos()
        out = buf.getvalue()
        self.assertIn("F A B", out)
        self.assertIn("DEMO 3", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
