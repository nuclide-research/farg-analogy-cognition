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
| `test_farg_loop.py` | A stdlib `unittest` suite (23 tests) that freezes the adversarial verification verdict as regression tests: no hardcoded answer, the slip/opposite/reheat ablations, the canonical distribution, cross-`PYTHONHASHSEED` determinism, the freeze-bar recovery, the give-up detector, and the LLM-reply parser. |
| `ANALYSIS.md` | The generalizable agent-design lesson distilled from building this: a more capable executor can reach a worse answer by routing around the productive failure, why that is structural, and the one-branch fix (a quality floor on convergence). |
| `false-freeze-and-the-capable-executor.md` | A conceptual bridge from the false-freeze finding to autonomous security-agent design: the capable executor is the false-freeze risk, the defense is a convergence gate anchored on a check the executor does not author, and an honest section on where the toy analogy breaks. Adversarially critiqued so it is not a forced analogy. |

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

To watch the dynamics instead of the table, pass `--plot` for an ASCII sparkline of
temperature and coherence per cycle. It picks a seed where the default bar
false-freezes and the raised bar recovers, then plots both: you can see the snag as a
temperature spike and the false-freeze as coherence stuck below the top while the
temperature flatlines low.

```
python3 farg_loop.py --plot
```

To run the test suite (stdlib only, no network, no model):

```
python3 -m unittest test_farg_loop -v
```

### Running with a real model as the executor

The codelet executor is pluggable. By default the loop runs offline with a scripted
proposer; pass `--llm` to swap in a real model that proposes the candidate rules,
while the control layer (coherence critic, temperature, snag, slip, retract) is
unchanged and still decides:

```
python3 farg_loop.py --llm                      # default backend: claude-code (your Max/Pro auth, no API key)
python3 farg_loop.py --llm --model haiku         # faster/cheaper model for this toy task
python3 farg_loop.py --llm --backend ollama      # local model, no network egress
python3 farg_loop.py --llm --backend openai      # needs OPENAI_API_KEY
python3 farg_loop.py --llm --no-scaffold         # show the model's raw contribution only
python3 farg_loop.py --llm --freeze-bar 0.99     # raise the aspiration bar (see below)
```

The `claude-code` backend shells out to the headless `claude` CLI and uses your
logged-in Claude Code subscription auth, so no API key is needed. The model only
WIDENS the candidate set. A deterministic scaffold floor (base rule plus the
`opposite`-gated slips) is unioned in by default, so the reframe is guaranteed
regardless of model quality; `--no-scaffold` removes it. The model is asked once
per problem (the prompt does not depend on the cycle), the reply is cached,
malformed or out-of-vocabulary rules are dropped, and a client error degrades
gracefully to the scaffold floor. The client is lazy-imported, so the offline demo
stays stdlib-only with no SDK installed.

#### The executor swap shifts the answer, and the freeze bar steers it back

Swapping the executor genuinely shifts the answer distribution while the control
law stays byte-for-byte identical. At the default freeze bar (0.90), measured live
with `claude-haiku` (40 seeds) versus the offline scripted run (300, deterministic):

```
  real model (haiku), bar 0.90      offline scripted, bar 0.90
    yyz  21/40                         wyz  143/300
    xyy  19/40                         xyy   83/300
    wyz   0/40                         yyz   74/300
```

The scripted scout has no clean candidate except the base rule, which always hits
the `z` wall, so it is forced through the snag that activates `opposite` and
surfaces the elegant double-slip `wyz`. The real model proactively offers simpler
"change the other end" readings (`yyz`, `xyy`) at coherence 0.93; those commit, the
temperature cools so fast the loop freezes, and the base rule is never
selected-and-snagged. `wyz` is reachable only through a snag, so an executor that
dodges the wall also dodges `wyz` (0/40). That is a live instance of the
false-freeze mode in `farg-deep-dive.md`: cooling onto a locally-coherent (0.93)
frame before the globally more elegant (1.0) one is ever surfaced.

Raising the freeze bar is the fix. The control law gains *aspiration-coupled
cooling*: it refuses to FREEZE on any frame below the bar, holding the temperature
search-warm so the scheduler keeps a real chance of re-trying the snag-inducing
base rule. Raise the bar to 0.99 and `wyz` comes back, with no change to the model:

```
                bar 0.90          bar 0.99
  scripted      wyz 143/300       wyz 290/300     (48% -> 97%)
  haiku (real)  wyz   0/40        wyz  23/40      (0% -> 58%, now the plurality)
```

A live `--freeze-bar 0.99` trace shows exactly how: the loop stays warm on the
0.93 escapes until it finally re-tries the wall, snags, and locks the reframe.

```
cyc               rule tried    ->     c     T   tau  action
  1    (leftmost, successor)   yyz  0.93  0.45  0.39  commit (below bar: stay warm)
  ...  (eight more 0.93 commits, temperature held warm at 0.45) ...
 10   (rightmost, successor)    --  0.00  1.00  0.72  SNAG->retract+reheat
 11-13 ... still exploring while `opposite` is hot ...
 14  (leftmost, predecessor)   wyz  1.00  0.06  0.15  commit
 15  (leftmost, predecessor)   wyz  1.00  0.05  0.15  FREEZE
ANSWER: xyz -> wyz   via (leftmost, predecessor)
```

`freeze_bar` defaults to 0.90, so the offline demo is unchanged. (Note: the
scripted distribution is now deterministic across runs. It previously drifted by a
few counts because candidate order came from set iteration under hash
randomization; the proposer now builds candidates in a fixed order. The model path
remains stochastic because the model's proposed rules vary slightly per call, so
the haiku counts above are one representative run.)

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

The surprising part, that a more capable executor reached a *worse* answer by routing
around the snag, generalizes past this toy. The lesson and the one-branch fix are
written up in [`ANALYSIS.md`](ANALYSIS.md).

## References

Primary FARG sources are listed at the end of `farg-deep-dive.md`. The lecture is
Douglas Hofstadter, "Analogy as the Core of Cognition," Stanford.
