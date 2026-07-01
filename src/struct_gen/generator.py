"""Generate C++ declarations from parsed node definitions."""

import re
from dataclasses import dataclass
from pathlib import Path

from struct_gen.model import Choice, Enum, Module, Node, ParsedDefinitionFile
from struct_gen.parser import parse_definition_file


class GenerationError(ValueError):
    """Raised when parsed definitions cannot be represented by the C++ backend."""


@dataclass(frozen=True, slots=True)
class GeneratedCpp:
    """The header and source generated for one definition file."""

    header: str
    source: str


def cpp_name(name: str) -> str:
    """Convert a definition name from CamelCase to snake_case."""
    with_word_boundaries = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", with_word_boundaries).lower()


def generate_cpp(parsed: ParsedDefinitionFile, header_name: str) -> GeneratedCpp:
    """Generate a C++ header and source for a parsed definition file."""
    module = parsed.module
    declarations = _declarations_by_name(module)
    mappings = _mappings_by_name(parsed)
    enums = tuple(item for item in module.definitions if isinstance(item, Enum))
    nodes = tuple(item for item in module.definitions if isinstance(item, Node))
    choices = _order_choices(module, declarations)

    body: list[str] = []
    body.extend(_render_enum(item) for item in enums)
    if enums:
        body.append("")
    body.extend(f"struct {cpp_name(item.name)};" for item in nodes)
    if nodes:
        body.append("")
    body.extend(_render_choice(item, declarations) for item in choices)
    if choices:
        body.append("")
    ordered_nodes = _order_nodes(nodes, declarations)
    body.extend(_render_node(item, declarations, mappings) for item in ordered_nodes)

    rendered_body = "\n".join(body).rstrip()
    include_spellings = dict.fromkeys(
        (
            "<memory>",
            "<optional>",
            "<string>",
            "<variant>",
            "<vector>",
            *parsed.backend_includes,
        )
    )
    includes = "\n".join(f"#include {spelling}" for spelling in include_spellings)
    header = (
        "#pragma once\n\n"
        f"{includes}\n\n"
        f"namespace {module.name} {{\n\n"
        f"{rendered_body}\n\n"
        f"}}  // namespace {module.name}\n"
    )
    source = f'#include "{header_name}"\n'
    return GeneratedCpp(header=header, source=source)


def generate_cpp_files(definition_path: Path) -> tuple[Path, Path]:
    """Parse a definition and write sibling .hpp and .cpp files."""
    parsed = parse_definition_file(definition_path)
    header_path = definition_path.with_suffix(".hpp")
    source_path = definition_path.with_suffix(".cpp")
    generated = generate_cpp(parsed, header_path.name)
    header_path.write_text(generated.header, encoding="utf-8", newline="\n")
    source_path.write_text(generated.source, encoding="utf-8", newline="\n")
    return header_path, source_path


def _declarations_by_name(module: Module) -> dict[str, Node | Choice | Enum]:
    result: dict[str, Node | Choice | Enum] = {}
    for declaration in module.definitions:
        if declaration.name in result:
            raise GenerationError(f"duplicate definition: {declaration.name}")
        result[declaration.name] = declaration
    return result


def _mappings_by_name(parsed: ParsedDefinitionFile) -> dict[str, str]:
    result: dict[str, str] = {}
    for mapping in parsed.type_mappings:
        if mapping.source_type in result:
            raise GenerationError(f"duplicate C++ backend mapping: {mapping.source_type}")
        result[mapping.source_type] = mapping.cpp_type
    return result


def _render_enum(item: Enum) -> str:
    values = ",\n".join(f"    {value}" for value in item.values)
    return f"enum class {cpp_name(item.name)}_t {{\n{values}\n}};"


def _render_choice(
    item: Choice,
    declarations: dict[str, Node | Choice | Enum],
) -> str:
    alternatives: list[str] = []
    for name in item.alternatives:
        target = declarations.get(name)
        if target is None:
            raise GenerationError(f"unknown choice alternative {name!r} in {item.name}")
        if isinstance(target, Enum):
            raise GenerationError(f"enum {name!r} cannot be a choice alternative")
        alternatives.append(cpp_name(name))
    return f"using {cpp_name(item.name)} = std::variant<{', '.join(alternatives)}>;"


def _render_node(
    item: Node,
    declarations: dict[str, Node | Choice | Enum],
    mappings: dict[str, str],
) -> str:
    fields: list[str] = []
    for field in item.fields:
        pointer_backed = False
        if field.type_name in mappings:
            field_type = mappings[field.type_name]
        else:
            target = declarations.get(field.type_name)
            if isinstance(target, Enum):
                field_type = f"{cpp_name(target.name)}_t"
            elif isinstance(target, (Node, Choice)):
                named_type = cpp_name(target.name)
                pointer_backed = not field.by_value
                field_type = named_type if field.by_value else f"std::unique_ptr<{named_type}>"
            else:
                raise GenerationError(f"unknown field type {field.type_name!r} in {item.name}")
        if field.multiple:
            field_type = f"std::vector<{field_type}>"
        elif field.optional and not pointer_backed:
            field_type = f"std::optional<{field_type}>"
        fields.append(f"    {field_type} {field.name};")
    members = "\n".join(fields)
    return f"struct {cpp_name(item.name)} {{\n{members}\n}};"


def _order_choices(
    module: Module,
    declarations: dict[str, Node | Choice | Enum],
) -> tuple[Choice, ...]:
    choices = {
        item.name: item for item in module.definitions if isinstance(item, Choice)
    }
    ordered: list[Choice] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(item: Choice) -> None:
        if item.name in visiting:
            raise GenerationError(f"cyclic choice dependency involving {item.name}")
        if item.name in visited:
            return
        visiting.add(item.name)
        for alternative in item.alternatives:
            target = declarations.get(alternative)
            if isinstance(target, Choice):
                visit(choices[target.name])
        visiting.remove(item.name)
        visited.add(item.name)
        ordered.append(item)

    for choice in choices.values():
        visit(choice)
    return tuple(ordered)


def _order_nodes(
    nodes: tuple[Node, ...],
    declarations: dict[str, Node | Choice | Enum],
) -> tuple[Node, ...]:
    ordered: list[Node] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def choice_node_dependencies(choice: Choice, seen: set[str]) -> tuple[Node, ...]:
        if choice.name in seen:
            return ()
        seen.add(choice.name)
        dependencies: list[Node] = []
        for alternative in choice.alternatives:
            target = declarations.get(alternative)
            if isinstance(target, Node):
                dependencies.append(target)
            elif isinstance(target, Choice):
                dependencies.extend(choice_node_dependencies(target, seen))
        return tuple(dependencies)

    def visit(node: Node) -> None:
        if node.name in visiting:
            raise GenerationError(f"cyclic value dependency involving {node.name}")
        if node.name in visited:
            return
        visiting.add(node.name)
        for field in node.fields:
            if not field.by_value:
                continue
            target = declarations.get(field.type_name)
            if isinstance(target, Node):
                visit(target)
            elif isinstance(target, Choice):
                for dependency in choice_node_dependencies(target, set()):
                    visit(dependency)
        visiting.remove(node.name)
        visited.add(node.name)
        ordered.append(node)

    for node in nodes:
        visit(node)
    return tuple(ordered)
