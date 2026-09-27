#!/usr/bin/env python3
"""
Post-mortem tool. Turns a run trace into the thing you actually reason about:
where did it stall, and what was it doing when it stalled.

Usage
-----
  python research/trace.py --list
  python research/trace.py --run 20260927-1412-ab12-systematic-s0__ls20
  python research/trace.py --run <id> --tail 60
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "results"


def load(run: str) -> dict:
    exact = RESULTS / f"{run}.json"
    if exact.exists():
        return json.loads(exact.read_text())
    matches = sorted(RESULTS.glob(f"*{run}*.json"))
    matches = [m for m in matches if not m.name.endswith(".summary.json")]
    if not matches:
        raise SystemExit(f"no trace matching {run!r} in {RESULTS}")
    if len(matches) > 1:
        print(f"[trace] {len(matches)} matches, using {matches[0].name}")
    return json.loads(matches[0].read_text())


def report(data: dict, tail: int) -> None:
    trace = data.get("trace") or []

    print(f"game          : {data.get('game')}")
    print(f"strategy      : {data.get('strategy')} (seed {data.get('seed')})")
    print(f"final state   : {data.get('final_state')}  won={data.get('won')}")
    print(f"best level    : {data.get('best_level')}   best score={data.get('best_score')}")
    print(f"actions used  : {data.get('actions_used')} in {data.get('seconds')}s")
    print()

    if not trace:
        print("no per-step trace (was ARC3_TRACE=1 set?)")
        return

    # Where did progress actually happen?
    print("--- level progression ---")
    last = None
    for step in trace:
        lvl = step.get("level")
        if lvl != last:
            print(f"  step {step['step']:>5}  level -> {lvl}  (action {step['action']})")
            last = lvl

    # Which actions were used, and how concentrated was the policy?
    print("\n--- action histogram ---")
    hist = Counter(s["action"] for s in trace)
    width = max(len(a) for a in hist)
    for action, count in hist.most_common():
        pct = 100 * count / len(trace)
        bar = "#" * int(pct / 2)
        print(f"  {action:<{width}}  {count:>6} ({pct:5.1f}%) {bar}")

    # How much of the run was spent re-treading old ground?
    sigs = [s["state_sig"] for s in trace]
    print(f"\ndistinct states visited : {len(set(sigs))} / {len(sigs)} steps")
    repeats = Counter(sigs).most_common(3)
    for sig, count in repeats:
        if count > 1:
            print(f"  state {sig} revisited {count}x")

    diag = data.get("diagnostics") or {}
    if diag:
        print("\n--- strategy diagnostics ---")
        print(json.dumps(diag, indent=2)[:2000])

    print(f"\n--- last {tail} actions before stop ---")
    for step in trace[-tail:]:
        print(
            f"  {step['step']:>5}  {step['action']:<12} "
            f"state={step['state_sig']} lvl={step.get('level')} "
            f"{step.get('game_state')}"
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", help="run id or any substring of the trace filename")
    ap.add_argument("--tail", type=int, default=40)
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list or not args.run:
        files = sorted(
            p for p in RESULTS.glob("*.json") if not p.name.endswith(".summary.json")
        )
        for p in files[-40:]:
            print(p.stem)
        if not files:
            print(f"(no traces yet in {RESULTS})")
        return 0

    report(load(args.run), args.tail)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
