from __future__ import annotations

from dataclasses import dataclass

from PySide6 import QtCore, QtWidgets


@dataclass(slots=True)
class LabeledCheckBoxStyle:
    """Bundle text and indicator sizing for reusable checkboxes."""

    text_color: str = "#f8fafc"
    font_size: int = 13
    font_weight: int = 500
    spacing: int = 10
    indicator_size: int = 18


class LabeledCheckBox(QtWidgets.QCheckBox):
    """Reusable checkbox with a right-side text label."""

    def __init__(
        self,
        text: str,
        *,
        style: LabeledCheckBoxStyle | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self._style = style or LabeledCheckBoxStyle()
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.set_style(self._style)

    def set_style(self, style: LabeledCheckBoxStyle) -> None:
        """Apply a new visual style to the checkbox."""

        self._style = style
        self.setStyleSheet(
            f"""
            QCheckBox {{
                color: {style.text_color};
                font-size: {style.font_size}px;
                font-weight: {style.font_weight};
                spacing: {style.spacing}px;
            }}
            QCheckBox::indicator {{
                width: {style.indicator_size}px;
                height: {style.indicator_size}px;
            }}
            """
        )
