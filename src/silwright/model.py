"""Syntax model for Silwright definition files."""

from dataclasses import dataclass, field

from silwright.diagnostics import SourceLocation


@dataclass(frozen=True, slots=True)
class Field:
    """A named field with a Silwright type reference."""

    name: str
    type_name: str
    multiple: bool = False
    by_value: bool = False
    optional: bool = False
    transient: bool = False
    fixed: bool = False
    location: SourceLocation | None = field(default=None, compare=False)
    type_location: SourceLocation | None = field(default=None, compare=False)


@dataclass(frozen=True, slots=True)
class Node:
    """A structured node declaration."""

    name: str
    fields: tuple[Field, ...] = ()
    traits: tuple[str, ...] = ()
    location: SourceLocation | None = field(default=None, compare=False)


@dataclass(frozen=True, slots=True)
class Trait:
    """Reusable fields generated as a base struct for nodes."""

    name: str
    fields: tuple[Field, ...] = ()
    location: SourceLocation | None = field(default=None, compare=False)


@dataclass(frozen=True, slots=True)
class Choice:
    """A sum type with optional traits propagated to its node alternatives."""

    name: str
    alternatives: tuple[str, ...]
    all_traits: tuple[str, ...] = ()
    location: SourceLocation | None = field(default=None, compare=False)


@dataclass(frozen=True, slots=True)
class Enum:
    """An enumeration with newly introduced values."""

    name: str
    values: tuple[str, ...]
    location: SourceLocation | None = field(default=None, compare=False)


type Definition = Node | Trait | Choice | Enum


@dataclass(frozen=True, slots=True)
class Module:
    """All declarations contained in one .ndef file."""

    name: str
    definitions: tuple[Definition, ...]
    location: SourceLocation | None = field(default=None, compare=False)


@dataclass(frozen=True, slots=True)
class TypeMapping:
    """A mapping from a Silwright type to a C++ type."""

    source_type: str
    cpp_type: str
    location: SourceLocation | None = field(default=None, compare=False)


@dataclass(frozen=True, slots=True)
class ParsedDefinitionFile:
    """A parsed module and the C++ backend mappings resolved for its directory."""

    module: Module
    type_mappings: tuple[TypeMapping, ...]
    backend_includes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CppBackendConfig:
    """Parsed contents of a backend_cpp.map file."""

    type_mappings: tuple[TypeMapping, ...]
    includes: tuple[str, ...]
