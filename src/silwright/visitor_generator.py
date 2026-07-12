"""Generate mutable tree visitor classes for node definitions."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from silwright.generated_file import write_generated_file
from silwright.model import Choice, Enum, Node, ParsedDefinitionFile, Trait
from silwright.naming import cpp_name
from silwright.parser import parse_definition_file
from silwright.semantic import ValidatedModel, analyze, ensure_validated


@dataclass(frozen=True, slots=True)
class GeneratedVisitorCpp:
    """Generated visitor header and source files."""

    header: str
    source: str


def generate_visitor_cpp(
    model: ParsedDefinitionFile | ValidatedModel,
    model_header_name: str,
    visitor_header_name: str,
) -> GeneratedVisitorCpp:
    """Generate mutable traversal support for a parsed module."""
    validated = ensure_validated(model)
    parsed = validated.parsed
    declarations = validated.declarations

    visitable_names = validated.visitable_names
    choices = tuple(
        item
        for item in parsed.module.definitions
        if isinstance(item, Choice) and item.name in visitable_names
    )
    list_alias_names = frozenset(item.name for item in validated.repeated_pointer_choices)
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
    replacement_helpers = "\n".join(
        line
        for item in choices
        for line in _replacement_helper_declarations(item, list_alias_names)
    )
    replacement_state = "\n".join(
        line
        for item in choices
        for line in _replacement_state_declarations(item, list_alias_names)
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
        f"{hooks}\n\n"
        f"{replacement_helpers}\n\n"
        "private:\n"
        f"{replacement_state}\n"
        "};\n\n"
        f"}}  // namespace {namespace}\n"
    )

    definitions: list[str] = []
    definitions.extend(_render_choice_visit(item) for item in choices)
    definitions.extend(
        _render_node_visit(item, declarations, list_alias_names) for item in nodes
    )
    definitions.extend(_render_hooks(item) for item in nodes)
    definitions.extend(
        _render_replacement_helpers(item, list_alias_names) for item in choices
    )
    source = (
        f'#include "{visitor_header_name}"\n\n'
        "#include <cassert>\n"
        "#include <utility>\n"
        "#include <variant>\n\n"
        f"namespace {namespace} {{\n\n"
        f"{'\n\n'.join(definitions)}\n\n"
        f"}}  // namespace {namespace}\n"
    )
    return GeneratedVisitorCpp(header=header, source=source)


def generate_visitor_files(
    definition_path: Path,
    *,
    generated_at: datetime | None = None,
    validated: ValidatedModel | None = None,
) -> tuple[Path, Path]:
    """Parse a definition and write its sibling visitor files."""
    parsed = validated or analyze(parse_definition_file(definition_path))
    stem = definition_path.stem
    header_path = definition_path.with_name(f"{stem}_visitor.hpp")
    source_path = definition_path.with_name(f"{stem}_visitor.cpp")
    generated = generate_visitor_cpp(
        parsed,
        definition_path.with_suffix(".hpp").name,
        header_path.name,
    )
    write_generated_file(header_path, generated.header, definition_path, generated_at)
    write_generated_file(source_path, generated.source, definition_path, generated_at)
    return header_path, source_path


def _render_choice_visit(item: Choice) -> str:
    type_name = cpp_name(item.name)
    return f'''void visitor::visit({type_name}& value) {{
    std::visit([this](auto& alternative) {{ visit(alternative); }}, value);
}}'''


def _choice_list_type(item: Choice, list_alias_names: frozenset[str]) -> str:
    type_name = cpp_name(item.name)
    if item.name in list_alias_names:
        return f"{type_name}_list"
    return f"std::vector<std::unique_ptr<{type_name}>>"


def _replacement_helper_declarations(
    item: Choice, list_alias_names: frozenset[str]
) -> tuple[str, str]:
    type_name = cpp_name(item.name)
    list_type = _choice_list_type(item, list_alias_names)
    return (
        f"    void replace_{type_name}(std::unique_ptr<{type_name}> replacement);",
        f"    void replace_{type_name}({list_type} replacements);",
    )


def _replacement_state_declarations(
    item: Choice, list_alias_names: frozenset[str]
) -> tuple[str, str, str]:
    type_name = cpp_name(item.name)
    list_type = _choice_list_type(item, list_alias_names)
    return (
        f"    bool has_{type_name}_replacements_ = false;",
        f"    {list_type} {type_name}_replacements_;",
        f"    {list_type} take_{type_name}_replacements();",
    )


def _render_node_visit(
    item: Node,
    declarations: dict[str, Node | Trait | Choice | Enum],
    list_alias_names: frozenset[str],
) -> str:
    statements = ["    enter(value);"]
    for field in item.fields:
        target = declarations.get(field.type_name)
        if field.by_value or field.transient or not isinstance(target, (Node, Choice)):
            continue
        access = f"value.{field.name}"
        if field.multiple:
            if isinstance(target, Choice):
                statements.extend(
                    _render_choice_multiple_field_visit(
                        access, target, field.fixed, list_alias_names
                    )
                )
            else:
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
            if isinstance(target, Choice):
                statements.extend(_render_choice_single_field_visit(access, target))
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


def _render_choice_single_field_visit(access: str, target: Choice) -> tuple[str, ...]:
    name = cpp_name(target.name)
    field_name = access.rsplit(".", 1)[1]
    replacements = f"replacements_{field_name}"
    return (
        f"    if ({access}) {{",
        f"        visit(*{access});",
        f"        if (has_{name}_replacements_) {{",
        f"            auto {replacements} = take_{name}_replacements();",
        f"            assert({replacements}.size() <= 1);",
        f"            if ({replacements}.empty()) {{",
        f"                {access} = nullptr;",
        "            } else {",
        f"                {access} = std::move({replacements}.front());",
        "            }",
        "        }",
        "    }",
    )


def _render_choice_multiple_field_visit(
    access: str,
    target: Choice,
    fixed: bool,
    list_alias_names: frozenset[str],
) -> tuple[str, ...]:
    name = cpp_name(target.name)
    field_name = access.rsplit(".", 1)[1]
    replacement_list = f"replacement_{field_name}"
    replacements = f"replacements_{field_name}"
    lines = [
        f"    {_choice_list_type(target, list_alias_names)} {replacement_list};",
        f"    {replacement_list}.reserve({access}.size());",
        f"    for (auto& child : {access}) {{",
        "        if (!child) {",
        f"            {replacement_list}.push_back(nullptr);",
        "            continue;",
        "        }",
        "        visit(*child);",
        f"        if (has_{name}_replacements_) {{",
        f"            auto {replacements} = take_{name}_replacements();",
    ]
    if fixed:
        lines.extend(
            (
                f"            assert({replacements}.size() == 1);",
                f"            {replacement_list}.push_back(std::move({replacements}.front()));",
            )
        )
    else:
        lines.extend(
            (
                f"            for (auto& replacement : {replacements}) {{",
                f"                {replacement_list}.push_back(std::move(replacement));",
                "            }",
            )
        )
    lines.extend(
        (
            "        } else {",
            f"            {replacement_list}.push_back(std::move(child));",
            "        }",
            "    }",
            f"    {access} = std::move({replacement_list});",
        )
    )
    return tuple(lines)


def _render_hooks(item: Node) -> str:
    type_name = cpp_name(item.name)
    return f'''void visitor::enter({type_name}&) {{}}

void visitor::leave({type_name}&) {{}}'''


def _render_replacement_helpers(item: Choice, list_alias_names: frozenset[str]) -> str:
    type_name = cpp_name(item.name)
    list_type = _choice_list_type(item, list_alias_names)
    return f'''void visitor::replace_{type_name}(std::unique_ptr<{type_name}> replacement) {{
    has_{type_name}_replacements_ = true;
    {type_name}_replacements_.clear();
    {type_name}_replacements_.push_back(std::move(replacement));
}}

void visitor::replace_{type_name}({list_type} replacements) {{
    has_{type_name}_replacements_ = true;
    {type_name}_replacements_ = std::move(replacements);
}}

{list_type} visitor::take_{type_name}_replacements() {{
    has_{type_name}_replacements_ = false;
    return std::move({type_name}_replacements_);
}}'''
