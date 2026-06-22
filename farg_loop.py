#!/usr/bin/env python3
"""
farg_loop.py - the smallest honest FARG-flavored agent loop.

What this demonstrates (and what it does NOT fake):
  The Topic-A control law made runnable. An ENDOGENOUS temperature, read off the
  COHERENCE of the current partial solution, plus a slip()-based REFRAME over an
  editable workspace. A snag does two SEPARATE things (this distinction was forced
  by adversarial ablation, see "What the ablation proved" below): it activates the
  `opposite` concept (which GATES the reframe) and it re-heats the temperature
  (which lengthens post-snag exploration). You can watch the loop cool on an easy
  frame, hit a wall, slip two concepts, and rebuild.

Domain (Copycat's own toy, chosen because it has a real snag):
  Given S0 -> S1, transform T0 by the same idea.
    abc -> abd ;  ijk -> ?     clean: rightmost+successor -> ijl   (NO snag)
    abc -> abd ;  xyz -> ?     z has no successor -> SNAG -> opposite activates
                               (gates the slip) + re-heat -> double-slip -> wyz

Honesty boundary (read this before trusting the demo):
  * The FARG CONTROL LAYER is real and runs offline with the stdlib only:
      - a mini-Slipnet with activation + depth + an `opposite` relation and slip()
      - an editable Workspace with a real retract
      - a STRUCTURAL coherence critic: on a clean apply, consistency/coverage/goal
        are constant 1.0 and only the 0.30*support term varies, so the signal that
        actually DISCRIMINATES the reframe (rule_support) is 100% structural; a
        wall short-circuits coherence to exactly 0.0
      - the endogenous temperature law  T = T_floor + (T_max-T_floor)*(1-c)^gamma
        plus a discrete SNAG re-heat impulse. Honest caveat: at the snag INSTANT
        c is forced to 0 so the law alone already gives T=T_max, and max(T_max,
        0.90) = T_max, so the impulse adds zero heat that cycle; its only
        measurable effect is to keep T elevated over the next few post-snag cycles
        (longer exploration, a few-percent shift in the answer distribution)
      - a temperature-gated stochastic scheduler (softmax at temp tau; scouts vs
        top-down probes)
  * The EXECUTOR is pluggable. ScriptedProposer ships as the default so the loop is
    watchable OFFLINE with the stdlib only. LLMProposer is now wired (opt-in via
    `--llm`): it asks a real model for candidate (pos, op) rules and parses +
    validates them into Rule objects against the legal vocabulary. The model only
    WIDENS the candidate set; the control layer (coherence critic -> temperature ->
    softmax selection, snag -> retract + `opposite`-gated slip) is byte-for-byte
    unchanged and still decides. By default a deterministic SCAFFOLD floor (base
    rule + opposite-gated slips) is unioned in, so the reframe is guaranteed
    regardless of model quality; `--no-scaffold` strips it to show the model's raw
    contribution. The client is lazy-imported, so this file stays importable and the
    offline demo stays stdlib-only when no SDK or API key is present.
  * NOTHING is hardcoded to the answer. `wyz` is not a string anywhere in the
    decision path. It EMERGES from slip(rightmost)->leftmost and
    slip(successor)->predecessor, each gated by the `opposite` concept that the
    snag (not the programmer) activates. Grep the file: every occurrence of
    "wyz" is in this docstring; it is never a literal in the decision path.

What the ablation proved (do not overclaim the temperature):
  * Remove slip entirely (base rule only): 50/50 xyz runs return None, stuck in a
    permanent snag loop. The slip is causally load-bearing.
  * Turn the re-heat OFF (snag() a no-op): still solves 300/300 with the same
    answers. Block only the `opposite` activation (re-heat fully on): 300/300 None.
    So the REFRAME IS GATED BY THE `opposite` ACTIVATION, NOT BY THE RE-HEAT. The
    two merely share the snag trigger; do not claim the heat drives the reframe.
  * The mirror case zyx -> ? reproduces the mechanism symmetrically: it infers
    (leftmost, predecessor), hits the LEFT wall, double-slips to (rightmost,
    successor) and yields abd as its plurality. Not xyz-special-cased.
"""

