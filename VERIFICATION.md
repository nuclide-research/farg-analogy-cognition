# Adversarial verification of farg_loop.py

Per NuClide doctrine, verification is the load-bearing stage: a scan (or a claim)
produces candidates; verification produces findings. Before committing the
prototype, a 5-agent adversarial workflow was run with one job: try to BREAK the
integrity claims, prove the demo is rigged, or show the answer is planted.

**Verdict: genuine-with-caveats (high confidence).** The prototype is not rigged.
One real overclaim was found and has been corrected (see below).

## Claims that survived independent attack

- **No hardcoded answer in the decision path.** Independent grep: every occurrence
  of `wyz`/`xyy`/`yyz`/`abd` lives only in docstrings or demo `Problem(...)`
  constructors. Zero answer literals in the logic. The answer emerges from
  `OPPOSITES`-dict lookups applied at runtime.
- **The reframe is emergent and symmetric, not xyz-special-cased.** The mirror case
  `zyx -> ?` independently reproduces: infers `(leftmost, predecessor)`, hits the
  LEFT wall on target `abc`, snags, double-slips to `(rightmost, successor)` and
  yields `abd` as its plurality (148/300), exactly as `wyz` dominates `xyz`
  (142/300). Same mechanism, mirrored.
- **The slip mechanism is causally load-bearing.** A `NoSlipProposer` ablation
  (base rule only) returns `None` in 50/50 `xyz` runs, stuck in a permanent snag
  loop. Remove slip and no answer emerges.
- **Temperature is endogenous and genuinely drives the answer DISTRIBUTION.** The
  `(1-c)^gamma` law matches the stated formula to machine precision. Forcing `tau`
  cold concentrates on the max-coherence `wyz`; forcing it hot flattens the
  distribution until `wyz` is no longer the mode. `tau()` reads the live mutated
  temperature and is the actual third arg to `softmax_choice`. Not decorative.
- **The discriminating coherence term cannot reference the answer.** `rule_support`
  has signature `(rule, base)`; a static scan shows zero references to the target,
  the answer, or the problem strings. It is a pure function of candidate-vs-base
  structure and awards 1.0 to the double-opposite-slip across all base rules
  tested.
- **The snag fires only on a wall.** `ijk` (clean) never snags; `xyz` snags exactly
  once at cycle 1. The `opposite` activation that licenses the slipped candidates
  is set by the snag, not by the author.
- **The executor is genuinely pluggable.** `ScriptedProposer` and `LLMProposer`
  share the identical `propose(self, prob, net) -> list[Rule]` signature;
  `LLMProposer` is an honest `NotImplementedError` stub.

## The one real overclaim (found, and FIXED)

- **(MEDIUM) The docstring framed the snag RE-HEAT as the driver of the reframe.**
  Ablation refutes this: making `snag()` a no-op (re-heat off) still solves 300/300
  with the same answers; blocking only the `opposite` activation (re-heat fully on)
  yields 300/300 `None`. So the reframe is causally gated by the `opposite`
  concept activation, NOT by the temperature re-heat. The two merely share the snag
  trigger. **Correction applied:** the module docstring now states the snag does two
  SEPARATE things (activate `opposite`, which gates the reframe; and re-heat T,
  which only lengthens post-snag exploration), and a "What the ablation proved"
  block records this explicitly.

## Lesser caveats (now disclosed in-code)

- The 0.90 re-heat impulse adds zero heat at the snag instant (the law already
  yields `T_max` when c is forced to 0, and `max(T_max, 0.90) = T_max`). Its only
  measurable effect is to lengthen the next few post-snag cycles. Now stated in the
  docstring.
- "Mostly structural" coherence is generous in magnitude: on a clean apply,
  consistency/coverage/goal are constant 1.0 (0.70 weight is a flat floor) and only
  the 0.30*support term varies. The signal that DISCRIMINATES the reframe is 100%
  structural, so the intent ("the critic is structural, not an answer lookup") is
  defensible, but the docstring now states the 70/30 split honestly.
- A snag short-circuits coherence to exactly 0.0 (the docstring previously said
  "near 0"). Corrected to "exactly 0.0".
- ~~The `LLMProposer` swap is unwired; the real-model executor is never
  exercised.~~ **RESOLVED (follow-up commit).** `LLMProposer` is now wired: it
  asks a model for candidate `(pos, op)` rules, parses and validates them against
  the legal vocabulary, caches the per-problem reply, and degrades to the scaffold
  floor on any client error. The full path (parse, propose, solve, cache,
  fallback, malformed-input rejection) is unit-verified with an injected stub
  client. Opt-in via `--llm` (`anthropic` | `ollama` | `openai`); the offline
  scripted demo remains the default and stays stdlib-only. Still honest: a live
  call against a hosted model was not exercised in CI, so whether a specific real
  model returns parseable rules is model-dependent.

Workflow: 5 agents, ~305k subagent tokens, 60 tool uses, ~414s.
