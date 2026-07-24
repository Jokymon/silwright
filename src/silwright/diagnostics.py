"""Structured diagnostics for user-facing Silwright errors."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class ErrorCode(StrEnum):
    """Stable diagnostic identifiers."""

    SYNTAX_ERROR = "SW0001"
    MISSING_BACKEND_MAP = "SW0002"
    INVALID_DEFINITION_SUFFIX = "SW0003"
    DUPLICATE_DEFINITION = "SW1001"
    DUPLICATE_BACKEND_MAPPING = "SW1002"
    DUPLICATE_MEMBER = "SW1003"
    INVALID_FIELD_MODIFIER = "SW1004"
    UNKNOWN_TRAIT = "SW1005"
    INVALID_TRAIT_REFERENCE = "SW1006"
    DUPLICATE_FIELD = "SW1007"
    UNKNOWN_FIELD_TYPE = "SW1008"
    CYCLIC_CHOICE = "SW1009"
    UNKNOWN_CHOICE_ALTERNATIVE = "SW1010"
    INVALID_CHOICE_ALTERNATIVE = "SW1011"
    CYCLIC_VALUE_DEPENDENCY = "SW1012"
    CPP_NAME_COLLISION = "SW1013"
    INVALID_CPP_IDENTIFIER = "SW1014"
    RESERVED_CPP_KEYWORD = "SW1015"
    AMBIGUOUS_TRANSFORMER_RETURN = "SW1016"
    DIRECT_TRANSFORMER_NODE_REFERENCE = "SW1017"
    GENERATION_FAILED = "SW2001"


@dataclass(frozen=True, slots=True)
class SourceLocation:
    """A one-based source location."""

    path: Path | None
    line: int
    column: int


class DiagnosticError(ValueError):
    """Base class for errors that can be shown without a Python traceback."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        location: SourceLocation | None = None,
        context: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.location = location
        self.context = context


def format_diagnostic(error: DiagnosticError) -> str:
    """Render a compiler-style diagnostic."""
    location = error.location
    if location is None:
        return f"error[{error.code}]: {error.message}"

    path = str(location.path) if location.path is not None else "<input>"
    result = [
        f"{path}:{location.line}:{location.column}: error[{error.code}]: {error.message}"
    ]
    if error.context is not None:
        result.extend(error.context.rstrip("\n").splitlines())
    else:
        source_line = _read_source_line(location)
        if source_line is not None:
            result.append(source_line)
            result.append(f"{' ' * (location.column - 1)}^")
    return "\n".join(result)


def _read_source_line(location: SourceLocation) -> str | None:
    if location.path is None:
        return None
    try:
        lines = location.path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    if location.line < 1 or location.line > len(lines):
        return None
    return lines[location.line - 1]
