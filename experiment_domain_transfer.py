#!/usr/bin/env python3
"""
experiment_domain_transfer.py - does the false-freeze TRANSFER to a second domain?

The capability sweep (EXPERIMENT.md) measured the false-freeze in the letter-string
domain. The open question it leaves: is the false-freeze a property of the CONTROL LAW,
or an artifact of the 26-letter toy? This runs the same comparison in a SECOND,
surface-different domain (diatonic melody, domain_music.py) that drives the SAME
imported solve()/ScriptedProposer, and asks whether the same shape reproduces.

Two parts:
  PART A - the loop is surface-blind (deterministic, instant). Run the scripted scout
           on both domains and show the elegant-answer distributions match to the
           count. The control law cannot see the surface, so given identical seeds and
           coherence values it MUST produce identical selection. This is a sanity proof,
           not a finding.
  PART B - the false-freeze transfers (the actual question). Run a real model on both
           domains, K candidate-set samples x S loop seeds, at bars 0.90 and 0.99. If
           the model false-freezes in BOTH domains (elegant rate far below the scout's,
           recovered by raising the bar), the phenomenon belongs to the loop.

Honesty: the two domains are DELIBERATELY isomorphic in relational structure; only the
surface differs. Part A's count-for-count match is therefore expected by construction,
not surprising. Part B is the real test: a model reads real notes vs real letters and
may behave differently, so a reproduction there is informative. K real samples is a
small sample of a stochastic model; this measures a mechanism on two toy problems.
"""
import json
from collections import Counter

import farg_loop as F
import domain_music as M

K = 3          # independent model-call samples of the candidate set
S = 100        # loop seeds per sample
BARS = (0.90, 0.99)
MODEL = "haiku"   # one capable executor, same model on both domains for a fair compare

DOMAINS = [
    {"name": "letters", "elegant": "wyz",
     "prob": lambda: F.Problem("abc", "abd", "xyz"),
     "proposer": lambda client: F.LLMProposer(client, scaffold=True)},
    {"name": "melody", "elegant": "F A B",
     "prob": lambda: M.MusicProblem("C D E", "C D F", "G A B"),
     "proposer": lambda client: M.music_llm_proposer(client, scaffold=True)},
]


def pct(counter, total, key):
    return round(100.0 * counter.get(key, 0) / total, 1) if total else 0.0


def run_scripted(dom):
    out = {}
    for bar in BARS:
        tally = Counter()
        for s in range(K * S):
            r, _, _ = F.solve(dom["prob"](), seed=1000 + s, freeze_bar=bar)
            tally[r] += 1
        out[bar] = (tally, pct(tally, K * S, dom["elegant"]))
    return out


def run_model(dom, client):
    tally = {bar: Counter() for bar in BARS}
    cand_sets = []
    for k in range(K):
        proposer = dom["proposer"](client)
        F.solve(dom["prob"](), proposer=proposer, seed=0, freeze_bar=0.90)  # cache the call
        if not proposer.last_raw:
            return None, None, f"empty model reply on sample {k}"
        cand_sets.append([str(x) for x in proposer.last_parsed])
        for bar in BARS:
            for s in range(S):
                r, _, _ = F.solve(dom["prob"](), proposer=proposer,
                                  seed=2000 + k * S + s, freeze_bar=bar)
                tally[bar][r] += 1
    return tally, cand_sets, None


def glyph(p, width=34):
    return "#" * round(width * p / 100.0)


def main():
    results = {"K": K, "S": S, "bars": list(BARS), "model": MODEL, "domains": {}}

    print("=" * 74)
    print("PART A - the loop is surface-blind  (scripted scout, deterministic)")
    print("=" * 74)
    scripted = {}
    for dom in DOMAINS:
        sc = run_scripted(dom)
        scripted[dom["name"]] = sc
        print(f"\n{dom['name']}  (elegant = {dom['elegant']!r})")
        for bar in BARS:
            tally, p = sc[bar]
            top = "  ".join(f"{k}:{v}" for k, v in tally.most_common(3))
            print(f"  bar {bar:.2f}: elegant {p:>5}%   dist[ {top} ]")
    le90 = scripted["letters"][0.90][1]
    me90 = scripted["melody"][0.90][1]
    print(f"\n  letters elegant@0.90 = {le90}% ; melody elegant@0.90 = {me90}%  "
          f"-> {'MATCH (loop is surface-blind)' if le90 == me90 else 'differ'}")

    try:
        client = F.make_llm_client("claude-code", MODEL)
    except Exception as e:
        print(f"\nPART B SKIPPED: could not build model client: {e}")
        results["part_b_skipped"] = str(e)
        with open("domain_transfer_results.json", "w") as f:
            json.dump(results, f, indent=2)
        return

    print("\n" + "=" * 74)
    print(f"PART B - does the false-freeze TRANSFER?  (model={MODEL}, K={K} x S={S})")
    print("=" * 74)
    for dom in DOMAINS:
        tally, cand_sets, err = run_model(dom, client)
        sc = scripted[dom["name"]]
        rec = {"elegant": dom["elegant"], "scout_090": sc[0.90][1], "scout_099": sc[0.99][1]}
        if err:
            print(f"\n{dom['name']}: MODEL SKIPPED ({err})")
            rec["model_error"] = err
            results["domains"][dom["name"]] = rec
            continue
        m90 = pct(tally[0.90], K * S, dom["elegant"])
        m99 = pct(tally[0.99], K * S, dom["elegant"])
        rec.update({"model_090": m90, "model_099": m99,
                    "candidate_sets": cand_sets,
                    "dist_090": dict(tally[0.90]), "dist_099": dict(tally[0.99])})
        results["domains"][dom["name"]] = rec
        print(f"\n{dom['name']}  (elegant = {dom['elegant']!r})")
        print(f"  scout @0.90 |{glyph(sc[0.90][1])} {sc[0.90][1]}%")
        print(f"  {MODEL} @0.90 |{glyph(m90)} {m90}%   <- false-freeze: model below scout")
        print(f"  {MODEL} @0.99 |{glyph(m99)} {m99}%   <- raised bar recovers")
        print(f"  model candidate samples: {cand_sets}")

    # verdict
    doms = results["domains"]
    if all("model_090" in d for d in doms.values()):
        transfers = all(d["model_090"] < d["scout_090"] and d["model_099"] > d["model_090"]
                        for d in doms.values())
        print("\n" + "-" * 74)
        print(f"VERDICT: false-freeze reproduces in BOTH domains: {transfers}")
        for n, d in doms.items():
            print(f"  {n:<8} scout {d['scout_090']:>5}% -> {MODEL} {d['model_090']:>5}% "
                  f"@0.90 ; recovers to {d['model_099']:>5}% @0.99")
        results["transfers"] = transfers

    with open("domain_transfer_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nraw results written to domain_transfer_results.json")


if __name__ == "__main__":
    main()
