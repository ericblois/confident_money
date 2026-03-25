from __future__ import annotations

from PySide6 import QtWidgets


class XGBoostContent(QtWidgets.QWidget):
    """Placeholder content for the future XGBoost panel."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_layout()

    def _build_layout(self) -> None:
        title_label = QtWidgets.QLabel("XGBoost")
        title_label.setObjectName("panelTitle")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(title_label)
        layout.addStretch(1)

