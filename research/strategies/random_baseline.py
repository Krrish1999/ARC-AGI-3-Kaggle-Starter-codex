"""
Control group. Mirrors the starter kit's random agent.

Every other strategy must beat this or it is not an improvement. Do not delete
this file — a benchmark you keep moving is not a benchmark.
"""

from __future__ import annotations

from typing import Any

from research import compat
from research.strategies.base import Strategy, register


@register("random")
class RandomBaseline(Strategy):
    max_actions = 2000

    def setup(self) -> None:
        self.pool = compat.playable_actions()

    def choose(self, frames: Any, latest_frame: Any) -> Any:
        action = self.rng.choice(self.pool)
        if compat.is_coordinate_action(action):
            h, w = compat.grid_dimensions(latest_frame)
            action = compat.with_coordinates(
                action, self.rng.randrange(w), self.rng.randrange(h)
            )
        return action
