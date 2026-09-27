"""
The file the competition framework drives, and the only agent file that ships.

It is deliberately thin. All intelligence lives in research/strategies/.

Locally, `research/runner.py` sets ARC3_STRATEGY / ARC3_TRACE to sweep ideas.
On Kaggle neither is set, so ACTIVE_STRATEGY below is what competes.
Bumping ACTIVE_STRATEGY is a deliberate act — it is the line that decides
what your next submission actually is.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

from research import compat
from research.strategies import base as strategy_base

# ---------------------------------------------------------------------------
# THIS LINE IS THE SUBMISSION. Change it on purpose, never as a side effect.
# ---------------------------------------------------------------------------
ACTIVE_STRATEGY = "systematic"
# ---------------------------------------------------------------------------

_TRACE_DIR = Path(__file__).resolve().parent.parent / "research" / "results"


class MyAgent(compat.Agent):  # type: ignore[misc,valid-type]
    """Adapter between the arc-agi framework and a Strategy."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        try:
            super().__init__(*args, **kwargs)
        except Exception:  # noqa: BLE001 - base may take a different signature
            pass

        name = os.environ.get("ARC3_STRATEGY", ACTIVE_STRATEGY)
        seed = int(os.environ.get("ARC3_SEED", "0"))

        self._strategy = strategy_base.get(name)(seed=seed)
        self._trace_on = os.environ.get("ARC3_TRACE") == "1"
        self._run_id = os.environ.get("ARC3_RUN_ID") or uuid.uuid4().hex[:12]
        self._game = os.environ.get("ARC3_GAME", "unknown")

        self._log: list[dict[str, Any]] = []
        self._last_sig: str | None = None
        self._last_action: Any = None
        self._started = time.time()
        self._best_score = 0.0
        self._best_level = 0

    # -- framework interface ---------------------------------------------

    def choose_action(self, frames: Any, latest_frame: Any) -> Any:
        self._settle(latest_frame)

        sig = compat.frame_signature(latest_frame)
        action = self._strategy.choose(frames, latest_frame)

        self._last_sig = sig
        self._last_action = action
        self._strategy.actions_taken += 1

        if self._trace_on:
            self._log.append(
                {
                    "step": self._strategy.actions_taken,
                    "state_sig": sig,
                    "action": compat.action_name(action),
                    "game_state": compat.frame_state(latest_frame),
                    "score": compat.frame_score(latest_frame),
                    "level": compat.frame_level(latest_frame),
                }
            )
        return action

    def is_done(self, frames: Any, latest_frame: Any) -> bool:
        self._settle(latest_frame)
        finished = self._strategy.done(frames, latest_frame)
        if finished and self._trace_on:
            self._flush(latest_frame)
        return finished

    # -- internals --------------------------------------------------------

    def _settle(self, latest_frame: Any) -> None:
        """Feed the outcome of the previous action back to the strategy."""
        if self._last_action is not None and self._last_sig is not None:
            self._strategy.observe(latest_frame, self._last_action, self._last_sig)
            self._last_action = None

        self._best_score = max(self._best_score, compat.frame_score(latest_frame))
        self._best_level = max(self._best_level, compat.frame_level(latest_frame))

    def _flush(self, latest_frame: Any) -> None:
        try:
            _TRACE_DIR.mkdir(parents=True, exist_ok=True)
            path = _TRACE_DIR / f"{self._run_id}__{self._game}.json"
            path.write_text(
                json.dumps(
                    {
                        "run_id": self._run_id,
                        "game": self._game,
                        "strategy": self._strategy.name,
                        "seed": self._strategy.seed,
                        "actions_used": self._strategy.actions_taken,
                        "final_state": compat.frame_state(latest_frame),
                        "won": compat.is_win(latest_frame),
                        "best_score": self._best_score,
                        "best_level": self._best_level,
                        "seconds": round(time.time() - self._started, 2),
                        "diagnostics": self._strategy.snapshot(),
                        "trace": self._log,
                    },
                    indent=2,
                    default=str,
                )
            )
        except Exception as exc:  # noqa: BLE001 - tracing must never kill a run
            print(f"[trace] write failed: {exc}")
