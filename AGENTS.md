# ARC-AGI-3 Research Repo — Agent Instructions

You are the research engineer on this repo. Kunal is the principal investigator.
You implement and measure; he decides direction and spends submissions.

## What this repo is

A local dev kit for the ARC Prize 2026 ARC-AGI-3 Kaggle competition. The agent
under development plays interactive grid-world games where the rules, the goal,
and the meaning of each action are unknown and must be discovered by acting.

## Hard constraints — never violate

- **The submission runs with NO INTERNET.** No API calls, no `requests`, no
  model downloads at runtime, no hosted LLMs (GPT / Claude / Gemini are all
  unavailable inside the Kaggle sandbox). Any model weights must be committed
  to the repo or attached as a Kaggle dataset.
- **Python 3.12 only.** Use the repo `.venv`. The competition's `arc-agi`
  package requires it.
- **Never touch `.kaggle/`.** Never run `make submit`. Never run any `kaggle`
  CLI command. Submissions are capped at 5/day and Kunal spends them manually.
- **`agent/my_agent.py` must always import cleanly and pass `make verify-local`.**
  If you break it, fix it before reporting.
- Do not add a dependency without saying so explicitly in your report. Every
  dependency has to survive an offline Kaggle install.

## What "better" means

Per-game scores run 0–100%. 100% means the agent beat the game using no more
actions than a human did. Final score is the average of per-game scores across
levels, so **levels reached gives partial credit**.

Optimise in this priority order:

1. Number of levels beaten (this is worth far more than anything else)
2. Actions used to beat them (efficiency is the second half of the metric)
3. Wall-clock runtime (must finish inside the Kaggle kernel time limit)

A change that beats one more level while using more actions is a WIN.
A change that uses fewer actions but beats fewer levels is a LOSS.

## Workflow for every change — follow exactly

1. **Write the hypothesis in `EXPERIMENTS.md` first.** One sentence, in this
   form: "If <change>, then <metric> improves, because <mechanism>."
   If you cannot state a mechanism, you do not have an experiment. Say so and
   stop.
2. **Implement as a NEW file** in `research/strategies/`. Never edit a strategy
   that already has recorded results — copy it and change the copy.
3. **Run it:**
   `python research/runner.py --strategy <name> --games all --seeds 3`
4. **Append the result table** to `EXPERIMENTS.md`, including runs that got
   worse. Paste failures verbatim; do not summarise away a stack trace.
5. **Stop and report.** One experiment per turn. Do not chain into the next
   idea on your own initiative.

## Prohibited

- Editing `research/runner.py` scoring logic to make numbers look better.
- Tuning against one game and reporting it as a general improvement.
- Running more than one experiment per turn.
- Deleting or rewriting past entries in `EXPERIMENTS.md`. It is append-only.
- Claiming an improvement from a single seed. Three seeds minimum.
- Silently catching exceptions to make a run "pass". A crash is a result.

## When you are stuck

Report the stall with evidence rather than trying more variants. The useful
output is: which game, which level, the last N actions before the stall, and
what the frame looked like when it stopped changing. Use
`python research/trace.py --run <run_id>` to produce that.

## Repo map

```
agent/my_agent.py          Thin wrapper. Selects the active strategy. Ships to Kaggle.
research/compat.py         Isolates every assumption about the arc-agi API.
research/strategies/       One file per idea. Append-only in spirit.
research/runner.py         Sweeps strategies x games x seeds, writes JSON.
research/trace.py          Turns a run JSON into a human-readable post-mortem.
research/results/          Run records. Append-only.
EXPERIMENTS.md             Hypothesis log. Append-only.
```

## Known unknown — read before your first change

`research/compat.py` contains best-effort introspection of the `arc-agi`
package (action enum, frame state, score fields). It was written without the
package installed. **Your first task in a fresh clone is to verify it against
the real API** (`make list-games`, `make pull-sample`, and reading the
installed package) and correct it. Report what was wrong. Everything else
depends on that file being right.
