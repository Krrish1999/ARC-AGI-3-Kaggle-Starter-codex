"""
Systematic exploration. The first strategy that should plausibly score > 0.

Hypothesis: most of random's wasted actions are (a) actions that do nothing in
this game at all, and (b) re-entering states already visited. Eliminating both
should reach deeper levels within the same action budget.

Mechanism, in three phases:
  1. PROBE   - try each simple action once, learn which ones move the world.
  2. NOVELTY - from each state, prefer untried effective actions; break ties
               toward actions that historically produced unseen states.
  3. POKE    - when novelty dries up, sweep coordinate actions over a coarse
               grid, since some games only advance through a targeted click.

This is a heuristic, not a learner. It exists to (a) put a non-zero on the
board and (b) generate the traces that tell you what actually needs learning.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from research import compat
from research.strategies.base import Strategy, register


@register("systematic")
class SystematicExplore(Strategy):
    max_actions = 4000

    #: consecutive novelty-free actions before switching to coordinate poking
    stall_threshold = 40
    #: spacing of the coordinate sweep grid, in cells
    poke_stride = 8

    def setup(self) -> None:
        self.simple = [
            a for a in compat.playable_actions() if not compat.is_coordinate_action(a)
        ]
        self.complex = [
            a for a in compat.playable_actions() if compat.is_coordinate_action(a)
        ]

        # Phase 1 bookkeeping
        self.probe_queue = list(self.simple)

        # action name -> counts
        self.effective: dict[str, int] = defaultdict(int)
        self.attempts: dict[str, int] = defaultdict(int)
        self.novel_hits: dict[str, int] = defaultdict(int)

        # state signature -> set of action names already tried there
        self.tried_here: dict[str, set[str]] = defaultdict(set)
        self.seen_states: set[str] = set()

        self.stall = 0
        self.poke_cursor = 0
        self._pending: tuple[str, str] | None = None  # (action_name, before_sig)

    # -- learning ---------------------------------------------------------

    def observe(self, latest_frame: Any, chosen: Any, before_sig: str) -> None:
        name = compat.action_name(chosen)
        after_sig = compat.frame_signature(latest_frame)

        self.attempts[name] += 1
        self.tried_here[before_sig].add(name)

        if after_sig != before_sig:
            self.effective[name] += 1

        if after_sig not in self.seen_states:
            self.seen_states.add(after_sig)
            self.novel_hits[name] += 1
            self.stall = 0
        else:
            self.stall += 1

    # -- policy -----------------------------------------------------------

    def _is_dead(self, action: Any) -> bool:
        """Tried enough times, never changed anything."""
        name = compat.action_name(action)
        return self.attempts[name] >= 6 and self.effective[name] == 0

    def _score(self, action: Any, sig: str) -> tuple[int, float]:
        name = compat.action_name(action)
        untried_here = 0 if name in self.tried_here[sig] else 1
        rate = self.novel_hits[name] / max(1, self.attempts[name])
        return (untried_here, rate)

    def choose(self, frames: Any, latest_frame: Any) -> Any:
        sig = compat.frame_signature(latest_frame)
        self.seen_states.add(sig)

        # Phase 1: probe every simple action exactly once.
        if self.probe_queue:
            return self.probe_queue.pop(0)

        # Phase 3: novelty exhausted -> sweep coordinates.
        if self.stall >= self.stall_threshold and self.complex:
            return self._poke(latest_frame)

        # Phase 2: novelty-guided choice over live simple actions.
        live = [a for a in self.simple if not self._is_dead(a)]
        if not live:
            live = self.simple or compat.playable_actions()

        best = max(live, key=lambda a: self._score(a, sig))
        # Small exploration floor so we never lock onto one action forever.
        if self.rng.random() < 0.05:
            best = self.rng.choice(live)
        return best

    def _poke(self, latest_frame: Any) -> Any:
        h, w = compat.grid_dimensions(latest_frame)
        cols = max(1, w // self.poke_stride)
        rows = max(1, h // self.poke_stride)
        cell = self.poke_cursor % (cols * rows)
        self.poke_cursor += 1
        x = (cell % cols) * self.poke_stride + self.poke_stride // 2
        y = (cell // cols) * self.poke_stride + self.poke_stride // 2
        action = self.rng.choice(self.complex)
        return compat.with_coordinates(action, min(x, w - 1), min(y, h - 1))

    # -- telemetry --------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        return {
            "distinct_states": len(self.seen_states),
            "effective_actions": dict(self.effective),
            "action_attempts": dict(self.attempts),
            "novel_hits": dict(self.novel_hits),
            "final_stall": self.stall,
            "pokes": self.poke_cursor,
        }
