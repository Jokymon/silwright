import pytest
from lark.exceptions import UnexpectedInput

from struct_gen import (
    Choice,
    CppBackendConfig,
    Enum,
    Field,
    Module,
    Node,
    ParsedDefinitionFile,
    Trait,
    TypeMapping,
    parse_cpp_backend_config,
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


def test_parse_cpp_backend_includes_and_mappings() -> None:
    source = """\
@include <cstddef>
@include "project/symbol.hpp"
index: std::size_t
type: project::type_id
"""

    assert parse_cpp_backend_config(source) == CppBackendConfig(
        type_mappings=(
            TypeMapping("index", "std::size_t"),
            TypeMapping("type", "project::type_id"),
        ),
        includes=("<cstddef>", '"project/symbol.hpp"'),
    )


@pytest.mark.parametrize(
    "options",
    (
        "Variable | Number | BinaryExpression",
        "Variable\n    | Number\n    | BinaryExpression",
        "Variable |\n    Number |\n    BinaryExpression",
        "Variable | Number |\n    BinaryExpression",
        "Variable | Number\n    | BinaryExpression",
    ),
)
def test_choice_options_allow_flexible_line_breaks(options: str) -> None:
    source = f"module example\nchoice Expr\n    {options}\nend\n"

    assert parse_definitions(source) == Module(
        "example", (Choice("Expr", ("Variable", "Number", "BinaryExpression")),)
    )


def test_choice_rejects_separator_without_following_option() -> None:
    with pytest.raises(UnexpectedInput):
        parse_definitions("module example\nchoice Expr\n    Variable |\nend\n")


def test_enum_options_allow_mixed_multiline_layout() -> None:
    source = """\
module example
enum BinaryOp
    Multiply | Division | Modulus | Plus | Minus
    | Equals | NotEquals | LessThan | LessThanEqual | GreaterThan | GreaterThanEqual
    | AndOp | OrOp | Shl | Shr
end
"""

    assert parse_definitions(source) == Module(
        "example",
        (
            Enum(
                "BinaryOp",
                (
                    "Multiply",
                    "Division",
                    "Modulus",
                    "Plus",
                    "Minus",
                    "Equals",
                    "NotEquals",
                    "LessThan",
                    "LessThanEqual",
                    "GreaterThan",
                    "GreaterThanEqual",
                    "AndOp",
                    "OrOp",
                    "Shl",
                    "Shr",
                ),
            ),
        ),
    )


def test_value_modifier_parses_for_single_and_repeated_fields() -> None:
    source = """\
module example
node Function
    head: value FunctionHead
    parameters: *value Parameter
end
"""

    assert parse_definitions(source) == Module(
        "example",
        (
            Node(
                "Function",
                (
                    Field("head", "FunctionHead", by_value=True),
                    Field("parameters", "Parameter", multiple=True, by_value=True),
                ),
            ),
        ),
    )


def test_value_remains_valid_as_a_field_name() -> None:
    source = "module example\nnode Number\n    value: number\nend\n"

    assert parse_definitions(source) == Module(
        "example", (Node("Number", (Field("value", "number"),)),)
    )


def test_optional_modifier_parses_for_builtin_and_value_fields() -> None:
    source = """\
module example
node Item
    label: ?identifier
    metadata: ?value Metadata
    child: ?Child
end
"""

    assert parse_definitions(source) == Module(
        "example",
        (
            Node(
                "Item",
                (
                    Field("label", "identifier", optional=True),
                    Field("metadata", "Metadata", by_value=True, optional=True),
                    Field("child", "Child", optional=True),
                ),
            ),
        ),
    )


def test_multiple_and_optional_modifiers_cannot_be_combined() -> None:
    with pytest.raises(UnexpectedInput):
        parse_definitions("module example\nnode Item\n    values: *?identifier\nend\n")


def test_traits_and_node_trait_lists_are_parsed() -> None:
    source = """\
module example
trait Location
    location: source_range
end
trait Documented
    documentation: identifier
end
node FunctionHead with Location, Documented
    name: identifier
end
"""

    assert parse_definitions(source) == Module(
        "example",
        (
            Trait("Location", (Field("location", "source_range"),)),
            Trait("Documented", (Field("documentation", "identifier"),)),
            Node(
                "FunctionHead",
                (Field("name", "identifier"),),
                traits=("Location", "Documented"),
            ),
        ),
    )


def test_transient_field_modifier_is_parsed() -> None:
    source = """\
module example
node FunctionDefinition
    function_scope: transient scope
end
"""

    assert parse_definitions(source) == Module(
        "example",
        (
            Node(
                "FunctionDefinition",
                (Field("function_scope", "scope", transient=True),),
            ),
        ),
    )


def test_comments_and_blank_lines_between_declarations_are_ignored() -> None:
    source = """\
// Module comment
module example // trailing module comment

node Empty
end
"""

    assert parse_definitions(source) == Module("example", (Node("Empty"),))


def test_comments_are_allowed_on_any_definition_line() -> None:
    source = """\
module example
node Number // declaration comment
    // Comment-only lines inside a definition are ignored.
    value: number // field comment
    // Another comment before the terminator.
end // terminator comment
"""

    assert parse_definitions(source) == Module(
        "example", (Node("Number", (Field("value", "number"),)),)
    )


def test_module_declaration_is_required() -> None:
    with pytest.raises(UnexpectedInput):
        parse_definitions("node Variable\nend\n")


def test_unclosed_definition_is_rejected() -> None:
    with pytest.raises(UnexpectedInput):
        parse_definitions("module example\nnode Variable\n    name: identifier\n")


def test_parse_definition_file_loads_sibling_cpp_backend_map(tmp_path) -> None:
    definition_path = tmp_path / "example.ndef"
    definition_path.write_text("module example\nnode Value\n    value: number\nend\n")
    (tmp_path / "backend_cpp.map").write_text(
        '@include <cstdint>\n@include "types.hpp"\nnumber: long\n'
    )

    assert parse_definition_file(definition_path) == ParsedDefinitionFile(
        module=Module("example", (Node("Value", (Field("value", "number"),)),)),
        type_mappings=(TypeMapping("number", "long"),),
        backend_includes=("<cstdint>", '"types.hpp"'),
    )


def test_parse_definition_file_requires_sibling_cpp_backend_map(tmp_path) -> None:
    definition_path = tmp_path / "example.ndef"
    definition_path.write_text("module example\n")

    with pytest.raises(FileNotFoundError, match=r"backend_cpp\.map"):
        parse_definition_file(definition_path)
