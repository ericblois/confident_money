from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from gui.components.labeled_checkbox import LabeledCheckBox

_CHART_BACKGROUND = "#24211f"


class ChartLeftPanel(QtWidgets.QFrame):
    """Placeholder container for future chart options."""

    close_requested = QtCore.Signal()
    show_trade_arrows_changed = QtCore.Signal(bool)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("chartLeftPanel")
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.setMinimumWidth(320)
        self.setStyleSheet(
            """
            QFrame#chartLeftPanel {
                background: """
            + _CHART_BACKGROUND
            + """;
                border-right: 1px solid rgba(248, 250, 252, 0.35);
            }
            QToolButton#leftPanelCloseButton {
                background: transparent;
                border: none;
                color: #f8fafc;
                font-size: 18px;
                font-weight: 600;
                min-height: 28px;
                max-height: 28px;
                min-width: 28px;
                max-width: 28px;
                padding: 0;
            }
            QToolButton#leftPanelCloseButton:hover {
                color: #cbd5e1;
            }
            QToolButton#leftPanelCloseButton:pressed {
                color: #94a3b8;
            }
            """
        )

        self._dismiss_button = QtWidgets.QToolButton(self)
        self._dismiss_button.setObjectName("leftPanelCloseButton")
        self._dismiss_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self._dismiss_button.setText("‹")
        self._dismiss_button.setToolTip("Hide chart options")
        self._show_trade_arrows_checkbox = LabeledCheckBox(
            "Show trade arrows",
            parent=self,
        )

        self._build_layout()
        self._dismiss_button.clicked.connect(self.close_requested.emit)
        self._show_trade_arrows_checkbox.toggled.connect(self.show_trade_arrows_changed.emit)

    def _build_layout(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(0)

        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addStretch(1)
        header_layout.addWidget(self._dismiss_button)

        layout.addLayout(header_layout)
        layout.addSpacing(18)
        layout.addWidget(self._show_trade_arrows_checkbox)
        layout.addStretch(1)

    def show_trade_arrows_enabled(self) -> bool:
        return self._show_trade_arrows_checkbox.isChecked()
