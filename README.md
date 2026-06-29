# struct-gen

`struct-gen` parses declarative node descriptions and generates C++ data types.

## Setup

Prerequisites:

- Git
- [uv](https://docs.astral.sh/uv/)
- Python 3.14 or newer; `uv` can install the requested interpreter when necessary

Clone the repository and create the locked development environment:

```shell
uv sync
```

Run all project checks:

```shell
uv run pytest
uv run ruff check .
uv run mypy
```

The package uses a `src` layout. Runtime dependencies and development tools are declared in
`pyproject.toml`; exact resolved versions are committed in `uv.lock`. Add dependencies with
`uv add <package>` and development dependencies with `uv add --dev <package>`.

## Usage

Generate C++ from the example node definition:

```shell
uv run struct-gen examples/simple_lang.ndef
```

The command automatically loads the required `builtin.map` from the same directory, then
writes `simple_lang.hpp` and `simple_lang.cpp` beside `simple_lang.ndef`. Existing output
files with those names are replaced. Syntax errors include their source location.

Library users can call `struct_gen.parse_definition_file(path)` for the same combined lookup
behavior. `struct_gen.parse_definitions(text)` and `struct_gen.parse_type_mappings(text)` are
available when parsing already-loaded content independently.

## Definition language

One `.ndef` file describes one module. Its required first declaration is `module <name>`;
the module name is intended to become the generated C++ namespace.

```text
module expressions

node Variable
    name: identifier
end

node Number
    value: number
end

choice Expr
    Variable | Number
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
```

- `node` declares a future C++ struct. Each field is written as `<name>: <type>`.
- Prefixing a field type with `*`, as in `code: *Expr`, makes it a repeated field.
- `choice` declares a sum type. Its alternatives refer to node types or other declared types.
- Choice alternatives may span lines. The `|` separator may be placed after the preceding
  option or at the start of the following option's line.
- `enum` declares a set of new enumerator names rather than references to node types.
- `end` closes every `node`, `choice`, and `enum` declaration.
- Names currently use ASCII letters, digits, and underscores and cannot start with a digit.
- `#` starts a line comment. Blank lines are accepted around declarations; blank or
  comment-only lines inside declaration bodies are not currently supported. Horizontal
  spacing is insignificant.

Built-in field types are mapped separately in a `.map` file:

```text
identifier: std::string
number: long
```

Each mapping has a struct-gen type on the left and its C++ type spelling on the right. For a
definition such as `simple_lang.ndef`, the parser always looks for `builtin.map` in the same
directory. See `examples/simple_lang.ndef` and `examples/builtin.map` for complete examples.

## Requirements and decisions

This section is maintained as requirements are discovered or changed during development.

- The project requires Python 3.14 or newer and uses `uv` for environments, dependencies,
  locking, and command execution.
- A `.ndef` file contains exactly one module and must start with a module declaration.
- A module may contain `node`, `choice`, and `enum` declarations in source order.
- Node fields and choice alternatives reference types by name. Enums introduce values by
  name. This distinction prevents enum values from being mistaken for type references.
- Built-in types and their C++ spellings live in the required `builtin.map` file beside each
  parsed `.ndef` file.
- Generated `.hpp` and `.cpp` files use the `.ndef` basename and are written beside it. The
  module name is used directly as the C++ namespace.
- Definition names are converted from CamelCase to snake_case. Enum names additionally use
  a `_t` suffix. Enum fields are scalar; node and choice fields use `std::unique_ptr`; built-in
  fields use their mapped C++ spelling.
- Repeated fields use `std::vector` around the otherwise generated field type. For example,
  `*identifier` becomes `std::vector<std::string>` and `*Expr` becomes
  `std::vector<std::unique_ptr<expr>>`.
- Choices are `std::variant` aliases. Node structs are forward-declared before choice aliases,
  then defined afterward. Choice-to-choice dependencies are ordered, and cycles between
  choice aliases are rejected because C++ aliases cannot be forward-declared.
- Parsing currently validates syntax only. Duplicate declarations, unresolved references,
  naming rules for generated C++, mapping conflicts, and recursive type constraints remain
  future semantic-validation decisions.
- Generated headers currently include `<memory>`, `<string>`, `<variant>`, and `<vector>`. A
  future mapping format may need to carry required include information for arbitrary mapped
  C++ types.

## Version control

The repository is initialized locally. To create the first commit:

```shell
git add .
git commit -m "Initial project scaffold"
```
