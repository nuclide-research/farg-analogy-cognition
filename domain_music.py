#!/usr/bin/env python3
"""
domain_music.py - a SECOND surface domain for the FARG loop: diatonic melody.

Why this file exists:
  The letter-string domain (farg_loop.py) showed a false-freeze: a capable executor
  cools onto a locally-coherent reading and never hits the snag that surfaces the
  elegant answer. The obvious question is whether that is a property of the CONTROL
  LAW or an artifact of the 26-letter toy. This file answers it by porting a second,
  surface-different domain that reuses the SAME control loop byte-for-byte:

      from farg_loop import solve, ScriptedProposer, LLMProposer, Temperature, Rule

  Nothing about temperature, snag re-heat, opposite-gated slip, softmax selection, the
  freeze bar, or the give-up detector is re-implemented here. solve() and
  ScriptedProposer are imported and driven UNCHANGED. This module supplies only the
  domain surface: a 7-note diatonic scale with a register ceiling/floor (the walls), an
  apply/infer/coherence trio, and the slip vocabulary {up<->down, leftmost<->rightmost}.

The analogy (Musicat lineage - FARG's own melodic-expectation project):
  one octave of a diatonic scale, C D E F G A B = degrees 0..6, BOUNDED:
  nothing below C (floor), nothing above B within the register (ceiling).

    C-D-E -> C-D-F ;  C-E-G -> ?    raise rightmost one step -> C-E-A   (NO snag)
    C-D-E -> C-D-F ;  G-A-B -> ?    B has no note above it -> SNAG -> opposite
                                    activates (gates the slip) + re-heat ->
                                    double-slip (leftmost, down) -> F-A-B

  Same skeleton as xyz->wyz, different surface. The base rule (rightmost, up) walls on
  the ceiling note B; the opposite-gated double slip reads the phrase as descending
  from the bottom instead of ascending into the ceiling, and that reframe scores top
  coherence. A capable proposer that offers clean "change the other end / other
  direction" readings (A-A-B, G-A-A at coherence 0.93) freezes before the wall is ever
  hit - exactly the letter-domain false-freeze, in a domain with no letters.

Honesty boundary:
  * The relational skeleton is DELIBERATELY isomorphic to the letter domain. That is
    the experiment, not a flaw: we hold the deep structure fixed and vary ONLY the
    surface, so any reproduction of the false-freeze is attributable to the control
    law and not to the alphabet. A reader is right that this is "the same problem in a
    new costume"; the point is to prove the costume does not matter. See DOMAINS.md.
  * The coherence critic is structural, identical in form to the letter critic (a wall
    tanks c to 0; otherwise 0.40 + 0.15 + 0.15 + 0.30*support). It models the structural
    elegance of the reframe, NOT real tonal cognition. A pitch here is an integer degree
    with a ceiling, not a heard note with key, meter, or expectation.
  * Nothing is hardcoded to the answer. "F A B" / degrees (3,5,6) / (leftmost, down)
    appear nowhere in the decision path. The reframe EMERGES from net.slip(rightmost)
    -> leftmost and net.slip(up) -> down, each gated by the `opposite` activation the
    snag (not the programmer) raises. Grep this file: those tokens live only in
    docstrings and the demo-print labels, never in apply/infer/coherence/proposer.
"""
from __future__ import annotations
from dataclasses import dataclass, field

from farg_loop import (Rule, _index, solve, ScriptedProposer, LLMProposer,
                       make_llm_client)

# ----------------------------------------------------------------------------
# scale primitives  (the walls live here: B has no note above, C none below)
# ----------------------------------------------------------------------------

SCALE = ["C", "D", "E", "F", "G", "A", "B"]      # one octave, 7 diatonic degrees
NOTE_TO_DEG = {n: i for i, n in enumerate(SCALE)}
CEILING = len(SCALE) - 1                          # 6 = B; no diatonic note above in register
FLOOR = 0                                         # 0 = C; no diatonic note below

def up(deg: int):
    return None if deg >= CEILING else deg + 1    # wall: nothing above B

def down(deg: int):
    return None if deg <= FLOOR else deg - 1       # wall: nothing below C

MUSIC_OPS = {"up": up, "down": down, "same": lambda d: d}

# the slip vocabulary for this domain. position slips are shared with letters; the
# directional slip is up<->down (the musical analog of successor<->predecessor).
MUSIC_OPPOSITES = {"rightmost": "leftmost", "leftmost": "rightmost",
                   "up": "down", "down": "up",
                   "first": "last", "last": "first"}

_MUSIC_VALID_OP = {"up", "down", "same"}

def degs(melody: str) -> tuple[int, ...]:
    """'C D E' -> (0,1,2). Accepts space-separated note names."""
    return tuple(NOTE_TO_DEG[tok] for tok in melody.split())

