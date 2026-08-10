from pathlib import Path

import pytest

from silwright import (
    Choice,
    Enum,
    Field,
    GenerationError,
    Module,
    Node,
    ParsedDefinitionFile,
    Trait,
    TypeMapping,
    cpp_name,
    generate_cpp,
)
from silwright.generator import generate_cpp_files


def _expressions() -> ParsedDefinitionFile:
    return ParsedDefinitionFile(
        module=Module(
            "expressions",
            (
                Node("Variable", (Field("name", "identifier"),)),
                Node("Number", (Field("value", "number"),)),
                Choice("Expr", ("Variable", "Number", "BinaryExpression")),
                Enum("Op", ("Add", "Subtract", "Multiply", "Divide", "Modulus")),
                Node(
                    "BinaryExpression",
                    (Field("op", "Op"), Field("left", "Expr"), Field("right", "Expr")),
                ),
                Node(
                    "FunctionDefinition",
                    (
                        Field("names", "identifier", multiple=True),
                        Field("code", "Expr", multiple=True),
                    ),
                ),
            ),
        ),
        type_mappings=(TypeMapping("identifier", "std::string"), TypeMapping("number", "long")),
    )


@pytest.mark.parametrize(
    ("source", "expected"),
    [("Op", "op"), ("BinaryExpression", "binary_expression"), ("HTTPServer", "http_server")],
)
def test_cpp_name(source: str, expected: str) -> None:
    assert cpp_name(source) == expected


def test_generate_cpp() -> None:
    generated = generate_cpp(_expressions(), "expressions.hpp")

    assert "namespace expressions {" in generated.header
    assert "enum class op_t {" in generated.header
    assert "struct binary_expression;" in generated.header
    assert (
        "using expr = std::variant<variable, number, binary_expression>;" in generated.header
    )
    assert "std::string name;" in generated.header
    assert "long value;" in generated.header
    assert "op_t op;" in generated.header
    assert "std::unique_ptr<expr> left;" in generated.header
    assert "std::vector<std::string> names;" in generated.header
    assert "expr_list code;" in generated.header
    assert "#include <vector>" in generated.header
    assert generated.source == '#include "expressions.hpp"\n'


def test_generate_cpp_separates_struct_definitions_with_empty_line() -> None:
    parsed = ParsedDefinitionFile(
        Module("example", (Node("First"), Node("Second"), Node("Third"))),
        (),
    )

    header = generate_cpp(parsed, "example.hpp").header

    assert "struct first {\n\n};\n\nstruct second {\n\n};\n\nstruct third {" in header


def test_generate_cpp_adds_list_alias_for_repeated_pointer_choice() -> None:
    parsed = ParsedDefinitionFile(
        Module(
            "example",
            (
                Node("Leaf"),
                Choice("Expr", ("Leaf",)),
                Node(
                    "Block",
                    (
                        Field("body", "Expr", multiple=True),
                        Field("fallback", "Expr", multiple=True),
                    ),
                ),
            ),
        ),
        (),
    )

    header = generate_cpp(parsed, "example.hpp").header

    assert header.count(
        "using expr_list = std::vector<std::unique_ptr<expr>>;"
    ) == 1
    assert "expr_list body;" in header


def test_generate_cpp_omits_list_alias_for_repeated_value_choice() -> None:
    parsed = ParsedDefinitionFile(
        Module(
            "example",
            (
                Node("Leaf"),
                Choice("Expr", ("Leaf",)),
                Node("Block", (Field("body", "Expr", multiple=True, by_value=True),)),
            ),
        ),
        (),
    )

    header = generate_cpp(parsed, "example.hpp").header

    assert "using expr_list" not in header


def test_generate_cpp_emits_deduplicated_backend_includes() -> None:
    parsed = ParsedDefinitionFile(
        Module("example", (Node("Value", (Field("value", "index"),)),)),
        (TypeMapping("index", "std::size_t"),),
        backend_includes=("<cstddef>", '"project/types.hpp"', "<cstddef>", "<vector>"),
    )

    header = generate_cpp(parsed, "example.hpp").header

    assert header.count("#include <cstddef>") == 1
    assert header.count("#include <vector>") == 1
    assert '#include "project/types.hpp"' in header


def test_generate_cpp_files_uses_definition_basename(tmp_path: Path) -> None:
    definition = tmp_path / "syntax.ndef"
    definition.write_text("module syntax\nnode Value\n    value: number\nend\n")
    (tmp_path / "backend_cpp.map").write_text("number: long\n")

    header, source = generate_cpp_files(definition)

    assert header == tmp_path / "syntax.hpp"
    assert source == tmp_path / "syntax.cpp"
    banner = (
        "// Source: syntax.ndef\n"
        "// Do not modify this file directly; regenerate it from the source definition.\n"
    )
    header_text = header.read_text()
    source_text = source.read_text()
    assert header_text.startswith("// This file was generated by Silwright")
    assert banner in header_text
    assert "// Generated:" not in header_text
    assert "namespace syntax" in header_text
    assert source_text.startswith("// This file was generated by Silwright")
    assert banner in source_text
    assert source_text.endswith('#include "syntax.hpp"\n')


def test_unknown_field_type_is_rejected() -> None:
    parsed = ParsedDefinitionFile(Module("bad", (Node("Value", (Field("x", "Missing"),)),)), ())

    with pytest.raises(GenerationError, match="unknown field type"):
        generate_cpp(parsed, "bad.hpp")


def test_cyclic_choice_dependencies_are_rejected() -> None:
    parsed = ParsedDefinitionFile(
        Module("bad", (Choice("First", ("Second",)), Choice("Second", ("First",)))), ()
    )

    with pytest.raises(GenerationError, match="cyclic choice dependency"):
        generate_cpp(parsed, "bad.hpp")


