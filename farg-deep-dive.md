# FARG deep-dive: Slipnet, Letter Spirit, and porting the loop to a modern agent

A four-part technical thread, built up one topic at a time. It starts from
Hofstadter's claim that analogy is the core of cognition, and ends at a runnable
prototype (`farg_loop.py`) of a FARG-flavored agent loop.

- Topic 1: the Slipnet update rule (the self-editing concept metric)
- Topic 2: Letter Spirit (the what/how tension, coherence across a whole set)
- Topic 3: mapping FARG onto a modern transformer/agent loop (what to add)
- Add #1, deep: turning solution coherence into temperature (the control law)

No em dashes anywhere by intent. ASCII diagrams are load-bearing, read them.

---

## Topic 1: The Slipnet update rule

The Slipnet is Copycat's long-term memory: a fixed graph of concepts whose metric
warps in real time. "Warps in real time" is the whole game, and it reduces to four
operations run every update cycle over two node variables and one dynamic link
variable.

### The node: two state variables

Every concept-node carries exactly two numbers (both 0 to 100):

```
   NODE  e.g. `opposite`, `successor`, `rightmost`, `a`, `group`
     |- activation   0..100   how "in play" this concept is RIGHT NOW (volatile)
     |- depth        0..100   how abstract this concept is (FIXED, hand-assigned)
```

- Activation is volatile. It rises from below (when the workspace builds a
  structure that uses the concept) and from the side (spreading from active
  neighbors). It decays every cycle.
- Conceptual depth is fixed and baked in. Surface concepts (`a`, `rightmost`) get
  low depth; abstract relational concepts (`opposite`, `identity`, `bond-category`)
  get high depth. Depth is not learned and not changed at runtime. It is the
  designer's claim about which ideas are deep.

### The link: where the deformation lives

Links are typed (successor/predecessor lateral links, category/is-a links, instance
links, and slip links like `successor`<->`predecessor`). Every link has a length:
short = conceptually close = cheap to traverse and to slip across; long = far =
improbable slippage.

The critical mechanism: a link's length is not fixed. It is governed by a label
node.

```
                 labeled by `opposite`
   successor  o==================o  predecessor
                 length = f( activation(opposite) )

   intrinsic length (say 60) when `opposite` is cold
   length -> 0          when `opposite` is fully active
```

