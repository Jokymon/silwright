"""Generate mutable tree visitor classes for node definitions."""

from dataclasses import dataclass
from pathlib import Path

from struct_gen.generator import GenerationError, cpp_name
from struct_gen.model import Choice, Enum, Node, ParsedDefinitionFile
from struct_gen.parser import parse_definition_file


@dataclass(frozen=True, slots=True)
class GeneratedVisitorCpp:
    """Generated visitor header and source files."""

    header: str
    source: str


def generate_visitor_cpp(
    parsed: ParsedDefinitionFile,
    model_header_name: str,
    visitor_header_name: str,
) -> GeneratedVisitorCpp:
    """Generate mutable traversal support for a parsed module."""
    declarations = {item.name: item for item in parsed.module.definitions}
    if len(declarations) != len(parsed.module.definitions):
        raise GenerationError("duplicate definitions cannot generate a visitor")
    if any(cpp_name(item.name) == "visitor" for item in parsed.module.definitions):
        raise GenerationError("definition name conflicts with generated visitor class")

    visitable_names = _visitable_definition_names(parsed, declarations)
    choices = tuple(
        item
        for item in parsed.module.definitions
        if isinstance(item, Choice) and item.name in visitable_names
    )
    nodes = tuple(
        item
        for item in parsed.module.definitions
        if isinstance(item, Node) and item.name in visitable_names
    )
    visitable = tuple(
        item
        for item in parsed.module.definitions
        if isinstance(item, (Choice, Node)) and item.name in visitable_names
    )
    namespace = parsed.module.name

    public_visits = "\n".join(
        f"    void visit({cpp_name(item.name)}& value);" for item in visitable
    )
    hooks = "\n".join(
        line
        for item in nodes
        for line in (
            f"    virtual void enter({cpp_name(item.name)}& value);",
            f"    virtual void leave({cpp_name(item.name)}& value);",
        )
    )
    header = (
        "#pragma once\n\n"
        f'#include "{model_header_name}"\n\n'
        f"namespace {namespace} {{\n\n"
        "class visitor {\n"
        "public:\n"
        "    virtual ~visitor() = default;\n\n"
        f"{public_visits}\n\n"
        "protected:\n"
        f"{hooks}\n"
        "};\n\n"
        f"}}  // namespace {namespace}\n"
    )

    definitions: list[str] = []
    definitions.extend(_render_choice_visit(item) for item in choices)
    definitions.extend(_render_node_visit(item, declarations) for item in nodes)
    definitions.extend(_render_hooks(item) for item in nodes)
    source = (
        f'#include "{visitor_header_name}"\n\n'
        "#include <variant>\n\n"
        f"namespace {namespace} {{\n\n"
        f"{'\n\n'.join(definitions)}\n\n"
        f"}}  // namespace {namespace}\n"
    )
    return GeneratedVisitorCpp(header=header, source=source)


def generate_visitor_files(definition_path: Path) -> tuple[Path, Path]:
    """Parse a definition and write its sibling visitor files."""
    parsed = parse_definition_file(definition_path)
    stem = definition_path.stem
    header_path = definition_path.with_name(f"{stem}_visitor.hpp")
    source_path = definition_path.with_name(f"{stem}_visitor.cpp")
    generated = generate_visitor_cpp(
        parsed,
        definition_path.with_suffix(".hpp").name,
        header_path.name,
    )
    header_path.write_text(generated.header, encoding="utf-8", newline="\n")
    source_path.write_text(generated.source, encoding="utf-8", newline="\n")
    return header_path, source_path


def _render_choice_visit(item: Choice) -> str:
    type_name = cpp_name(item.name)
    return f'''void visitor::visit({type_name}& value) {{
    std::visit([this](auto& alternative) {{ visit(alternative); }}, value);
}}'''


def _render_node_visit(
    item: Node,
    declarations: dict[str, Node | Choice | Enum],
) -> str:
    statements = ["    enter(value);"]
    for field in item.fields:
        target = declarations.get(field.type_name)
        if field.by_value or not isinstance(target, (Node, Choice)):
            continue
        access = f"value.{field.name}"
        if field.multiple:
            statements.extend(
                (
                    f"    for (auto& child : {access}) {{",
                    "        if (child) {",
                    "            visit(*child);",
                    "        }",
                    "    }",
                )
            )
        else:
            statements.extend(
                (
                    f"    if ({access}) {{",
                    f"        visit(*{access});",
                    "    }",
                )
            )
    statements.append("    leave(value);")
    body = "\n".join(statements)
    return f'''void visitor::visit({cpp_name(item.name)}& value) {{
{body}
}}'''


def _render_hooks(item: Node) -> str:
    type_name = cpp_name(item.name)
    return f'''void visitor::enter({type_name}&) {{}}

void visitor::leave({type_name}&) {{}}'''


def _visitable_definition_names(
    parsed: ParsedDefinitionFile,
    declarations: dict[str, Node | Choice | Enum],
) -> set[str]:
    """Find definitions that can participate in pointer-backed traversal."""
    structured = {
        item.name: item
        for item in parsed.module.definitions
        if isinstance(item, (Node, Choice))
    }
    referenced: set[str] = set()
    visitable: set[str] = set()

    for item in parsed.module.definitions:
        if isinstance(item, Node):
            for field in item.fields:
                if field.type_name not in structured:
                    continue
                referenced.add(field.type_name)
                if not field.by_value:
                    visitable.add(field.type_name)
        elif isinstance(item, Choice):
            referenced.update(
                alternative for alternative in item.alternatives if alternative in structured
            )

    # A definition that is not used by another definition remains a public traversal root.
    visitable.update(structured.keys() - referenced)

    # Dispatching a choice requires visit overloads for every one of its alternatives.
    pending = list(visitable)
    while pending:
        name = pending.pop()
        item = declarations[name]
        if not isinstance(item, Choice):
            continue
        for alternative in item.alternatives:
            if alternative in structured and alternative not in visitable:
                visitable.add(alternative)
                pending.append(alternative)
    return visitable
