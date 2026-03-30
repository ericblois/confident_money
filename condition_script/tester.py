from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic

import numpy as np
import pandas as pd

from features.features import (
    FEATURE_CALCULATOR_PARAMETER_NAMES_BY_SCRIPT,
    FEATURE_CALCULATORS_BY_SCRIPT,
    FEATURE_INFOS_BY_SCRIPT,
    FEATURE_SCRIPT_FUNCTION_INFOS_BY_NAME,
    SCRIPT_FUNCTION_ALIAS_INFOS,
    SCRIPT_FUNCTION_INFOS_BY_NAME,
    SCRIPT_PARAMETER_INFOS_BY_NAME,
    ScriptFunctionInfo,
    calc_log_return,
    calc_log_value,
    calc_realized_vol,
)
from condition_script.parser import parse_condition, parse_expression
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
    ReturnT,
    UnaryExpression,
    parameter,
    signature,
)


type RuntimeScalar = float | int | bool | str
type RuntimeValue = RuntimeScalar | pd.Series


@dataclass(frozen=True, slots=True)
class RuntimeFunction(Generic[ReturnT]):
    definition: FunctionDefinition[ReturnT]
    evaluator: "RuntimeEvaluator"


type RuntimeEvaluator = Callable[[pd.DataFrame, tuple[RuntimeValue, ...]], RuntimeValue]
type FunctionRegistry = dict[str, RuntimeFunction[Any]]


def get_default_function_registry() -> FunctionRegistry:
    return dict(_DEFAULT_FUNCTIONS)


def get_default_function_definitions() -> tuple[FunctionDefinition[Any], ...]:
    return tuple(
        runtime_function.definition
        for runtime_function in _DEFAULT_FUNCTIONS.values()
    )


def evaluate_expression(
    dataframe: pd.DataFrame,
    expression: str | Expression[Any],
    *,
    functions: FunctionRegistry | None = None,
) -> RuntimeValue:
    registry = functions or get_default_function_registry()
    parsed_expression = (
        parse_expression(expression, functions=registry)
        if isinstance(expression, str)
        else expression
    )
    return _evaluate_expression(dataframe, parsed_expression, registry)


def evaluate_condition(
    dataframe: pd.DataFrame,
    condition: str | ConditionExpression,
    *,
    functions: FunctionRegistry | None = None,
) -> pd.Series:
    registry = functions or get_default_function_registry()
    parsed_condition = ( parse_condition(condition, functions=registry)
        if isinstance(condition, str)
        else condition
    )
    result = _evaluate_expression(dataframe, parsed_condition, registry)
    return _as_boolean_series(dataframe, result).rename("condition")


def add_condition_column(
    dataframe: pd.DataFrame,
    condition: str | ConditionExpression,
    *,
    output_column: str = "condition",
    functions: FunctionRegistry | None = None,
) -> pd.DataFrame:
    output = dataframe.copy()
    output[output_column] = evaluate_condition(
        output,
        condition,
        functions=functions,
    )
    return output


def _evaluate_expression(
    dataframe: pd.DataFrame,
    expression: Expression[Any],
    functions: FunctionRegistry,
) -> RuntimeValue:
    if isinstance(expression, LiteralExpression):
        return expression.value

    if isinstance(expression, ColumnExpression):
        return _get_column_value(dataframe, expression.name, expression.value_type)

    if isinstance(expression, UnaryExpression):
        operand = _evaluate_expression(dataframe, expression.operand, functions)
        if expression.operator == "not":
            if isinstance(operand, pd.Series):
                return ~_as_boolean_series(dataframe, operand)
            return not _as_boolean_scalar(operand)
        if expression.operator == "+":
            return +operand
        if expression.operator == "-":
            return -operand

        raise ValueError(f"Unsupported unary operator: {expression.operator}")

    if isinstance(expression, ArithmeticExpression):
        left = _evaluate_expression(dataframe, expression.left, functions)
        right = _evaluate_expression(dataframe, expression.right, functions)
        return _apply_arithmetic_operator(expression.operator, left, right)

    if isinstance(expression, ComparisonExpression):
        left = _evaluate_expression(dataframe, expression.left, functions)
        right = _evaluate_expression(dataframe, expression.right, functions)
        return _apply_comparison_operator(dataframe, expression.operator, left, right)

    if isinstance(expression, LogicalExpression):
        values = [
            _evaluate_expression(dataframe, value_expression, functions)
            for value_expression in expression.values
        ]
        return _apply_logical_operator(dataframe, expression.operator, values)

    if isinstance(expression, FunctionCallExpression):
        runtime_function = functions.get(expression.definition.name)
        if runtime_function is None:
            raise ValueError(f"Unknown runtime function '{expression.definition.name}'.")

        arguments = tuple(
            _evaluate_expression(dataframe, argument, functions)
            for argument in expression.arguments
        )
        return runtime_function.evaluator(dataframe, arguments)

    raise TypeError(f"Unsupported expression node: {type(expression)!r}")


