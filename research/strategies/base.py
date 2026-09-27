"""
Strategy interface.

A Strategy is the brain. `agent/my_agent.py` is the body that the competition
framework drives. Keeping them separate means you can sweep twenty brains
without touching the file that ships to Kaggle.

Contract:
  - `choose(frames, latest_frame)` returns a GameAction.
  - `done(frames, latest_frame)` returns True to stop playing.
  - Strategies are constructed once per game, with a seed.
  - Strategies must be deterministic given their seed.
"""

from __future__ import annotations

import random
from typing import Any

from research import compat

_REGISTRY: dict[str, type["Strategy"]] = {}


def register(name: str):
    def wrap(cls):
        cls.name = name
        _REGISTRY[name] = cls
        return cls

    return wrap


def get(name: str) -> type["Strategy"]:
    if name not in _REGISTRY:
        load_all()
    if name not in _REGISTRY:
        raise KeyError(f"unknown strategy {name!r}; known: {sorted(_REGISTRY)}")
    return _REGISTRY[name]


def available() -> list[str]:
    load_all()
    return sorted(_REGISTRY)


def load_all() -> None:
    """Import every sibling module so decorators run."""
    import importlib
    import pkgutil

    import research.strategies as pkg

    for mod in pkgutil.iter_modules(pkg.__path__):
        if mod.name != "base":
            importlib.import_module(f"research.strategies.{mod.name}")


class Strategy:
    """Subclass this. Override `choose`. Override `done` only if you must."""

    name: str = "unnamed"

    #: Hard ceiling on actions per game. Safety net against infinite play.
    max_actions: int = 5000

    def __init__(self, seed: int = 0, **kwargs: Any) -> None:
        self.seed = seed
        self.rng = random.Random(seed)
        self.actions_taken = 0
        self.config = kwargs
        self.setup()

    # -- hooks ------------------------------------------------------------

    def setup(self) -> None:
        """Per-game initialisation. Called once at construction."""

    def observe(self, latest_frame: Any, chosen: Any, before_sig: str) -> None:
        """
        Called by the agent AFTER each action resolves, with the frame that
        resulted. Use it to learn which actions do anything at all.
        """

    def choose(self, frames: Any, latest_frame: Any) -> Any:
        raise NotImplementedError

    def done(self, frames: Any, latest_frame: Any) -> bool:
        if self.actions_taken >= self.max_actions:
            return True
        return compat.is_win(latest_frame)

    # -- telemetry --------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        """Extra per-run diagnostics to embed in the result JSON. Override freely."""
        return {}
