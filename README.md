# Analogy as the core of cognition: from Hofstadter to a runnable FARG loop

A small, self-contained study that starts from a Douglas Hofstadter lecture and
ends at a working prototype. The thread: take Hofstadter's claim that analogy is
the core of cognition, contrast the mechanism that the Fluid Analogies Research
Group (FARG) built to model it against modern word-embedding and transformer
machinery, and then build the smallest honest runnable approximation of a
FARG-style control loop.

## Contents

| File | What it is |
|------|------------|
| `analogy-as-the-core-of-cognition-essay.md` | A 2,304-word first-person essay distilled from the raw lecture transcript, written in Hofstadter's voice. Keeps four examples: the subscript story, the three shadows, corridor/hurricane, Einstein's two bell curves. |
| `analogy-as-the-core-of-cognition-raw-transcript.md` | The raw ASR transcript of the Stanford lecture the essay is distilled from. Source material, kept for provenance. |
| `farg-deep-dive.md` | The four-part technical thread: (1) the Slipnet update rule, (2) Letter Spirit and the what/how tension, (3) mapping FARG onto a modern agent loop, (4) the coherence-to-temperature control law in detail. ASCII diagrams are load-bearing. |
| `farg_loop.py` | A single-file, stdlib-only, runnable FARG-flavored agent loop. Implements activation/depth, label-gated slippage, a coherence critic, endogenous temperature with snag re-heat, and a softmax scheduler. The answer emerges; it is not hardcoded. |

## The argument in one paragraph

A word embedding gives you one frozen metric: closeness is a fixed dot product set
at training time, and the famous king - man + woman = queen arithmetic rides on
that frozen geometry. FARG's Slipnet gives you a metric that deforms in real time:
concepts have a fixed conceptual depth but a volatile activation, and activation
retunes the lengths of the labeled links between concepts every cycle. So
"closeness" is never a point sliding toward another point; it is an abstract
relation (`opposite`, `successor`) waking up and pulling its endpoints together,
mediated by a third, deeper concept. That runtime deformation, plus a temperature
read off solution coherence that re-heats on a snag, is exactly what a transformer
lacks and what `farg_loop.py` reconstructs in miniature.

## Running the prototype

```
python3 farg_loop.py
```

Pure standard library, no dependencies. It runs three demos on the Copycat
letter-string domain (abc -> abd, so what does ijk -> ? and xyz -> ?):

- Demo 1: `ijk` with no alphabet wall (the easy case, no snag).
- Demo 2: `xyz`, where taking the successor of `z` hits the end of the alphabet,
  triggers a snag, re-heats the temperature, activates the `opposite` concept, and
  lets the frame flip so the answer emerges as `wyz`.
- Demo 3: 300 stochastic runs of the `xyz` case, printing the distribution of
  answers. `wyz` is the plurality, not a certainty. The point is that the answer
  is genuinely emergent from the slippage dynamics, not a literal in the code.

### Running with a real model as the executor

The codelet executor is pluggable. By default the loop runs offline with a scripted
proposer; pass `--llm` to swap in a real model that proposes the candidate rules,
while the control layer (coherence critic, temperature, snag, slip, retract) is
unchanged and still decides:

```
python3 farg_loop.py --llm                          # default backend: anthropic (needs ANTHROPIC_API_KEY)
python3 farg_loop.py --llm --backend ollama         # local model, no network egress
python3 farg_loop.py --llm --backend openai         # needs OPENAI_API_KEY
python3 farg_loop.py --llm --no-scaffold             # show the model's raw contribution only
python3 farg_loop.py --llm --problem rst             # try a different target string
```

The model only WIDENS the candidate set. A deterministic scaffold floor (base rule
plus the `opposite`-gated slips) is unioned in by default, so the reframe is
guaranteed regardless of model quality; `--no-scaffold` removes it. The model is
asked once per problem (the prompt does not depend on the cycle), the reply is
cached, malformed or out-of-vocabulary rules are dropped, and a client error
degrades gracefully to the scaffold floor. The client is lazy-imported, so the
offline demo stays stdlib-only with no SDK installed.

A nice consequence: when the model proposes the elegant `(leftmost, predecessor)`
reading up front, the loop reaches `wyz` in two cycles with no snag at all. A
smarter executor shortcuts the search; the control layer still scores and selects.

## What is honest about it, and what is a toy

Honest: the temperature is endogenous (computed from workspace coherence, not set
by hand), it re-heats on a snag, the workspace supports a real retract, slippage is
gated by an activated concept, the answer is selected stochastically from emergent
proposals, and the LLM executor is genuinely wired (parse, validate, cache,
graceful fallback) behind the same `propose()` contract as the scripted one.

A toy: the domain is tiny, the concept graph is hand-built, and the shipped demo
defaults to the scripted proposer so it runs offline. The LLM path is wired and
unit-verified with an injected stub client, but whether a given real model returns
parseable rules depends on the model. It is a faithful skeleton of the control law,
not a re-implementation of Copycat.

## References

Primary FARG sources are listed at the end of `farg-deep-dive.md`. The lecture is
Douglas Hofstadter, "Analogy as the Core of Cognition," Stanford.