from __future__ import annotations
import random
from dataclasses import dataclass, field

# ----------------------------------------------------------------------------
# alphabet primitives  (the "wall" lives here: z has no successor, a no predecessor)
# ----------------------------------------------------------------------------

def successor(ch: str):
    return None if ch == "z" else chr(ord(ch) + 1)

def predecessor(ch: str):
    return None if ch == "a" else chr(ord(ch) - 1)

OPS = {"successor": successor, "predecessor": predecessor,
       "identity": lambda c: c}

# ----------------------------------------------------------------------------
# mini-Slipnet:  nodes have activation + (fixed) depth; `opposite` gates slips
# ----------------------------------------------------------------------------

# opposite pairs are the slip links; `opposite` is the deep label node that,
# when activated, makes these links cheap to traverse (Topic 1's label-gated length)
OPPOSITES = {"rightmost": "leftmost", "leftmost": "rightmost",
             "successor": "predecessor", "predecessor": "successor",
             "first": "last", "last": "first"}

class Slipnet:
    def __init__(self):
        # activation in [0,1]; depth in [0,1] (deep -> slow decay, Topic 1 step 1)
        self.activation = {"opposite": 0.0}
        self.depth = {"opposite": 0.90}      # `opposite` is an abstract, deep concept
        self.SLIP_THRESHOLD = 0.50           # link is "short enough" to slip above this

    def bump(self, concept: str, amount: float = 1.0):
        self.activation[concept] = min(1.0, self.activation.get(concept, 0.0) + amount)

    def decay(self):
        # depth-scaled decay: deep concepts persist, shallow ones wash out (Topic 1)
        for c, a in list(self.activation.items()):
            self.activation[c] = a * self.depth.get(c, 0.30)

    def slip(self, concept: str) -> str:
        """Return the opposite-linked concept IFF `opposite` is activated past the
        threshold; otherwise the concept stands. This is the whole reframing
        primitive. It consults state; it does not know about any answer."""
        if concept in OPPOSITES and self.activation.get("opposite", 0.0) >= self.SLIP_THRESHOLD:
            return OPPOSITES[concept]
        return concept

# ----------------------------------------------------------------------------
# rules (the structures built on the workspace) + how they apply / snag
# ----------------------------------------------------------------------------

@dataclass(frozen=True)
class Rule:
    pos: str   # leftmost | rightmost | middle
    op: str    # successor | predecessor | identity

    def __str__(self):
        return f"({self.pos}, {self.op})"

