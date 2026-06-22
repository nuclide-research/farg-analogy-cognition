# The Capable Executor Is the False-Freeze Risk

Swap the dumb proposer for a capable model and the elegant answer vanishes. Under a byte-for-byte identical control law, the toy's plurality answer `wyz` went from 143 of 300 runs down to 0 of 40. The capable model proposed clean, locally coherent readings. They scored a coherence of 0.93, cleared the default 0.90 freeze bar, and committed before the base rule was ever tried and snagged. The smarter executor reached the worse answer. It was smart enough to route around the productive failure.

That inverts the intuition. A more capable executor does not lower false-freeze risk. It raises it. A fluent model clears a low quality bar instantly and commits to the first locally coherent answer before the productive failure ever fires. Capability and false-freeze risk move together. The defense is not a smarter model. It is a convergence gate set in the control layer and anchored on a check the executor does not author.

## What the toy actually shows

The Copycat loop has a wall. `apply_rule` returns `(None, reason)` when the operation is undefined on the target letter. The successor of `z` does not exist. When that happens, `coherence_of` short-circuits the score to exactly 0.0. The dumb proposer keeps banging the base rule into that wall. The wall activates the `opposite` concept, and `opposite` gates a slip: `rightmost` becomes `leftmost`, `successor` becomes `predecessor`. A double slip produces the elegant reframe that scores a coherence of 1.0. The reframe lives on the far side of the snag.

The capable model never gets there. It proposes a clean reading that scores 0.93, the loop cools, the loop freezes. The base rule is never tried, so the wall is never hit, so `opposite` never activates, so the slip never fires. A confident, fluent, mediocre answer. Raise the freeze bar to 0.99, one number, no model change, and `wyz` comes back as the plurality at 23 of 40.

Those numbers are one toy problem, one model, forty live runs at default settings, and a self-built critic. They illustrate a mechanism. They are not a measured property of capable agents.

## The bridge that holds

The recon loop has the same shape, with one mapping carrying the weight.

```
TOY TERM                       RECON ANALOG
-----------------------------  ------------------------------------------
snag / wall                ->  null probe: a zero-hit query, an empty
(apply_rule -> None)           top-level listing, an auth-gated redirect

reframe / slip             ->  signature variant-generation, gated on the
(opposite-gated)               snag: vary the angle, do not run blind

false-freeze               ->  capable agent labeling a shallow candidate
(c=0.93 clears 0.90)           "actionable" because it cleared a low bar

freeze bar                 ->  the verification rung as a quality floor on
(c >= bar, T low, stable)      convergence, not a stopping rule

give-up detector           ->  dead-vs-reframe, reached only by EXHAUSTION
(consec snags -> None)         of the variant space, never by assumption

executor != system         ->  split the proposer from the critic; never
(control layer is fixed)       let the actor judge whether to settle
```

The load-bearing one is false-freeze. It maps onto the methodology's hardest line with a real referent. A 200 is platform identity, not auth state. A fluent agent returns a clean, 200-shaped answer that clears a low bar and calls it a finding. It never fires the data-layer probe. The clean reading is the 0.93 answer. The reframe is the full-record pull that the smart-but-shallow loop skips. The surface already scored good enough. Skipped verification does not fail randomly. It fails systematically. Confident, reproducible, wrong numbers. The scan is the easy part, and the easy part is where the lies enter.

The snag maps to the null probe, and the methodology already treats it as load-bearing. A query returning 0 is a signal to vary the signature, not a conclusion. The slip maps to that variant-generation, and the toy makes the coupling exact. The reframe is gated on the snag, not run blind. The probe came back empty, so you vary the angle. The loop hit the wall, so it slips `opposite`. Same move, same trigger. The give-up detector maps narrowly. The toy's is a fixed counter. The methodology's is exhaustion of an open-ended variant space. The principle transfers. The threshold does not.

The architecture mapping is the design payload. The toy's control layer is byte-for-byte identical across the dumb proposer and the capable model. The proposer changed; the loop did not. Half the repo is a model-free test suite. That separation is the lesson. PentAGI splits Researcher, Developer, and Executor into distinct roles. It is a third-party reference clone, useful here only as an architecture sketch, not as NuClide code. The transferable point is the division of labor. Never let the proposer also judge whether to settle. The better the proposer, the faster it talks the loop into settling.

## Where the analogy breaks

The toy guarantees the answer is reachable. A deterministic scaffold floor unions the base rule and its opposite-gated slips into the candidate set regardless of model quality. The test suite pins the dependency: block the slip and `wyz` never appears, offer only the base rule and the loop gives up rather than converge. So the recovery earlier, the real model going from 0 of 40 at the default bar to 23 of 40 at the 0.99 bar, holds only with that floor in place. Strip it, run `--no-scaffold` with a model that proposes only clean readings, and no bar can recover the reframe, because the reframe is no longer in the candidate set. Raising the bar then buys non-convergence, not insight. The entire "raise the bar, recover the insight" result is load-bearing only because the answer was nailed to the far wall before the run started.

Real open-ended recon ships no such floor. If a model never proposes the reframe, no control law can rescue it. The second break is sharper. The toy's critic is a hand-built oracle that scores the double slip highest by construction. Real assessment has no oracle that certifies elegant beats fluent. That judgment is often exactly what the model is being trusted to make. If your coherence signal is the model's own confidence, raising the bar does not buy harder search. It buys louder self-asserted confidence. The loop becomes endless non-convergence, not insight. Refusing to settle is not free. In a real engagement it is the burned budget, the tunnel-vision dwell on one host while the clock runs out. The toy cannot run out of money, so it shows only one failure mode. The methodology pairs every "search more" with a give-up detector and the restraint ethic: slow down before burning the engagement.

So the transfer is conditional, and the conditions are not optional. It works only where the reframe is guaranteed into the candidate set by a generator the model does not control, and where the bar is gated on a mechanical ground-truth check the executor does not author. A populated-data read. A full-record pull. A byte-level banner. Names are the finding before any payload is read. You enumerate metadata, you do not exfiltrate. Verify the data class by pulling a real record, not by pattern-matching field names. Assert nothing unverified. Log blocked access as surface open, access not exercised.

## The one design implication

Build the freeze bar as a refusal to settle for good while elegant is one verified probe away. Gate it on a fired external check, never on the model's self-grade. A high bar over a self-reported confidence signal is worse than no bar. It teaches the model to claim more. The bar has to be cleared by a probe that read ground truth, or it is decorative. That single rule survives the disanalogy. The rest does not transfer on its own.

The corollary is operational. As your executor model gets more capable, you need the gate more, not less. A more fluent model produces confident, locally coherent, mediocre findings at a higher rate, not a lower one. The fix was never a smarter model. It is a loop that does not trust its own fluency as a convergence signal. VisorAgent, the active-exploitation module, runs against controlled and lab targets only, never a live operator endpoint, and that boundary holds regardless of how the convergence gate is tuned. The gate decides when to stop searching. It does not decide where to point the gun.
