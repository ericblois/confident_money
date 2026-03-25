from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from gui.script_box import ConditionScriptBox


class ChartRightPanel(QtWidgets.QFrame):
    """Chart-specific side panel that hosts the reusable script input box."""

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
            "info": "#475569",
            "success": "#166534",
            "error": "#b91c1c",
        }

        self.setObjectName("chartRightPanel")
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.setMinimumWidth(320)
        self.setStyleSheet(
            """
            QFrame#chartRightPanel {
                background: #f8fafc;
                border-left: 1px solid #dbe4ee;
            }
            QLabel#scriptTitle {
                color: #0f172a;
                font-size: 16px;
                font-weight: 600;
            }
            QLabel#scriptHelp {
                color: #475569;
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

        self.script_box = ConditionScriptBox(initial_script=initial_script, parent=self)

        self._status_label = QtWidgets.QLabel()
        self._status_label.setObjectName("scriptStatus")
        self._status_label.setWordWrap(True)

        self._run_button = QtWidgets.QPushButton("Run Condition")
        self._shortcuts: list[QtGui.QShortcut] = []

        self._build_layout()
        self._connect_signals()
        self._install_shortcuts()
        self.show_hint(
            "Write a boolean condition using dataframe columns and helper functions. Autocomplete and function argument hints update as you type."
        )

    def _build_layout(self) -> None:
        title_label = QtWidgets.QLabel("Script Editor")
        title_label.setObjectName("scriptTitle")

        help_label = QtWidgets.QLabel("Buy when:")
        help_label.setObjectName("scriptHelp")
        help_label.setWordWrap(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(title_label)
        layout.addWidget(help_label)
        layout.addWidget(self.script_box, 1)
        layout.addWidget(self._status_label)
        layout.addWidget(self._run_button)

    def _connect_signals(self) -> None:
        self._run_button.clicked.connect(self._emit_run_requested)
        self.script_box.script_changed.connect(self.script_changed.emit)

    def _install_shortcuts(self) -> None:
        for key_sequence in ("Ctrl+Return", "Ctrl+Enter"):
            shortcut = QtGui.QShortcut(QtGui.QKeySequence(key_sequence), self)
            shortcut.activated.connect(self._emit_run_requested)
            self._shortcuts.append(shortcut)

    def script_text(self) -> str:
        return self.script_box.script_text()

    def set_script_text(self, script: str) -> None:
        self.script_box.set_script_text(script)

    def show_hint(self, message: str) -> None:
        self._set_status(message, tone="info")

    def show_success(self, message: str) -> None:
        self._set_status(message, tone="success")

    def show_error(self, message: str) -> None:
        self._set_status(message, tone="error")

    def _set_status(self, message: str, *, tone: str) -> None:
        self._status_label.setStyleSheet(f"color: {self._status_palette[tone]};")
        self._status_label.setText(message)

    def _emit_run_requested(self) -> None:
        self.run_requested.emit(self.script_text())