def notes(ds) -> str:
    """(3,5,6) -> 'F A B'. The display inverse of degs(); never on the decision path."""
    return " ".join(SCALE[d] for d in ds)

# ----------------------------------------------------------------------------
# rule application / inference / coherence  (same FORM as the letter critic)
# ----------------------------------------------------------------------------

def apply_rule_music(rule: Rule, ds: tuple[int, ...]):
    """(result_degrees, None) on a clean apply, or (None, reason) on a SNAG: the
    operation is undefined at the register boundary (up at B, down at C)."""
    i = _index(rule.pos, ds)
    newdeg = MUSIC_OPS[rule.op](ds[i])
    if newdeg is None:
        return None, f"wall: {rule.op}('{SCALE[ds[i]]}') leaves the register"
    return ds[:i] + (newdeg,) + ds[i + 1:], None

def infer_rule_music(d0: tuple[int, ...], d1: tuple[int, ...]) -> Rule:
    """Read S0->S1 to get the base rule. C-D-E -> C-D-F : index 2 (rightmost), up."""
    i = next(k for k in range(len(d0)) if d0[k] != d1[k])
    pos = {0: "leftmost", len(d0) - 1: "rightmost"}.get(i, "middle")
    if up(d0[i]) == d1[i]:
        op = "up"
    elif down(d0[i]) == d1[i]:
        op = "down"
    else:
        op = "same"
    return Rule(pos, op)

def rule_support_music(rule: Rule, base: Rule) -> float:
    """Identical in form to the letter critic's rule_support: reward keeping the
    original change's shape (an end position + a directional op) and theme coherence
    (how many components slipped under the SAME `opposite` theme). The double
    opposite-slip scores highest; it is not a lookup of any particular melody."""
    if rule == base:
        return 1.0
    mirror = 1.0 if (rule.pos in ("leftmost", "rightmost")
                     and rule.op in ("up", "down")) else 0.5
    slipped = (1 if rule.pos == MUSIC_OPPOSITES.get(base.pos) else 0) + \
              (1 if rule.op == MUSIC_OPPOSITES.get(base.op) else 0)
    theme = slipped / 2.0
    return 0.5 * mirror + 0.5 * theme

def coherence_music(rule: Rule, prob: "MusicProblem"):
    """c in [0,1], same weights as the letter critic. A snag short-circuits to 0.0."""
    result, snag = apply_rule_music(rule, prob.target_degs)
    if result is None:
        return 0.0, None, snag
    consistency, coverage, goal = 1.0, 1.0, 1.0
    support = rule_support_music(rule, prob.base_rule)
    c = 0.40 * consistency + 0.15 * coverage + 0.15 * goal + 0.30 * support
    return c, notes(result), None

# ----------------------------------------------------------------------------
# the domain object solve() drives. Duck-types the letter Problem: it exposes
# base_rule, coherence(rule), opposites, and s0/s1/target (for the LLM prompt).
# ----------------------------------------------------------------------------

@dataclass
class MusicProblem:
    s0: str; s1: str; target: str                      # space-separated note names
    base_rule: Rule = field(init=False)
    target_degs: tuple = field(init=False)
    opposites: dict = field(init=False)
    def __post_init__(self):
        self.base_rule = infer_rule_music(degs(self.s0), degs(self.s1))
        self.target_degs = degs(self.target)
        self.opposites = MUSIC_OPPOSITES                # injected into solve()'s Slipnet
    def coherence(self, rule: Rule):
        return coherence_music(rule, self)

# ----------------------------------------------------------------------------
# LLM proposer for this domain = the SAME LLMProposer, given a music prompt + op set
# ----------------------------------------------------------------------------

MUSIC_PROMPT = (
    "You are a single perception codelet in a Copycat-style analogy solver, working in "
    "a MUSICAL domain.\n"
    "A transformation maps a short melody S0 to S1 on the diatonic scale "
    "C D E F G A B (one octave). Propose candidate rules that would transform the "
    "target melody T0 in the SAME spirit.\n\n"
    "A rule is a (position, operation) pair:\n"
    "  position  in: leftmost | rightmost | middle\n"
    "  operation in: up | down | same   (up/down = one scale step)\n"
    "The scale has walls: 'B' has no note above it in the register, 'C' none below. If "
    "the obvious rule would leave the register on T0, ALSO propose how it could bend "
    "(act on the other end, or flip the direction).\n\n"
    "S0 = {s0}\nS1 = {s1}\nT0 = {t0}\n\n"
    "Reply with ONLY a JSON array of objects, each {{\"pos\": ..., \"op\": ...}}, "
    "ordered most-natural first, 1 to 5 rules. No prose."
)

