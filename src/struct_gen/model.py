"""Domain objects describing generated C++ nodes."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Field:
    """A named C++ field on a node."""

    name: str
    cpp_type: str


@dataclass(frozen=True, slots=True)
class Node:
    """A C++ node description."""

    name: str
    fields: tuple[Field, ...] = ()