Schematic form (the shape is canonical, the constant is Mitchell's):

```
   effective_length(link) = intrinsic_length * (1 - activation(label_node)/100)
```

Activating the label node `opposite` physically shortens every link it labels
(`successor`<->`predecessor`, `leftmost`<->`rightmost`, `first`<->`last`). That is
how context bends the concept-metric: not by moving nodes, but by retuning the
distances between them through the activation of the abstract relation that
connects them. There is no equivalent move anywhere in an embedding space.

### The per-cycle update (the four operations)

```
   1. DECAY        every node loses activation, scaled by depth
                   new_act = old_act * (depth/100)            [shape; constant is impl]
                   -> depth-100 node keeps everything; depth-0 washes out at once
                   -> ABSTRACT concepts persist, surface concepts evaporate

   2. SPREAD       active nodes push activation to neighbors,
                   amount ~ (1 - effective_length/100) * source_activation
                   -> short (currently-relevant) links transmit hard;
                      long links barely conduct

   3. JUMP         any node above a threshold may snap to full activation (100),
                   probabilistically, P rising with current activation
                   -> a concept that is "warm enough" can fully trigger

   4. RELINK       recompute every labeled link's effective length from its
                   label node's (just-updated) activation
                   -> THIS is the metric deformation; the graph's geometry
                      is now different than it was one cycle ago
```

The loop closes on itself: structures built in the workspace pump activation into
nodes, decay and spread redistribute it, triggering sharpens it, and relinking
turns that activation into changed distances, which changes which slippages the
next round of codelets can cheaply make, which changes what structures get built.
Cognition here is a metric that edits itself under the pressure of what is
currently being perceived.

### Worked micro-trace: how `opposite` rescues xyz

Problem: abc->abd, xyz->? Numbers illustrative; the dynamics are the point.

```
  STATE A (before snag)
    activation(opposite) ~ 0
    effective_length(successor<->predecessor) = 60 * (1 - 0/100)   = 60   (far)
    P(slip successor->predecessor) ~ low -> system keeps trying "rightmost->successor"

  THE SNAG
    codelet tries to take successor(z); z is `last` in the alphabet -> fails.
    Failure builds descriptions: z is `last`, like a is `first`.
    Those descriptions pump activation into `first`, `last`. `first` and `last`
    are joined by a slip link labeled `opposite` -> spreading feeds `opposite`.
    `opposite` crosses threshold -> JUMP -> activation(opposite) = 100.

  STATE B (after `opposite` triggers)
    effective_length(successor<->predecessor) = 60 * (1 - 100/100) = 0   (adjacent!)
    effective_length(leftmost<->rightmost)    -> 0
    effective_length(first<->last)            -> 0
    A correspondence codelet proposing the WHOLE FRAME FLIP
      abc <-> zyx  (rightmost<->leftmost, successor<->predecessor)
    passes its strength test cheaply. Rule "replace rightmost by successor"
    slips to "replace leftmost by predecessor". predecessor(x) = w -> wyz.
```

Depth earns its keep here: `opposite` is a deep node, so once triggered it stays
hot for many cycles (slow decay), holding all those slip links short long enough
for the system to tear down the old reading and rebuild. A shallow concept would
decay before the rebuild finished and the insight would evaporate.

### The three jobs of conceptual depth

```
   1. PERSISTENCE   deep concepts decay slowly -> an abstract insight outlives the
                    surface details that triggered it
   2. PRESSURE      deep active concepts spawn higher-urgency top-down codelets
                    -> the system works harder to honor deep ideas than shallow ones
   3. WEIGHT        a correspondence resting on deep shared concepts is STRONGER,
                    lowers temperature more -> "abc<->zyx via opposite" feels more
                    elegant than a shallow letter-by-letter map, and the system
                    knows it
```

> Insight. The Slipnet has no moving parts in space. Nodes never move; their DEPTH
> is frozen. The only thing that changes is activation, and activation's job is to
> RETUNE LINK LENGTHS. So "two concepts became close" is never a point sliding
> toward another point (the embedding picture). It is an abstract relation
> (`opposite`) waking up and pulling its endpoints together. Closeness is mediated
> by a third, deeper concept, and that mediation is recomputed every cycle.

---

## Topic 2: Letter Spirit

Copycat, Tabletop, and Metacat each produce one answer to one problem. Letter
Spirit is the FARG model that has to produce a whole mutually-consistent set and
keep it coherent. It is built on Hofstadter's deepest claim about categories: that
what a thing is and how it is done cannot be pried apart. The name encodes the
thesis. A "letter" (its category) and its "spirit" (its style) are the two things
in tension.

### The domain: gridfonts, and why

Letters drawn on a small fixed grid of dots, using only a fixed inventory of legal
straight segments (the "quanta," on the order of 56). A gridletter is a subset of
those segments. The grid is a deliberate cage, the same methodological move as
letter-strings for Copycat: strip the medium down so the conceptual problem stands
naked. What makes an 'a' an 'a', and what makes two letters belong to the same
font?

### The central tension: letter (what) vs. spirit (how)

```
   LETTER  = categorical identity   the abstract "a-ness" that survives any style
   SPIRIT  = stylistic identity     the consistent FLAVOR this particular font
                                      brings to every letter it renders
```

The thesis and the hard part: you cannot cleanly separate them. There is no
pipeline of "design pure a-ness, then apply a style filter." The style is expressed
through the very features that carry the category, and the category is only ever
seen through some style. Push on the category and you move the style; push on the
style and you risk the letter no longer reading.

### Roles: the trick that lets one machinery carry both

A letter-category is a structure of roles plus norms: 'the bowl', 'the ascender',
'the crossbar', 'the post', 'the tail'. Recognition is mapping a gridletter's parts
onto the roles of some category.

```
   CATEGORY (what)  =  WHICH roles are present and how they connect
   STYLE    (how)   =  the consistent way roles are REALIZED across letters
                       (this font always: high crossbars, left-leaning posts ...)
```

Style is a cross-letter regularity in role-realization; category is the
role-structure itself. The same role machinery carries both, which is why they
cannot separate: they are two readings of one mark.

### Architecture: four modules around the central feedback loop of creativity

```
                |-----------------------------------------------|
                |        THE CENTRAL FEEDBACK LOOP OF CREATIVITY  |
   spirit so far|   |----------|  abstract spec  |---------|     |
   ------------>|   | IMAGINER | --------------->| DRAFTER |     |
                |   | what to  |                 | render  |     |
                |   | try next |                 | to grid |     |
                |   |----------|                 |----+----|     |
                |        ^                            |          |
                |        | revise                     v          |
                |   |----+------|  "still reads?"  |---------|    |
                |   |ADJUDICATOR|<----------------| EXAMINER |    |
                |   | "our      |  letter-id +    | recognize|   |
                |   |  spirit?" |  confidence     | category |   |
                |   |-----------|                 |---------|    |
                |-----------------------------------------------|
```

- Imaginer proposes what to try next, biased by the induced spirit.
- Drafter turns an abstract role-spec into concrete grid segments.
- Examiner perceives the drafted gridletter and recognizes its category (the
  "what"). McGraw 1995. This is pure Topic-1 machinery (Slipnet of roles, workspace
  holding the gridletter, codelets building part-to-role correspondences,
  temperature, conceptual slippage on ambiguous parts).
- Adjudicator perceives the style (the "how"): induces the font's norms from
  accepted letters and judges fit. Rehling 2001, the part that made it a full
  creative system.

A new letter is accepted only when the Examiner says "this still reads as a 'k'"
AND the Adjudicator says "this is in our spirit." Fail either and the loop revises.

### Why this is the "coherence across a set" model

```
   Copycat / Tabletop / Metacat   ->  ONE answer, evaluated locally
   Letter Spirit                  ->  26 artifacts, evaluated GLOBALLY
                                      each must read correctly (local)
                                      all must share one spirit (global)
```

The constraint is a fixed point. There is no spirit specified up front; it is
induced from a few seed letters and extrapolated to 21 unseen categories. Each new
letter is itself an analogy: the spirit is the shared essence, transferred to a new
categorical target. The system can be wrong about its own spirit until enough of
the alphabet exists to pin it down.

### Bridge to Topic 1

Letter Spirit reuses the Slipnet engine for perception and wraps creation around
it. The Examiner is Copycat's deforming-metric machine pointed at gridletters. What
Letter Spirit adds: a second perceptual axis (the Adjudicator perceiving style) and
a closed make-and-check loop where perception drives generation and back.

> Insight. Every other FARG model answers "what is the analog of X?" once. Letter
> Spirit answers "make the whole set in the same spirit," forcing a GLOBAL
> coherence constraint with no spec, only seeds. It sites that constraint on
> Hofstadter's central nerve, the inseparability of WHAT from HOW, by making both
> ride on the same ROLE structure.

---

## Topic 3: Mapping FARG onto a modern agent loop

Given everything a transformer and an agent harness already do, what is actually
missing, and what would you bolt on to approximate FARG?

### The honest baseline (do not reinvent these)

```
   FARG idea                     already present (crudely) as
   ---------------------------   ---------------------------------------
   activation / context-sense    self-attention (context-conditioned reps)
   parallel exploration          best-of-n, self-consistency, ToT / MCTS
   build-and-backtrack            tree-of-thought branch + backtrack
   self-critique                  Reflexion / verifier / LLM-as-judge
   a temperature knob             sampling temperature (softmax on output)
```

The gap is not "agents can't explore or critique." It is how these are controlled
and represented. Four things are missing in kind, not degree.

### The mapping (FARG -> nearest analog -> gap -> concrete add)

```
 FARG MECHANISM            NEAREST TODAY              MISSING                    ADD
 -----------------------   ------------------------   ------------------------   -----------------------------
 Slipnet activation/spread self-attention             resets each forward pass   external concept graph with
                                                       no persistent metric       runtime activation
 label-gated link length   (nothing; attention soft)  THE BIGGEST GAP. metric    explicit slip(X,P) op over
 = SLIPPAGE                                            frozen post-train          the external graph
 conceptual DEPTH          token freq / nothing       no persistence ranking     tag concepts w/ depth; deep
                                                       of abstractions            ones persist, resist override
 Coderack scheduler        best-of-n / parallel       no staged commit; all      population of probes, urgency
                            sampling                   goal-conditioned           + ALWAYS-ON bottom-up scouts
 terraced scan             ToT / MCTS expansion       expand by flat self-eval   cheap-propose -> cheap-test
                                                                                  -> expensive-commit relay
 workspace build AND       CoT scratchpad             CoT MONOTONIC; can't       typed editable blackboard
 DESTROY                    (append-only)             retract                    with a real RETRACT op
 TEMPERATURE endogenous,   sampling temp (EXOGENOUS,  not state-derived; no      coherence critic -> temp +
 coherence-read, re-heats   fixed by hand)            re-heat on snag            discard prob; SPIKES on snag
 Metacat THEMES            CoT text / sys-prompt      not a typed object;        explicit theme stack: name,
 (reified, clampable)       strategy                  can't clamp or compare     clamp, compare-by-theme
 Metacat episodic trace +  Reflexion / scratch mem    over raw text; no loop     structured process log keyed
 self-watching                                        detection over PROCESS     by theme+slip; rut detector
 Letter Spirit dual-axis + multi-file gen + global    no induced spirit model;   induced spirit + adjudicator
 set coherence              critic (rare)             weak reopen of committed   that reopens to a fixed point
```

### The four additions that actually matter

1. Endogenous temperature (the most distinctive missing piece). An LLM's sampling
   temperature is hand-set and fixed. Copycat's is read off solution coherence,
   feeds back into how recklessly it samples and how willing it is to demolish, and
   RE-HEATS on a snag. See the control law section below.

2. An editable workspace with a real retract. CoT is append-only; dead reasoning
   still conditions everything after it. FARG destroys structures. Add a typed
   blackboard the agent reads, writes, and DELETES from, with live context rebuilt
   from the current blackboard, not the full history.

3. An external deforming metric with an explicit slippage op. You cannot make the
   transformer's internal metric deform at runtime; it froze at pretraining. Put an
   editable metric beside it and expose one op:
   `slip(concept X, pressure P) -> Y` ("under P, X's nearest relative is Y").

4. Reified themes + episodic self-watching. A theme is a named, typed pressure
   driving the current approach. Make it clampable (steer search), comparable (are
   two solutions the same idea?), and logged episodically with a rut detector that
   forces a re-heat when it re-enters an equivalent state.

### Reference architecture: a FARG-flavored agent loop

```
                         |----------------------------------------------|
        bottom-up scouts |  SCHEDULER (urgency-weighted probe queue)     | top-down probes
        (always-on)  --->|   pick probe ~ urgency; staged commit         |<--- (hot themes /
                         |---------------+------------------------------|      active concepts)
                                         | run one probe
                                         v
                              |--------------------|   reads/writes/RETRACTS
                              |   LLM (executor)    |<--------------------------|
                              |  proposes/tests one |                           |
                              |  small structure    |----------|                |
                              |--------+------------|          v                |
                  calls slip(X,P)      |            |-------------------|       |
                         v             |            |  WORKSPACE         |------|
              |--------------------|   |            |  (typed, editable, |
              | CONCEPT METRIC      |  |            |   retractable)     |
              | activation + depth  |  |            |-------+-----------|
              | + label-gated edges |  |                    | structure quality
              | -> licensed slips   |  |                    v
              |--------------------|   |            |-------------------|
                                       |            | COHERENCE CRITIC  |
              |--------------------|   |            | -> TEMPERATURE     |
              | THEME STACK         |<-|            | (sampling sharpness|
              | name / clamp /      |               |  + discard prob;   |
              | compare             |               |  SPIKES on snag)   |
              |--------+-----------|                |-------+-----------|
                       |                                    |
                       v                                    |
              |--------------------|<---------------------- |
              | EPISODIC MONITOR    |  detects ruts -> forces re-heat / new clamp
              | log by theme+slip   |
              |--------------------|
```

The LLM is no longer the whole system; it is the codelet executor inside a loop
whose control (temperature, scheduling, retract, slippage, themes, rut-detection)
lives in cheap external machinery.

> Insight. The frozen metric is the only FARG capability you genuinely cannot
> retrofit into a transformer, so you externalize it. Everything else FARG has and
> agents lack is a CONTROL-LAYER absence, not a model absence: temperature read off
> coherence that re-heats on a snag, a workspace you can DESTROY from, themes you
> can clamp and compare, and a monitor that watches the process for ruts.

---

## Add #1, deep: turning solution coherence into temperature

The highest-leverage bolt-on, because it is the one control signal a modern agent
loop completely lacks.

### What "coherence" is, operationally

A scalar c in [0,1] aggregating four signals over the current partial solution:

```
   c = w1*consistency + w2*coverage + w3*support + w4*goal_proximity     (sum w = 1)

   consistency    1 - (contradictions among committed structures, normalized)
   coverage       fraction of the problem's "objects" incorporated into structure
   support        mean verifier/critic confidence over committed structures
   goal_proximity 1 - normalized distance to the acceptance criteria
```

Discipline: consistency and coverage are cheap and structural (run every cycle);
support and goal_proximity may need a judge (run on transitions only). Coherence is
mostly a structural read of the blackboard, with judgment sampled sparingly. If you
let it become one expensive vibe-check per step, you have rebuilt LLM-as-judge.

### The control law: c -> temperature -> three actions

```
   T = T_floor + (T_max - T_floor) * (1 - c)^gamma              # endogenous temperature

   (a) sampling sharpness   tau = tau_min + (tau_max - tau_min)*(T/T_max)
                            high T -> flat softmax -> EXPLORE; low T -> sharp -> COMMIT
   (b) demolish willingness P(retract structure) = delta * (T/T_max)^eta
   (c) scout ratio          scout_frac = s_min + (s_max - s_min)*(T/T_max)
                            high T -> more bottom-up curiosity probes
```

```
   T
  Tmax| o                                    o snag re-heat (impulse, then decay)
      |  oo                                  |
      |    ooo                              | o
 Tfloor|.........ooooooooooooooo===========+......ooooooo  <- floor never reaches 0
      +------------------------------------------------> coherence c (and time ->)
        c low (incoherent)        c high (coherent)   snag drops c, T jumps
```

Two non-negotiable invariants from FARG:
- T_floor > 0 and s_min > 0. Exploration never fully dies. If T hits 0 you get a
  confident freeze with no escape, the wrong-but-sure failure.
- gamma is the convergence aggressiveness. Low gamma wanders; high gamma commits
  early and risks a false freeze.

### Re-heat dynamics (what makes it FARG, not simulated annealing)

A smooth T = f(c) alone is just adaptive annealing. The FARG-defining behavior is
the snag: a discrete event that forces heat back in against the smooth trend.

```
   snag triggers (any of):
     * a contradiction appears among committed structures
     * a goal sub-condition is proven unreachable under the CURRENT frame
     * N consecutive probes fail to extend the structure
     * the episodic rut-detector fires

   on snag:  T <- max(T, T_reheat)        # impulse up
             then T decays back toward f(c) over k cycles
```

Without the snag impulse, a system that has cooled into a locally-coherent wrong
frame stays there. The snag is the only thing that injects the heat needed to
retract committed structure and let slip() propose a reframe. The snag detector is
therefore the reliability-critical component.

### The one real failure: false freeze

```
   build structure -> c rises -> T falls -> choices sharpen + demolish-prob falls
        -> reinforces the dominant structure -> c rises further -> FREEZE
           (convergence when the frame is RIGHT; a confident error when WRONG)
```

Three antidotes, all required together: residual exploration at all temperatures
(T_floor, s_min > 0), a sensitive snag detector, and a CALIBRATED coherence critic.
If the critic says coherent when it is not, you freeze on a false high c and no snag
fires. Prefer structural signals that cannot be fooled by fluent-but-wrong text.

A fourth antidote, found and measured while running farg_loop.py with a real model:
ASPIRATION-COUPLED COOLING. Give the freeze a quality bar (freeze_bar) and refuse to
cool into a freeze on any frame below it; hold the temperature search-warm while
unsatisfied. The prototype made the failure concrete. With claude-haiku as the
executor, the model proposed simpler "change the other end" readings at coherence
0.93; the loop cooled and froze on them and the elegant 1.0 answer (reachable only
through a snag) appeared 0 times in 40 runs. Raising the bar from 0.90 to 0.99
recovered it: scripted 48% -> 97%, the real model 0% -> 58%, with NO change to the
model. The mechanism: below the bar the controller stays warm, so the scheduler
keeps re-trying the snag-inducing base rule, the snag activates `opposite`, and the
reframe surfaces and locks. The lesson generalizes: a freeze with no quality floor
will settle for the first locally-coherent answer an executor happens to offer, and
a better executor that offers a "good enough" escape can paradoxically reach a worse
answer by never being forced through the snag that the elegant answer requires.

### Cost discipline: tiered measurement

```
   every cycle (cheap, structural):   consistency, coverage   -> provisional c
   on a transition (commit/retract):  support, goal_proximity -> refresh c
   on a candidate snag:               one focused judge call to confirm the snag
```

### How this differs from what exists

```
   classical simulated annealing : T(t) on a FIXED schedule, blind to state,
                                   CANNOT re-heat
   LLM sampling temperature      : a hand-set CONSTANT, exogenous, global
   entropy-aware adaptive sampling : T keyed to TOKEN-level predictive entropy
                                     (local uncertainty), not solution coherence
   THIS (FARG-ported)            : T endogenous, read off SOLUTION-level coherence,
                                   adaptive, and RE-HEATABLE on a snag
```

### Implementable spec (realized in farg_loop.py)

```
   state: workspace W, episodic log E, temperature T
   loop each cycle:
     c_struct   = w1*consistency(W) + w2*coverage(W)             # cheap, every cycle
     if transition: c = c_struct + w3*support(W) + w4*goal_prox(W)
     else:          c = blend(c_struct, last_full_c)
     T = T_floor + (T_max - T_floor)*(1 - c)^gamma
     if snag_detected(W, E): T = max(T, T_reheat); log_snag(E)
     tau        = tau_min + (tau_max - tau_min)*(T/T_max)
     p_discard  = delta*(T/T_max)^eta
     scout_frac = s_min + (s_max - s_min)*(T/T_max)
     # scheduler: with prob scout_frac pick a bottom-up scout else top-down probe
     # run probe via LLM at sampling temp tau; maybe commit; maybe retract (p_discard)
     if c >= c_accept and T <= T_freeze: return W      # converged
```

> Insight. The control law is four lines, but the engineering risk lives in two
> places: the coherence read and the snag detector. Make coherence mostly
> STRUCTURAL so fluent-but-wrong text cannot inflate it, and make the snag detector
> sensitive enough to re-heat before a wrong frame hardens. The smooth c->T curve
> gives you adaptive annealing; the discrete snag impulse is the one thing that
> separates a FARG loop from a fancy temperature schedule.

---

## References (FARG primary sources)

- D. Hofstadter and the Fluid Analogies Research Group, "Fluid Concepts and
  Creative Analogies," 1995.
- M. Mitchell, "Analogy-Making as Perception" (Copycat), 1993.
- R. French, "The Subtlety of Sameness" (Tabletop), MIT Press, 1995.
- G. McGraw, "Letter Spirit: Emergent High-Level Perception of Letters Using Fluid
  Concepts," 1995 (the Examiner).
- J. Rehling, "Letter Spirit (Part Two): Modeling Creativity in a Visual Domain,"
  2001 (the full creative loop, the Adjudicator).
- J. Marshall, "Metacat: A Self-Watching Cognitive Architecture," 1999 (themes,
  episodic trace, self-watching).
