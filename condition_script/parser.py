from __future__ import annotations

import ast
import io
import token
import tokenize
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal, cast

from condition_script.types import (
    ANY,
    BOOLEAN,
    NUMBER,
    STRING,
    ArithmeticExpression,
    ColumnExpression,
    ComparisonOperator,
    ComparisonExpression,
    ConditionExpression,
    Expression,
    FunctionCallExpression,
    FunctionDefinition,
    LiteralExpression,
    LogicalExpression,
    ScriptType,
    UnaryExpression,
    WORD_COMPARISON_OPERATORS,
)


type FunctionRegistry = Mapping[str, object]
type NameTypeResolver = Callable[[str], ScriptType[Any]]
type _TokenKind = Literal["name", "number", "string", "operator", "eof"]

_BOOLEAN_LITERALS = {"True": True, "False": False}
_ADDITIVE_OPERATORS = {"+", "-"}
_MULTIPLICATIVE_OPERATORS = {"*", "/", "%"}
_SYMBOL_COMPARISON_OPERATORS = {"==", "!=", ">", ">=", "<", "<="}


@dataclass(frozen=True, slots=True)
class _Token:
    kind: _TokenKind
    text: str


class _Parser:
    def __init__(
        self,
        tokens: Sequence[_Token],
        *,
        functions: FunctionRegistry,
        resolve_name_type: NameTypeResolver,
    ) -> None:
        self._tokens = tokens
        self._index = 0
        self._functions = functions
        self._resolve_name_type = resolve_name_type

    def parse(self) -> Expression[Any]:
        return self._parse_or_expression()

    def ensure_finished(self) -> None:
        if self._current.kind != "eof":
            raise ValueError(f"Unsupported condition syntax near '{self._current.text}'.")

    @property
    def _current(self) -> _Token:
        return self._tokens[self._index]

    def _advance(self) -> _Token:
        token_value = self._current
        if token_value.kind != "eof":
            self._index += 1
        return token_value

    def _match_name(self, name: str) -> bool:
        if self._current.kind == "name" and self._current.text == name:
            self._advance()
            return True
        return False

    def _match_operator(self, operator: str) -> bool:
        if self._current.kind == "operator" and self._current.text == operator:
            self._advance()
            return True
        return False

    def _expect_operator(self, operator: str, *, message: str) -> None:
        if not self._match_operator(operator):
            raise ValueError(message)

    def _parse_or_expression(self) -> Expression[Any]:
        expression = self._parse_and_expression()
        if not self._match_name("or"):
            return expression

        values = [
            _ensure_type(expression, BOOLEAN, context="Logical operator 'or'"),
            _ensure_type(
                self._parse_and_expression(),
                BOOLEAN,
                context="Logical operator 'or'",
            ),
        ]

        while self._match_name("or"):
            values.append(
                _ensure_type(
                    self._parse_and_expression(),
                    BOOLEAN,
                    context="Logical operator 'or'",
                )
            )

        return LogicalExpression(operator="or", values=tuple(values))

    def _parse_and_expression(self) -> Expression[Any]:
        expression = self._parse_not_expression()
        if not self._match_name("and"):
            return expression

        values = [
            _ensure_type(expression, BOOLEAN, context="Logical operator 'and'"),
            _ensure_type(
                self._parse_not_expression(),
                BOOLEAN,
                context="Logical operator 'and'",
            ),
        ]

        while self._match_name("and"):
            values.append(
                _ensure_type(
                    self._parse_not_expression(),
                    BOOLEAN,
                    context="Logical operator 'and'",
                )
            )

        return LogicalExpression(operator="and", values=tuple(values))

    def _parse_not_expression(self) -> Expression[Any]:
        if self._match_name("not"):
            operand = _ensure_type(
                self._parse_not_expression(),
                BOOLEAN,
                context="Unary operator 'not'",
            )
            return UnaryExpression(operator="not", operand=operand, value_type=BOOLEAN)

        return self._parse_comparison_expression()

    def _parse_comparison_expression(self) -> Expression[Any]:
        left = self._parse_additive_expression()
        comparisons: list[ComparisonExpression] = []

        while self._is_comparison_operator(self._current):
            operator = self._consume_comparison_operator()
            right = self._parse_additive_expression()
            comparisons.append(
                self._build_comparison_expression(operator, left, right)
            )
            left = right

        if not comparisons:
            return left

        if len(comparisons) > 1 and any(
            comparison.operator == "crosses" for comparison in comparisons
        ):
            raise ValueError("Comparison operator 'crosses' does not support chaining.")

        if len(comparisons) == 1:
            return comparisons[0]
        return LogicalExpression(operator="and", values=tuple(comparisons))

    def _build_comparison_expression(
        self,
        operator: str,
        left: Expression[Any],
        right: Expression[Any],
    ) -> ComparisonExpression:
        if operator == "crosses":
            _ensure_type(left, NUMBER, context="Comparison operator 'crosses'")
            _ensure_type(right, NUMBER, context="Comparison operator 'crosses'")

        return ComparisonExpression(
            operator=cast(ComparisonOperator, operator),
            left=left,
            right=right,
        )

    def _parse_additive_expression(self) -> Expression[Any]:
        expression = self._parse_multiplicative_expression()

        while self._current.kind == "operator" and self._current.text in _ADDITIVE_OPERATORS:
            operator = self._advance().text
            right = self._parse_multiplicative_expression()
            _ensure_type(expression, NUMBER, context=f"Arithmetic operator '{operator}'")
            _ensure_type(right, NUMBER, context=f"Arithmetic operator '{operator}'")
            expression = ArithmeticExpression(operator=operator, left=expression, right=right)

        return expression

    def _parse_multiplicative_expression(self) -> Expression[Any]:
        expression = self._parse_unary_math_expression()

        while (
            self._current.kind == "operator"
            and self._current.text in _MULTIPLICATIVE_OPERATORS
        ):
            operator = self._advance().text
            right = self._parse_unary_math_expression()
            _ensure_type(expression, NUMBER, context=f"Arithmetic operator '{operator}'")
            _ensure_type(right, NUMBER, context=f"Arithmetic operator '{operator}'")
            expression = ArithmeticExpression(operator=operator, left=expression, right=right)

        return expression

    def _parse_unary_math_expression(self) -> Expression[Any]:
        if self._match_operator("+"):
            operand = _ensure_type(
                self._parse_unary_math_expression(),
                NUMBER,
                context="Unary operator '+'",
            )
            return UnaryExpression(operator="+", operand=operand, value_type=NUMBER)

        if self._match_operator("-"):
            operand = _ensure_type(
                self._parse_unary_math_expression(),
                NUMBER,
                context="Unary operator '-'",
            )
            return UnaryExpression(operator="-", operand=operand, value_type=NUMBER)

        return self._parse_power_expression()

    def _parse_power_expression(self) -> Expression[Any]:
        expression = self._parse_primary_expression()

        if self._match_operator("**"):
            right = self._parse_unary_math_expression()
            _ensure_type(expression, NUMBER, context="Arithmetic operator '**'")
            _ensure_type(right, NUMBER, context="Arithmetic operator '**'")
            return ArithmeticExpression(operator="**", left=expression, right=right)

        return expression

    def _parse_primary_expression(self) -> Expression[Any]:
        if self._match_operator("("):
            expression = self._parse_or_expression()
            self._expect_operator(")", message="Expected ')' to close the expression.")
            return expression

        current_token = self._current

        if current_token.kind == "number":
            self._advance()
            value = ast.literal_eval(current_token.text)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError(f"Unsupported constant value: {value!r}")
            return LiteralExpression(value=value, value_type=NUMBER)

        if current_token.kind == "string":
            self._advance()
            value = ast.literal_eval(current_token.text)
            if not isinstance(value, str):
                raise ValueError(f"Unsupported constant value: {value!r}")
            return LiteralExpression(value=value, value_type=STRING)

        if current_token.kind == "name":
            self._advance()
            if current_token.text in _BOOLEAN_LITERALS:
                return LiteralExpression(
                    value=_BOOLEAN_LITERALS[current_token.text],
                    value_type=BOOLEAN,
                )

            if self._match_operator("("):
                return self._parse_function_call(current_token.text)

            return ColumnExpression(
                name=current_token.text,
                value_type=self._resolve_name_type(current_token.text),
            )

        raise ValueError(f"Unsupported condition syntax near '{current_token.text}'.")

    def _parse_function_call(self, function_name: str) -> FunctionCallExpression[Any]:
        function_definition = _get_function_definition(self._functions, function_name)
        arguments: list[Expression[Any]] = []

        if not self._match_operator(")"):
            while True:
                arguments.append(self._parse_or_expression())
                if self._match_operator(")"):
                    break
                if self._current.kind == "operator" and self._current.text == "=":
                    raise ValueError("Keyword arguments are not supported in condition scripts.")
                self._expect_operator(
                    ",",
                    message="Expected ',' or ')' after function argument.",
                )

        argument_tuple = tuple(arguments)
        matched_signature = function_definition.match_signature(argument_tuple)
        if matched_signature is None:
            raise ValueError(
                "Invalid arguments for function "
                f"'{function_name}'. Expected one of: {function_definition.format_signatures()}"
            )

        return FunctionCallExpression(
            definition=function_definition,
            signature=matched_signature,
            arguments=argument_tuple,
        )

    def _is_comparison_operator(self, token_value: _Token) -> bool:
        if token_value.kind == "operator":
            return token_value.text in _SYMBOL_COMPARISON_OPERATORS
        if token_value.kind == "name":
            return token_value.text in WORD_COMPARISON_OPERATORS
        return False

    def _consume_comparison_operator(self) -> str:
        if not self._is_comparison_operator(self._current):
            raise ValueError(
                f"Unsupported condition syntax near '{self._current.text}'."
            )
        return self._advance().text


