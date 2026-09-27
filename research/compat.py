"""
Isolation layer for every assumption this repo makes about the `arc-agi` package.

Written defensively, WITHOUT the package installed. Each helper introspects the
real objects at runtime and falls back gracefully. When you discover the actual
API shape, correct it HERE and nowhere else — strategies must never touch the
arc-agi package directly.

Verify with:
    python -c "from research import compat; compat.report()"
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

# --------------------------------------------------------------------------
# Import the framework
# --------------------------------------------------------------------------

GameAction: Any = None
Agent: Any = object
_IMPORT_ERROR: str | None = None

for _mod in ("arc_agi", "arc_agi.agents", "arc_agi.agents.agent", "agents.agent"):
    try:
        _m = __import__(_mod, fromlist=["GameAction", "Agent"])
        GameAction = getattr(_m, "GameAction", GameAction)
        Agent = getattr(_m, "Agent", Agent)
        if GameAction is not None:
            break
    except Exception as exc:  # noqa: BLE001 - we genuinely want any failure
        _IMPORT_ERROR = f"{_mod}: {exc}"


def framework_available() -> bool:
    return GameAction is not None


# --------------------------------------------------------------------------
# Actions
# --------------------------------------------------------------------------

# Names that are control-flow rather than gameplay moves.
_CONTROL_NAMES = {"RESET", "NOOP", "NONE", "UNKNOWN", "INVALID"}

# Actions that carry coordinates ("complex" actions in ARC-AGI-3 terms).
_COORDINATE_HINTS = {"ACTION6", "COMPLEX", "CLICK", "POINT"}


def all_actions() -> list[Any]:
    """Every member of the GameAction enum, in declaration order."""
    if GameAction is None:
        return []
    try:
        return list(GameAction)
    except TypeError:
        return [
            getattr(GameAction, n)
            for n in dir(GameAction)
            if n.isupper() and not n.startswith("_")
        ]


def playable_actions() -> list[Any]:
    """Gameplay actions only — RESET and friends excluded."""
    return [a for a in all_actions() if action_name(a) not in _CONTROL_NAMES]


def action_name(action: Any) -> str:
    return getattr(action, "name", str(action)).upper()


def reset_action() -> Any | None:
    for a in all_actions():
        if action_name(a) == "RESET":
            return a
    return None


def is_coordinate_action(action: Any) -> bool:
    """True if this action needs (x, y) data attached before it is meaningful."""
    name = action_name(action)
    return any(h in name for h in _COORDINATE_HINTS)


def with_coordinates(action: Any, x: int, y: int) -> Any:
    """
    Attach coordinates to a complex action.

    The arc-agi API has historically used `action.set_data({"x": ..., "y": ...})`.
    We try several shapes and return the action either way — a coordinate action
    sent without data is still a legal (if useless) move, so we never crash here.
    """
    payload = {"x": int(x), "y": int(y)}
    for attempt in (
        lambda: action.set_data(payload),
        lambda: setattr(action, "data", payload),
        lambda: action.reasoning.update(payload),  # some builds stash it here
    ):
        try:
            attempt()
            return action
        except Exception:  # noqa: BLE001
            continue
    return action


# --------------------------------------------------------------------------
# Frames
# --------------------------------------------------------------------------


def frame_grid(latest_frame: Any) -> Any:
    """The raw pixel/grid payload of a frame, whatever attribute holds it."""
    for attr in ("frame", "grid", "observation", "pixels", "state_grid"):
        val = getattr(latest_frame, attr, None)
        if val is not None:
            return val
    return None


def frame_state(latest_frame: Any) -> str:
    """
    Game state as an upper-case string.
    Typically one of: NOT_PLAYED, NOT_FINISHED, WIN, GAME_OVER.
    """
    val = getattr(latest_frame, "state", None)
    if val is None:
        return "UNKNOWN"
    return getattr(val, "name", str(val)).upper()


def frame_score(latest_frame: Any) -> float:
    for attr in ("score", "points", "level_score"):
        val = getattr(latest_frame, attr, None)
        if isinstance(val, (int, float)):
            return float(val)
    return 0.0


def frame_level(latest_frame: Any) -> int:
    for attr in ("level", "current_level", "stage"):
        val = getattr(latest_frame, attr, None)
        if isinstance(val, int):
            return val
    # Many builds express level progress through score alone.
    return int(frame_score(latest_frame))


def is_terminal(latest_frame: Any) -> bool:
    return frame_state(latest_frame) in {"WIN", "GAME_OVER"}


def is_win(latest_frame: Any) -> bool:
    return frame_state(latest_frame) == "WIN"


def frame_signature(latest_frame: Any) -> str:
    """
    Stable hash of what the agent can see. Used to detect no-op actions and
    to recognise revisited states. Falls back to repr() if the grid is exotic.
    """
    grid = frame_grid(latest_frame)
    try:
        blob = json.dumps(grid, sort_keys=True, default=str)
    except Exception:  # noqa: BLE001
        blob = repr(grid)
    return hashlib.sha1(blob.encode("utf-8", "replace")).hexdigest()[:16]


def grid_dimensions(latest_frame: Any) -> tuple[int, int]:
    """(height, width) of the visible grid, best effort. Defaults to 64x64."""
    grid = frame_grid(latest_frame)
    try:
        # Frames are often a list of one-or-more 2D layers.
        layer = grid
        while isinstance(layer, list) and layer and isinstance(layer[0], list):
            if layer and isinstance(layer[0][0], list):
                layer = layer[0]
                continue
            return len(layer), len(layer[0])
        if isinstance(layer, list) and layer:
            return len(layer), len(layer)
    except Exception:  # noqa: BLE001
        pass
    return 64, 64


def changed(before: Any, after: Any) -> bool:
    """Did the world respond at all to the last action?"""
    return frame_signature(before) != frame_signature(after)


# --------------------------------------------------------------------------
# Diagnostics
# --------------------------------------------------------------------------


def report() -> None:
    """Print what this layer thinks the API looks like. Run this first."""
    print("framework importable :", framework_available())
    if _IMPORT_ERROR and not framework_available():
        print("last import error    :", _IMPORT_ERROR)
        return
    actions = all_actions()
    print("GameAction members   :", [action_name(a) for a in actions])
    print("playable actions     :", [action_name(a) for a in playable_actions()])
    print("reset action         :", action_name(reset_action()) if reset_action() else None)
    print(
        "coordinate actions   :",
        [action_name(a) for a in actions if is_coordinate_action(a)],
    )


if __name__ == "__main__":
    report()
