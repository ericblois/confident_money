from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, Literal, TypeVar


class NumberValue:
    """Marker type for numeric expressions."""


class BooleanValue:
    """Marker type for boolean expressions."""


class StringValue:
    """Marker type for string expressions."""


class AnyValue:
    """Marker type for expressions that can accept any result type."""


KindT = TypeVar("KindT", covariant=True)
ReturnT = TypeVar("ReturnT", covariant=True)


@dataclass(frozen=True, slots=True)
class ScriptType(Generic[KindT]):
    name: str


NUMBER = ScriptType[NumberValue]("number")
BOOLEAN = ScriptType[BooleanValue]("boolean")
STRING = ScriptType[StringValue]("string")
ANY = ScriptType[AnyValue]("any")


@dataclass(frozen=True, slots=True)
class ParameterSpec:
    name: str
    accepted_types: tuple[ScriptType[Any], ...]

    def accepts(self, value_type: ScriptType[Any]) -> bool:
        return ANY in self.accepted_types or value_type in self.accepted_types

    def format_types(self) -> str:
        return " | ".join(script_type.name for script_type in self.accepted_types)


def parameter(name: str, *accepted_types: ScriptType[Any]) -> ParameterSpec:
    if not accepted_types:
        raise ValueError("Parameter specs require at least one accepted type.")

    return ParameterSpec(name=name, accepted_types=tuple(accepted_types))


@dataclass(frozen=True, slots=True)
class FunctionSignature(Generic[ReturnT]):
    parameters: tuple[ParameterSpec, ...]
    return_type: ScriptType[ReturnT]

    def matches(self, arguments: tuple["AnyExpression", ...]) -> bool:
        if len(arguments) != len(self.parameters):
            return False

        return all(
            parameter_spec.accepts(argument.value_type)
            for parameter_spec, argument in zip(self.parameters, arguments, strict=True)
        )

    def format(self, function_name: str) -> str:
        params = ", ".join(
            f"{parameter_spec.name}: {parameter_spec.format_types()}"
            for parameter_spec in self.parameters
        )
        return f"{function_name}({params}) -> {self.return_type.name}"


def signature(
    return_type: ScriptType[ReturnT],
    *parameters: ParameterSpec,
) -> FunctionSignature[ReturnT]:
    return FunctionSignature(parameters=tuple(parameters), return_type=return_type)


@dataclass(frozen=True, slots=True)
class FunctionDefinition(Generic[ReturnT]):
    name: str
    signatures: tuple[FunctionSignature[ReturnT], ...]

    def match_signature(
        self,
        arguments: tuple["AnyExpression", ...],
    ) -> FunctionSignature[ReturnT] | None:
        for candidate in self.signatures:
            if candidate.matches(arguments):
                return candidate

        return None

    def format_signatures(self) -> str:
        return "; ".join(signature.format(self.name) for signature in self.signatures)


@dataclass(frozen=True, slots=True)
class Expression(Generic[KindT]):
    pass


@dataclass(frozen=True, slots=True)
class LiteralExpression(Expression[KindT]):
    value: Any
    value_type: ScriptType[KindT]


@dataclass(frozen=True, slots=True)
class ColumnExpression(Expression[KindT]):
    name: str
    value_type: ScriptType[KindT]


type ArithmeticOperator = Literal["+", "-", "*", "/", "%", "**"]
type ComparisonOperator = Literal["==", "!=", ">", ">=", "<", "<="]
type LogicalOperator = Literal["and", "or"]
type UnaryOperator = Literal["+", "-", "not"]


@dataclass(frozen=True, slots=True)
class UnaryExpression(Expression[Any]):
    operator: UnaryOperator
    operand: "AnyExpression"
    value_type: ScriptType[Any]


@dataclass(frozen=True, slots=True)
class ArithmeticExpression(Expression[NumberValue]):
    operator: ArithmeticOperator
    left: "AnyExpression"
    right: "AnyExpression"
    value_type: ScriptType[NumberValue] = field(default=NUMBER, init=False)


@dataclass(frozen=True, slots=True)
class ComparisonExpression(Expression[BooleanValue]):
    operator: ComparisonOperator
    left: "AnyExpression"
    right: "AnyExpression"
    value_type: ScriptType[BooleanValue] = field(default=BOOLEAN, init=False)


@dataclass(frozen=True, slots=True)
class LogicalExpression(Expression[BooleanValue]):
    operator: LogicalOperator
    values: tuple["AnyExpression", ...]
    value_type: ScriptType[BooleanValue] = field(default=BOOLEAN, init=False)


@dataclass(frozen=True, slots=True)
class FunctionCallExpression(Expression[ReturnT]):
    definition: FunctionDefinition[ReturnT]
    signature: FunctionSignature[ReturnT]
    arguments: tuple["AnyExpression", ...]
    value_type: ScriptType[ReturnT] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "value_type", self.signature.return_type)


type AnyExpression = Expression[Any]
type ConditionExpression = Expression[BooleanValue]

