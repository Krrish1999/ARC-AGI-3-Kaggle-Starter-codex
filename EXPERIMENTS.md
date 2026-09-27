# Experiment Log

Append-only. Never edit or delete a past entry. Negative results are the point.

Rule: no experiment runs before its hypothesis is written here. If three runs
happen without a written hypothesis, stop and write instead of running.

Template — copy this block for every experiment:

```
## E-XXX  <short name>          <date>

**Hypothesis.** If <change>, then <metric> improves, because <mechanism>.

**What I changed.** research/strategies/<file>.py — one sentence.

**Command.** python research/runner.py --compare <baseline> <new> --games all --seeds 3

**Result.**
| strategy | runs | wins | mean level | max level | mean actions | crashes |
| --- | --- | --- | --- | --- | --- | --- |

**Verdict.** CONFIRMED / REFUTED / INCONCLUSIVE — one sentence on why.

**What this rules out.** The thing I no longer need to try.

**Next question.** One, not five.
```

---

## E-000  Harness bring-up                              (not run yet)

**Hypothesis.** Not an experiment — infrastructure. The goal is a green
`make verify-local` and one recorded baseline run, so every later number has
something to be compared against.

**Checklist.**
- [ ] `make setup` succeeds on Python 3.12
- [ ] `python -c "from research import compat; compat.report()"` prints the real
      action enum, and `compat.py` has been corrected against it
- [ ] `python research/runner.py --list` prints strategies and game ids
- [ ] `python research/runner.py --strategy random --games all --seeds 3` completes
- [ ] `python research/trace.py --run <id>` renders a post-mortem
- [ ] `make verify-local` passes with ACTIVE_STRATEGY unchanged

**Result.**

**Verdict.**

---

## E-001  Systematic exploration vs random             (not run yet)

**Hypothesis.** If the agent (a) stops issuing actions that have never changed
the frame in this game and (b) prefers untried actions from the current state,
then mean level reached improves over random within the same action budget,
because random spends most of its budget on dead actions and on re-entering
states it has already seen.

**Command.** `python research/runner.py --compare random systematic --games all --seeds 3`

**Result.**

**Verdict.**

**Next question.**
