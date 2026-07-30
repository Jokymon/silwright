import re

import pytest

from silwright import (
    Choice,
    Enum,
    Field,
    Module,
    Node,
    ParsedDefinitionFile,
    SemanticError,
    Trait,
    TypeMapping,
    analyze,
    generate_cpp,
    generate_dump_cpp,
    generate_visitor_cpp,
)


def test_analysis_builds_shared_generator_metadata() -> None:
    parsed = ParsedDefinitionFile(
        Module(
            "syntax",
            (
                Trait("Location", (Field("location", "index"),)),
                Node("Leaf", (Field("value", "number"),)),
                Choice("Expr", ("Leaf", "Branch")),
                Node(
                    "Branch",
                    (Field("child", "Expr"),),
                    traits=("Location",),
                ),
            ),
        ),
        (TypeMapping("index", "std::size_t"), TypeMapping("number", "long")),
    )

    validated = analyze(parsed)

    assert tuple(validated.declarations) == ("Location", "Leaf", "Expr", "Branch")
    assert validated.mappings == {"index": "std::size_t", "number": "long"}
    assert validated.node_fields["Branch"] == (
        Field("location", "index"),
        Field("child", "Expr"),
    )
    assert tuple(item.name for item in validated.ordered_choices) == ("Expr",)
    assert validated.repeated_pointer_choices == ()
    assert {"Expr", "Leaf", "Branch"} <= validated.visitable_names


def test_all_generators_accept_one_validated_model() -> None:
    validated = analyze(
        ParsedDefinitionFile(Module("syntax", (Node("Leaf"),)), ())
    )

    assert "struct leaf" in generate_cpp(validated, "syntax.hpp").header
    assert "const leaf&" in generate_dump_cpp(
        validated, "syntax.hpp", "syntax_dump.hpp", "syntax_dump.ipp"
    ).header
    assert "void visit(leaf&" in generate_visitor_cpp(
        validated, "syntax.hpp", "syntax_visitor.hpp"
    ).header


def test_choice_allwith_traits_apply_transitively_and_are_deduplicated() -> None:
    parsed = ParsedDefinitionFile(
        Module(
            "syntax",
            (
                Trait("Location", (Field("location", "index"),)),
                Trait("Attributes", (Field("attributes", "index"),)),
                Node("Leaf", traits=("Location",)),
                Node("Other"),
                Choice("Atom", ("Leaf", "Other"), all_traits=("Location",)),
                Choice(
                    "Expr",
                    ("Atom",),
                    all_traits=("Location", "Attributes", "Attributes"),
                ),
            ),
        ),
        (TypeMapping("index", "std::size_t"),),
    )

    validated = analyze(parsed)

    assert validated.node_traits == {
        "Leaf": ("Location", "Attributes"),
        "Other": ("Location", "Attributes"),
    }
    header = generate_cpp(validated, "syntax.hpp").header
    assert "struct leaf : public location, public attributes" in header
    assert "struct other : public location, public attributes" in header