def _index(pos: str, s: str) -> int:
    return {"leftmost": 0, "rightmost": len(s) - 1, "middle": len(s) // 2}[pos]

def apply_rule(rule: Rule, s: str):
    """Returns (result_string, None) on a clean apply, or (None, reason) on a SNAG
    (the wall: no successor of z / no predecessor of a)."""
    i = _index(rule.pos, s)
    newch = OPS[rule.op](s[i])
    if newch is None:
        return None, f"wall: {rule.op}('{s[i]}') is undefined"
    return s[:i] + newch + s[i + 1:], None

def infer_rule(s0: str, s1: str) -> Rule:
    """Read S0->S1 to get the base rule. abc->abd : index 2 (rightmost), c->d (successor)."""
    i = next(k for k in range(len(s0)) if s0[k] != s1[k])
    pos = {0: "leftmost", len(s0) - 1: "rightmost"}.get(i, "middle")
    if successor(s0[i]) == s1[i]:
        op = "successor"
    elif predecessor(s0[i]) == s1[i]:
        op = "predecessor"
    else:
        op = "identity"
    return Rule(pos, op)

# ----------------------------------------------------------------------------
# editable workspace (with a real retract)
# ----------------------------------------------------------------------------

@dataclass
class Workspace:
    rule: Rule | None = None
    result: str | None = None
    def commit(self, rule: Rule, result: str): self.rule, self.result = rule, result
    def retract(self): self.rule, self.result = None, None

# ----------------------------------------------------------------------------
# coherence critic  (mostly STRUCTURAL: a wall tanks it to 0)
# ----------------------------------------------------------------------------

@dataclass
class Problem:
    s0: str; s1: str; target: str
    base_rule: Rule = field(init=False)
    def __post_init__(self): self.base_rule = infer_rule(self.s0, self.s1)

def rule_support(rule: Rule, base: Rule) -> float:
    """Reward (a) keeping the ORIGINAL change's shape (an end position + a
    directional op) and (b) THEME COHERENCE: how many components were slipped
    under the SAME `opposite` theme. Both end-touching directional => the double
    opposite-slip scores highest. This is why the coherent reframe wins; it is
    not a lookup of any particular string."""
    if rule == base:
        return 1.0
    mirror = 1.0 if (rule.pos in ("leftmost", "rightmost")
                     and rule.op in ("successor", "predecessor")) else 0.5
    slipped = (1 if rule.pos == OPPOSITES.get(base.pos) else 0) + \
              (1 if rule.op == OPPOSITES.get(base.op) else 0)
    theme = slipped / 2.0
    return 0.5 * mirror + 0.5 * theme

def coherence_of(rule: Rule, prob: Problem):
    """c in [0,1]. A snag (result None) short-circuits c to exactly 0.0 (the branch
    returns before consistency/coverage/goal/support are ever computed)."""
    result, snag = apply_rule(rule, prob.target)
    if result is None:
        return 0.0, None, snag
    consistency, coverage, goal = 1.0, 1.0, 1.0
    support = rule_support(rule, prob.base_rule)
    c = 0.40 * consistency + 0.15 * coverage + 0.15 * goal + 0.30 * support
    return c, result, None

# ----------------------------------------------------------------------------
# endogenous temperature controller (Topic A) + snag re-heat impulse
# ----------------------------------------------------------------------------

class Temperature:
    def __init__(self, T_max=1.0, T_floor=0.05, gamma=2.0, T_reheat=0.90):
        self.T_max, self.T_floor, self.gamma, self.T_reheat = T_max, T_floor, gamma, T_reheat
        self.reheat_impulse = 0.0
        self.value = T_max

    def update(self, c: float) -> float:
        law = self.T_floor + (self.T_max - self.T_floor) * (1.0 - c) ** self.gamma
        self.value = max(law, self.reheat_impulse)      # impulse can push T up vs the law
        self.reheat_impulse *= 0.5                       # impulse decays each cycle
        return self.value

    def snag(self):
        self.reheat_impulse = self.T_reheat              # re-heat AGAINST rising coherence

    # tau = softmax temperature for internal choices (hot -> flat, cold -> sharp)
    def tau(self) -> float:
        return 0.12 + 0.60 * (self.value / self.T_max)

# ----------------------------------------------------------------------------
# executor (pluggable). Scripted ships; LLM is a one-class swap.
# ----------------------------------------------------------------------------

class ScriptedProposer:
    """Proposes candidate rules. Bottom-up scout always offers the base rule.
    Top-down probes (only when `opposite` is activated) offer the slipped variants,
    built by calling slipnet.slip() on the base rule's components. The proposer
    never reasons about the target answer; it just generates structurally-licensed
    candidates and lets the critic + temperature decide."""
    def propose(self, prob: Problem, net: Slipnet) -> list[Rule]:
        base = prob.base_rule
        cands = [base]                                   # scout (bottom-up)
        if net.activation.get("opposite", 0.0) >= net.SLIP_THRESHOLD:
            sp, so = net.slip(base.pos), net.slip(base.op)   # slip endpoints
            for p in {base.pos, sp}:
                for o in {base.op, so}:
                    r = Rule(p, o)
                    if r != base:
                        cands.append(r)
        # de-dup, preserve order
        seen, out = set(), []
        for r in cands:
            if r not in seen:
                seen.add(r); out.append(r)
        return out

# ---- LLM executor (wired). Imports stay lazy so the offline demo needs no SDK. --

_VALID_POS = {"leftmost", "rightmost", "middle"}
_VALID_OP = {"successor", "predecessor", "identity"}

def _parse_rules(raw: str) -> list[Rule]:
    """Parse a model reply into VALIDATED Rule objects. Pull the first JSON array,
    keep only entries whose (pos, op) are in the legal vocabulary, dedup. Anything
    malformed is silently dropped - the control layer is never fed an illegal rule."""
    import json, re
    if not raw:
        return []
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    try:
        data = json.loads(m.group(0) if m else raw)
    except Exception:
        return []
    out, seen = [], set()
    for item in data if isinstance(data, list) else []:
        if not isinstance(item, dict):
            continue
        pos = str(item.get("pos", "")).strip().lower()
        op = str(item.get("op", "")).strip().lower()
        if pos in _VALID_POS and op in _VALID_OP:
            r = Rule(pos, op)
            if r not in seen:
                seen.add(r); out.append(r)
    return out

_DEFAULT_MODELS = {"claude-code": None, "anthropic": "claude-haiku-4-5-20251001",
                   "ollama": "llama3.2", "openai": "gpt-4o-mini"}

def make_llm_client(backend: str, model: str | None = None):
    """Return a callable  prompt:str -> completion:str  for the chosen backend.
    Lazy-imports the SDK/CLI inside the branch so importing this module never
    requires it. `claude-code` shells out to the installed `claude` CLI in headless
    mode and uses your logged-in Claude Code (Max/Pro) auth - no API key needed, the
    right default when you have a subscription rather than API credits.
    anthropic/openai read an API key from env; ollama runs LOCAL (no cloud egress)."""
    model = model or _DEFAULT_MODELS.get(backend)
    if backend == "claude-code":
        import subprocess, shutil
        exe = shutil.which("claude")
        if not exe:
            raise RuntimeError("the `claude` CLI is not on PATH (install Claude Code)")
        def call(prompt: str) -> str:
            # headless one-shot using the logged-in subscription auth. cwd is neutral
            # so a project CLAUDE.md cannot leak into the codelet prompt.
            cmd = [exe, "-p", prompt, "--output-format", "text"]
            if model:
                cmd += ["--model", model]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd="/tmp")
            if r.returncode != 0:
                raise RuntimeError(r.stderr.strip() or f"claude exited {r.returncode}")
            return r.stdout
        return call
    if backend == "anthropic":
        from anthropic import Anthropic            # pip install anthropic ; ANTHROPIC_API_KEY
        client = Anthropic()
        def call(prompt: str) -> str:
            msg = client.messages.create(
                model=model, max_tokens=512,
                messages=[{"role": "user", "content": prompt}])
            return "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
        return call
    if backend == "ollama":
        import ollama                              # local daemon; no network egress
        def call(prompt: str) -> str:
            r = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}])
            return r["message"]["content"]
        return call
    if backend == "openai":
        from openai import OpenAI                  # pip install openai ; OPENAI_API_KEY
        client = OpenAI()
        def call(prompt: str) -> str:
            r = client.chat.completions.create(
                model=model, max_tokens=512,
                messages=[{"role": "user", "content": prompt}])
            return r.choices[0].message.content or ""
        return call
    raise ValueError(f"unknown backend: {backend!r} (use anthropic|ollama|openai)")

