import pytest
from lark.exceptions import UnexpectedInput

from struct_gen import (
    Choice,
    Enum,
    Field,
    Module,
    Node,
    ParsedDefinitionFile,
    TypeMapping,
    parse_definition_file,
    parse_definitions,
    parse_type_mappings,
)


def test_parse_complete_module() -> None:
    source = """\
module expressions

node Variable
    name : identifier
end

node Number
    value : number
end

choice Expr
    Variable | Number | BinaryExpression
end

enum Op
    Add | Subtract | Multiply | Divide | Modulus
end

node BinaryExpression
    op: Op
    left: Expr
    right: Expr
end

node FunctionDefinition
    code: *Expr
end
"""

    assert parse_definitions(source) == Module(
        name="expressions",
        definitions=(
            Node(name="Variable", fields=(Field("name", "identifier"),)),
            Node(name="Number", fields=(Field("value", "number"),)),
            Choice("Expr", ("Variable", "Number", "BinaryExpression")),
            Enum("Op", ("Add", "Subtract", "Multiply", "Divide", "Modulus")),
            Node(
                name="BinaryExpression",
                fields=(Field("op", "Op"), Field("left", "Expr"), Field("right", "Expr")),
            ),
            Node(name="FunctionDefinition", fields=(Field("code", "Expr", multiple=True),)),
        ),
    )


def test_parse_type_mappings() -> None:
    assert parse_type_mappings("identifier : std::string\nnumber: long\n") == (
        TypeMapping("identifier", "std::string"),
        TypeMapping("number", "long"),
    )


def test_comments_and_blank_lines_between_declarations_are_ignored() -> None:
    source = """\
# Module comment
module example

node Empty
end
"""

    assert parse_definitions(source) == Module("example", (Node("Empty"),))


def test_module_declaration_is_required() -> None:
    with pytest.raises(UnexpectedInput):
        parse_definitions("node Variable\nend\n")


def test_unclosed_definition_is_rejected() -> None:
    with pytest.raises(UnexpectedInput):
        parse_definitions("module example\nnode Variable\n    name: identifier\n")


def test_parse_definition_file_loads_sibling_builtin_map(tmp_path) -> None:
    definition_path = tmp_path / "example.ndef"
    definition_path.write_text("module example\nnode Value\n    value: number\nend\n")
    (tmp_path / "builtin.map").write_text("number: long\n")

    assert parse_definition_file(definition_path) == ParsedDefinitionFile(
        module=Module("example", (Node("Value", (Field("value", "number"),)),)),
        type_mappings=(TypeMapping("number", "long"),),
    )


def test_parse_definition_file_requires_sibling_builtin_map(tmp_path) -> None:
    definition_path = tmp_path / "example.ndef"
    definition_path.write_text("module example\n")

    with pytest.raises(FileNotFoundError, match=r"builtin\.map"):
        parse_definition_file(definition_path)
