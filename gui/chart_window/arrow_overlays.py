from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ArrowOverlay:
    """Describe an arrow drawn from one chart coordinate to another."""

    start_x: Any
    start_y: float
    end_x: Any
    end_y: float
    pane: str = "main"
    color: str = "#f8fafc"
    width: float = 2.0
    opacity: float = 0.95
    head_length: float | None = None
    tip_angle: float = 22.0
    base_angle: float = 12.0
    label_text: str | None = None
    label_side: str = "below"
    label_visible_max_months: int | None = None
