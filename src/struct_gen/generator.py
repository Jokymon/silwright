"""C++ source generation."""

from struct_gen.model import Node


def generate_header(node: Node) -> str:
    """Render a node as a standalone C++ header."""
    members = "\n".join(f"    {field.cpp_type} {field.name};" for field in node.fields)
    body = f"\n{members}\n" if members else "\n"
    return f"#pragma once\n\nstruct {node.name} {{{body}}};\n"

