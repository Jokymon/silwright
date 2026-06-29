from pathlib import Path

import pytest

from struct_gen import (
    Choice,
    Enum,
    Field,
    GenerationError,
    Module,
    Node,
    ParsedDefinitionFile,
    TypeMapping,
    cpp_name,
    generate_cpp,
)
from struct_gen.generator import generate_cpp_files


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
    assert generated.source == '#include "expressions.hpp"\n'


def test_generate_cpp_files_uses_definition_basename(tmp_path: Path) -> None:
    definition = tmp_path / "syntax.ndef"
    definition.write_text("module syntax\nnode Value\n    value: number\nend\n")
    (tmp_path / "builtin.map").write_text("number: long\n")

    header, source = generate_cpp_files(definition)

    assert header == tmp_path / "syntax.hpp"
    assert source == tmp_path / "syntax.cpp"
    assert "namespace syntax" in header.read_text()
    assert source.read_text() == '#include "syntax.hpp"\n'


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