@pytest.mark.parametrize(
    ("parsed", "message"),
    (
        (
            ParsedDefinitionFile(Module("bad", (Node("Same"), Node("Same"))), ()),
            "duplicate definition: Same",
        ),
        (
            ParsedDefinitionFile(
                Module("bad", (Node("Item", (Field("field", "Missing"),)),)), ()
            ),
            "unknown field type 'Missing' in Item",
        ),
        (
            ParsedDefinitionFile(Module("bad", (Choice("Item", ("Missing",)),)), ()),
            "unknown choice alternative 'Missing' in Item",
        ),
        (
            ParsedDefinitionFile(
                Module("bad", (Node("Item"),)),
                (TypeMapping("number", "long"), TypeMapping("number", "int")),
            ),
            "duplicate C++ backend mapping: number",
        ),
        (
            ParsedDefinitionFile(Module("bad", (Enum("Op", ("Add", "Add")),)), ()),
            "duplicate enum entry 'Add' in Op",
        ),
        (
            ParsedDefinitionFile(
                Module("bad", (Node("Leaf"), Choice("Item", ("Leaf", "Leaf")))), ()
            ),
            "duplicate choice alternative 'Leaf' in Item",
        ),
        (
            ParsedDefinitionFile(
                Module(
                    "bad",
                    (
                        Node(
                            "Item",
                            (Field("values", "number", multiple=True, optional=True),),
                        ),
                    ),
                ),
                (TypeMapping("number", "long"),),
            ),
            "field 'values' in Item cannot be multiple and optional",
        ),
        (
            ParsedDefinitionFile(
                Module("bad", (Node("Item", (Field("value", "number", fixed=True),)),)),
                (TypeMapping("number", "long"),),
            ),
            "field 'value' in Item cannot be fixed without being multiple",
        ),
        (
            ParsedDefinitionFile(Module("bad-name", (Node("Item"),)), ()),
            "module generates invalid C++ identifier 'bad-name'",
        ),
        (
            ParsedDefinitionFile(Module("bad", (Node("Class"),)), ()),
            "definition 'Class' generates reserved C++ keyword 'class'",
        ),
        (
            ParsedDefinitionFile(
                Module("bad", (Node("HTTPServer"), Node("HttpServer"))), ()
            ),
            "C++ name collision: 'HTTPServer' and 'HttpServer' both generate 'http_server'",
        ),
        (
            ParsedDefinitionFile(
                Module("bad", (Enum("Op", ("Add",)), Node("OpT"))), ()
            ),
            "C++ name collision: 'Op' and 'OpT' both generate 'op_t'",
        ),
        (
            ParsedDefinitionFile(
                Module(
                    "bad",
                    (
                        Node("Leaf"),
                        Choice("Expr", ("Leaf",)),
                        Node("ExprList"),
                        Node("Block", (Field("body", "Expr", multiple=True),)),
                    ),
                ),
                (),
            ),
            "generated list alias for 'Expr' conflicts with 'ExprList' as 'expr_list'",
        ),
        (
            ParsedDefinitionFile(
                Module(
                    "bad",
                    (
                        Node("Child"),
                        Trait(
                            "Metadata",
                            (Field("child", "Child", by_value=True),),
                        ),
                    ),
                ),
                (),
            ),
            "trait field 'child' in Metadata cannot contain a node or choice by value",
        ),
        (
            ParsedDefinitionFile(
                Module("bad", (Node("Item", traits=("Missing",)),)), ()
            ),
            "unknown trait 'Missing' on Item",
        ),
        (
            ParsedDefinitionFile(
                Module("bad", (Node("Base"), Node("Item", traits=("Base",)))), ()
            ),
            "'Base' on Item is not a trait",
        ),
        (
            ParsedDefinitionFile(
                Module("bad", (Node("Item", (Field("class", "number"),)),)),
                (TypeMapping("number", "long"),),
            ),
            "field 'class' in Item generates reserved C++ keyword 'class'",
        ),
        (
            ParsedDefinitionFile(Module("namespace", (Node("Item"),)), ()),
            "module generates reserved C++ keyword 'namespace'",
        ),
    ),
)
def test_analysis_rejects_invalid_models(
    parsed: ParsedDefinitionFile, message: str
) -> None:
    with pytest.raises(SemanticError, match=re.escape(message)):
        analyze(parsed)


def test_choice_allwith_rejects_unknown_and_non_trait_names() -> None:
    with pytest.raises(SemanticError, match="unknown trait 'Missing' on Expr"):
        analyze(
            ParsedDefinitionFile(
                Module("bad", (Node("Leaf"), Choice("Expr", ("Leaf",), ("Missing",)))),
                (),
            )
        )

    with pytest.raises(SemanticError, match="'Leaf' on Expr is not a trait"):
        analyze(
            ParsedDefinitionFile(
                Module("bad", (Node("Leaf"), Choice("Expr", ("Leaf",), ("Leaf",)))),
                (),
            )
        )


def test_choice_allwith_participates_in_field_collision_validation() -> None:
    with pytest.raises(SemanticError, match="duplicate field 'location' in Leaf"):
        analyze(
            ParsedDefinitionFile(
                Module(
                    "bad",
                    (
                        Trait("Location", (Field("location", "index"),)),
                        Node("Leaf", (Field("location", "index"),)),
                        Choice("Expr", ("Leaf",), ("Location",)),
                    ),
                ),
                (TypeMapping("index", "int"),),
            )
        )
