#!/usr/bin/env python3
"""
experiment_capability_sweep.py - does a more capable executor false-freeze MORE?

The bridge essay (false-freeze-and-the-capable-executor.md) asserts that a more
capable executor RAISES false-freeze risk: a fluent model clears a low coherence bar
faster, commits to the first locally-coherent reading, and never hits the wall that
produces the elegant reframe (wyz). That claim rested on one model (haiku). This puts
several models through the SAME control law and measures it.

Hypothesis:
  wyz% at the default bar 0.90 DECREASES as the executor gets more capable
  (scripted > haiku > sonnet > opus), and the 0.99 bar recovers it for all of them.

Method:
  For each executor, sample its proposed candidate set K times (K real model calls;
  the prompt is identical across seeds, so within one sample the loop reuses the
  cached reply). Run S loop seeds per sample at bars 0.90 and 0.99. Scaffold stays ON
  (the default), so the opposite-gated reframe is reachable AFTER a snag for every
  executor; any false-freeze is the model's clean-reading bias winning the softmax
  before the base rule is ever selected and snagged, not an unreachable answer. The
  scripted proposer is the capability=none baseline.

  Real model calls go through the wired claude-code backend (logged-in Max/Pro auth).
  Local ollama is included if its daemon is up. Stdlib + farg_loop only.

Honesty: K real samples per model is a small sample of the model's candidate-set
variance; S seeds is the loop RNG. The capability ordering haiku<sonnet<opus is an
assumption. This measures a mechanism on one toy problem, not a population property.
"""
import json
import farg_loop as F
from collections import Counter

PROB = lambda: F.Problem("abc", "abd", "xyz")
BARS = (0.90, 0.99)
K = 3          # independent model-call samples of the candidate set
S = 100        # loop seeds per candidate set  (K*S = 300 runs / model / bar)
BASE = "(rightmost, successor)"        # the snag-inducing base rule
REFRAME = "(leftmost, predecessor)"    # the elegant double-slip -> wyz

# executor, claude --model arg (or ollama model), display label, capability rank
EXECUTORS = [
    ("scripted",    None,        "scripted (none)", 0),
    ("claude-code", "haiku",     "haiku",           1),
    ("claude-code", "sonnet",    "sonnet",          2),
    ("claude-code", "opus",      "opus",            3),
    ("ollama",      "llama3.2",  "llama3.2 (local)", None),
]


def run_scripted():
    tally = {bar: Counter() for bar in BARS}
    for bar in BARS:
        for s in range(K * S):
            r, _, _ = F.solve(PROB(), seed=1000 + s, freeze_bar=bar)
            tally[bar][r] += 1
    return tally, [], None


def run_model(backend, model):
    try:
        client = F.make_llm_client(backend, model)
    except Exception as e:
        return None, None, f"client build failed: {e}"
    cand_sets, tally = [], {bar: Counter() for bar in BARS}
    for k in range(K):
        proposer = F.LLMProposer(client, scaffold=True)
        try:
            F.solve(PROB(), proposer=proposer, seed=0, freeze_bar=0.90)  # triggers + caches the model call
        except Exception as e:
            return None, None, f"model call failed on sample {k}: {e}"
        if not proposer.last_raw:
            return None, None, f"empty model reply on sample {k} (call failed)"
        cand_sets.append([str(x) for x in proposer.last_parsed])
        for bar in BARS:
            for s in range(S):
                r, _, _ = F.solve(PROB(), proposer=proposer, seed=2000 + k * S + s, freeze_bar=bar)
                tally[bar][r] += 1
    return tally, cand_sets, None


def pct(tally, bar, key="wyz"):
    tot = sum(tally[bar].values())
    return 100.0 * tally[bar].get(key, 0) / tot if tot else 0.0


def bar_glyph(p, width=40):
    return "#" * round(width * p / 100.0)


def main():
    results = []
    for backend, model, label, rank in EXECUTORS:
        print(f"\n>>> running executor: {label} ...", flush=True)
        if backend == "scripted":
            tally, cand_sets, err = run_scripted()
        else:
            tally, cand_sets, err = run_model(backend, model)
        if err:
            print(f"    SKIP ({label}): {err}", flush=True)
            results.append({"label": label, "rank": rank, "error": err})
            continue
        flat = [c for cs in cand_sets for c in cs]
        proposes_base = any(BASE in cs for cs in cand_sets)
        proposes_reframe = any(REFRAME in cs for cs in cand_sets)
        clean = sorted({c for c in flat if c not in (BASE, REFRAME)})
        row = {
            "label": label, "rank": rank,
            "wyz_090": round(pct(tally, 0.90), 1),
            "wyz_099": round(pct(tally, 0.99), 1),
            "dist_090": dict(tally[0.90]), "dist_099": dict(tally[0.99]),
            "candidate_sets": cand_sets,
            "proposes_base_rule": proposes_base,
            "proposes_reframe": proposes_reframe,
            "clean_readings_offered": clean,
            "runs_per_bar": K * S,
        }
        results.append(row)
        print(f"    wyz@0.90 = {row['wyz_090']}%   wyz@0.99 = {row['wyz_099']}%", flush=True)
        print(f"    proposes base rule: {proposes_base}   proposes reframe: {proposes_reframe}", flush=True)
        print(f"    distinct clean readings offered: {clean}", flush=True)

    ok = [r for r in results if "error" not in r]

    print("\n" + "=" * 72)
    print("CAPABILITY SWEEP  (xyz problem; scaffold ON; K*S runs per cell)")
    print("=" * 72)
    print(f"{'executor':<18}{'wyz@0.90':>10}{'wyz@0.99':>10}{'base?':>8}{'reframe?':>10}")
    print("-" * 72)
    for r in ok:
        print(f"{r['label']:<18}{r['wyz_090']:>9.1f}%{r['wyz_099']:>9.1f}%"
              f"{str(r['proposes_base_rule']):>8}{str(r['proposes_reframe']):>10}")

    print("\nwyz% at the default bar 0.90 (capability axis, hypothesis: decreasing):")
    ordered = sorted([r for r in ok if r["rank"] is not None], key=lambda r: r["rank"])
    for r in ordered:
        print(f"  {r['label']:<18}|{bar_glyph(r['wyz_090'])} {r['wyz_090']:.1f}%")
    for r in [r for r in ok if r["rank"] is None]:
        print(f"  {r['label']:<18}|{bar_glyph(r['wyz_090'])} {r['wyz_090']:.1f}%   (local; rank n/a)")

    if len(ordered) >= 2:
        seq = [r["wyz_090"] for r in ordered]
        mono = all(seq[i] >= seq[i + 1] for i in range(len(seq) - 1))
        print(f"\nmonotonic non-increasing along capability axis: {mono}   sequence={seq}")

    with open("experiment_results.json", "w") as f:
        json.dump({"K": K, "S": S, "bars": list(BARS), "results": results}, f, indent=2)
    print("\nraw results written to experiment_results.json")


if __name__ == "__main__":
    main()
