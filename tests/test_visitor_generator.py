import pytest

from struct_gen import (
    Choice,
    Field,
    GenerationError,
    Module,
    Node,
    ParsedDefinitionFile,
    TypeMapping,
    generate_visitor_cpp,
)


def _module() -> ParsedDefinitionFile:
    return ParsedDefinitionFile(
        Module(
            "syntax",
            (
                Node("Leaf", (Field("value", "identifier"),)),
                Choice("Expr", ("Leaf", "Branch")),
                Node(
                    "Branch",
                    (
                        Field("single", "Expr"),
                        Field("children", "Expr", multiple=True),
                        Field("embedded", "Leaf", by_value=True),
                        Field("metadata", "Metadata", by_value=True),
                        Field("projection", "PlaceElem", by_value=True),
                        Field("tooling_child", "ToolingNode", transient=True),
                        Field("scalar", "identifier"),
                    ),
                ),
                Node("Metadata", (Field("label", "identifier"),)),
                Node("Deref"),
                Node("Field"),
                Choice("PlaceElem", ("Deref", "Field")),
                Node("ToolingNode"),
            ),
        ),
        (TypeMapping("identifier", "std::string"),),
    )


def test_visitor_header_exposes_mutable_visits_and_hooks() -> None:
    header = generate_visitor_cpp(_module(), "syntax.hpp", "syntax_visitor.hpp").header

    assert '#include "syntax.hpp"' in header
    assert "class visitor" in header
    assert "virtual ~visitor() = default;" in header
    assert "void visit(expr& value);" in header
    assert "void visit(branch& value);" in header
    assert "virtual void enter(branch& value);" in header
    assert "virtual void leave(branch& value);" in header
    assert "metadata&" not in header
    assert "place_elem&" not in header
    assert "deref&" not in header
    assert "field&" not in header
    assert "tooling_node&" not in header


def test_visitor_source_dispatches_choices_and_traverses_pointer_children() -> None:
    source = generate_visitor_cpp(_module(), "syntax.hpp", "syntax_visitor.hpp").source

    assert "std::visit([this](auto& alternative) { visit(alternative); }, value);" in source
    assert "enter(value);" in source
    assert "if (value.single)" in source
    assert "visit(*value.single);" in source
    assert "for (auto& child : value.children)" in source
    assert "visit(*child);" in source
    assert "value.embedded" not in source
    assert "value.metadata" not in source
    assert "value.projection" not in source
    assert "value.tooling_child" not in source
    assert "value.scalar" not in source
    branch_visit = source[source.index("void visitor::visit(branch& value)") :]
    assert branch_visit.index("enter(value);") < branch_visit.index("visit(*value.single);")
    assert branch_visit.index("visit(*value.single);") < branch_visit.index("leave(value);")


def test_visitor_name_conflict_is_rejected() -> None:
    parsed = ParsedDefinitionFile(Module("syntax", (Node("Visitor"),)), ())

    with pytest.raises(GenerationError, match="conflicts with generated visitor"):
        generate_visitor_cpp(parsed, "syntax.hpp", "syntax_visitor.hpp")


def test_unreferenced_node_remains_a_visitor_entry_point() -> None:
    parsed = ParsedDefinitionFile(Module("syntax", (Node("Root"),)), ())

    header = generate_visitor_cpp(parsed, "syntax.hpp", "syntax_visitor.hpp").header

    assert "void visit(root& value);" in header
