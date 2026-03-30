from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from html import escape
from typing import Any

from features.features import build_search_sort_key

from .types import (
    FunctionDefinition,
    FunctionSignature,
    ScriptAutocompleteEntry,
    build_script_autocomplete_entries,
)


@dataclass(frozen=True, slots=True)
class SignatureContext:
    function_definition: FunctionDefinition[Any]
    signature: FunctionSignature[Any]
    current_argument_index: int


def get_default_autocomplete_entries() -> tuple[ScriptAutocompleteEntry, ...]:
    from .tester import get_default_function_definitions

    return build_script_autocomplete_entries(get_default_function_definitions())


def get_script_autocomplete_suggestions(
    entries: Sequence[ScriptAutocompleteEntry],
    query: str,
    *,
    limit: int = 3,
) -> list[ScriptAutocompleteEntry]:
    """Return the strongest autocomplete matches for the current token."""

    ranked_entries: list[tuple[tuple[int, int, int, str], ScriptAutocompleteEntry]] = []
    for entry in entries:
        sort_key = _autocomplete_sort_key(entry, query)
        if sort_key is not None:
            ranked_entries.append((sort_key, entry))

    ranked_entries.sort(key=lambda ranked_entry: ranked_entry[0])
    return [entry for _, entry in ranked_entries[: max(0, limit)]]


def extract_signature_context(
    script_text: str,
    cursor_position: int,
    function_definitions: Mapping[str, FunctionDefinition[Any]],
) -> SignatureContext | None:
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

        if _is_identifier_character(character) and (
            character.isalpha() or character == "_" or last_identifier is not None
        ):
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
                if script_text[identifier_end:index].strip() == "":
                    function_name = last_identifier[0]

            call_stack.append({"function_name": function_name, "argument_index": 0})
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
        signature = _select_signature_for_argument(
            function_definition,
            current_argument_index,
        )
        return SignatureContext(
            function_definition=function_definition,
            signature=signature,
            current_argument_index=current_argument_index,
        )

    return None


def build_signature_hint_html(
    signature_context: SignatureContext,
    *,
    text_color: str | None = None,
    font_size_pt: int | None = None,
) -> str:
    """Render a compact signature hint with the active argument emphasized."""

    formatted_parameters: list[str] = []
    for index, parameter_spec in enumerate(signature_context.signature.parameters):
        parameter_label = escape(parameter_spec.name)
        if index == signature_context.current_argument_index:
            formatted_parameters.append(f"<b>{parameter_label}</b>")
        else:
            formatted_parameters.append(parameter_label)

    contents = (
        f"<b>{escape(signature_context.function_definition.name)}</b>("
        f"{', '.join(formatted_parameters)})"
    )
    if text_color is None and font_size_pt is None:
        return contents

    style_parts: list[str] = []
    if text_color is not None:
        style_parts.append(f"color:{text_color}")
    if font_size_pt is not None:
        style_parts.append(f"font-size:{font_size_pt}pt")
    return f"<span style='{'; '.join(style_parts)}'>{contents}</span>"


def _is_identifier_character(character: str) -> bool:
    return character.isalnum() or character == "_"


def _autocomplete_sort_key(
    entry: ScriptAutocompleteEntry,
    query: str,
) -> tuple[int, int, int, str] | None:
    kind_priority = {"function": 0, "operator": 1, "parameter": 2}[entry.kind]
    return build_search_sort_key(
        query,
        script_name=entry.short_name,
        full_name=entry.full_name,
        priority=kind_priority,
    )


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


__all__ = [
    "SignatureContext",
    "build_signature_hint_html",
    "extract_signature_context",
    "get_default_autocomplete_entries",
    "get_script_autocomplete_suggestions",
]
