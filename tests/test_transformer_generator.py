import pytest

from silwright import (
    Choice,
    Field,
    Module,
    Node,
    ParsedDefinitionFile,
    SemanticError,
    TypeMapping,
)
from silwright.semantic import analyze
from silwright.transformer_generator import generate_transformer_cpp


def _module() -> ParsedDefinitionFile:
    return ParsedDefinitionFile(
        Module(
            "syntax",
            (
                Node("Leaf", (Field("value", "identifier"),)),
                Node("Other", (Field("value", "identifier"),)),
                Choice("Expr", ("Leaf", "Other", "Branch")),
                Node(
                    "Branch",
                    (
                        Field("single", "Expr"),
                        Field("children", "Expr", multiple=True),
                        Field("embedded", "Leaf", by_value=True),
                        Field("tooling_child", "Other", transient=True),
                        Field("scalar", "identifier"),
                    ),
                ),
                Node("ValueOnly", (Field("child", "Leaf", by_value=True),)),
                Node("Holder", (Field("value_only", "ValueOnly", by_value=True),)),
            ),
        ),
        (TypeMapping("identifier", "std::string"),),
    )


def test_transformer_header_exposes_rewrite_and_node_hooks() -> None:
    header = generate_transformer_cpp(
        _module(), "syntax.hpp", "syntax_transformer.hpp"
    ).header

    assert "class transformer" in header
    assert "virtual ~transformer() = default;" in header
    assert "expr_list rewrite(std::unique_ptr<expr> node);" in header
    assert "expr_list rewrite(std::unique_ptr<leaf> node);" in header
    assert "expr_list rewrite(std::unique_ptr<branch> node);" in header
    assert "virtual expr_list visit_multiple(leaf& value);" in header
    assert "virtual expr_list visit_multiple(branch& value);" in header
    assert "visit_multiple(expr& value)" not in header
    assert "rewrite_children(expr& value)" not in header
    assert "value_only" not in header


def test_transformer_source_dispatches_choices_and_rewrites_children() -> None:
    source = generate_transformer_cpp(
        _module(), "syntax.hpp", "syntax_transformer.hpp"
    ).source

    assert "#include <cassert>" in source
    assert "#include <type_traits>" in source
    assert "return std::visit([this] (auto& alternative) -> expr_list {" in source
    assert "using alternative_type = std::decay_t<decltype(alternative)>;" in source
    assert "auto replacements = rewrite(" in source
    assert "std::make_unique<alternative_type>(std::move(alternative)))" in source
    assert "result.push_back(std::move(replacement));" in source
    assert "std::make_unique<expr>(std::move(value))" in source
    assert "if (!node) {\n        return {};" in source
    assert "auto replacement_single = rewrite(std::move(value.single));" in source
    assert "assert(replacement_single.size() <= 1);" in source
    assert "value.single = nullptr;" in source
    assert "expr_list replacement_children;" in source
    assert "replacement_children.push_back(std::move(replacement));" in source
    assert "value.children = std::move(replacement_children);" in source
    assert "value.embedded" not in source
    assert "value.tooling_child" not in source
    assert "value.scalar" not in source


def test_transformer_generates_single_hooks_when_no_multiple_context_exists() -> None:
    parsed = ParsedDefinitionFile(
        Module(
            "syntax",
            (
                Node("Leaf", (Field("value", "identifier"),)),
                Choice("Expr", ("Leaf",)),
                Node("Root", (Field("child", "Expr"),)),
            ),
        ),
        (TypeMapping("identifier", "std::string"),),
    )

    generated = generate_transformer_cpp(
        parsed, "syntax.hpp", "syntax_transformer.hpp"
    )

    assert "std::unique_ptr<expr> rewrite(std::unique_ptr<expr> node);" in generated.header
    assert "virtual std::unique_ptr<expr> visit_single(leaf& value);" in generated.header
    assert "auto replacement = rewrite(" in generated.source
    assert "return std::move(replacement);" in generated.source
    assert "return std::make_unique<expr>(std::move(value));" in generated.source


def test_transformer_spells_vector_for_multiple_choice_without_list_alias() -> None:
    parsed = ParsedDefinitionFile(
        Module(
            "syntax",
            (
                Node("Leaf", (Field("value", "identifier"),)),
                Choice("Inner", ("Leaf",)),
                Choice("Outer", ("Inner",)),
                Node("Root", (Field("children", "Inner", multiple=True),)),
            ),
        ),
        (TypeMapping("identifier", "std::string"),),
    )

    generated = generate_transformer_cpp(
        parsed, "syntax.hpp", "syntax_transformer.hpp"
    )

    assert "inner_list rewrite(std::unique_ptr<inner> node);" in generated.header
    assert (
        "std::vector<std::unique_ptr<outer>> rewrite(std::unique_ptr<outer> node);"
        in generated.header
    )
    assert "outer_list" not in generated.header


def test_transformer_name_conflict_is_rejected() -> None:
    parsed = ParsedDefinitionFile(Module("bad", (Node("Transformer"),)), ())

    with pytest.raises(SemanticError, match="conflicts with generated transformer"):
        analyze(parsed)


def test_transformer_rejects_ambiguous_choice_return_type() -> None:
    parsed = ParsedDefinitionFile(
        Module(
            "bad",
            (
                Node("Leaf"),
                Choice("First", ("Leaf",)),
                Choice("Second", ("Leaf",)),
            ),
        ),
        (),
    )

    with pytest.raises(SemanticError, match="multiple transformable choices"):
        analyze(parsed)


def test_transformer_rejects_direct_field_for_choice_returning_node() -> None:
    parsed = ParsedDefinitionFile(
        Module(
            "bad",
            (
                Node("Leaf"),
                Choice("Expr", ("Leaf",)),
                Node("Root", (Field("leaf", "Leaf"),)),
            ),
        ),
        (),
    )

    with pytest.raises(SemanticError, match="references node 'Leaf' directly"):
        analyze(parsed)
