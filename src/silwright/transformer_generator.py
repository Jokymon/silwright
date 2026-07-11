"""Generate mutable bottom-up tree transformer classes for node definitions."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from silwright.generated_file import write_generated_file
from silwright.model import Choice, Enum, Node, ParsedDefinitionFile, Trait
from silwright.naming import cpp_name
from silwright.parser import parse_definition_file
from silwright.semantic import ValidatedModel, analyze, ensure_validated


@dataclass(frozen=True, slots=True)
class GeneratedTransformerCpp:
    """Generated transformer header and source files."""

    header: str
    source: str


def generate_transformer_cpp(
    model: ParsedDefinitionFile | ValidatedModel,
    model_header_name: str,
    transformer_header_name: str,
) -> GeneratedTransformerCpp:
    """Generate mutable bottom-up transformation support for a parsed module."""
    validated = ensure_validated(model)
    parsed = validated.parsed
    declarations = validated.declarations
    visitable_names = validated.visitable_names
    multiple_names = validated.transformer_multiple_names
    return_choices = validated.transformer_return_choices
    list_alias_names = frozenset(item.name for item in validated.repeated_pointer_choices)
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
    transformable = tuple(
        item
        for item in parsed.module.definitions
        if isinstance(item, (Choice, Node)) and item.name in visitable_names
    )
    namespace = parsed.module.name

    public_rewrites = "\n".join(
        _render_rewrite_declaration(item, multiple_names, list_alias_names, return_choices)
        for item in transformable
    )
    hooks = "\n".join(
        f"    virtual {_visit_return_type(item, multiple_names, list_alias_names, return_choices)} "
        f"{_visit_name(item, multiple_names)}({cpp_name(item.name)}& value);"
        for item in nodes
    )
    rewrite_children = "\n".join(
        f"    void rewrite_children({cpp_name(item.name)}& value);" for item in nodes
    )
    header = (
        "#pragma once\n\n"
        f'#include "{model_header_name}"\n\n'
        f"namespace {namespace} {{\n\n"
        "class transformer {\n"
        "public:\n"
        "    virtual ~transformer() = default;\n\n"
        f"{public_rewrites}\n\n"
        "protected:\n"
        f"{hooks}\n\n"
        "private:\n"
        f"{rewrite_children}\n"
        "};\n\n"
        f"}}  // namespace {namespace}\n"
    )

    definitions: list[str] = []
    definitions.extend(
        _render_choice_rewrite(item, multiple_names, list_alias_names, return_choices)
        for item in choices
    )
    definitions.extend(
        _render_node_rewrite(item, multiple_names, list_alias_names, return_choices)
        for item in nodes
    )
    definitions.extend(
        _render_rewrite_children(item, declarations, multiple_names) for item in nodes
    )
    definitions.extend(
        _render_hook(item, multiple_names, list_alias_names, return_choices) for item in nodes
    )
    source = (
        f'#include "{transformer_header_name}"\n\n'
        "#include <cassert>\n"
        "#include <type_traits>\n"
        "#include <utility>\n"
        "#include <variant>\n\n"
        f"namespace {namespace} {{\n\n"
        f"{'\n\n'.join(definitions)}\n\n"
        f"}}  // namespace {namespace}\n"
    )
    return GeneratedTransformerCpp(header=header, source=source)


def generate_transformer_files(
    definition_path: Path,
    *,
    generated_at: datetime | None = None,
    validated: ValidatedModel | None = None,
) -> tuple[Path, Path]:
    """Parse a definition and write its sibling transformer files."""
    parsed = validated or analyze(parse_definition_file(definition_path))
    stem = definition_path.stem
    header_path = definition_path.with_name(f"{stem}_transformer.hpp")
    source_path = definition_path.with_name(f"{stem}_transformer.cpp")
    generated = generate_transformer_cpp(
        parsed,
        definition_path.with_suffix(".hpp").name,
        header_path.name,
    )
    write_generated_file(header_path, generated.header, definition_path, generated_at)
    write_generated_file(source_path, generated.source, definition_path, generated_at)
    return header_path, source_path


def _rewrite_return_type(
    item: Node | Choice,
    multiple_names: frozenset[str],
    list_alias_names: frozenset[str] = frozenset(),
    return_choices: dict[str, Choice] | None = None,
) -> str:
    result_item: Node | Choice = item
    if return_choices is not None and isinstance(item, Node):
        result_item = return_choices.get(item.name, item)
    type_name = cpp_name(result_item.name)
    if item.name in multiple_names:
        if isinstance(result_item, Choice) and result_item.name in list_alias_names:
            return f"{type_name}_list"
        return f"std::vector<std::unique_ptr<{type_name}>>"
    return f"std::unique_ptr<{type_name}>"


def _render_rewrite_declaration(
    item: Node | Choice,
    multiple_names: frozenset[str],
    list_alias_names: frozenset[str],
    return_choices: dict[str, Choice],
) -> str:
    return_type = _rewrite_return_type(
        item, multiple_names, list_alias_names, return_choices
    )
    return f"    {return_type} rewrite(std::unique_ptr<{cpp_name(item.name)}> node);"


def _visit_return_type(
    item: Node,
    multiple_names: frozenset[str],
    list_alias_names: frozenset[str],
    return_choices: dict[str, Choice],
) -> str:
    return _rewrite_return_type(item, multiple_names, list_alias_names, return_choices)


def _visit_name(item: Node, multiple_names: frozenset[str]) -> str:
    return "visit_multiple" if item.name in multiple_names else "visit_single"


def _render_node_rewrite(
    item: Node,
    multiple_names: frozenset[str],
    list_alias_names: frozenset[str],
    return_choices: dict[str, Choice],
) -> str:
    type_name = cpp_name(item.name)
    return_type = _rewrite_return_type(item, multiple_names, list_alias_names, return_choices)
    null_return = "{}" if item.name in multiple_names else "nullptr"
    visit_name = _visit_name(item, multiple_names)
    return f'''{return_type} transformer::rewrite(std::unique_ptr<{type_name}> node) {{
    if (!node) {{
        return {null_return};
    }}
    rewrite_children(*node);
    return {visit_name}(*node);
}}'''


def _render_choice_rewrite(
    item: Choice,
    multiple_names: frozenset[str],
    list_alias_names: frozenset[str],
    return_choices: dict[str, Choice],
) -> str:
    type_name = cpp_name(item.name)
    return_type = _rewrite_return_type(item, multiple_names, list_alias_names)
    null_return = "{}" if item.name in multiple_names else "nullptr"
    if item.name in multiple_names:
        return f'''{return_type} transformer::rewrite(std::unique_ptr<{type_name}> node) {{
    if (!node) {{
        return {null_return};
    }}
    return std::visit([this] (auto& alternative) -> {return_type} {{
        using alternative_type = std::decay_t<decltype(alternative)>;
        auto replacements = rewrite(
            std::make_unique<alternative_type>(std::move(alternative)));
        {return_type} result;
        for (auto& replacement : replacements) {{
            if (replacement) {{
                if constexpr (std::is_same_v<
                    typename std::decay_t<decltype(replacement)>::element_type,
                    {type_name}>) {{
                    result.push_back(std::move(replacement));
                }} else {{
                    result.push_back(std::make_unique<{type_name}>(std::move(*replacement)));
                }}
            }}
        }}
        return result;
    }}, *node);
}}'''
    return f'''{return_type} transformer::rewrite(std::unique_ptr<{type_name}> node) {{
    if (!node) {{
        return {null_return};
    }}
    return std::visit([this] (auto& alternative) -> {return_type} {{
        using alternative_type = std::decay_t<decltype(alternative)>;
        auto replacement = rewrite(
            std::make_unique<alternative_type>(std::move(alternative)));
        if (!replacement) {{
            return nullptr;
        }}
        if constexpr (std::is_same_v<
            typename std::decay_t<decltype(replacement)>::element_type,
            {type_name}>) {{
            return std::move(replacement);
        }} else {{
            return std::make_unique<{type_name}>(std::move(*replacement));
        }}
    }}, *node);
}}'''


def _render_rewrite_children(
    item: Node,
    declarations: dict[str, Node | Trait | Choice | Enum],
    multiple_names: frozenset[str],
) -> str:
    statements: list[str] = []
    for field in item.fields:
        target = declarations.get(field.type_name)
        if field.by_value or field.transient or not isinstance(target, (Node, Choice)):
            continue
        access = f"value.{field.name}"
        target_multiple = field.type_name in multiple_names
        if field.multiple:
            if field.fixed:
                statements.extend(_render_fixed_multiple_field_rewrite(access, target))
            else:
                statements.extend(_render_multiple_field_rewrite(access, target))
        elif target_multiple:
            statements.extend(_render_single_from_multiple_rewrite(access))
        else:
            statements.append(f"    {access} = rewrite(std::move({access}));")
    body = "\n".join(statements) if statements else "    (void)value;"
    return f'''void transformer::rewrite_children({cpp_name(item.name)}& value) {{
{body}
}}'''


def _render_multiple_field_rewrite(access: str, target: Node | Choice) -> tuple[str, ...]:
    field_name = access.rsplit(".", 1)[1]
    replacement_type = (
        f"{cpp_name(target.name)}_list"
        if isinstance(target, Choice)
        else f"std::vector<std::unique_ptr<{cpp_name(target.name)}>>"
    )
    return (
        f"    {replacement_type} replacement_{field_name};",
        f"    for (auto& child : {access}) {{",
        "        auto replacements = rewrite(std::move(child));",
        "        for (auto& replacement : replacements) {",
        "            if (replacement) {",
        f"                replacement_{field_name}.push_back(std::move(replacement));",
        "            }",
        "        }",
        "    }",
        f"    {access} = std::move(replacement_{field_name});",
    )


def _render_fixed_multiple_field_rewrite(
    access: str, target: Node | Choice
) -> tuple[str, ...]:
    field_name = access.rsplit(".", 1)[1]
    replacement_type = (
        f"{cpp_name(target.name)}_list"
        if isinstance(target, Choice)
        else f"std::vector<std::unique_ptr<{cpp_name(target.name)}>>"
    )
    return (
        f"    {replacement_type} replacement_{field_name};",
        f"    replacement_{field_name}.reserve({access}.size());",
        f"    for (auto& child : {access}) {{",
        "        if (!child) {",
        f"            replacement_{field_name}.push_back(nullptr);",
        "            continue;",
        "        }",
        "        auto replacements = rewrite(std::move(child));",
        "        assert(replacements.size() == 1);",
        f"        replacement_{field_name}.push_back(std::move(replacements.front()));",
        "    }",
        f"    {access} = std::move(replacement_{field_name});",
    )


def _render_single_from_multiple_rewrite(access: str) -> tuple[str, ...]:
    return (
        f"    auto replacement_{access.rsplit('.', 1)[1]} = rewrite(std::move({access}));",
        f"    assert(replacement_{access.rsplit('.', 1)[1]}.size() <= 1);",
        f"    if (replacement_{access.rsplit('.', 1)[1]}.empty()) {{",
        f"        {access} = nullptr;",
        "    } else {",
        f"        {access} = std::move(replacement_{access.rsplit('.', 1)[1]}.front());",
        "    }",
    )


def _render_hook(
    item: Node,
    multiple_names: frozenset[str],
    list_alias_names: frozenset[str],
    return_choices: dict[str, Choice],
) -> str:
    type_name = cpp_name(item.name)
    return_type = _visit_return_type(item, multiple_names, list_alias_names, return_choices)
    visit_name = _visit_name(item, multiple_names)
    result_choice = return_choices.get(item.name)
    result_type_name = cpp_name(result_choice.name) if result_choice is not None else type_name
    if item.name in multiple_names:
        return f'''{return_type} transformer::{visit_name}({type_name}& value) {{
    {return_type} result;
    result.push_back(std::make_unique<{result_type_name}>(std::move(value)));
    return result;
}}'''
    return f'''{return_type} transformer::{visit_name}({type_name}& value) {{
    return std::make_unique<{result_type_name}>(std::move(value));
}}'''
