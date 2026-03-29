from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from gui.script_box import ConditionScriptBox


class ScriptContent(QtWidgets.QWidget):
    """Host the reusable script editor content shown in the right panel."""

    run_requested = QtCore.Signal(str, str)
    script_changed = QtCore.Signal(str, str)

    def __init__(
        self,
        *,
        initial_script: str = "",
        initial_sell_script: str = "",
        status_palette: dict[str, str],
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._status_palette = status_palette
        self._shortcuts: list[QtGui.QShortcut] = []

        self.script_box = ConditionScriptBox(initial_script=initial_script, parent=self)
        self.sell_script_box = ConditionScriptBox(
            initial_script=initial_sell_script,
            parent=self,
        )

        self._status_label = QtWidgets.QLabel()
        self._status_label.setObjectName("scriptStatus")
        self._status_label.setWordWrap(True)

        self._run_button = QtWidgets.QPushButton("Run Conditions")

        self._build_layout()
        self._connect_signals()
        self._install_shortcuts()
        self.show_hint(
            "Write boolean buy and sell conditions using dataframe columns and helper functions. Autocomplete and function argument hints update as you type."
        )

    def _build_layout(self) -> None:
        title_label = QtWidgets.QLabel("Script Editor")
        title_label.setObjectName("panelTitle")

        buy_label = QtWidgets.QLabel("Buy when:")
        buy_label.setObjectName("panelHelp")
        buy_label.setWordWrap(True)

        sell_label = QtWidgets.QLabel("Sell when:")
        sell_label.setObjectName("panelHelp")
        sell_label.setWordWrap(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(title_label)
        layout.addWidget(buy_label)
        layout.addWidget(self.script_box, 1)
        layout.addWidget(sell_label)
        layout.addWidget(self.sell_script_box, 1)
        layout.addWidget(self._status_label)
        layout.addWidget(self._run_button)

    def _connect_signals(self) -> None:
        self._run_button.clicked.connect(self._emit_run_requested)
        self.script_box.script_changed.connect(self._emit_script_changed)
        self.sell_script_box.script_changed.connect(self._emit_script_changed)

    def _install_shortcuts(self) -> None:
        for key_sequence in ("Ctrl+Return", "Ctrl+Enter"):
            shortcut = QtGui.QShortcut(QtGui.QKeySequence(key_sequence), self)
            shortcut.activated.connect(self._emit_run_requested)
            self._shortcuts.append(shortcut)

    def script_text(self) -> str:
        return self.script_box.script_text()

    def set_script_text(self, script: str) -> None:
        self.script_box.set_script_text(script)

    def sell_script_text(self) -> str:
        return self.sell_script_box.script_text()

    def set_sell_script_text(self, script: str) -> None:
        self.sell_script_box.set_script_text(script)

    def show_hint(self, message: str) -> None:
        self._set_status(message, tone="info")

    def show_success(self, message: str) -> None:
        self._set_status(message, tone="success")

    def show_error(self, message: str) -> None:
        self._set_status(message, tone="error")

    def _set_status(self, message: str, *, tone: str) -> None:
        self._status_label.setStyleSheet(f"color: {self._status_palette[tone]};")
        self._status_label.setText(message)

    def _emit_script_changed(self) -> None:
        self.script_changed.emit(self.script_text(), self.sell_script_text())

    def _emit_run_requested(self) -> None:
        self.run_requested.emit(self.script_text(), self.sell_script_text())
