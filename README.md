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

## What is honest about it, and what is a toy

Honest: the temperature is endogenous (computed from workspace coherence, not set
by hand), it re-heats on a snag, the workspace supports a real retract, slippage is
gated by an activated concept, and the answer is selected stochastically from
emergent proposals.

A toy: the proposer for the demo is scripted rather than an LLM (an `LLMProposer`
stub shows the one-class swap), the domain is tiny, and the concept graph is
hand-built. It is a faithful skeleton of the control law, not a re-implementation
of Copycat.

## References

Primary FARG sources are listed at the end of `farg-deep-dive.md`. The lecture is
Douglas Hofstadter, "Analogy as the Core of Cognition," Stanford.
