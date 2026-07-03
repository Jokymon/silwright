"""Generate YAML-like C++ dump functions for node definitions."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from struct_gen.generated_file import write_generated_file
from struct_gen.generator import GenerationError, cpp_name, resolve_node_fields
from struct_gen.model import Choice, Enum, Field, Node, ParsedDefinitionFile, Trait
from struct_gen.parser import parse_definition_file


@dataclass(frozen=True, slots=True)
class GeneratedDumpCpp:
    """Generated dumper declaration, implementation, and source files."""

    header: str
    implementation: str
    source: str


def generate_dump_cpp(
    parsed: ParsedDefinitionFile,
    model_header_name: str,
    dump_header_name: str,
    implementation_name: str,
) -> GeneratedDumpCpp:
    """Generate templated YAML-like dump support for a parsed module."""
    declarations = {item.name: item for item in parsed.module.definitions}
    if len(declarations) != len(parsed.module.definitions):
        raise GenerationError("duplicate definitions cannot generate dump functions")

    enums = tuple(item for item in parsed.module.definitions if isinstance(item, Enum))
    choices = tuple(item for item in parsed.module.definitions if isinstance(item, Choice))
    nodes = tuple(item for item in parsed.module.definitions if isinstance(item, Node))
    node_fields = resolve_node_fields(parsed.module, declarations)
    namespace = parsed.module.name

    public_declarations = [
        "template <class Context, class Value>",
        "void dump_value(std::ostream& out, Context& ctx, const Value& value);",
        "",
        "template <class Context>",
        "void dump_value(std::ostream& out, Context& ctx, const std::string& value);",
        "",
        "template <class Context>",
        "void dump_value(std::ostream& out, Context& ctx, const bool& value);",
    ]
    for enum_item in enums:
        enum_type = f"{cpp_name(enum_item.name)}_t"
        public_declarations.extend(
            (
                "",
                "template <class Context>",
                "void dump_value(",
                f"    std::ostream& out, Context& ctx, const {enum_type}& value);",
                "",
                *_dump_declaration(enum_type),
            )
        )
    for choice_item in choices:
        public_declarations.extend(("", *_dump_declaration(cpp_name(choice_item.name))))
    for node_item in nodes:
        public_declarations.extend(("", *_dump_declaration(cpp_name(node_item.name))))

    header = (
        "#pragma once\n\n"
        f'#include "{model_header_name}"\n\n'
        "#include <ostream>\n"
        "#include <string>\n\n"
        f"namespace {namespace} {{\n\n"
        f"{'\n'.join(public_declarations)}\n\n"
        f"}}  // namespace {namespace}\n\n"
        f'#include "{implementation_name}"\n'
    )

    definitions = [_dump_helpers()]
    definitions.extend(_render_enum_dump(item) for item in enums)
    definitions.extend(_render_choice_dump(item) for item in choices)
    definitions.extend(
        _render_node_dump(item, node_fields[item.name], declarations) for item in nodes
    )
    implementation = (
        "#pragma once\n\n"
        "#include <string_view>\n"
        "\n"
        f"namespace {namespace} {{\n\n"
        f"{'\n\n'.join(definitions)}\n\n"
        f"}}  // namespace {namespace}\n"
    )
    source = f'#include "{dump_header_name}"\n'
    return GeneratedDumpCpp(header=header, implementation=implementation, source=source)


def generate_dump_files(
    definition_path: Path, *, generated_at: datetime | None = None
) -> tuple[Path, Path, Path]:
    """Parse a definition and write its sibling dumper files."""
    parsed = parse_definition_file(definition_path)
    stem = definition_path.stem
    header_path = definition_path.with_name(f"{stem}_dump.hpp")
    implementation_path = definition_path.with_name(f"{stem}_dump.ipp")
    source_path = definition_path.with_name(f"{stem}_dump.cpp")
    generated = generate_dump_cpp(
        parsed,
        definition_path.with_suffix(".hpp").name,
        header_path.name,
        implementation_path.name,
    )
    write_generated_file(header_path, generated.header, definition_path, generated_at)
    write_generated_file(
        implementation_path, generated.implementation, definition_path, generated_at
    )
    write_generated_file(source_path, generated.source, definition_path, generated_at)
    return header_path, implementation_path, source_path


def _dump_declaration(type_name: str) -> tuple[str, str]:
    return (
        "template <class Context>",
        f"void dump(std::ostream& out, Context& ctx, const {type_name}& value, int indent = 0);",
    )


def _dump_helpers() -> str:
    return r'''namespace dump_detail {

inline void write_indent(std::ostream& out, int indent) {
    for (int index = 0; index < indent; ++index) {
        out.put(' ');
    }
}

inline void write_quoted(std::ostream& out, std::string_view value) {
    constexpr char hex[] = "0123456789abcdef";
    out.put('"');
    for (const unsigned char character : value) {
        switch (character) {
        case '"': out << "\\\""; break;
        case '\\': out << "\\\\"; break;
        case '\b': out << "\\b"; break;
        case '\f': out << "\\f"; break;
        case '\n': out << "\\n"; break;
        case '\r': out << "\\r"; break;
        case '\t': out << "\\t"; break;
        default:
            if (character < 0x20) {
                out << "\\u00" << hex[character >> 4] << hex[character & 0x0f];
            } else {
                out.put(static_cast<char>(character));
            }
        }
    }
    out.put('"');
}

template <class>
inline constexpr bool has_no_dump_value = false;

}  // namespace dump_detail

template <class Context, class Value>
inline void dump_value(std::ostream& out, Context&, const Value& value) {
    if constexpr (requires { out << value; }) {
        out << value;
    } else {
        static_assert(
            dump_detail::has_no_dump_value<Value>,
            "value is not streamable; provide a dump_value overload in its namespace");
    }
}

template <class Context>
inline void dump_value(std::ostream& out, Context&, const std::string& value) {
    dump_detail::write_quoted(out, value);
}

template <class Context>
inline void dump_value(std::ostream& out, Context&, const bool& value) {
    out << (value ? "true" : "false");
}'''


def _render_enum_dump(item: Enum) -> str:
    type_name = f"{cpp_name(item.name)}_t"
    cases = "\n".join(
        f'    case {type_name}::{value}: out << "{value}"; return;' for value in item.values
    )
    return f'''template <class Context>
inline void dump_value(std::ostream& out, Context&, const {type_name}& value) {{
    switch (value) {{
{cases}
    }}
    out << "<unknown {item.name}>";
}}

template <class Context>
inline void dump(
    std::ostream& out, Context& ctx, const {type_name}& value, int indent) {{
    dump_detail::write_indent(out, indent);
    dump_value(out, ctx, value);
    out.put('\\n');
}}'''


def _render_choice_dump(item: Choice) -> str:
    type_name = cpp_name(item.name)
    return f'''template <class Context>
inline void dump(
    std::ostream& out, Context& ctx, const {type_name}& value, int indent) {{
    std::visit(
        [&](const auto& alternative) {{ dump(out, ctx, alternative, indent); }},
        value);
}}'''


def _render_node_dump(
    item: Node,
    fields: tuple[Field, ...],
    declarations: dict[str, Node | Trait | Choice | Enum],
) -> str:
    lines = [
        "    dump_detail::write_indent(out, indent);",
        f'    out << "_type: {item.name}\\n";',
    ]
    for field in fields:
        lines.extend(_render_field_dump(field, declarations))
    body = "\n".join(lines)
    return f'''template <class Context>
inline void dump(
    std::ostream& out, Context& ctx, const {cpp_name(item.name)}& value, int indent) {{
{body}
}}'''


def _render_field_dump(
    field: Field,
    declarations: dict[str, Node | Trait | Choice | Enum],
) -> tuple[str, ...]:
    target = declarations.get(field.type_name)
    structured = isinstance(target, (Node, Choice))
    pointer = structured and not field.by_value
    optional_value = field.optional and not pointer
    access = f"value.{field.name}"
    prefix = (
        "    dump_detail::write_indent(out, indent);",
        f'    out << "{field.name}:";',
    )

    if field.multiple:
        item_dump: tuple[str, ...]
        if structured:
            target_value = "*item" if pointer else "item"
            if pointer:
                item_dump = (
                    "        if (!item) {",
                    '            out << " null\\n";',
                    "        } else {",
                    "            out.put('\\n');",
                    f"            dump(out, ctx, {target_value}, indent + 8);",
                    "        }",
                )
            else:
                item_dump = (
                    "        out.put('\\n');",
                    f"        dump(out, ctx, {target_value}, indent + 8);",
                )
        else:
            item_dump = (
                '        out.put(\' \');',
                "        dump_value(out, ctx, item);",
                "        out.put('\\n');",
            )
        return (
            *prefix,
            f"    if ({access}.empty()) {{",
            '        out << " []\\n";',
            "    } else {",
            "        out.put('\\n');",
            f"        for (const auto& item : {access}) {{",
            "            dump_detail::write_indent(out, indent + 4);",
            '            out.put(\'-\');',
            *(f"    {line}" for line in item_dump),
            "        }",
            "    }",
        )

    if structured:
        target_value = f"*{access}" if pointer or optional_value else access
        if pointer:
            return (
                *prefix,
                f"    if (!{access}) {{",
                '        out << " null\\n";',
                "    } else {",
                "        out.put('\\n');",
                f"        dump(out, ctx, {target_value}, indent + 4);",
                "    }",
            )
        if optional_value:
            return (
                *prefix,
                f"    if (!{access}) {{",
                '        out << " null\\n";',
                "    } else {",
                "        out.put('\\n');",
                f"        dump(out, ctx, {target_value}, indent + 4);",
                "    }",
            )
        return (
            *prefix,
            "    out.put('\\n');",
            f"    dump(out, ctx, {target_value}, indent + 4);",
        )

    if optional_value:
        return (
            *prefix,
            f"    if (!{access}) {{",
            '        out << " null\\n";',
            "    } else {",
            '        out.put(\' \');',
            f"        dump_value(out, ctx, *{access});",
            "        out.put('\\n');",
            "    }",
        )

    return (
        *prefix,
        '    out.put(\' \');',
        f"    dump_value(out, ctx, {access});",
        "    out.put('\\n');",
    )