def parse_expression(
    script: str,
    *,
    functions: FunctionRegistry | None = None,
    resolve_name_type: NameTypeResolver | None = None,
) -> Expression[Any]:
    if not script.strip():
        raise ValueError("Condition scripts cannot be empty.")

    resolved_functions = functions or _get_default_function_registry()
    resolved_name_type = resolve_name_type or _default_name_type
    parser = _Parser(
        _tokenize_script(script),
        functions=resolved_functions,
        resolve_name_type=resolved_name_type,
    )
    expression = parser.parse()
    parser.ensure_finished()
    return expression


def parse_condition(
    script: str,
    *,
    functions: FunctionRegistry | None = None,
    resolve_name_type: NameTypeResolver | None = None,
) -> ConditionExpression:
    expression = parse_expression(
        script,
        functions=functions,
        resolve_name_type=resolve_name_type,
    )
    if expression.value_type != BOOLEAN:
        raise ValueError("Condition scripts must evaluate to a boolean expression.")

    return cast(ConditionExpression, expression)


def _build_default_function_registry() -> FunctionRegistry:
    from condition_script.tester import get_default_function_definitions

    return {
        function_definition.name: function_definition
        for function_definition in get_default_function_definitions()
    }


@lru_cache(maxsize=1)
def _get_default_function_registry() -> FunctionRegistry:
    return _build_default_function_registry()


