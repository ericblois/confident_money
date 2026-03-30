from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from condition_script.parser import parse_expression
from condition_script.types import (
    ArithmeticExpression,
    ColumnExpression,
    ComparisonExpression,
    Expression,
    FunctionCallExpression,
    LiteralExpression,
    LogicalExpression,
    UnaryExpression,
)
from features.features import FEATURE_INFOS_BY_SCRIPT, SCRIPT_FUNCTION_ALIAS_INFOS


_FEATURE_ALIAS_TARGETS_BY_NAME = {
    alias_info.name: alias_info.target_name
    for alias_info in SCRIPT_FUNCTION_ALIAS_INFOS
}


@dataclass(frozen=True, slots=True)
class ScriptFeatureCall:
    rendered_call: str
    function_name: str
    feature_name: str
    feature_category: str
    full_name: str
    parameter_names: tuple[str, ...]
    expression: FunctionCallExpression[Any]


def collect_script_feature_calls(
    script: str | Expression[Any],
) -> tuple[ScriptFeatureCall, ...]:
    parsed_expression = parse_expression(script) if isinstance(script, str) else script
    seen_rendered_calls: set[str] = set()
    feature_calls: list[ScriptFeatureCall] = []

    for feature_expression in _iter_feature_calls(parsed_expression):
        rendered_call = render_script_expression(feature_expression)
        if rendered_call in seen_rendered_calls:
            continue

        function_name = feature_expression.definition.name
        feature_name = _FEATURE_ALIAS_TARGETS_BY_NAME.get(function_name, function_name)
        feature_info = FEATURE_INFOS_BY_SCRIPT.get(feature_name)
        if feature_info is None:
            continue

        seen_rendered_calls.add(rendered_call)
        feature_calls.append(
            ScriptFeatureCall(
                rendered_call=rendered_call,
                function_name=function_name,
                feature_name=feature_name,
                feature_category=feature_info.category,
                full_name=feature_expression.definition.full_name,
                parameter_names=tuple(
                    parameter_spec.name
                    for parameter_spec in feature_expression.signature.parameters
                ),
                expression=feature_expression,
            )
        )

    return tuple(feature_calls)


def render_script_expression(expression: Expression[Any]) -> str:
    if isinstance(expression, LiteralExpression):
        return repr(expression.value)

    if isinstance(expression, ColumnExpression):
        return expression.name

    if isinstance(expression, UnaryExpression):
        operand_text = render_script_expression(expression.operand)
        if expression.operator == "not":
            return f"not {operand_text}"
        return f"{expression.operator}{operand_text}"

    if isinstance(expression, ArithmeticExpression):
        return (
            f"({render_script_expression(expression.left)} "
            f"{expression.operator} "
            f"{render_script_expression(expression.right)})"
        )

    if isinstance(expression, ComparisonExpression):
        return (
            f"({render_script_expression(expression.left)} "
            f"{expression.operator} "
            f"{render_script_expression(expression.right)})"
        )

    if isinstance(expression, LogicalExpression):
        return (
            "("
            + f" {expression.operator} ".join(
                render_script_expression(value_expression)
                for value_expression in expression.values
            )
            + ")"
        )

    if isinstance(expression, FunctionCallExpression):
        rendered_arguments = ", ".join(
            render_script_expression(argument)
            for argument in expression.arguments
        )
        return f"{expression.definition.name}({rendered_arguments})"

    raise TypeError(f"Unsupported expression node: {type(expression)!r}")


def _iter_feature_calls(
    expression: Expression[Any],
) -> tuple[FunctionCallExpression[Any], ...]:
    collected_calls: list[FunctionCallExpression[Any]] = []
    _collect_feature_calls(expression, collected_calls)
    return tuple(collected_calls)


def _collect_feature_calls(
    expression: Expression[Any],
    collected_calls: list[FunctionCallExpression[Any]],
) -> None:
    if isinstance(expression, UnaryExpression):
        _collect_feature_calls(expression.operand, collected_calls)
        return

    if isinstance(expression, ArithmeticExpression | ComparisonExpression):
        _collect_feature_calls(expression.left, collected_calls)
        _collect_feature_calls(expression.right, collected_calls)
        return

    if isinstance(expression, LogicalExpression):
        for value_expression in expression.values:
            _collect_feature_calls(value_expression, collected_calls)
        return

    if isinstance(expression, FunctionCallExpression):
        for argument in expression.arguments:
            _collect_feature_calls(argument, collected_calls)
        collected_calls.append(expression)
