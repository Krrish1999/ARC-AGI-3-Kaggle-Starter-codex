# Cloud-first setup — your laptop runs nothing

Use this instead of `SETUP.md` if your machine can't host the framework.
Your laptop needs a browser and a GitHub account. That is the whole list.

## The three machines

| Where | Does what | Costs you |
| --- | --- | --- |
| GitHub | Holds the repo. Single source of truth. | Free |
| Codex Cloud | Runs the agent, sweeps strategies, writes results back as commits. | Codex plan |
| Kaggle notebooks | Free real-environment runs + the actual submission. | Free (quota-limited) |
| Your laptop | Reads diffs in a browser. Clicks "Submit to Competition". | Nothing |

Note what is *not* here: no local venv, no local `arc-agi` install, no
`environment_files` cache on your disk, no Kaggle CLI, no `.kaggle` token on
your machine.

## Step 1 — repo on GitHub

Do this entirely in the browser:

1. Open `github.com/arcprize/ARC-AGI-3-Kaggle-Starter` and **Fork** it.
2. In your fork, use **Add file → Upload files** to add `AGENTS.md`,
   `EXPERIMENTS.md`, `SETUP-CLOUD.md`, `codex-setup.sh` and the `research/`
   folder, and to replace `agent/my_agent.py`.

No clone required.

## Step 2 — Codex Cloud environment

In Codex, create an environment pointed at your fork, then:

- **Setup script**: paste the contents of `codex-setup.sh`.
- **Package versions**: pin Python to 3.12. The `arc-agi` package requires it
  and the default image may ship something else.
- **Agent internet access**: leave it **off**.

That last one is not a limitation to work around — it is the feature. Kaggle
evaluates in a sandbox with no internet, which rules out API calls to hosted
models. An agent phase that is already offline means a strategy that secretly
depended on a network call fails in Codex instead of failing on a submission
you can't get back.

The consequence: **everything downloadable must be downloaded in the setup
script.** That is what step 3 of `codex-setup.sh` is doing when it warms
`environment_files/`. If that directory is empty when the agent phase starts,
every run dies with "Could not create environment" and Codex will waste the
whole task guessing why.

Container state caches for about 12 hours, so the slow setup happens roughly
once a day, not once a task.

## Step 3 — first three tasks, in order

Run each as its own cloud task. Read the diff before accepting.

**Task 1 — prove the environment works.**
> Read AGENTS.md. Run `python research/runner.py --list` and paste the output.
> Then run `python research/runner.py --strategy random --games all --seeds 1`.
> Report the summary table and any crash verbatim. Change no code yet.

If this fails, the problem is the setup script, not the agent. Fix that first.

**Task 2 — correct the compat layer.**
> research/compat.py guesses at the arc-agi API without having seen it. Read the
> installed arc-agi package in .venv and correct compat.py against the real
> GameAction enum and frame fields. Show me the diff and the output of
> compat.report(). Touch no other file.

**Task 3 — the notebook packager.**
> Run `make notebook`, then `grep -c "class SystematicExplore" notebooks/submission.ipynb`.
> If it is 0, fix scripts/build_notebook.py to inline the whole research package
> so the notebook is self-contained, and prove it with the same grep.
> Do not run `make submit`.

Task 3 matters more than it looks. The starter assumes one agent file; this kit
adds a package. If the packager doesn't inline it, your submission crashes on
import and you've burned a submission on an ImportError.

## Step 4 — submitting without a local Kaggle setup

Two routes. Pick one.

**Route A — Kaggle web UI (no token anywhere).** Have Codex commit
`notebooks/submission.ipynb`. Open it on GitHub, copy the raw JSON, and in
Kaggle use **Create → Notebook → File → Import Notebook**. Run all, then
**Submit to Competition** and pick `submission.parquet`.

**Route B — token as a Codex secret.** Put your Kaggle token in the Codex
environment as a *secret*, and have the setup script write it to
`.kaggle/access_token`. Secrets are only available during setup and are removed
before the agent phase, so Codex itself can never read it or spend a
submission. You'd still trigger `make submit` yourself.

Route A is what I'd do until the pipeline is proven.

## Step 5 — Kaggle as your second compute tier

Kaggle notebooks are real compute you already have access to, and Phase A
("Save & Run All") does **not** consume a submission — only clicking *Submit to
Competition* does. So a saved notebook run is a free full-scale evaluation on
the real engine.

Use it for anything that outgrows the Codex container: long sweeps, and later
any GPU work. Keep Codex for the write-measure-analyse loop and Kaggle for the
expensive confirmation run.

## Patch for AGENTS.md

Add this section so Codex knows where it is:

```markdown
## Environment

You run in Codex Cloud, offline. There is no internet in your phase.
- Never `pip install` anything. If a dependency is missing, say so and stop —
  it has to go in the setup script, which you do not control.
- `environment_files/` was cached during setup. Do not delete it. If a run
  fails with "Could not create environment", the cache is the cause; report
  that rather than trying to re-download.
- Container state is ephemeral. Anything you want kept must be committed.
  Commit result summaries and EXPERIMENTS.md entries; never commit raw traces.
- Kunal's laptop cannot run this repo. "Just run it locally" is never advice
  you give him.
```

## What you give up, honestly

- **Feedback latency.** A cloud task is minutes; a local edit-run loop is
  seconds. You compensate by batching: ask for one experiment with three seeds
  across all games, not one game at a time.
- **Poking at things yourself.** You can't drop into a REPL and look at a frame.
  This is why `research/trace.py` exists — the post-mortem is your substitute
  for direct observation, so keep it good.
- **Debugging setup failures.** When the container is broken you're reading
  logs, not prodding a live machine. Keep `codex-setup.sh` loud and
  fail-fast for exactly this reason.
