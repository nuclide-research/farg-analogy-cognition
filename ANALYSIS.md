# What a 230-line toy taught me about LLM agent loops

This started as a faithfulness exercise: take Hofstadter's claim that analogy is the
core of cognition, take the control law the Fluid Analogies Research Group built to
model it, and write the smallest honest version that runs. The point was to be
correct about FARG, not to learn anything about today's agents. Then I made the
codelet executor pluggable so a real model could drive it, ran it, and the result
was the opposite of what I expected. The toy turned out to be a clean rig for one
lesson that does generalize. This is that lesson.

## The setup, in one breath

The loop has two halves. A **control layer** that is fixed and deterministic: a
coherence critic scores a candidate, an endogenous temperature is read off that
coherence (`T = T_floor + (T_max - T_floor)(1-c)^gamma`), a softmax picks the next
move at that temperature, and a wall (the snag) retracts the move, re-heats, and
activates the `opposite` concept that licenses a reframe. And an **executor** that
proposes the candidate rules. The executor is the only swappable part. Scripted
proposer by default; pass `--llm` and a real model fills that slot instead. The
model only widens the candidate set. The control layer still decides.

The toy problem is Copycat's own: `abc -> abd`, so `xyz -> ?`. The base rule is "take
the successor of the rightmost letter." On `xyz` that hits the end of the alphabet.
There is no successor of `z`. That is the wall.

## Finding 1: the executor is not the system

Swap the scripted proposer for `claude-haiku` and the answer distribution moves, even
though the control law is byte-for-byte identical. That alone is worth saying out
loud. We talk about "the model" as if the model were the agent. In any loop with a
real control layer, the model is one component, and you can change it without
changing what the system is. The scaffold around the model has its own behavior, and
that behavior is testable in isolation. Half of this repo is a test suite that never
calls a model at all.

## Finding 2: a better executor reached a worse answer

Here is the part I did not expect. Measured live, at the default settings:

```
  scripted proposer            real model (haiku)
    wyz  143/300                 yyz  21/40
    xyy   83/300                 xyy  19/40
    yyz   74/300                 wyz   0/40
```

`wyz` is the elegant answer. It is the one that needs the insight: notice the wall,
flip both the end you act on and the direction, and read `xyz` as counting down from
the left. The scripted proposer finds it as a *plurality* because the scripted
proposer is dumb. It has nothing to offer but the base rule, so it walks straight
into the wall, snags, and the snag is what activates the reframe. It finds the good
answer by failing first.

The real model is smarter. It looks at `xyz` and proposes reasonable, clean readings
right away: change the other end, change the direction, do not touch the `z`. Those
readings are coherent enough (0.93) to commit. The loop commits one, cools, and
freezes before the base rule is ever tried and snagged. The model never hits the
wall, so it never gets the insight that lives on the far side of the wall. `wyz`
drops to zero.

The smarter executor produced the worse answer, and it produced it *because* it was
smart enough to avoid the productive failure. This is not a quirk of one model. It is
structural. The elegant answer was reachable only through a snag, and a capable
proposer routes around snags by design.

## Finding 3: the fix is a quality floor on convergence

The bug is not in the model. The model did its job. The bug is that the control law
let the loop *settle* on the first thing that was merely good. The fix is one branch,
which I called aspiration-coupled cooling: refuse to freeze on any frame below a
coherence bar, and hold the temperature search-warm while you are below it, so the
scheduler keeps a real chance of re-trying the move that snags. Raise the bar from
0.90 to 0.99 and `wyz` comes back, with no change to the model:

```
                bar 0.90          bar 0.99
  scripted      wyz 143/300       wyz 290/300     (48% -> 97%)
  haiku (real)  wyz   0/40        wyz  23/40      (0% -> 58%, now the plurality)
```

The generalization is the useful part. Most agent loops have an implicit freeze bar,
and it is usually "the first answer that parses and looks plausible." That is a low
bar, and a capable model clears it instantly, which is exactly when you get a
confident, fluent, locally-coherent, mediocre answer. The lesson is not "make the
model try harder." It is "do not let the loop commit until the answer clears a bar
you set on purpose, and keep it exploring while it has not." The aspiration belongs
in the scaffold, not in the model's prompt. You can hold a fixed model to a higher
standard by changing one number in the control layer.

## Finding 4: the cheap deterministic scaffold is where correctness lives

The two real bugs I hit in this project were both in the scaffold, not the model.

The first was a determinism leak. The "fixed seed" distribution drifted a few counts
run to run. The cause was that the proposer built its candidate list by iterating
over Python sets, whose order is randomized per process by `PYTHONHASHSEED`, and that
reordered the softmax inputs. The model was not involved. The fix was to build
candidates in a fixed order. There is now a test that runs the whole distribution
under two different hash seeds and asserts they are identical.

The second was a missing give-up condition. A dead or stubborn executor that snags
every cycle would spin all the way to the cycle cap doing nothing. The fix was a
counter: stop after N consecutive snags with no clean commit. Again, the model was
not involved, and there is a test that injects a dead executor and asserts the loop
stops early.

The point is that the parts of an agent you can make deterministic are the parts you
can make *correct*, and you should push as much of the system into that region as you
can. The model is stochastic and you verify it by sampling. Everything around the
model can be pinned and unit-tested. In this repo the model-free half is the half
with the regression suite, and that is the right ratio.

## The Hofstadter tie-back

The snag is not an error to be engineered away. In FARG the snag is the mechanism. It
is the wall that forces the system to stop applying the rule it has and go looking
for a different framing. The reframe is gated by the snag, not by the temperature, a
distinction an ablation in this repo had to force me to make honestly. An executor
that is good enough to never hit the wall is an executor that never has the insight,
because in this domain the insight is on the other side of the wall.

That is the uncomfortable transfer to real agents. We are building executors that are
very good at not hitting walls. The thing we should be careful not to optimize away is
the productive failure, the moment the obvious move does not work and the system has
to think differently. If your loop always takes the first fluent answer, you have
built something that is good at avoiding exactly the failures that produce insight.
The fix is not a smarter model. It is a loop that refuses to settle for good when
elegant is one snag away.