def music_llm_proposer(client, *, scaffold=True, verbose=False):
    """The same LLMProposer class, configured for the music vocabulary. No new control
    logic; just a different prompt template and legal op set."""
    return LLMProposer(client, scaffold=scaffold, verbose=verbose,
                       prompt=MUSIC_PROMPT, valid_op=_MUSIC_VALID_OP)

# ----------------------------------------------------------------------------
# demos  (mirror farg_loop's offline demos, in the music surface)
# ----------------------------------------------------------------------------

def _print_trace(title, prob, result, rule, trace):
    print(f"\n=== {title}:  {prob.s0} -> {prob.s1} ; {prob.target} -> ?   "
          f"base rule {prob.base_rule} ===")
    print(f"{'cyc':>3} {'rule tried':>24} {'->':>7} {'c':>5} {'T':>5} {'tau':>5}  action")
    print("-" * 80)
    for (cy, r, res, c, T, tau, act) in trace:
        print(f"{cy:>3} {str(r):>24} {str(res or '--'):>7} {c:>5.2f} {T:>5.2f} {tau:>5.2f}  {act}")
    if result is None:
        print(f"NO SOLUTION for {prob.target} (gave up: snag loop, no viable clean candidate)")
    else:
        print(f"ANSWER: {prob.target} -> {result}   via {rule}")

def _run_offline_demos():
    print("FARG-flavored loop :: SECOND DOMAIN = diatonic melody")
    print("control law imported UNCHANGED from farg_loop (solve, ScriptedProposer, Temperature)")
    print("executor: ScriptedProposer (offline, stdlib only)")

    # 1) easy frame: rightmost note is not the ceiling, so no wall, no snag
    p1 = MusicProblem("C D E", "C D F", "C E G")
    r, rule, tr = solve(p1, seed=1)
    _print_trace("DEMO 1  (no snag)", p1, r, rule, tr)

    # 2) the wall: target ends on the ceiling note B -> snag -> reframe
    p2 = MusicProblem("C D E", "C D F", "G A B")
    r, rule, tr = solve(p2, seed=7)
    _print_trace("DEMO 2  (snag -> re-heat -> reframe)", p2, r, rule, tr)

    # 3) distribution over 300 runs: the elegant double-slip dominates by coherence
    print("\n=== DEMO 3  (300 runs of 'G A B' -> ?, varied seeds: distribution of answers) ===")
    from collections import Counter
    tally = Counter()
    for s in range(300):
        res, rule, _ = solve(MusicProblem("C D E", "C D F", "G A B"), seed=1000 + s)
        tally[(res, str(rule))] += 1
    for (res, rule), n in tally.most_common():
        bar = "#" * round(60 * n / 300)
        print(f"  {str(res):>7} via {rule:>24}  {n:>3}/300  {bar}")
    print("  (the elegant double-opposite-slip dominates by coherence, not by fiat)")

def _run_llm_demo(args):
    backend, model = args.backend, args.model
    print(f"FARG-flavored loop :: SECOND DOMAIN = diatonic melody")
    print(f"executor = LLMProposer  (backend={backend}, model={model})")
    print(f"scaffold floor: {'ON' if not args.no_scaffold else 'OFF (model candidates only)'}")
    try:
        client = make_llm_client(backend, model)
    except Exception as e:
        print(f"\n[could not build the {backend} client: {e}]")
        return
    proposer = music_llm_proposer(client, scaffold=not args.no_scaffold, verbose=True)
    print(f"freeze bar: {args.freeze_bar:.2f}")
    prob = MusicProblem("C D E", "C D F", args.problem)
    r, rule, tr = solve(prob, proposer=proposer, seed=args.seed, freeze_bar=args.freeze_bar)
    print(f"\nmodel's parsed candidates: {[str(x) for x in proposer.last_parsed] or 'none usable'}")
    if proposer.last_raw is not None:
        print(f"model raw reply (truncated): {' '.join(proposer.last_raw.split())[:200]}")
    _print_trace(f"LLM DEMO  (executor={backend})", prob, r, rule, tr)

def main():
    import argparse
    ap = argparse.ArgumentParser(
        description="FARG loop, second domain (diatonic melody). Reuses the imported "
                    "control law unchanged. Default runs OFFLINE (stdlib only).")
    ap.add_argument("--llm", action="store_true", help="use an LLM as the codelet executor")
    ap.add_argument("--backend", default="claude-code",
                    choices=["claude-code", "anthropic", "ollama", "openai"])
    ap.add_argument("--model", default=None)
    ap.add_argument("--no-scaffold", action="store_true")
    ap.add_argument("--problem", default="G A B", help="target melody for the LLM demo")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--freeze-bar", type=float, default=0.90)
    args = ap.parse_args()
    if args.llm:
        _run_llm_demo(args)
    else:
        _run_offline_demos()

if __name__ == "__main__":
    main()
