"""Generate C++ code from node descriptions."""

from struct_gen.generator import generate_header
from struct_gen.model import Field, Node

__all__ = ["Field", "Node", "generate_header"]