class LLMProposer:
    """The swap point, now real. Same propose(self, prob, net) -> list[Rule] contract
    as ScriptedProposer, so solve() does not change. It asks a model for candidate
    rules, parses+validates them, and (by default) UNIONs in the deterministic
    scaffold floor so the control layer's guarantees hold no matter what the model
    says. The model is asked ONCE per problem (the prompt does not depend on cycle or
    net state), so its reply is cached and the per-cycle cost is just the cheap
    scaffold recompute."""

    PROMPT = (
        "You are a single perception codelet in a Copycat-style analogy solver.\n"
        "A transformation maps string S0 to S1. Propose candidate rules that would "
        "transform the target string T0 in the SAME spirit.\n\n"
        "A rule is a (position, operation) pair:\n"
        "  position  in: leftmost | rightmost | middle\n"
        "  operation in: successor | predecessor | identity\n"
        "The alphabet has walls: 'z' has no successor, 'a' has no predecessor. If the "
        "obvious rule would hit a wall on T0, ALSO propose how it could bend (flip the "
        "end you act on, or flip the direction).\n\n"
        "S0 = {s0}\nS1 = {s1}\nT0 = {t0}\n\n"
        "Reply with ONLY a JSON array of objects, each {{\"pos\": ..., \"op\": ...}}, "
        "ordered most-natural first, 1 to 5 rules. No prose."
    )

    def __init__(self, client, *, scaffold: bool = True, verbose: bool = False):
        self.client = client          # callable: prompt -> completion text
        self.scaffold = scaffold      # keep the deterministic control-layer floor
        self.verbose = verbose
        self._cache: dict[str, str] = {}
        self.last_raw: str | None = None
        self.last_parsed: list[Rule] = []

    def propose(self, prob: Problem, net: Slipnet) -> list[Rule]:
        prompt = self.PROMPT.format(s0=prob.s0, s1=prob.s1, t0=prob.target)
        if prompt not in self._cache:
            try:
                self._cache[prompt] = self.client(prompt)
            except Exception as e:                # network/key/SDK failure -> scaffold floor
                self._cache[prompt] = ""
                if self.verbose:
                    print(f"  [LLM error: {e}; falling back to scaffold]")
        raw = self._cache[prompt]
        self.last_raw = raw
        cands = _parse_rules(raw)
        self.last_parsed = list(cands)
        if self.scaffold:                         # union the deterministic floor in
            for r in ScriptedProposer().propose(prob, net):
                if r not in cands:
                    cands.append(r)
        elif not cands:                           # no floor and model gave nothing usable
            cands = [prob.base_rule]
        return cands