def _apply_arithmetic_operator(
    operator: str,
    left: RuntimeValue,
    right: RuntimeValue,
) -> RuntimeValue:
    if operator == "+":
        return left + right
    if operator == "-":
        return left - right
    if operator == "*":
        return left * right
    if operator == "/":
        return left / right
    if operator == "%":
        return left % right
    if operator == "**":
        return left**right

    raise ValueError(f"Unsupported arithmetic operator: {operator}")


def _apply_comparison_operator(
    dataframe: pd.DataFrame,
    operator: str,
    left: RuntimeValue,
    right: RuntimeValue,
) -> RuntimeValue:
    if operator == "==":
        return left == right
    if operator == "!=":
        return left != right
    if operator == ">":
        return left > right
    if operator == ">=":
        return left >= right
    if operator == "<":
        return left < right
    if operator == "<=":
        return left <= right
    if operator == "crosses":
        left_series = _as_numeric_series(
            dataframe,
            left,
            parameter_name="left",
            allow_column_name=False,
        )
        right_series = _as_numeric_series(
            dataframe,
            right,
            parameter_name="right",
            allow_column_name=False,
        )
        return (
            left_series.gt(right_series)
            & left_series.shift(1).le(right_series.shift(1))
        ).fillna(False).astype(bool)

    raise ValueError(f"Unsupported comparison operator: {operator}")


def _apply_logical_operator(
    dataframe: pd.DataFrame,
    operator: str,
    values: list[RuntimeValue],
) -> RuntimeValue:
    if all(not isinstance(value, pd.Series) for value in values):
        scalar_values = [_as_boolean_scalar(value) for value in values]
        return all(scalar_values) if operator == "and" else any(scalar_values)

    boolean_values = [_as_boolean_series(dataframe, value) for value in values]
    result = boolean_values[0]
    for value in boolean_values[1:]:
        result = result & value if operator == "and" else result | value

    return result


def _get_column_value(
    dataframe: pd.DataFrame,
    column_name: str,
    value_type: Any,
) -> pd.Series:
    if column_name not in dataframe.columns:
        raise ValueError(f"Column '{column_name}' not found in the dataframe.")

    series = dataframe[column_name].reindex(dataframe.index)
    if value_type == NUMBER:
        return pd.to_numeric(series, errors="coerce")
    if value_type == BOOLEAN:
        return _as_boolean_series(dataframe, series)

    return series


def _as_boolean_series(
    dataframe: pd.DataFrame,
    value: RuntimeValue,
) -> pd.Series:
    if isinstance(value, pd.Series):
        aligned = value.reindex(dataframe.index)
    else:
        aligned = pd.Series(value, index=dataframe.index)

    if pd.api.types.is_bool_dtype(aligned) or pd.api.types.is_dtype_equal(
        aligned.dtype,
        "boolean",
    ):
        return aligned.fillna(False).astype(bool)

    return aligned.where(aligned.notna(), False).astype(bool)


def _as_boolean_scalar(value: RuntimeValue) -> bool:
    if isinstance(value, pd.Series):
        raise ValueError("Expected a scalar boolean value.")

    if pd.isna(value):
        return False

    return bool(value)


def _as_scalar_value(value: RuntimeValue, *, parameter_name: str) -> RuntimeScalar:
    if isinstance(value, pd.Series):
        raise ValueError(f"'{parameter_name}' must be a scalar value, not a series.")

    return value


def _as_numeric_series(
    dataframe: pd.DataFrame,
    value: RuntimeValue,
    *,
    parameter_name: str,
    allow_column_name: bool = True,
) -> pd.Series:
    if isinstance(value, str):
        if not allow_column_name:
            raise ValueError(f"'{parameter_name}' does not accept string values.")
        if value not in dataframe.columns:
            raise ValueError(f"Column '{value}' not found in the dataframe.")
        return pd.to_numeric(dataframe[value], errors="coerce").reindex(dataframe.index)

    if isinstance(value, pd.Series):
        return pd.to_numeric(value.reindex(dataframe.index), errors="coerce")

    return pd.Series(float(value), index=dataframe.index, dtype=float)


def _default_close_series(dataframe: pd.DataFrame) -> pd.Series:
    return _as_numeric_series(dataframe, "close", parameter_name="close")


def _series_frame(dataframe: pd.DataFrame, **columns: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            column_name: series.reindex(dataframe.index)
            for column_name, series in columns.items()
        },
        index=dataframe.index,
    )


