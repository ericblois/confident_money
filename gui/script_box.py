from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any, Sequence

from PySide6 import QtCore, QtGui, QtWidgets

from condition_script import get_default_function_registry
from condition_script.types import (
    FunctionDefinition,
    FunctionSignature,
    ScriptAutocompleteEntry,
    build_script_autocomplete_entries,
)


DEFAULT_SCRIPT_PLACEHOLDER = (
    "close > mv_avg('close', 20)\n"
    "and volume > mv_avg('volume', 20)"
)
MAX_AUTOCOMPLETE_SUGGESTIONS = 3


@dataclass(frozen=True, slots=True)
class _CompletionContext:
    token_start: int
    token_end: int
    typed_text: str


@dataclass(frozen=True, slots=True)
class _SignatureContext:
    function_definition: FunctionDefinition[Any]
    signature: FunctionSignature[Any]
    current_argument_index: int


def _is_identifier_character(character: str) -> bool:
    return character.isalnum() or character == "_"


def _extract_completion_context(
    script_text: str,
    cursor_position: int,
) -> _CompletionContext | None:
    if cursor_position < 0 or cursor_position > len(script_text):
        return None

    token_start = cursor_position
    while token_start > 0 and _is_identifier_character(script_text[token_start - 1]):
        token_start -= 1

    token_end = cursor_position
    while token_end < len(script_text) and _is_identifier_character(script_text[token_end]):
        token_end += 1

    if token_start == token_end:
        return None

    token_text = script_text[token_start:cursor_position]
    full_token = script_text[token_start:token_end]
    if not token_text or not full_token or not (full_token[0].isalpha() or full_token[0] == "_"):
        return None

    return _CompletionContext(
        token_start=token_start,
        token_end=token_end,
        typed_text=token_text,
    )


def _autocomplete_sort_key(
    entry: ScriptAutocompleteEntry,
    query: str,
) -> tuple[int, int, int, str] | None:
    normalized_query = query.strip().lower()
    if not normalized_query:
        return None

    short_name = entry.short_name.lower()
    full_name = entry.full_name.lower()
    full_name_words = full_name.replace("-", " ").split()
    kind_priority = 0 if entry.kind == "function" else 1

    if short_name == normalized_query:
        return (0, kind_priority, len(entry.short_name), short_name)
    if short_name.startswith(normalized_query):
        return (1, kind_priority, len(entry.short_name), short_name)
    if any(word.startswith(normalized_query) for word in full_name_words):
        return (2, kind_priority, len(entry.short_name), short_name)
    if normalized_query in short_name:
        return (3, kind_priority, len(entry.short_name), short_name)
    if normalized_query in full_name:
        return (4, kind_priority, len(entry.short_name), short_name)

    return None


def get_script_autocomplete_suggestions(
    entries: Sequence[ScriptAutocompleteEntry],
    query: str,
    *,
    limit: int = MAX_AUTOCOMPLETE_SUGGESTIONS,
) -> list[ScriptAutocompleteEntry]:
    """Return the strongest autocomplete matches for the current token."""

    ranked_entries: list[tuple[tuple[int, int, int, str], ScriptAutocompleteEntry]] = []
    for entry in entries:
        sort_key = _autocomplete_sort_key(entry, query)
        if sort_key is not None:
            ranked_entries.append((sort_key, entry))

    ranked_entries.sort(key=lambda ranked_entry: ranked_entry[0])
    return [entry for _, entry in ranked_entries[: max(0, limit)]]


def _select_signature_for_argument(
    function_definition: FunctionDefinition[Any],
    argument_index: int,
) -> FunctionSignature[Any]:
    matching_signatures = [
        signature
        for signature in function_definition.signatures
        if argument_index < len(signature.parameters)
    ]
    if matching_signatures:
        return min(matching_signatures, key=lambda signature: len(signature.parameters))

    return max(function_definition.signatures, key=lambda signature: len(signature.parameters))


