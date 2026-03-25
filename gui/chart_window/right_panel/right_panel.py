from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from .script_content import ScriptContent
from .xgboost_content import XGBoostContent

_CHART_BACKGROUND = "#24211f"
_TAB_BORDER_COLOR = "#f8fafc"


class _TabFiller(QtWidgets.QFrame):
    """Fill the unused tab-row width with a border-only spacer."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("tabFiller")
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )


class ChartRightPanel(QtWidgets.QFrame):
    """Chart-specific side panel with tabs for script editing and XGBoost."""

    run_requested = QtCore.Signal(str)
    script_changed = QtCore.Signal(str)

    def __init__(
        self,
        *,
        initial_script: str = "",
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._status_palette = {
            "info": "#cbd5e1",
            "success": "#86efac",
            "error": "#fca5a5",
        }

        self.setObjectName("chartRightPanel")
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.setMinimumWidth(320)
        self.setStyleSheet(
            """
            QFrame#chartRightPanel {
                background: """
            + _CHART_BACKGROUND
            + """;
                border-left: 1px solid rgba(248, 250, 252, 0.35);
            }
            QTabBar {
                background: """
            + _CHART_BACKGROUND
            + """;
            }
            QWidget#tabRow {
                background: """
            + _CHART_BACKGROUND
            + """;
            }
            QStackedWidget#tabContent {
                background: """
            + _CHART_BACKGROUND
            + """;
                border: none;
            }
            QFrame#tabFiller {
                background: """
            + _CHART_BACKGROUND
            + """;
                border-bottom: 2px solid """
            + _TAB_BORDER_COLOR
            + """;
            }
            QTabBar::tab {
                background: """
            + _CHART_BACKGROUND
            + """;
                border-top: 2px solid """
            + _TAB_BORDER_COLOR
            + """;
                border-right: 1px solid """
            + _TAB_BORDER_COLOR
            + """;
                border-bottom: 2px solid """
            + _TAB_BORDER_COLOR
            + """;
                border-left: 0;
                color: """
            + _TAB_BORDER_COLOR
            + """;
                font-size: 13px;
                font-weight: 600;
                margin: 0;
                padding: 10px 20px;
                border-radius: 0;
            }
            QTabBar::tab:first {
                border-left: 1px solid """
            + _TAB_BORDER_COLOR
            + """;
            }
            QTabBar::tab:selected {
                border-bottom: 0;
                padding-bottom: 12px;
            }
            QTabBar::tab:hover {
                color: """
            + _TAB_BORDER_COLOR
            + """;
            }
            QLabel#panelTitle {
                color: #f8fafc;
                font-size: 16px;
                font-weight: 600;
            }
            QLabel#panelHelp {
                color: #cbd5e1;
            }
            QLabel#scriptStatus {
                padding-top: 4px;
            }
            QPushButton {
                background: #2563eb;
                border: none;
                border-radius: 6px;
                color: white;
                font-weight: 600;
                min-height: 36px;
                padding: 0 14px;
            }
            QPushButton:hover {
                background: #1d4ed8;
            }
            QPushButton:pressed {
                background: #1e40af;
            }
            """
        )

        self._tab_bar = QtWidgets.QTabBar(self)
        self._tab_bar.setDrawBase(False)
        self._tab_bar.setDocumentMode(True)
        self._tab_bar.setExpanding(False)
        self._tab_bar.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Maximum,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self._left_tab_filler = _TabFiller(self)
        self._right_tab_filler = _TabFiller(self)
        self._tab_row = QtWidgets.QWidget(self)
        self._tab_row.setObjectName("tabRow")
        self._content_stack = QtWidgets.QStackedWidget(self)
        self._content_stack.setObjectName("tabContent")

        self._script_content = ScriptContent(
            initial_script=initial_script,
            status_palette=self._status_palette,
            parent=self,
        )
        self._xgboost_content = XGBoostContent(parent=self)

        self.script_box = self._script_content.script_box

        self._build_layout()
        self._connect_signals()

    def _build_layout(self) -> None:
        container = QtWidgets.QVBoxLayout(self)
        container.setContentsMargins(0, 18, 0, 18)
        container.setSpacing(0)

        tab_row_layout = QtWidgets.QHBoxLayout(self._tab_row)
        tab_row_layout.setContentsMargins(0, 0, 0, 0)
        tab_row_layout.setSpacing(0)

        self._tab_bar.addTab("Script Editor")
        self._tab_bar.addTab("XGBoost")
        self._tab_bar.setCurrentIndex(0)

        self._content_stack.addWidget(self._script_content)
        self._content_stack.addWidget(self._xgboost_content)

        filler_height = self._tab_bar.sizeHint().height()
        self._left_tab_filler.setFixedHeight(filler_height)
        self._right_tab_filler.setFixedHeight(filler_height)

        tab_row_layout.addWidget(self._left_tab_filler, 1)
        tab_row_layout.addWidget(self._tab_bar)
        tab_row_layout.addWidget(self._right_tab_filler, 1)

        container.addWidget(self._tab_row)
        container.addSpacing(16)

        content_wrapper = QtWidgets.QWidget(self)
        content_layout = QtWidgets.QVBoxLayout(content_wrapper)
        content_layout.setContentsMargins(18, 0, 18, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self._content_stack)

        container.addWidget(content_wrapper, 1)

    def _connect_signals(self) -> None:
        self._script_content.run_requested.connect(self.run_requested.emit)
        self._script_content.script_changed.connect(self.script_changed.emit)
        self._tab_bar.currentChanged.connect(self._content_stack.setCurrentIndex)

    def script_text(self) -> str:
        return self._script_content.script_text()

    def set_script_text(self, script: str) -> None:
        self._script_content.set_script_text(script)

    def show_hint(self, message: str) -> None:
        self._script_content.show_hint(message)

    def show_success(self, message: str) -> None:
        self._script_content.show_success(message)

    def show_error(self, message: str) -> None:
        self._script_content.show_error(message)