def _as_positive_int(value: RuntimeValue, *, parameter_name: str) -> int:
    if isinstance(value, pd.Series):
        raise ValueError(f"'{parameter_name}' must be a scalar number, not a series.")

    numeric_value = float(value)
    if not np.isfinite(numeric_value) or numeric_value <= 0 or not numeric_value.is_integer():
        raise ValueError(f"'{parameter_name}' must be a positive integer.")

    return int(numeric_value)


def _is_feature_source_arg(arg_type: str) -> bool:
    return arg_type == "source" or arg_type.endswith("_source")


def _resolve_feature_source_argument(
    dataframe: pd.DataFrame,
    working_dataframe: pd.DataFrame,
    value: RuntimeValue,
    *,
    function_name: str,
    parameter_name: str,
) -> tuple[pd.DataFrame, str]:
    if isinstance(value, str):
        return working_dataframe, value

    series = (
        value.reindex(dataframe.index)
        if isinstance(value, pd.Series)
        else pd.Series(value, index=dataframe.index)
    )
    if working_dataframe is dataframe:
        working_dataframe = dataframe.copy()

    temp_column_index = 0
    temp_column_name = (
        f"__condition_feature_{function_name}_{parameter_name}_{temp_column_index}"
    )
    while temp_column_name in working_dataframe.columns:
        temp_column_index += 1
        temp_column_name = (
            f"__condition_feature_{function_name}_{parameter_name}_{temp_column_index}"
        )

    working_dataframe[temp_column_name] = series
    return working_dataframe, temp_column_name


def _resolve_feature_scalar_argument(
    value: RuntimeValue,
    *,
    parameter_name: str,
    arg_type: str,
) -> RuntimeScalar:
    scalar_value = _as_scalar_value(value, parameter_name=parameter_name)
    if arg_type == "boolean_flag":
        return _as_boolean_scalar(scalar_value)
    return scalar_value


def _full_parameter_names(function_info: ScriptFunctionInfo) -> tuple[str, ...]:
    return max(function_info.signatures, key=len)


def _build_feature_evaluator(
    function_info: ScriptFunctionInfo,
    calc_function: Callable[..., pd.Series],
    *,
    feature_name: str,
    feature_parameter_names: tuple[str, ...] | None = None,
    target_parameter_names: tuple[str, ...] | None = None,
) -> RuntimeEvaluator:
    feature_arg_infos_by_name = {
        feature_arg_info.script_name: feature_arg_info
        for feature_arg_info in FEATURE_INFOS_BY_SCRIPT[feature_name].all_args
    }
    script_parameter_names = _full_parameter_names(function_info)
    resolved_feature_parameter_names = (
        script_parameter_names
        if feature_parameter_names is None
        else feature_parameter_names
    )
    resolved_target_parameter_names = (
        resolved_feature_parameter_names
        if target_parameter_names is None
        else target_parameter_names
    )
    if (
        len(script_parameter_names) != len(resolved_feature_parameter_names)
        or len(script_parameter_names) != len(resolved_target_parameter_names)
    ):
        raise ValueError(
            f"Function '{function_info.name}' has mismatched feature bridge metadata."
        )
    parameter_infos = tuple(
        feature_arg_infos_by_name[feature_parameter_name]
        for feature_parameter_name in resolved_feature_parameter_names
    )

    def evaluator(
        dataframe: pd.DataFrame,
        arguments: tuple[RuntimeValue, ...],
    ) -> pd.Series:
        working_dataframe = dataframe
        resolved_arguments: dict[str, RuntimeScalar | str] = {}
        parameter_names = script_parameter_names[: len(arguments)]
        target_names = resolved_target_parameter_names[: len(arguments)]
        active_parameter_infos = parameter_infos[: len(arguments)]

        for argument_value, parameter_name, target_name, parameter_info in zip(
            arguments,
            parameter_names,
            target_names,
            active_parameter_infos,
            strict=True,
        ):
            if _is_feature_source_arg(parameter_info.arg_type):
                working_dataframe, resolved_value = _resolve_feature_source_argument(
                    dataframe,
                    working_dataframe,
                    argument_value,
                    function_name=function_info.name,
                    parameter_name=parameter_name,
                )
            else:
                resolved_value = _resolve_feature_scalar_argument(
                    argument_value,
                    parameter_name=parameter_name,
                    arg_type=parameter_info.arg_type,
                )
            resolved_arguments[target_name] = resolved_value

        return calc_function(working_dataframe, **resolved_arguments)

    return evaluator