def _extract_signature_context(
    script_text: str,
    cursor_position: int,
    function_definitions: dict[str, FunctionDefinition[Any]],
) -> _SignatureContext | None:
    if cursor_position < 0 or cursor_position > len(script_text):
        return None

    call_stack: list[dict[str, Any]] = []
    last_identifier: tuple[str, int, int] | None = None
    string_quote: str | None = None
    is_escaped = False
    index = 0

    while index < cursor_position:
        character = script_text[index]

        if string_quote is not None:
            if is_escaped:
                is_escaped = False
            elif character == "\\":
                is_escaped = True
            elif character == string_quote:
                string_quote = None
            index += 1
            continue

        if character in ("'", '"'):
            string_quote = character
            last_identifier = None
            index += 1
            continue

        if _is_identifier_character(character) and (character.isalpha() or character == "_" or last_identifier is not None):
            start_index = index
            index += 1
            while index < cursor_position and _is_identifier_character(script_text[index]):
                index += 1
            last_identifier = (script_text[start_index:index], start_index, index)
            continue

        if character == "(":
            function_name = None
            if last_identifier is not None:
                _, _, identifier_end = last_identifier
                between_text = script_text[identifier_end:index]
                if between_text.strip() == "":
                    function_name = last_identifier[0]

            call_stack.append(
                {
                    "function_name": function_name,
                    "argument_index": 0,
                }
            )
            last_identifier = None
            index += 1
            continue

        if character == ")":
            if call_stack:
                call_stack.pop()
            last_identifier = None
            index += 1
            continue

        if character == ",":
            if call_stack:
                call_stack[-1]["argument_index"] += 1
            last_identifier = None
            index += 1
            continue

        if not character.isspace():
            last_identifier = None
        index += 1

    for call_context in reversed(call_stack):
        function_name = call_context["function_name"]
        if function_name is None:
            continue

        function_definition = function_definitions.get(function_name)
        if function_definition is None:
            continue

        current_argument_index = int(call_context["argument_index"])
        signature = _select_signature_for_argument(function_definition, current_argument_index)
        return _SignatureContext(
            function_definition=function_definition,
            signature=signature,
            current_argument_index=current_argument_index,
        )

    return None


def build_signature_hint_html(signature_context: _SignatureContext) -> str:
    """Render a compact signature hint with the active argument emphasized."""

    formatted_parameters: list[str] = []
    for index, parameter_spec in enumerate(signature_context.signature.parameters):
        parameter_label = escape(parameter_spec.name)
        if index == signature_context.current_argument_index:
            formatted_parameters.append(f"<b>{parameter_label}</b>")
        else:
            formatted_parameters.append(parameter_label)

    return (
        "<span style='color:#1e293b; font-size:10pt;'>"
        f"<b>{escape(signature_context.function_definition.name)}</b>("
        f"{', '.join(formatted_parameters)})"
        "</span>"
    )


class _AutocompleteDelegate(QtWidgets.QStyledItemDelegate):
    """Paint each suggestion as a short name with a descriptive subtitle."""

    FULL_NAME_ROLE = QtCore.Qt.ItemDataRole.UserRole

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ) -> None:
        painter.save()

        title = index.data(QtCore.Qt.ItemDataRole.DisplayRole) or ""
        subtitle = index.data(self.FULL_NAME_ROLE) or ""

        if option.state & QtWidgets.QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QtGui.QColor("#dbeafe"))
        else:
            painter.fillRect(option.rect, QtGui.QColor("#ffffff"))

        title_rect = option.rect.adjusted(12, 7, -12, -20)
        subtitle_rect = option.rect.adjusted(12, 28, -12, -6)

        title_font = QtGui.QFont(option.font)
        title_font.setBold(True)
        subtitle_font = QtGui.QFont(option.font)
        subtitle_font.setPointSize(max(8, subtitle_font.pointSize() - 1))

        painter.setFont(title_font)
        painter.setPen(QtGui.QColor("#0f172a"))
        painter.drawText(
            title_rect,
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
            str(title),
        )

        painter.setFont(subtitle_font)
        painter.setPen(QtGui.QColor("#64748b"))
        painter.drawText(
            subtitle_rect,
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
            str(subtitle),
        )
        painter.restore()

    def sizeHint(
        self,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ) -> QtCore.QSize:
        del option, index
        return QtCore.QSize(320, 52)


