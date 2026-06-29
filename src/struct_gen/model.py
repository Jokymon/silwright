"""Syntax model for struct-gen definition files."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Field:
    """A named field with a struct-gen type reference."""

    name: str
    type_name: str


@dataclass(frozen=True, slots=True)
class Node:
    """A structured node declaration."""

    name: str
    fields: tuple[Field, ...] = ()


@dataclass(frozen=True, slots=True)
class Choice:
    """A sum type whose alternatives refer to other declared types."""

    name: str
    alternatives: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Enum:
    """An enumeration with newly introduced values."""

    name: str
    values: tuple[str, ...]


type Definition = Node | Choice | Enum


@dataclass(frozen=True, slots=True)
class Module:
    """All declarations contained in one .ndef file."""

    name: str
    definitions: tuple[Definition, ...]


@dataclass(frozen=True, slots=True)
class TypeMapping:
    """A mapping from a built-in struct-gen type to a C++ type."""

    source_type: str
    cpp_type: str


@dataclass(frozen=True, slots=True)
class ParsedDefinitionFile:
    """A parsed module and the built-in mappings resolved for its directory."""

    module: Module
    type_mappings: tuple[TypeMapping, ...]