def _eval_log_return(dataframe: pd.DataFrame, arguments: tuple[RuntimeValue, ...]) -> pd.Series:
    if len(arguments) == 1:
        window = _as_positive_int(arguments[0], parameter_name="window")
        working_dataframe = _series_frame(dataframe, close=_default_close_series(dataframe))
        working_dataframe["log_close"] = calc_log_value(working_dataframe, "close")
        return calc_log_return(working_dataframe, "log_close", window)

    source = _as_numeric_series(dataframe, arguments[0], parameter_name="source")
    window = _as_positive_int(arguments[1], parameter_name="window")
    working_dataframe = _series_frame(dataframe, source=source)
    return calc_log_return(working_dataframe, "source", window)


def _eval_vlt(dataframe: pd.DataFrame, arguments: tuple[RuntimeValue, ...]) -> pd.Series:
    if len(arguments) == 1:
        window = _as_positive_int(arguments[0], parameter_name="window")
        min_periods = window
        working_dataframe = _series_frame(dataframe, close=_default_close_series(dataframe))
        working_dataframe["log_close"] = calc_log_value(working_dataframe, "close")
        working_dataframe["log_return"] = calc_log_return(working_dataframe, "log_close", 1)
        return calc_realized_vol(
            working_dataframe,
            "log_return",
            window,
            min_periods=min_periods,
        )

    source = _as_numeric_series(dataframe, arguments[0], parameter_name="source")
    window = _as_positive_int(arguments[1], parameter_name="window")
    min_periods = (
        window
        if len(arguments) < 3
        else _as_positive_int(arguments[2], parameter_name="min_periods")
    )
    working_dataframe = _series_frame(dataframe, source=source)
    return calc_realized_vol(
        working_dataframe,
        "source",
        window,
        min_periods=min_periods,
    )


def _build_default_function_registry() -> FunctionRegistry:
    registry: FunctionRegistry = {}
    parameter_specs = {
        parameter_name: parameter(
            parameter_info.name,
            *(
                _script_type_for_name(type_name)
                for type_name in parameter_info.accepted_types
            ),
        )
        for parameter_name, parameter_info in SCRIPT_PARAMETER_INFOS_BY_NAME.items()
    }

    for feature_name, calc_function in FEATURE_CALCULATORS_BY_SCRIPT.items():
        function_info = FEATURE_SCRIPT_FUNCTION_INFOS_BY_NAME[feature_name]
        _register(
            registry,
            function_info,
            _build_feature_evaluator(
                function_info,
                calc_function,
                feature_name=feature_name,
                target_parameter_names=FEATURE_CALCULATOR_PARAMETER_NAMES_BY_SCRIPT[feature_name],
            ),
            parameter_specs,
        )

    custom_alias_evaluators: dict[str, RuntimeEvaluator] = {
        "log_return": _eval_log_return,
        "vlt": _eval_vlt,
        "realized_vol": _eval_vlt,
    }

    for alias_info in SCRIPT_FUNCTION_ALIAS_INFOS:
        function_info = SCRIPT_FUNCTION_INFOS_BY_NAME[alias_info.name]
        evaluator = custom_alias_evaluators.get(alias_info.name)
        if evaluator is None:
            target_function_info = FEATURE_SCRIPT_FUNCTION_INFOS_BY_NAME[alias_info.target_name]
            alias_parameter_names = _full_parameter_names(function_info)
            target_feature_parameter_names = _full_parameter_names(target_function_info)
            target_parameter_names = FEATURE_CALCULATOR_PARAMETER_NAMES_BY_SCRIPT[
                alias_info.target_name
            ]
            evaluator = _build_feature_evaluator(
                function_info,
                FEATURE_CALCULATORS_BY_SCRIPT[alias_info.target_name],
                feature_name=alias_info.target_name,
                feature_parameter_names=target_feature_parameter_names[
                    : len(alias_parameter_names)
                ],
                target_parameter_names=target_parameter_names[: len(alias_parameter_names)],
            )

        _register(
            registry,
            function_info,
            evaluator,
            parameter_specs,
        )

    return registry


def _register(
    registry: FunctionRegistry,
    function_info: ScriptFunctionInfo,
    evaluator: RuntimeEvaluator,
    parameter_specs: dict[str, Any],
) -> None:
    signatures = tuple(
        signature(
            _script_type_for_name(function_info.return_type),
            *(parameter_specs[parameter_name] for parameter_name in parameter_names),
        )
        for parameter_names in function_info.signatures
    )
    registry[function_info.name] = RuntimeFunction(
        definition=FunctionDefinition(name=function_info.name, signatures=signatures),
        evaluator=evaluator,
    )


def _script_type_for_name(type_name: str) -> Any:
    if type_name == "number":
        return NUMBER
    if type_name == "boolean":
        return BOOLEAN
    if type_name == "string":
        return STRING
    if type_name == "any":
        return ANY
    raise ValueError(f"Unsupported script value type '{type_name}'.")


_DEFAULT_FUNCTIONS = _build_default_function_registry()
