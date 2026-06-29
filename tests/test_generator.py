from struct_gen import Field, Node, generate_header


def test_generate_header() -> None:
    node = Node(
        name="BinaryExpression",
        fields=(
            Field(name="left", cpp_type="Node*"),
            Field(name="right", cpp_type="Node*"),
        ),
    )

    assert generate_header(node) == (
        "#pragma once\n\n"
        "struct BinaryExpression {\n"
        "    Node* left;\n"
        "    Node* right;\n"
        "};\n"
    )