class _AutocompletePopup(QtWidgets.QFrame):
    """Display a small suggestion list anchored near the text cursor."""

    suggestion_selected = QtCore.Signal(object)
    ENTRY_ROLE = QtCore.Qt.ItemDataRole.UserRole + 1

    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("scriptAutocompletePopup")
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.hide()

        self._signature_label = QtWidgets.QLabel()
        self._signature_label.setWordWrap(True)
        self._signature_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self._signature_label.hide()

        self._list_widget = QtWidgets.QListWidget()
        self._list_widget.setItemDelegate(_AutocompleteDelegate(self._list_widget))
        self._list_widget.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self._list_widget.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._list_widget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list_widget.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list_widget.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self._list_widget.setMouseTracking(True)
        self._list_widget.itemEntered.connect(self._list_widget.setCurrentItem)
        self._list_widget.itemClicked.connect(self._emit_clicked_suggestion)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._signature_label)
        layout.addWidget(self._list_widget)

        self.setStyleSheet(
            """
            QFrame#scriptAutocompletePopup {
                background: white;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
            }
            QLabel {
                border-bottom: 1px solid #e2e8f0;
                padding: 10px 12px;
                background: #f8fafc;
                color: #0f172a;
            }
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
                padding: 4px 0;
            }
            QListWidget::item {
                border: none;
                margin: 0;
                padding: 0;
            }
            """
        )

    def show_suggestions(
        self,
        suggestions: Sequence[ScriptAutocompleteEntry],
        *,
        signature_hint_html: str | None,
        position: QtCore.QPoint,
    ) -> None:
        self._list_widget.clear()
        self._signature_label.clear()

        if signature_hint_html:
            self._signature_label.setText(signature_hint_html)
            self._signature_label.show()
        else:
            self._signature_label.hide()

        for suggestion in suggestions:
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.ItemDataRole.DisplayRole, suggestion.short_name)
            item.setData(_AutocompleteDelegate.FULL_NAME_ROLE, suggestion.subtitle)
            item.setData(self.ENTRY_ROLE, suggestion)
            self._list_widget.addItem(item)

        if self._list_widget.count() == 0:
            self._list_widget.hide()
        else:
            self._list_widget.show()
            self._list_widget.setCurrentRow(0)

        if self._list_widget.count() == 0 and not signature_hint_html:
            self.hide()
            return

        popup_height = 0
        if self._signature_label.isVisible():
            signature_height = self._signature_label.sizeHint().height()
            popup_height += signature_height
        if self._list_widget.isVisible():
            item_height = max(52, self._list_widget.sizeHintForRow(0))
            popup_height += item_height * self._list_widget.count() + 10
        parent_width = self.parentWidget().width() if self.parentWidget() is not None else 340
        popup_width = min(max(280, parent_width - 32), 420)
        self.resize(popup_width, popup_height)
        self.move(position)
        self.raise_()
        self.show()

    def move_selection(self, step: int) -> None:
        if not self.isVisible() or self._list_widget.count() == 0:
            return

        next_row = (self._list_widget.currentRow() + step) % self._list_widget.count()
        self._list_widget.setCurrentRow(next_row)

    def select_current_suggestion(self) -> bool:
        if not self.isVisible():
            return False

        item = self._list_widget.currentItem()
        if item is None:
            return False

        self._emit_item(item)
        return True

    def _emit_clicked_suggestion(self, item: QtWidgets.QListWidgetItem) -> None:
        self._emit_item(item)

    def _emit_item(self, item: QtWidgets.QListWidgetItem) -> None:
        suggestion = item.data(self.ENTRY_ROLE)
        if suggestion is not None:
            self.suggestion_selected.emit(suggestion)


