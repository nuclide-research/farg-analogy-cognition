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

## Update: I measured it, and it corrected me (EXPERIMENT.md)

Findings 2 and 3 were written from a single live sample of one model. Later I ran the
sweep properly: four executors, three candidate-set samples each, 100 loop seeds per
sample, both bars. The full numbers and method are in `EXPERIMENT.md`. Three things
changed.

The coarse claim held. A fluent executor false-freezes far more than the dumb scout.
The scout sits at 47.7% `wyz` at the default bar. Every frontier model, haiku, sonnet,
opus, sits near 20%. Swapping a dumb proposer for a capable one more than halves the
elegant-answer rate. That is the real finding and it is robust.

The monotonic version was wrong. Among the three frontier models the rate is flat,
near 20%, not a slope. The effect saturates the moment a model is fluent enough to
offer plausible distractor readings. "More capable, more false-freeze" is true at the
dumb-to-fluent step and false past it.

The mechanism was wrong for real models. The "far side of the wall" story is the
scout's story. The frontier models often propose the reframe directly, so the elegant
answer is on the menu at full coherence from the first cycle, no wall needed, and
false-freeze still happens. The real mechanism is dilution: the elegant reading is
out-voted by a crowd of good-enough 0.93 readings and frozen out by cooling. And the
single-sample "0 of 40" in Finding 2 was not robust. Sampled three times, haiku sits
at 18.7%, because whether a model proposes the reframe varies call to call.

The fix held but is not sufficient. Raising the bar to 0.99 recovers `wyz`, but less
for the capable models (45 to 70%) than for the scout (97%), and worse the wider the
model's distractor menu. The convergence gate refuses to settle for good. It does not,
by itself, find elegant when the executor floods the candidate set and the budget is
finite.

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

## Related work: what this is really called

The base phenomenon is not new. A search loop cools onto a locally coherent answer
before a better one surfaces. That is **premature convergence under a cooling
schedule**, and it is a textbook instance of the **exploration-exploitation tradeoff**.

In evolutionary computation it is called premature convergence: the population loses
the diversity it needs to keep searching and settles on a suboptimal point. In
simulated annealing it is the quenching trap, lower the temperature too fast and the
system freezes into a local minimum because the configuration space was not explored.
The vocabulary of "false-freeze" is borrowed straight from there. An endogenous
temperature falls, uphill moves get rejected, the search locks onto the current basin.

The FARG/Copycat tradition is the closest mechanism. Copycat's computational
temperature is read off the coherence of the structures built so far. It cools as the
system finds a locally coherent answer, and cooling is commitment. The parallel
terraced scan is the loop in which the freeze happens. Snags are the named engine of
breakthrough: a better answer is reachable only through a conceptual block that raises
temperature and forces open-mindedness. Marshall and Hofstadter flagged the danger in
1996: final temperature is only a crude proxy for quality, and Copycat had no
self-watching faculty to notice it had committed to a mediocre answer. That is
false-freeze in all but the name, and their fix, Metacat, was to add the self-watching.

The LLM literature documents the same shape. Models think too fast and make premature
decisions, committing before the deeper signal lands. Hallucinations snowball when a
model over-commits to an early mistake it can separately recognize as wrong. None of
this is the contribution.

**What is claimed here is the executor-capability inversion: a more capable proposer
raises the freeze risk because it clears the local quality bar faster, never hits the
snag that would force open-mindedness, and so cools sooner.** Be honest about novelty.
The direction of this inversion is already documented. The literature reports premature
confidence rising with model scale, and stronger models anchoring harder, under the
umbrella term inverse scaling. So the directional finding is prior art. It is also not
clean. "Think Too Fast" finds reasoning models like o1 explore better, not worse, and
my own sweep agrees with that complication: it found no monotonic gradient among
frontier models (see `EXPERIMENT.md`). The effect saturates at the dumb-to-fluent step
rather than scaling with capability.

What is not yet stated in that literature is the specific mechanism: an endogenous
coherence-read temperature in an agent search loop, where the executor's own fluency
suppresses the snag that regulates cooling. The framing ties the FARG temperature
mechanism to the capability-scale inversion. That join is the only new part, and it is
a framing, not a result.

The defense follows in one line. Gate convergence on an external ground-truth check,
not the model's self-grade. The freeze is dangerous because low temperature is a
coherence proxy, not a quality measure. Replace the proxy at the commit gate and the
snag fires when it should.

### Citations

- Mitchell, *Abstraction and Analogy-Making in Artificial Intelligence* (2021). https://arxiv.org/pdf/2102.10717
- Marshall and Hofstadter, *Beyond Copycat: Incorporating Self-Watching into a Computer Model of High-Level Perception and Analogy-Making* (1996). https://science.slc.edu/jmarshall/papers/maics96.pdf
- *Hofstadterian Architecture* (notes on FARG/Copycat snags). https://notes.fringeling.com/HofstadterianArchitecture/
- *Premature convergence*, Wikipedia. https://en.wikipedia.org/wiki/Premature_convergence
- *Cooling Schedule*, Phys 466, University of Illinois. https://courses.physics.illinois.edu/phys466/sp2013/projects/2001/team1/cooling.htm
- *Multi-armed bandit*, Wikipedia. https://en.wikipedia.org/wiki/Multi-armed_bandit
- *Large Language Models Think Too Fast To Explore Effectively*. https://arxiv.org/html/2501.18009
- *How Language Model Hallucinations Can Snowball*. https://arxiv.org/abs/2305.13534
- *Anchoring Bias in Large Language Models: An Experimental Study*. https://arxiv.org/html/2412.06593v1
- *Understanding and Mitigating Premature Confidence for Better LLM Reasoning*. https://arxiv.org/abs/2605.24396
- *Discovering Language Model Behaviors with Model-Written Evaluations*. https://arxiv.org/abs/2212.09251