# ----------------------------------------------------------------------------
# the loop
# ----------------------------------------------------------------------------

def softmax_choice(items, scores, tau, rng):
    import math
    ws = [math.exp(s / max(tau, 1e-6)) for s in scores]
    tot = sum(ws)
    r, acc = rng.random() * tot, 0.0
    for it, w in zip(items, ws):
        acc += w
        if r <= acc:
            return it
    return items[-1]

def solve(prob: Problem, proposer=None, seed=0, max_cycles=40, verbose=False):
    rng = random.Random(seed)
    proposer = proposer or ScriptedProposer()
    net, ws, temp = Slipnet(), Workspace(), Temperature()
    last_clean, stable = None, 0
    trace = []

    for cycle in range(1, max_cycles + 1):
        cands = proposer.propose(prob, net)
        scored = [(r, coherence_of(r, prob)) for r in cands]
        # choose a candidate by coherence, softmax-sharpened by the CURRENT temperature
        items = [r for r, _ in scored]
        cvals = [c for _, (c, _, _) in scored]
        chosen = softmax_choice(items, cvals, temp.tau(), rng)
        c, result, snag = coherence_of(chosen, prob)

        if snag:                                         # SNAG path
            ws.retract()
            net.bump("opposite", 1.0)                    # the snag activates `opposite`
            temp.snag()                                  # re-heat
            T = temp.update(c)
            last_clean, stable = None, 0
            trace.append((cycle, chosen, None, c, T, temp.tau(), "SNAG->retract+reheat"))
        else:                                            # clean apply
            ws.commit(chosen, result)
            T = temp.update(c)
            stable = stable + 1 if chosen == last_clean else 1
            last_clean = chosen
            act = "commit"
            # freeze when a clean reading is COHERENT, COOL, and STABLE
            if c >= 0.90 and T <= 0.15 and stable >= 2:
                act = "FREEZE"
                trace.append((cycle, chosen, result, c, T, temp.tau(), act))
                net.decay()
                return result, chosen, trace
            trace.append((cycle, chosen, result, c, T, temp.tau(), act))

        net.decay()                                      # slipnet relaxes each cycle

    return ws.result, ws.rule, trace

# ----------------------------------------------------------------------------
# demos
# ----------------------------------------------------------------------------

def _print_trace(title, prob, result, rule, trace):
    print(f"\n=== {title}:  {prob.s0}->{prob.s1} ; {prob.target}->?   base rule {prob.base_rule} ===")
    print(f"{'cyc':>3} {'rule tried':>24} {'->':>5} {'c':>5} {'T':>5} {'tau':>5}  action")
    print("-" * 78)
    for (cy, r, res, c, T, tau, act) in trace:
        print(f"{cy:>3} {str(r):>24} {str(res or '--'):>5} {c:>5.2f} {T:>5.2f} {tau:>5.2f}  {act}")
    print(f"ANSWER: {prob.target} -> {result}   via {rule}")

