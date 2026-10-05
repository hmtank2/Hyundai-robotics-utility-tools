"""Small, toolkit-independent motion model for the interactive graph."""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass
class GraphPoint:
    x: float
    y: float
    anchor_x: float
    anchor_y: float
    vx: float = 0.0
    vy: float = 0.0
    scale: float = 1.0


def advance(points: list[GraphPoint], hover: int | None, dragged: int | None,
            pointer: tuple[float, float] | None) -> bool:
    """Advance one animation frame; return whether another frame is useful."""
    moving = False
    for index, point in enumerate(points):
        target_scale = 1.45 if index == hover else 1.0
        point.scale += (target_scale - point.scale) * 0.28
        moving |= abs(target_scale - point.scale) > 0.01
        if index == dragged:
            point.vx = point.vy = 0.0
            continue
        fx = (point.anchor_x - point.x) * 0.035
        fy = (point.anchor_y - point.y) * 0.035
        if pointer is not None and hover is not None and index != hover:
            dx, dy = point.x - pointer[0], point.y - pointer[1]
            distance = max(math.hypot(dx, dy), 1.0)
            if distance < 95:
                push = (95 - distance) / 95 * 1.8
                fx += dx / distance * push
                fy += dy / distance * push
        point.vx = (point.vx + fx) * 0.84
        point.vy = (point.vy + fy) * 0.84
        point.x += point.vx
        point.y += point.vy
        moving |= abs(point.vx) + abs(point.vy) > 0.08
    return moving
