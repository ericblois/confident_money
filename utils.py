from __future__ import annotations

import sys


_LAST_CONSOLE_LOADING_LENGTH = 0
_LAST_CONSOLE_LOADING_ACTIVE = False
_CONSOLE_LOADING_BAR_WIDTH = 30


def console_loading(percent: float, message: str = "Loading") -> None:
    """Render a single-line console loading bar and overwrite the previous one."""
    global _LAST_CONSOLE_LOADING_ACTIVE, _LAST_CONSOLE_LOADING_LENGTH

    clamped_percent = max(0.0, min(100.0, float(percent)))
    filled_width = round((_CONSOLE_LOADING_BAR_WIDTH * clamped_percent) / 100)
    bar = "#" * filled_width + "-" * (_CONSOLE_LOADING_BAR_WIDTH - filled_width)
    message_prefix = f"{message.strip()} " if message.strip() else ""
    loading_message = f"{message_prefix}[{bar}] {clamped_percent:6.2f}%"
    padding = " " * max(0, _LAST_CONSOLE_LOADING_LENGTH - len(loading_message))
    prefix = "\r" if _LAST_CONSOLE_LOADING_ACTIVE else ""
    suffix = "\n" if clamped_percent >= 100.0 else ""

    sys.stdout.write(f"{prefix}{loading_message}{padding}{suffix}")
    sys.stdout.flush()

    _LAST_CONSOLE_LOADING_ACTIVE = clamped_percent < 100.0
    _LAST_CONSOLE_LOADING_LENGTH = 0 if clamped_percent >= 100.0 else len(loading_message)
