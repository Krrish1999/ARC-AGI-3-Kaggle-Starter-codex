#!/usr/bin/env python3
"""
Sweep runner: strategy x game x seed -> results/<run_id>.summary.json

It does NOT reimplement the game loop. It shells out to the starter kit's
own `scripts/play_local.py`, passing the strategy through environment
variables, and collects the per-game traces the agent writes itself. That way
the harness stays correct even as the framework changes underneath it.

Usage
-----
  python research/runner.py --strategy systematic --games all --seeds 3
  python research/runner.py --strategy random --games ls20,ft09 --seeds 1
  python research/runner.py --compare random systematic --games all --seeds 3
  python research/runner.py --list
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "research" / "results"
PLAY_LOCAL = ROOT / "scripts" / "play_local.py"
PYTHON = str(ROOT / ".venv" / "bin" / "python")
if not Path(PYTHON).exists():
    PYTHON = sys.executable


# ---------------------------------------------------------------------------
# game discovery
# ---------------------------------------------------------------------------


def list_games() -> list[str]:
    cache = ROOT / "environment_files"
    if cache.is_dir():
        games = sorted(p.name for p in cache.iterdir() if p.is_dir())
        if games:
            return games
    print(f"[runner] {cache} is empty — setup did not warm the cache")
    return []

# ---------------------------------------------------------------------------
# single run
# ---------------------------------------------------------------------------


def play(strategy: str, game: str, seed: int, run_id: str, timeout: int) -> dict:
    env = {
        **os.environ,
        "ARC3_STRATEGY": strategy,
        "ARC3_SEED": str(seed),
        "ARC3_TRACE": "1",
        "ARC3_RUN_ID": f"{run_id}-s{seed}",
        "ARC3_GAME": game,
        "PYTHONPATH": str(ROOT),
    }

    cmd = [PYTHON, str(PLAY_LOCAL)]
    if game != "all":
        cmd += ["--game", game]

    started = time.time()
    try:
        proc = subprocess.run(
            cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout
        )
        stdout, stderr, rc = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired:
        stdout, stderr, rc = "", f"TIMEOUT after {timeout}s", -9

    trace_path = RESULTS / f"{run_id}-s{seed}__{game}.json"
    trace = {}
    if trace_path.exists():
        try:
            trace = json.loads(trace_path.read_text())
        except Exception as exc:  # noqa: BLE001
            trace = {"trace_parse_error": str(exc)}

    if not trace:
        rc = rc or 70  # exited clean but played nothing — treat as failure
        stderr = (stderr or "") + f"\nNO TRACE at {trace_path}; agent never ran"

    return {
        "strategy": strategy,
        "game": game,
        "seed": seed,
        "returncode": rc,
        "seconds": round(time.time() - started, 2),
        "won": bool(trace.get("won")),
        "best_level": trace.get("best_level", 0),
        "best_score": trace.get("best_score", 0.0),
        "actions_used": trace.get("actions_used", 0),
        "distinct_states": (trace.get("diagnostics") or {}).get("distinct_states"),
        "stderr_tail": (stderr or "")[-1500:],
        "stdout_tail": (stdout or "")[-1500:],
    }


# ---------------------------------------------------------------------------
# aggregation
# ---------------------------------------------------------------------------


def aggregate(rows: list[dict]) -> dict:
    by_strategy: dict[str, dict] = {}
    for strat in sorted({r["strategy"] for r in rows}):
        sel = [r for r in rows if r["strategy"] == strat]
        levels = [r["best_level"] for r in sel]
        by_strategy[strat] = {
            "runs": len(sel),
            "wins": sum(r["won"] for r in sel),
            "mean_level": round(statistics.fmean(levels), 3) if levels else 0,
            "max_level": max(levels, default=0),
            "mean_actions": round(
                statistics.fmean([r["actions_used"] for r in sel]), 1
            )
            if sel
            else 0,
            "crashes": sum(r["returncode"] not in (0, None) for r in sel),
            "mean_seconds": round(statistics.fmean([r["seconds"] for r in sel]), 1),
        }
    return by_strategy


def as_markdown(summary: dict) -> str:
    head = (
        "| strategy | runs | wins | mean level | max level | mean actions | crashes |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
    )
    body = "".join(
        f"| {k} | {v['runs']} | {v['wins']} | {v['mean_level']} | "
        f"{v['max_level']} | {v['mean_actions']} | {v['crashes']} |\n"
        for k, v in summary.items()
    )
    return head + body


# ---------------------------------------------------------------------------
# cli
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy")
    ap.add_argument("--compare", nargs="+", help="two or more strategy names")
    ap.add_argument("--games", default="all", help="'all' or comma-separated ids")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=1800, help="seconds per run")
    ap.add_argument("--list", action="store_true", help="list strategies and games")
    args = ap.parse_args()

    sys.path.insert(0, str(ROOT))
    from research.strategies import base as strategy_base  # noqa: E402

    if args.list:
        print("strategies:", strategy_base.available())
        print("games     :", list_games())
        return 0

    strategies = args.compare or ([args.strategy] if args.strategy else [])
    if not strategies:
        ap.error("pass --strategy NAME or --compare A B")

    for s in strategies:
        strategy_base.get(s)  # fail fast on typos

    games = ["all"] if args.games == "all" else args.games.split(",")
    run_id = f"{time.strftime('%Y%m%d-%H%M')}-{uuid.uuid4().hex[:4]}"
    RESULTS.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    total = len(strategies) * len(games) * args.seeds
    n = 0
    for strat in strategies:
        for game in games:
            for seed in range(args.seeds):
                n += 1
                print(f"[{n}/{total}] {strat} :: {game} :: seed {seed}", flush=True)
                row = play(strat, game, seed, f"{run_id}-{strat}", args.timeout)
                rows.append(row)
                flag = "WIN" if row["won"] else ""
                print(
                    f"      level={row['best_level']} actions={row['actions_used']} "
                    f"rc={row['returncode']} {flag}",
                    flush=True,
                )
                if row["returncode"] not in (0, None):
                    print(f"      stderr: {row['stderr_tail'][-400:]}", flush=True)

    summary = aggregate(rows)
    out = RESULTS / f"{run_id}.summary.json"
    out.write_text(
        json.dumps(
            {"run_id": run_id, "args": vars(args), "summary": summary, "rows": rows},
            indent=2,
        )
    )

    print("\n" + as_markdown(summary))
    print(f"written: {out.relative_to(ROOT)}")
    print("\nPaste the table above into EXPERIMENTS.md under your hypothesis.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