def _run_offline_demos():
    print("FARG-flavored loop :: endogenous temperature, snag re-heat, slip() reframe")
    print("executor: ScriptedProposer (offline, stdlib only)")

    # 1) easy frame: no wall, no snag, cools and commits on cycle 1-2
    p1 = Problem("abc", "abd", "ijk")
    r, rule, tr = solve(p1, seed=1, verbose=True)
    _print_trace("DEMO 1  (no snag)", p1, r, rule, tr)

    # 2) the wall: snag at z -> re-heat -> slip(rightmost)->leftmost,
    #    slip(successor)->predecessor -> reframe. Fixed seed for a clean trace.
    p2 = Problem("abc", "abd", "xyz")
    r, rule, tr = solve(p2, seed=7, verbose=True)
    _print_trace("DEMO 2  (snag -> re-heat -> reframe)", p2, r, rule, tr)

    # 3) stochasticity + elegance bias: 300 runs of the xyz problem, varied seeds.
    #    The coherent double-slip is selected most often as the system cools;
    #    less-coherent clean answers appear as a minority. Nothing is hardcoded.
    print("\n=== DEMO 3  (300 runs of xyz, varied seeds: distribution of answers) ===")
    from collections import Counter
    tally = Counter()
    for s in range(300):
        res, rule, _ = solve(Problem("abc", "abd", "xyz"), seed=1000 + s)
        tally[(res, str(rule))] += 1
    for (res, rule), n in tally.most_common():
        bar = "#" * round(60 * n / 300)
        print(f"  {res} via {rule:>24}  {n:>3}/300  {bar}")
    print("  (the elegant double-opposite-slip dominates by coherence, not by fiat)")

def _run_llm_demo(args):
    """Same loop, real model as the codelet executor. The control layer is untouched;
    only the proposer changes. We print the model's parsed candidates so you can see
    its contribution, then run the loop to show the SAME control law still decides."""
    backend, model = args.backend, args.model or _DEFAULT_MODELS.get(args.backend)
    print(f"FARG-flavored loop :: executor = LLMProposer  (backend={backend}, model={model})")
    print(f"scaffold floor: {'ON (model widens; deterministic reframe guaranteed)' if not args.no_scaffold else 'OFF (model candidates only)'}")
    try:
        client = make_llm_client(backend, model)
    except Exception as e:
        print(f"\n[could not build the {backend} client: {e}]")
        print("install the SDK and set the API key, or try --backend ollama for a local model.")
        return
    proposer = LLMProposer(client, scaffold=not args.no_scaffold, verbose=True)

    prob = Problem("abc", "abd", args.problem)
    r, rule, tr = solve(prob, proposer=proposer, seed=args.seed, max_cycles=12, verbose=True)
    print(f"\nmodel's parsed candidates (validated): {[str(x) for x in proposer.last_parsed] or 'none usable'}")
    if proposer.last_raw is not None:
        snippet = " ".join(proposer.last_raw.split())[:200]
        print(f"model raw reply (truncated): {snippet}")
    _print_trace(f"LLM DEMO  (executor={backend})", prob, r, rule, tr)

def main():
    import argparse
    ap = argparse.ArgumentParser(
        description="FARG-flavored agent loop. Default runs OFFLINE (stdlib only). "
                    "--llm swaps in a real model as the codelet executor.")
    ap.add_argument("--llm", action="store_true",
                    help="use an LLM as the codelet executor (default: offline ScriptedProposer)")
    ap.add_argument("--backend", default="claude-code",
                    choices=["claude-code", "anthropic", "ollama", "openai"],
                    help="LLM backend for --llm (default: claude-code, uses your "
                         "logged-in Max/Pro auth; ollama is local/no-egress)")
    ap.add_argument("--model", default=None, help="model id (per-backend default if omitted)")
    ap.add_argument("--no-scaffold", action="store_true",
                    help="drop the deterministic control-layer floor; LLM candidates only")
    ap.add_argument("--problem", default="xyz", help="target string for the LLM demo (default: xyz)")
    ap.add_argument("--seed", type=int, default=7, help="RNG seed for the LLM demo")
    args = ap.parse_args()
    if args.llm:
        _run_llm_demo(args)
    else:
        _run_offline_demos()

if __name__ == "__main__":
    main()