def _default_name_type(name: str) -> ScriptType[Any]:
    return STRING if name == "date" else NUMBER


def _tokenize_script(script: str) -> tuple[_Token, ...]:
    tokens: list[_Token] = []

    try:
        raw_tokens = tokenize.generate_tokens(io.StringIO(script).readline)
        for raw_token in raw_tokens:
            if raw_token.type in {
                token.NEWLINE,
                tokenize.NL,
                token.INDENT,
                token.DEDENT,
                token.ENDMARKER,
                tokenize.COMMENT,
            }:
                continue

            if raw_token.type == token.NAME:
                tokens.append(_Token(kind="name", text=raw_token.string))
                continue

            if raw_token.type == token.NUMBER:
                tokens.append(_Token(kind="number", text=raw_token.string))
                continue

            if raw_token.type == token.STRING:
                tokens.append(_Token(kind="string", text=raw_token.string))
                continue

            if raw_token.type == token.OP:
                tokens.append(_Token(kind="operator", text=raw_token.string))
                continue

            if raw_token.type == tokenize.ERRORTOKEN and raw_token.string.isspace():
                continue

            raise ValueError(f"Unsupported condition syntax near '{raw_token.string}'.")
    except tokenize.TokenError as error:
        raise ValueError(str(error)) from error

    tokens.append(_Token(kind="eof", text=""))
    return tuple(tokens)


def _get_function_definition(
    functions: FunctionRegistry,
    name: str,
) -> FunctionDefinition[Any]:
    function_entry = functions.get(name)
    if function_entry is None:
        available = ", ".join(sorted(functions))
        raise ValueError(f"Unknown function '{name}'. Available functions: {available}")

    if isinstance(function_entry, FunctionDefinition):
        return function_entry

    definition = getattr(function_entry, "definition", None)
    if isinstance(definition, FunctionDefinition):
        return definition

    raise TypeError(f"Function registry entry for '{name}' does not expose a definition.")


def _ensure_type(
    expression: Expression[Any],
    *accepted_types: ScriptType[Any],
    context: str,
) -> Expression[Any]:
    if ANY in accepted_types or expression.value_type in accepted_types:
        return expression

    expected = " | ".join(script_type.name for script_type in accepted_types)
    raise ValueError(
        f"{context} requires {expected} expressions, got {expression.value_type.name}."
    )
