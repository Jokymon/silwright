from struct_gen import (
    Choice,
    Enum,
    Field,
    Module,
    Node,
    ParsedDefinitionFile,
    Trait,
    TypeMapping,
    generate_dump_cpp,
)


def _module() -> ParsedDefinitionFile:
    return ParsedDefinitionFile(
        Module(
            "syntax",
            (
                Trait("Location", (Field("location", "identifier"),)),
                Node("Text", (Field("value", "identifier"),)),
                Choice("Expr", ("Text", "Group")),
                Enum("Kind", ("Plain", "Nested")),
                Node(
                    "Group",
                    (
                        Field("kind", "Kind"),
                        Field("label", "identifier"),
                        Field("child", "Expr"),
                        Field("items", "Expr", multiple=True),
                        Field("inline_item", "Text", by_value=True),
                        Field("optional_label", "identifier", optional=True),
                        Field("optional_item", "Text", by_value=True, optional=True),
                        Field("cache", "identifier", transient=True),
                    ),
                    traits=("Location",),
                ),
            ),
        ),
        (TypeMapping("identifier", "std::string"),),
    )


def test_dump_file_structure_and_public_declarations() -> None:
    generated = generate_dump_cpp(
        _module(), "syntax.hpp", "syntax_dump.hpp", "syntax_dump.ipp"
    )

    assert '#include "syntax.hpp"' in generated.header
    assert '#include "syntax_dump.ipp"' in generated.header
    assert "void dump_value(std::ostream& out" in generated.header
    assert "std::ostream& out, Context& ctx, const kind_t& value);" in generated.header
    assert "const group& value, int indent = 0" in generated.header
    assert generated.source == '#include "syntax_dump.hpp"\n'


def test_dump_implementation_handles_all_field_shapes() -> None:
    implementation = generate_dump_cpp(
        _module(), "syntax.hpp", "syntax_dump.hpp", "syntax_dump.ipp"
    ).implementation

    assert 'out << "_type: Group\\n";' in implementation
    assert 'out << "location:";' in implementation
    assert 'out << "kind:";' in implementation
    assert "dump_value(out, ctx, value.kind);" in implementation
    assert "if (!value.child)" in implementation
    assert "dump(out, ctx, *value.child, indent + 4);" in implementation
    assert "for (const auto& item : value.items)" in implementation
    assert "dump(out, ctx, *item, indent + 8);" in implementation
    assert "dump(out, ctx, value.inline_item, indent + 4);" in implementation
    assert 'out << " []\\n";' in implementation
    assert 'out << " null\\n";' in implementation
    assert "dump_value(out, ctx, *value.optional_label);" in implementation
    assert "dump(out, ctx, *value.optional_item, indent + 4);" in implementation
    assert "value.cache" not in implementation


def test_dump_implementation_uses_visit_enum_names_and_escaped_strings() -> None:
    implementation = generate_dump_cpp(
        _module(), "syntax.hpp", "syntax_dump.hpp", "syntax_dump.ipp"
    ).implementation

    assert "std::visit(" in implementation
    assert 'case kind_t::Plain: out << "Plain"; return;' in implementation
    assert "Context&, const kind_t& value" in implementation
    assert "out.put('\\n');" in implementation
    assert "out.put('\n');" not in implementation
    assert (
        "inline void dump_value(std::ostream& out, Context&, const Value& value)"
        in implementation
    )
    assert "if constexpr (requires { out << value; })" in implementation
    assert "value is not streamable; provide a dump_value overload" in implementation
    assert 'case \'\\n\': out << "\\\\n"; break;' in implementation
    assert 'out << (value ? "true" : "false");' in implementation