class ConditionScriptEditor(QtWidgets.QPlainTextEdit):
    """Plain-text script editor with a small cursor-anchored autocomplete popup."""

    def __init__(
        self,
        autocomplete_entries: Sequence[ScriptAutocompleteEntry],
        function_definitions: Sequence[FunctionDefinition[Any]],
        *,
        popup_parent: QtWidgets.QWidget,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._autocomplete_entries = tuple(autocomplete_entries)
        self._function_definitions = {
            function_definition.name: function_definition
            for function_definition in function_definitions
        }
        self._popup_parent = popup_parent
        self._completion_context: _CompletionContext | None = None
        self._autocomplete_popup = _AutocompletePopup(popup_parent)
        self._autocomplete_popup.suggestion_selected.connect(self._insert_suggestion)

        self.textChanged.connect(self._refresh_editor_assistance)
        self.cursorPositionChanged.connect(self._refresh_editor_assistance)
        self.verticalScrollBar().valueChanged.connect(self._refresh_popup_position)
        self.horizontalScrollBar().valueChanged.connect(self._refresh_popup_position)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if self._autocomplete_popup.isVisible():
            if event.key() == QtCore.Qt.Key.Key_Down:
                self._autocomplete_popup.move_selection(1)
                return
            if event.key() == QtCore.Qt.Key.Key_Up:
                self._autocomplete_popup.move_selection(-1)
                return
            if event.key() in (
                QtCore.Qt.Key.Key_Return,
                QtCore.Qt.Key.Key_Enter,
                QtCore.Qt.Key.Key_Tab,
                QtCore.Qt.Key.Key_Backtab,
            ):
                if self._autocomplete_popup.select_current_suggestion():
                    return
            if event.key() == QtCore.Qt.Key.Key_Escape:
                self._hide_autocomplete()
                return

        super().keyPressEvent(event)

    def focusOutEvent(self, event: QtGui.QFocusEvent) -> None:
        self._hide_autocomplete()
        super().focusOutEvent(event)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._refresh_popup_position()

    def _refresh_editor_assistance(self) -> None:
        """Refresh autocomplete suggestions and function signature help together."""

        cursor = self.textCursor()
        if cursor.hasSelection():
            self._hide_autocomplete()
            return

        script_text = self.toPlainText()
        cursor_position = cursor.position()
        completion_context = _extract_completion_context(script_text, cursor_position)
        signature_context = _extract_signature_context(
            script_text,
            cursor_position,
            self._function_definitions,
        )
        suggestions = (
            get_script_autocomplete_suggestions(
                self._autocomplete_entries,
                completion_context.typed_text,
            )
            if completion_context is not None
            else []
        )
        signature_hint_html = (
            build_signature_hint_html(signature_context)
            if signature_context is not None
            else None
        )

        if not suggestions and signature_hint_html is None:
            self._hide_autocomplete()
            return

        self._completion_context = completion_context
        self._autocomplete_popup.show_suggestions(
            suggestions,
            signature_hint_html=signature_hint_html,
            position=self._popup_position(),
        )

    def _refresh_popup_position(self) -> None:
        if self._autocomplete_popup.isVisible():
            self._autocomplete_popup.move(self._popup_position())

    def _popup_position(self) -> QtCore.QPoint:
        cursor_rect = self.cursorRect()
        global_position = self.viewport().mapToGlobal(cursor_rect.bottomLeft() + QtCore.QPoint(0, 6))
        return self._popup_parent.mapFromGlobal(global_position)

    def _hide_autocomplete(self) -> None:
        self._completion_context = None
        self._autocomplete_popup.hide()

    def _insert_suggestion(self, suggestion: ScriptAutocompleteEntry) -> None:
        if self._completion_context is None:
            return

        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.setPosition(self._completion_context.token_start)
        cursor.setPosition(
            self._completion_context.token_end,
            QtGui.QTextCursor.MoveMode.KeepAnchor,
        )
        cursor.insertText(suggestion.short_name)

        if suggestion.kind == "function":
            next_character = self._character_at_position(cursor.position())
            if next_character != "(":
                cursor.insertText("()")
                cursor.movePosition(QtGui.QTextCursor.MoveOperation.Left)
        cursor.endEditBlock()

        self.setTextCursor(cursor)
        self.setFocus()
        self._refresh_editor_assistance()

    def _character_at_position(self, position: int) -> str:
        script_text = self.toPlainText()
        if 0 <= position < len(script_text):
            return script_text[position]
        return ""


class ConditionScriptBox(QtWidgets.QFrame):
    """Side-panel editor for writing and running stock condition scripts."""

    run_requested = QtCore.Signal(str)

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

        function_registry = get_default_function_registry()
        function_definitions = tuple(
            runtime_function.definition
            for runtime_function in function_registry.values()
        )
        autocomplete_entries = build_script_autocomplete_entries(function_definitions)

        self.setObjectName("conditionScriptPanel")
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.setMinimumWidth(320)
        self.setStyleSheet(
            """
            QFrame#conditionScriptPanel {
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
            QPlainTextEdit {
                background: white;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                color: #111827;
                selection-background-color: #bfdbfe;
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

        self._editor = ConditionScriptEditor(
            autocomplete_entries,
            function_definitions,
            popup_parent=self,
            parent=self,
        )
        self._editor.setPlaceholderText(DEFAULT_SCRIPT_PLACEHOLDER)
        self._editor.setPlainText(initial_script)
        self._editor.setTabStopDistance(24)

        self._status_label = QtWidgets.QLabel()
        self._status_label.setObjectName("scriptStatus")
        self._status_label.setWordWrap(True)

        self._run_button = QtWidgets.QPushButton("Run Condition")
        self._run_button.clicked.connect(self._emit_run_requested)
        self._shortcuts: list[QtGui.QShortcut] = []

        self._build_layout()
        self._install_shortcuts()
        self.show_hint(
            "Write a boolean condition using dataframe columns and helper functions. Autocomplete and function argument hints update as you type."
        )

    def _build_layout(self) -> None:
        """Create a compact editor layout with the run button anchored at the bottom."""

        title_label = QtWidgets.QLabel("Condition Script")
        title_label.setObjectName("scriptTitle")

        help_label = QtWidgets.QLabel(
            "Type a function or parameter name to see up to three suggestions below the cursor."
        )
        help_label.setObjectName("scriptHelp")
        help_label.setWordWrap(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(title_label)
        layout.addWidget(help_label)
        layout.addWidget(self._editor, 1)
        layout.addWidget(self._status_label)
        layout.addWidget(self._run_button)

    def _install_shortcuts(self) -> None:
        """Add keyboard shortcuts so scripts can be run without leaving the editor."""

        for key_sequence in ("Ctrl+Return", "Ctrl+Enter"):
            shortcut = QtGui.QShortcut(QtGui.QKeySequence(key_sequence), self)
            shortcut.activated.connect(self._emit_run_requested)
            self._shortcuts.append(shortcut)

    def script_text(self) -> str:
        return self._editor.toPlainText().strip()

    def set_script_text(self, script: str) -> None:
        self._editor.setPlainText(script)

    def show_hint(self, message: str) -> None:
        self._set_status(message, tone="info")

    def show_success(self, message: str) -> None:
        self._set_status(message, tone="success")

    def show_error(self, message: str) -> None:
        self._set_status(message, tone="error")

    def _set_status(self, message: str, *, tone: str) -> None:
        """Render script feedback with a small amount of color-coded emphasis."""

        self._status_label.setStyleSheet(f"color: {self._status_palette[tone]};")
        self._status_label.setText(message)

    def _emit_run_requested(self) -> None:
        self.run_requested.emit(self.script_text())