def test_value_fields_are_embedded_and_dependency_ordered() -> None:
    parsed = ParsedDefinitionFile(
        Module(
            "functions",
            (
                Node(
                    "FunctionDefinition",
                    (
                        Field("head", "FunctionHead", by_value=True),
                        Field("parameters", "Parameter", multiple=True, by_value=True),
                    ),
                ),
                Node("FunctionHead", (Field("name", "identifier"),)),
                Node("Parameter", (Field("name", "identifier"),)),
            ),
        ),
        (TypeMapping("identifier", "std::string"),),
    )

    header = generate_cpp(parsed, "functions.hpp").header

    assert "function_head head;" in header
    assert "std::vector<parameter> parameters;" in header
    assert header.index("struct function_head {") < header.index("struct function_definition {")
    assert header.index("struct parameter {") < header.index("struct function_definition {")


def test_recursive_value_fields_are_rejected() -> None:
    parsed = ParsedDefinitionFile(
        Module(
            "bad",
            (
                Node("First", (Field("second", "Second", by_value=True),)),
                Node("Second", (Field("first", "First", by_value=True),)),
            ),
        ),
        (),
    )

    with pytest.raises(GenerationError, match="cyclic value dependency"):
        generate_cpp(parsed, "bad.hpp")


def test_optional_fields_use_optional_except_for_owned_node_pointers() -> None:
    parsed = ParsedDefinitionFile(
        Module(
            "optional_fields",
            (
                Enum("Kind", ("One", "Two")),
                Node("Child"),
                Node(
                    "Parent",
                    (
                        Field("name", "identifier", optional=True),
                        Field("kind", "Kind", optional=True),
                        Field("embedded", "Child", by_value=True, optional=True),
                        Field("pointer", "Child", optional=True),
                    ),
                ),
            ),
        ),
        (TypeMapping("identifier", "std::string"),),
    )

    header = generate_cpp(parsed, "optional_fields.hpp").header

    assert "#include <optional>" in header
    assert "std::optional<std::string> name;" in header
    assert "std::optional<kind_t> kind;" in header
    assert "std::optional<child> embedded;" in header
    assert "std::unique_ptr<child> pointer;" in header


def test_traits_generate_bases_and_inherited_fields() -> None:
    parsed = ParsedDefinitionFile(
        Module(
            "example",
            (
                Trait("Location", (Field("location", "source_range"),)),
                Node(
                    "FunctionHead",
                    (Field("name", "identifier"),),
                    traits=("Location",),
                ),
            ),
        ),
        (
            TypeMapping("source_range", "project::source_range"),
            TypeMapping("identifier", "std::string"),
        ),
    )

    header = generate_cpp(parsed, "example.hpp").header

    assert "struct location {\n    project::source_range location;\n};" in header
    assert "struct function_head : public location {" in header
    assert "std::string name;" in header
    assert header.count("project::source_range location;") == 1


def test_allwith_generates_recursive_mutable_and_const_trait_accessors() -> None:
    parsed = ParsedDefinitionFile(
        Module(
            "example",
            (
                Trait("Location", (Field("location", "source_range"),)),
                Node("Leaf"),
                Choice("Primary", ("Leaf",)),
                Choice("Expr", ("Primary",), all_traits=("Location",)),
            ),
        ),
        (TypeMapping("source_range", "int"),),
    )

    header = generate_cpp(parsed, "example.hpp").header

    assert "Trait& as_trait(std::variant<Alternatives...>& value)" in header
    assert "const Trait& as_trait(const std::variant<Alternatives...>& value)" in header
    assert "return as_trait_impl<Trait>(alternative);" in header
    assert "static_cast" not in header
    assert header.count("    return value;") == 2
    assert header.index("using expr =") < header.index("Trait& as_trait(")


def test_trait_accessor_is_omitted_without_allwith() -> None:
    parsed = ParsedDefinitionFile(
        Module("example", (Node("Leaf"), Choice("Expr", ("Leaf",)))), ()
    )

    assert "as_trait" not in generate_cpp(parsed, "example.hpp").header


def test_as_trait_name_is_reserved() -> None:
    parsed = ParsedDefinitionFile(Module("bad", (Node("AsTrait"),)), ())

    with pytest.raises(GenerationError, match="conflicts with generated trait accessor"):
        generate_cpp(parsed, "bad.hpp")


def test_trait_field_collisions_are_rejected() -> None:
    parsed = ParsedDefinitionFile(
        Module(
            "bad",
            (
                Trait("Location", (Field("location", "source_range"),)),
                Node(
                    "Item",
                    (Field("location", "source_range"),),
                    traits=("Location",),
                ),
            ),
        ),
        (TypeMapping("source_range", "int"),),
    )

    with pytest.raises(GenerationError, match="duplicate field 'location' in Item"):
        generate_cpp(parsed, "bad.hpp")


def test_traits_cannot_be_choice_alternatives() -> None:
    parsed = ParsedDefinitionFile(
        Module("bad", (Trait("Location"), Choice("Item", ("Location",)))), ()
    )

    with pytest.raises(
        GenerationError, match="trait 'Location' cannot be a choice alternative"
    ):
        generate_cpp(parsed, "bad.hpp")


def test_transient_fields_are_still_generated() -> None:
    parsed = ParsedDefinitionFile(
        Module(
            "example",
            (
                Node(
                    "FunctionDefinition",
                    (Field("function_scope", "scope", transient=True),),
                ),
            ),
        ),
        (TypeMapping("scope", "std::unique_ptr<scope>"),),
    )

    header = generate_cpp(parsed, "example.hpp").header

    assert "std::unique_ptr<scope> function_scope;" in header
