# Past the toy: the false-freeze in a second domain

The letter-string study left one question open. The false-freeze (a capable executor
cools onto a locally-coherent reading and never hits the snag that surfaces the elegant
answer) was measured on one domain: Copycat letter strings. Is it a property of the
control law, or an artifact of the 26-letter toy?

This is the test. I ported a second, surface-different domain (`domain_music.py`,
diatonic melody) that drives the SAME control loop, and asked whether the false-freeze
reproduces. It does.

## The architecture, and why it is the real proof

The control law is imported, not re-implemented. `domain_music.py` opens with:

```python
from farg_loop import (Rule, _index, solve, ScriptedProposer, LLMProposer,
                       make_llm_client)
```

`solve`, the temperature law, the snag re-heat, the softmax selection, the freeze bar,
the give-up detector, and the scripted proposer are the same objects the letter domain
uses. The test suite asserts this by identity:

```
test_solve_is_the_same_object               M.solve is F.solve
test_scripted_proposer_is_the_same_object   M.ScriptedProposer is F.ScriptedProposer
```

To make `solve` domain-generic I made five surgical, behavior-preserving changes to
`farg_loop.py`. Each defaults to the letter behavior, so the 23 existing letter tests
still pass unchanged. That is the proof the letter path is byte-identical, not the
claim.

```
1. Slipnet(opposites=None)        inject the slip vocabulary; default = letter OPPOSITES
2. solve -> Slipnet(getattr(prob, "opposites", None))   letter Problem has no attr -> default
3. solve -> prob.coherence(rule)  domain hook; Problem.coherence delegates to coherence_of
4. _parse_rules(.., valid_op=..)  parser takes the legal op set; default = letter ops
5. LLMProposer(prompt=, valid_op=)  reuse the proposer + cache + scaffold, new vocabulary
```

A second domain now supplies only its surface: a `MusicProblem` that exposes
`base_rule`, `coherence(rule)`, `opposites`, and `s0/s1/target`, plus an apply / infer /
coherence trio over a 7-note scale. The control loop never learns which domain it drives.

## The domain

One octave of a diatonic scale, `C D E F G A B` = degrees 0..6, bounded. Nothing below
C (the floor), nothing above B in the register (the ceiling). The walls. `up` walls at
B, `down` walls at C, exactly as `successor` walls at z and `predecessor` at a.

```
LETTERS                              MELODY
abc -> abd ; xyz -> ?                C-D-E -> C-D-F ; G-A-B -> ?
base rule (rightmost, successor)     base rule (rightmost, up)
  successor of z is undefined -> WALL    up from B leaves the register -> WALL
opposite-gated double slip:          opposite-gated double slip:
  (leftmost, predecessor) -> wyz       (leftmost, down) -> F-A-B
single-slip distractors at c=0.93:   single-slip distractors at c=0.93:
  (leftmost, successor)  -> yyz         (leftmost, up)    -> A-A-B
  (rightmost, predecessor) -> xyy       (rightmost, down) -> G-A-A
```

The relational skeleton is deliberately isomorphic. That is the experimental design,
not a flaw: hold the deep structure fixed, vary only the surface, and any reproduction
of the false-freeze is attributable to the control law and not to the alphabet. A reader
is right that this is the same problem in a new costume. The point is to prove the
costume does not matter. The "is this just relabeling?" objection is answered in Part A.

## Part A: the loop is surface-blind

Run the scripted scout on both domains, same seeds, both bars.

```
                  elegant@0.90   elegant@0.99
  letters            47.7%          96.7%        dist  wyz:143  xyy:83  yyz:74
  melody             47.7%          96.7%        dist  F A B:143  G A A:83  A A B:74
```

The distributions match to the count. `wyz:143 xyy:83 yyz:74` and
`F A B:143 G A A:83 A A B:74` are the same numbers because the loop cannot see the
surface. Identical seeds and identical coherence values produce identical softmax draws
and identical selection. A regression test pins this under the label map
wyz<->F-A-B, xyy<->G-A-A, yyz<->A-A-B. So the scripted result already shows the mechanism
is domain-general by construction. It is a sanity proof, not a finding.

## Part B: the false-freeze transfers

The real test. A real model (haiku) reads real notes versus real letters and may behave
differently, so a reproduction here is informative. K=3 candidate-set samples x S=100
loop seeds, both bars, same model on both domains.

```
            scout@0.90   model@0.90   model@0.99
  letters     47.7%         3.7%        41.3%
  melody      47.7%        18.3%        56.7%

  letters  |################ 47.7%  scout
           |# 3.7%                  haiku  (false-freeze)
           |############## 41.3%    haiku @0.99  (recovered)

  melody   |################ 47.7%  scout
           |###### 18.3%            haiku  (false-freeze)
           |################### 56.7%  haiku @0.99  (recovered)
```

VERDICT: the false-freeze reproduces in both domains. In both, the capable model lands
far below the dumb scout at the default bar, and raising the bar to 0.99 recovers the
elegant answer. The phenomenon is a property of the loop, not the letters.

## The honest part: why the two magnitudes differ

The default-bar numbers differ between domains in this run: 3.7% for letters, 18.3% for
melody. That gap is NOT a domain property. It is the candidate-set variance already
documented in `EXPERIMENT.md` ("whether a model proposes the reframe varies call to
call"), showing up live.

Look at the sampled candidate sets. In this run, none of the three letter samples
proposed the reframe rule `(leftmost, predecessor)`, so `wyz` was reachable only through
the snag, and it landed at 3.7%. One of the three melody samples proposed `(leftmost,
down)` directly, so `F-A-B` was on the menu more often, and it landed at 18.3%. Same
model, same settings, different sampled calls.

This also reconciles with the capability sweep, where haiku on letters was 18.7%, not
3.7%. There, one of three letter samples happened to propose the reframe. Here, zero of
three did. The single-sample number is not robust, which is exactly the caveat
`EXPERIMENT.md` records. The robust claims are directional and they hold in both
domains: model far below scout at the default bar, recovery when the bar is raised.

## What this does and does not establish

Establishes:
- The false-freeze is a property of the control law. It reproduces under a different
  surface with the loop driven byte-for-byte unchanged.
- The fix transfers too. Raising the freeze bar recovers the elegant answer in both
  domains.
- The architecture generalizes. A new domain is a surface module (apply / infer /
  coherence / slip vocabulary), not a new control loop.

Does not establish:
- That music and letters false-freeze at different rates. The per-domain magnitudes here
  are dominated by candidate-set sampling noise, not domain structure.
- Anything about real tonal cognition. The melody critic is structural, identical in
  form to the letter critic. A pitch here is an integer degree with a register ceiling,
  not a heard note with key, meter, or expectation.
- A population property of capable agents. Two toy problems, one model, K=3 samples.

## Reproduce

```
python3 domain_music.py                      # offline demos in the music surface
python3 -m unittest test_domain_music -v     # 20 tests, stdlib only, no model
python3 experiment_domain_transfer.py        # Part A + Part B (Part B makes model calls)
```

Raw data: `domain_transfer_results.json`.
