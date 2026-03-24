from __future__ import annotations

import ast
from collections.abc import Callable, Mapping
from typing import Any, cast

from condition_script.types import (
    ANY,
    BOOLEAN,
    NUMBER,
    STRING,
    ArithmeticExpression,
    ColumnExpression,
    ComparisonExpression,
    ConditionExpression,
    Expression,
    FunctionCallExpression,
    FunctionDefinition,
    LiteralExpression,
    LogicalExpression,
    ScriptType,
    UnaryExpression,
)


type FunctionRegistry = Mapping[str, object]
type NameTypeResolver = Callable[[str], ScriptType[Any]]


def parse_expression(
    script: str,
    *,
    functions: FunctionRegistry | None = None,
    resolve_name_type: NameTypeResolver | None = None,
) -> Expression[Any]:
    if not script.strip():
        raise ValueError("Condition scripts cannot be empty.")

    parsed_expression = ast.parse(script, mode="eval")
    resolved_functions = functions or _get_default_functions()
    resolved_name_type = resolve_name_type or _default_name_type

    return _parse_node(
        parsed_expression.body,
        functions=resolved_functions,
        resolve_name_type=resolved_name_type,
    )


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


def _get_default_functions() -> FunctionRegistry:
    from condition_script.tester import get_default_function_registry

    return get_default_function_registry()


def _default_name_type(name: str) -> ScriptType[Any]:
    return STRING if name == "date" else NUMBER


def _parse_node(
    node: ast.AST,
    *,
    functions: FunctionRegistry,
    resolve_name_type: NameTypeResolver,
) -> Expression[Any]:
    if isinstance(node, ast.BoolOp):
        operator = _parse_bool_operator(node.op)
        values = tuple(
            _ensure_type(
                _parse_node(value, functions=functions, resolve_name_type=resolve_name_type),
                BOOLEAN,
                context=f"Logical operator '{operator}'",
            )
            for value in node.values
        )
        return LogicalExpression(operator=operator, values=values)

    if isinstance(node, ast.UnaryOp):
        operand = _parse_node(node.operand, functions=functions, resolve_name_type=resolve_name_type)
        if isinstance(node.op, ast.Not):
            _ensure_type(operand, BOOLEAN, context="Unary operator 'not'")
            return UnaryExpression(operator="not", operand=operand, value_type=BOOLEAN)

        if isinstance(node.op, ast.UAdd):
            _ensure_type(operand, NUMBER, context="Unary operator '+'")
            return UnaryExpression(operator="+", operand=operand, value_type=NUMBER)

        if isinstance(node.op, ast.USub):
            _ensure_type(operand, NUMBER, context="Unary operator '-'")
            return UnaryExpression(operator="-", operand=operand, value_type=NUMBER)

        raise ValueError(f"Unsupported unary operator: {_node_text(node)}")

    if isinstance(node, ast.BinOp):
        left = _parse_node(node.left, functions=functions, resolve_name_type=resolve_name_type)
        right = _parse_node(node.right, functions=functions, resolve_name_type=resolve_name_type)
        operator = _parse_arithmetic_operator(node.op)
        _ensure_type(left, NUMBER, context=f"Arithmetic operator '{operator}'")
        _ensure_type(right, NUMBER, context=f"Arithmetic operator '{operator}'")
        return ArithmeticExpression(operator=operator, left=left, right=right)

    if isinstance(node, ast.Compare):
        return _parse_compare(
            node,
            functions=functions,
            resolve_name_type=resolve_name_type,
        )

    if isinstance(node, ast.Call):
        if node.keywords:
            raise ValueError("Keyword arguments are not supported in condition scripts.")
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only direct function calls are supported in condition scripts.")

        function_name = node.func.id
        function_definition = _get_function_definition(functions, function_name)
        arguments = tuple(
            _parse_node(argument, functions=functions, resolve_name_type=resolve_name_type)
            for argument in node.args
        )
        matched_signature = function_definition.match_signature(arguments)
        if matched_signature is None:
            raise ValueError(
                "Invalid arguments for function "
                f"'{function_name}'. Expected one of: {function_definition.format_signatures()}"
            )

        return FunctionCallExpression(
            definition=function_definition,
            signature=matched_signature,
            arguments=arguments,
        )

    if isinstance(node, ast.Name):
        return ColumnExpression(name=node.id, value_type=resolve_name_type(node.id))

    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool):
            return LiteralExpression(value=node.value, value_type=BOOLEAN)
        if isinstance(node.value, (int, float)):
            return LiteralExpression(value=node.value, value_type=NUMBER)
        if isinstance(node.value, str):
            return LiteralExpression(value=node.value, value_type=STRING)

        raise ValueError(f"Unsupported constant value: {node.value!r}")

    raise ValueError(f"Unsupported condition syntax: {_node_text(node)}")


def _parse_compare(
    node: ast.Compare,
    *,
    functions: FunctionRegistry,
    resolve_name_type: NameTypeResolver,
) -> Expression[Any]:
    left = _parse_node(node.left, functions=functions, resolve_name_type=resolve_name_type)
    comparisons: list[ComparisonExpression] = []

    for operator_node, comparator_node in zip(node.ops, node.comparators, strict=True):
        right = _parse_node(
            comparator_node,
            functions=functions,
            resolve_name_type=resolve_name_type,
        )
        comparisons.append(
            ComparisonExpression(
                operator=_parse_comparison_operator(operator_node),
                left=left,
                right=right,
            )
        )
        left = right

    if len(comparisons) == 1:
        return comparisons[0]

    return LogicalExpression(operator="and", values=tuple(comparisons))


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


def _parse_arithmetic_operator(operator_node: ast.operator) -> str:
    if isinstance(operator_node, ast.Add):
        return "+"
    if isinstance(operator_node, ast.Sub):
        return "-"
    if isinstance(operator_node, ast.Mult):
        return "*"
    if isinstance(operator_node, ast.Div):
        return "/"
    if isinstance(operator_node, ast.Mod):
        return "%"
    if isinstance(operator_node, ast.Pow):
        return "**"

    raise ValueError(f"Unsupported arithmetic operator: {operator_node!r}")


def _parse_comparison_operator(operator_node: ast.cmpop) -> str:
    if isinstance(operator_node, ast.Eq):
        return "=="
    if isinstance(operator_node, ast.NotEq):
        return "!="
    if isinstance(operator_node, ast.Gt):
        return ">"
    if isinstance(operator_node, ast.GtE):
        return ">="
    if isinstance(operator_node, ast.Lt):
        return "<"
    if isinstance(operator_node, ast.LtE):
        return "<="

    raise ValueError(f"Unsupported comparison operator: {operator_node!r}")


def _parse_bool_operator(operator_node: ast.boolop) -> str:
    if isinstance(operator_node, ast.And):
        return "and"
    if isinstance(operator_node, ast.Or):
        return "or"

    raise ValueError(f"Unsupported boolean operator: {operator_node!r}")


def _node_text(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return ast.dump(node)
