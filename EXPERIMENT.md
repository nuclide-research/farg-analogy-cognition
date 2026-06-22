# Capability sweep: does a more capable executor false-freeze more?

The bridge essay claimed a more capable executor raises false-freeze risk. That rested
on one model. This measures four executors through the same control law. The result
confirms the coarse claim and falsifies the fine one. Read it as a correction to the
essay, not a victory lap.

Reproduce: `python3 experiment_capability_sweep.py` (real model calls go through the
wired claude-code backend). Raw data: `experiment_results.json`.

## Method

One control law. Four executors: the scripted scout (capability none), and haiku,
sonnet, opus through the claude-code backend. For each model, sample its proposed
candidate set K=3 times (three real model calls), then run S=100 loop seeds per sample
at freeze bar 0.90 and 0.99. That is 300 runs per cell. The scaffold floor stays ON,
so the opposite-gated reframe is reachable for every executor and any false-freeze is
the executor's clean-reading bias winning the softmax, not an unreachable answer. A
local llama3.2 was attempted; the daemon was down, so it is logged as not run, not
counted.

## Result

```
executor          wyz@0.90   wyz@0.99   proposes base?  proposes reframe?  clean readings
scripted (none)     47.7%      96.7%        no              no                 0
haiku               18.7%      70.0%        yes             yes (1 of 3)       3
sonnet              20.7%      45.3%        yes             yes (1 of 3)       5
opus                20.3%      51.7%        yes             yes (1 of 3)       5
```

wyz% at the default bar 0.90:

```
scripted |####################### 47.7%   (0 distractor readings)
haiku    |######### 18.7%                  (3)
sonnet   |########## 20.7%                 (5)
opus     |########## 20.3%                 (5)
```

wyz% recovery at the raised bar 0.99:

```
scripted (0 readings) |################################ 96.7%
haiku    (3 readings) |####################### 70.0%
opus     (5 readings) |################# 51.7%
sonnet   (5 readings) |############### 45.3%
```

## What holds

The coarse claim holds and holds hard. A fluent executor false-freezes far more than
the dumb scout at the default bar. The scout sits at 47.7% wyz. Every frontier model
sits near 20%. Swapping a dumb proposer for a capable one more than halves the elegant
answer rate, under a byte-for-byte identical control law. That is the core finding and
it is robust across three independent models.

The reason is visible in the candidate sets. The scout proposes one rule, the base
rule, which hits the wall. Every frontier model proposes a crowd of plausible clean
readings: rightmost-predecessor gives xyy, leftmost-successor gives yyz. Those score
0.93, clear the 0.90 bar, and win the warm softmax before the elegant reading is ever
locked. The scout has no such distractors, so it is forced through the snag that
surfaces the reframe.

## What breaks

Two things the essay got wrong.

First, there is no capability gradient among frontier models. The sequence at the
default bar is [47.7, 18.7, 20.7, 20.3]. The drop is the single step from scout to
fluent. After that it is flat. haiku, the least capable of the three, has the lowest
wyz of the three, the opposite of a monotonic "more capable, more false-freeze." The
effect saturates the moment a model is fluent enough to propose plausible distractors.
What matters is crossing that threshold, not how far past it you are. The monotonic
version of the claim is false.

Second, the mechanism is not wall-dodging for a real model. The toy's clean story is
that wyz lives on the far side of a wall and a fluent proposer never hits the wall.
But the models propose the reframe directly in one of three samples. When they do, the
reframe is on the menu at coherence 1.0 from the first cycle, no wall required, and
false-freeze still happens. The real mechanism is dilution. The elegant reading
competes against a crowd of good-enough 0.93 readings in a warm softmax, loses the
vote often enough, and gets frozen out when the loop cools. For the scout the wall is
the only path to wyz. For a fluent model wyz is on the ballot and gets out-voted.

## The signal that did track

Menu breadth, not capability, predicts the high-bar recovery. Raise the bar to 0.99
and the loop refuses to settle below it. The scout recovers wyz almost completely at
96.7% because it has no distractors to dilute the search. haiku, offering 3 clean
readings, recovers to 70%. opus and sonnet, each offering 5, recover to 51.7% and
45.3%. The wider the model's menu of plausible-but-shallow readings, the worse the
convergence gate recovers the elegant answer within a bounded cycle budget. The 0.99
distributions for sonnet and opus also carry a few null results: runs that never
converged inside the budget. That is the non-convergence cost the essay predicted a
high bar would pay, showing up in the data.

So the convergence gate is necessary but not sufficient. A gate refuses to settle for
good. It does not, on its own, find elegant when the executor floods the candidate set
with plausible alternatives and the search budget is finite.

## Correction to the published numbers

The essay and ANALYSIS.md cite haiku at 0 of 40 wyz at the default bar. That was one
candidate-set sample, taken in an earlier session, where haiku happened not to propose
the reframe. Whether a model proposes the reframe varies call to call: here it was 1 of
3 for every model. Sampled three times, haiku sits at 18.7%, not 0. The single-sample
0 of 40 was not robust. These K=3, S=100 numbers supersede it.

## Limitations

Three real candidate-set samples per model is a small sample of a stochastic model. S
seeds is only the loop RNG. The capability ordering haiku < sonnet < opus is an
assumption. The claude-code backend may be near-deterministic on a structured prompt,
which would understate candidate-set variance. This is one toy problem. It measures a
mechanism. It is not a population property of capable agents. The honest one-line
takeaway: a fluent executor false-freezes far more than a dumb one, the effect
saturates rather than scaling with capability, and the breadth of the executor's
plausible-distractor menu, not its raw capability, is what defeats the convergence
gate.
