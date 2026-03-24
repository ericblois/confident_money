from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic

import numpy as np
import pandas as pd

from analysis.features import (
    calc_breakout_distance,
    calc_distance_to_col,
    calc_log_return,
    calc_log_value,
    calc_momentum,
    calc_mv_avg,
    calc_range_position,
    calc_realized_vol,
    calc_rel_momentum,
    calc_rel_return,
    calc_rel_trend_r2,
    calc_rel_trend_slope,
    calc_trend_r2,
    calc_trend_slope,
    calc_vwap,
)
from condition_script.parser import parse_condition, parse_expression
from condition_script.types import (
    BOOLEAN,
    NUMBER,
    ArithmeticExpression,
    ColumnExpression,
    ComparisonExpression,
    ConditionExpression,
    Expression,
    FunctionCallExpression,
    FunctionDefinition,
    FunctionSignature,
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
    parsed_condition = (
        parse_condition(condition, functions=registry)
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
        return _apply_comparison_operator(expression.operator, left, right)

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


def _eval_mv_avg(dataframe: pd.DataFrame, arguments: tuple[RuntimeValue, ...]) -> pd.Series:
    source = _as_numeric_series(dataframe, arguments[0], parameter_name="source")
    window = _as_positive_int(arguments[1], parameter_name="window")
    min_periods = (
        1
        if len(arguments) < 3
        else _as_positive_int(arguments[2], parameter_name="min_periods")
    )
    working_dataframe = _series_frame(dataframe, source=source)
    return calc_mv_avg(working_dataframe, "source", window, min_periods=min_periods)


def _eval_vwap(dataframe: pd.DataFrame, arguments: tuple[RuntimeValue, ...]) -> pd.Series:
    window = _as_positive_int(arguments[0], parameter_name="window")
    price_arg = arguments[1] if len(arguments) >= 2 else "close"
    volume_arg = arguments[2] if len(arguments) >= 3 else "volume"
    min_periods = (
        window
        if len(arguments) < 4
        else _as_positive_int(arguments[3], parameter_name="min_periods")
    )
    price_series = _as_numeric_series(dataframe, price_arg, parameter_name="price")
    volume_series = _as_numeric_series(dataframe, volume_arg, parameter_name="volume")
    working_dataframe = _series_frame(
        dataframe,
        price=price_series,
        volume=volume_series,
    )
    return calc_vwap(
        working_dataframe,
        window,
        price_col="price",
        volume_col="volume",
        min_periods=min_periods,
    )


def _eval_distance(dataframe: pd.DataFrame, arguments: tuple[RuntimeValue, ...]) -> pd.Series:
    left = _as_numeric_series(dataframe, arguments[0], parameter_name="left")
    right = _as_numeric_series(dataframe, arguments[1], parameter_name="right")
    working_dataframe = _series_frame(dataframe, left=left, right=right)
    return calc_distance_to_col(working_dataframe, "left", "right")


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


def _eval_momentum(dataframe: pd.DataFrame, arguments: tuple[RuntimeValue, ...]) -> pd.Series:
    return_series = _as_numeric_series(dataframe, arguments[0], parameter_name="return")
    volatility_series = _as_numeric_series(dataframe, arguments[1], parameter_name="volatility")
    working_dataframe = _series_frame(
        dataframe,
        return_value=return_series,
        volatility=volatility_series,
    )
    return calc_momentum(working_dataframe, "return_value", "volatility")


def _eval_trend_slope(dataframe: pd.DataFrame, arguments: tuple[RuntimeValue, ...]) -> pd.Series:
    source = _as_numeric_series(dataframe, arguments[0], parameter_name="source")
    window = _as_positive_int(arguments[1], parameter_name="window")
    working_dataframe = _series_frame(dataframe, source=source)
    return calc_trend_slope(working_dataframe, "source", window)


def _eval_trend_r2(dataframe: pd.DataFrame, arguments: tuple[RuntimeValue, ...]) -> pd.Series:
    source = _as_numeric_series(dataframe, arguments[0], parameter_name="source")
    window = _as_positive_int(arguments[1], parameter_name="window")
    working_dataframe = _series_frame(dataframe, source=source)
    return calc_trend_r2(working_dataframe, "source", window)


def _eval_breakout_distance(
    dataframe: pd.DataFrame,
    arguments: tuple[RuntimeValue, ...],
) -> pd.Series:
    source = _as_numeric_series(dataframe, arguments[0], parameter_name="source")
    window = _as_positive_int(arguments[1], parameter_name="window")
    min_periods = (
        window
        if len(arguments) < 3
        else _as_positive_int(arguments[2], parameter_name="min_periods")
    )
    working_dataframe = _series_frame(dataframe, source=source)
    return calc_breakout_distance(
        working_dataframe,
        "source",
        window,
        min_periods=min_periods,
    )


def _eval_range_position(
    dataframe: pd.DataFrame,
    arguments: tuple[RuntimeValue, ...],
) -> pd.Series:
    source = _as_numeric_series(dataframe, arguments[0], parameter_name="source")
    window = _as_positive_int(arguments[1], parameter_name="window")
    min_periods = (
        window
        if len(arguments) < 3
        else _as_positive_int(arguments[2], parameter_name="min_periods")
    )
    working_dataframe = _series_frame(dataframe, source=source)
    return calc_range_position(
        working_dataframe,
        "source",
        window,
        min_periods=min_periods,
    )


def _eval_rel_return(dataframe: pd.DataFrame, arguments: tuple[RuntimeValue, ...]) -> pd.Series:
    return_series = _as_numeric_series(dataframe, arguments[0], parameter_name="return")
    benchmark_series = _as_numeric_series(dataframe, arguments[1], parameter_name="benchmark")
    window = _as_positive_int(arguments[2], parameter_name="window")
    working_dataframe = _series_frame(
        dataframe,
        return_value=return_series,
        benchmark=benchmark_series,
    )
    return calc_rel_return(working_dataframe, "return_value", "benchmark", window)


def _eval_rel_momentum(dataframe: pd.DataFrame, arguments: tuple[RuntimeValue, ...]) -> pd.Series:
    rel_return_series = _as_numeric_series(dataframe, arguments[0], parameter_name="rel_return")
    return_series = _as_numeric_series(dataframe, arguments[1], parameter_name="return")
    benchmark_return_series = _as_numeric_series(
        dataframe,
        arguments[2],
        parameter_name="benchmark_return",
    )
    window = _as_positive_int(arguments[3], parameter_name="window")
    min_periods = (
        window
        if len(arguments) < 5
        else _as_positive_int(arguments[4], parameter_name="min_periods")
    )
    working_dataframe = _series_frame(
        dataframe,
        rel_return=rel_return_series,
        return_value=return_series,
        benchmark_return=benchmark_return_series,
    )
    return calc_rel_momentum(
        working_dataframe,
        "rel_return",
        "return_value",
        "benchmark_return",
        window,
        min_periods=min_periods,
    )


def _eval_rel_trend_slope(dataframe: pd.DataFrame, arguments: tuple[RuntimeValue, ...]) -> pd.Series:
    source = _as_numeric_series(dataframe, arguments[0], parameter_name="source")
    benchmark = _as_numeric_series(dataframe, arguments[1], parameter_name="benchmark")
    window = _as_positive_int(arguments[2], parameter_name="window")
    working_dataframe = _series_frame(dataframe, source=source, benchmark=benchmark)
    return calc_rel_trend_slope(working_dataframe, "source", "benchmark", window)


def _eval_rel_trend_r2(dataframe: pd.DataFrame, arguments: tuple[RuntimeValue, ...]) -> pd.Series:
    source = _as_numeric_series(dataframe, arguments[0], parameter_name="source")
    benchmark = _as_numeric_series(dataframe, arguments[1], parameter_name="benchmark")
    window = _as_positive_int(arguments[2], parameter_name="window")
    working_dataframe = _series_frame(dataframe, source=source, benchmark=benchmark)
    return calc_rel_trend_r2(working_dataframe, "source", "benchmark", window)


def _build_default_function_registry() -> FunctionRegistry:
    registry: FunctionRegistry = {}

    numeric_source = parameter("source", NUMBER)
    numeric_left = parameter("left", NUMBER)
    numeric_right = parameter("right", NUMBER)
    numeric_benchmark = parameter("benchmark", NUMBER)
    numeric_return = parameter("return", NUMBER)
    numeric_rel_return = parameter("rel_return", NUMBER)
    numeric_volatility = parameter("volatility", NUMBER)
    numeric_price = parameter("price", NUMBER)
    numeric_volume = parameter("volume", NUMBER)
    window = parameter("window", NUMBER)
    min_periods = parameter("min_periods", NUMBER)

    _register(
        registry,
        "mv_avg",
        _eval_mv_avg,
        signature(NUMBER, numeric_source, window),
        signature(NUMBER, numeric_source, window, min_periods),
    )
    _register(
        registry,
        "moving_avg",
        _eval_mv_avg,
        signature(NUMBER, numeric_source, window),
        signature(NUMBER, numeric_source, window, min_periods),
    )
    _register(
        registry,
        "vwap",
        _eval_vwap,
        signature(NUMBER, window),
        signature(NUMBER, window, numeric_price),
        signature(NUMBER, window, numeric_price, numeric_volume),
        signature(NUMBER, window, numeric_price, numeric_volume, min_periods),
    )
    _register(
        registry,
        "distance",
        _eval_distance,
        signature(NUMBER, numeric_left, numeric_right),
    )
    _register(
        registry,
        "log_return",
        _eval_log_return,
        signature(NUMBER, window),
        signature(NUMBER, numeric_source, window),
    )
    _register(
        registry,
        "vlt",
        _eval_vlt,
        signature(NUMBER, window),
        signature(NUMBER, numeric_source, window),
        signature(NUMBER, numeric_source, window, min_periods),
    )
    _register(
        registry,
        "realized_vol",
        _eval_vlt,
        signature(NUMBER, window),
        signature(NUMBER, numeric_source, window),
        signature(NUMBER, numeric_source, window, min_periods),
    )
    _register(
        registry,
        "momentum",
        _eval_momentum,
        signature(NUMBER, numeric_return, numeric_volatility),
    )
    _register(
        registry,
        "trend_slope",
        _eval_trend_slope,
        signature(NUMBER, numeric_source, window),
    )
    _register(
        registry,
        "trend_r2",
        _eval_trend_r2,
        signature(NUMBER, numeric_source, window),
    )
    _register(
        registry,
        "breakout_distance",
        _eval_breakout_distance,
        signature(NUMBER, numeric_source, window),
        signature(NUMBER, numeric_source, window, min_periods),
    )
    _register(
        registry,
        "range_position",
        _eval_range_position,
        signature(NUMBER, numeric_source, window),
        signature(NUMBER, numeric_source, window, min_periods),
    )
    _register(
        registry,
        "rel_return",
        _eval_rel_return,
        signature(NUMBER, numeric_return, numeric_benchmark, window),
    )
    _register(
        registry,
        "rel_momentum",
        _eval_rel_momentum,
        signature(NUMBER, numeric_rel_return, numeric_return, numeric_benchmark, window),
        signature(NUMBER, numeric_rel_return, numeric_return, numeric_benchmark, window, min_periods),
    )
    _register(
        registry,
        "rel_trend_slope",
        _eval_rel_trend_slope,
        signature(NUMBER, numeric_source, numeric_benchmark, window),
    )
    _register(
        registry,
        "rel_trend_r2",
        _eval_rel_trend_r2,
        signature(NUMBER, numeric_source, numeric_benchmark, window),
    )

    return registry


def _register(
    registry: FunctionRegistry,
    name: str,
    evaluator: RuntimeEvaluator,
    *signatures: FunctionSignature[Any],
) -> None:
    registry[name] = RuntimeFunction(
        definition=FunctionDefinition(name=name, signatures=signatures),
        evaluator=evaluator,
    )


_DEFAULT_FUNCTIONS = _build_default_function_registry()
