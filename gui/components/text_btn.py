from __future__ import annotations

from dataclasses import dataclass

from PySide6 import QtCore, QtWidgets


@dataclass(slots=True)
class TextBtnStyle:
    """Bundle the visual settings for a reusable text button."""

    background: str = "#2563eb"
    hover_background: str = "#1d4ed8"
    pressed_background: str = "#1e40af"
    text_color: str = "#ffffff"
    border_color: str = "transparent"
    hover_border_color: str | None = None
    pressed_border_color: str | None = None
    border_radius: int = 6
    min_height: int = 36
    horizontal_padding: int = 14
    font_size: int = 13
    font_weight: int = 600


class TextBtn(QtWidgets.QPushButton):
    """Reusable text button with configurable colors and sizing."""

    def __init__(
        self,
        text: str,
        *,
        style: TextBtnStyle | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self._style = style or TextBtnStyle()
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.set_style(self._style)

    def set_style(self, style: TextBtnStyle) -> None:
        """Apply a new style profile to the button."""

        self._style = style
        hover_border_color = style.hover_border_color or style.border_color
        pressed_border_color = style.pressed_border_color or hover_border_color

        self.setMinimumHeight(style.min_height)
        self.setStyleSheet(
            f"""
            QPushButton {{
                background: {style.background};
                border: 1px solid {style.border_color};
                border-radius: {style.border_radius}px;
                color: {style.text_color};
                font-size: {style.font_size}px;
                font-weight: {style.font_weight};
                padding: 0 {style.horizontal_padding}px;
            }}
            QPushButton:hover {{
                background: {style.hover_background};
                border-color: {hover_border_color};
            }}
            QPushButton:pressed {{
                background: {style.pressed_background};
                border-color: {pressed_border_color};
            }}
            """
        )
