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

The command automatically loads the required `backend_cpp.map` from the same directory, then
writes the model `.hpp`/`.cpp`, dump `_dump.hpp`/`_dump.ipp`/`_dump.cpp`, and visitor
`_visitor.hpp`/`_visitor.cpp` files beside `simple_lang.ndef`. Existing generated output files
are replaced. Syntax errors include their source location.

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
    head: value FunctionHead
    code: *Expr
end
```

- `node` declares a future C++ struct. Each field is written as `<name>: <type>`.
- Prefixing a field type with `*`, as in `code: *Expr`, makes it a repeated field.
- Prefixing a field type with `?`, as in `label: ?identifier`, makes it optional. Built-in,
  enum, and `value` fields use `std::optional`; pointer-backed node and choice fields remain
  `std::unique_ptr` because they already represent absence. `*` and `?` cannot be combined.
- Prefixing a field type with `value`, as in `head: value FunctionHead`, embeds node or choice
  types directly instead of using `std::unique_ptr`. The modifiers compose as
  `parameters: *value Parameter` for `std::vector<parameter>`.
- `choice` declares a sum type. Its alternatives refer to node types or other declared types.
- Choice alternatives may span lines. The `|` separator may be placed after the preceding
  option or at the start of the following option's line, and these layouts may be mixed within
  one choice definition.
- `enum` declares a set of new enumerator names rather than references to node types.
- Enum entries support the same inline, multiline, and mixed `|` layouts as choice alternatives.
- `end` closes every `node`, `choice`, and `enum` declaration.
- Names currently use ASCII letters, digits, and underscores and cannot start with a digit.
- `//` starts a comment that continues to the end of the line. Comments may occupy a complete
  line or follow regular definition code. Multiline comments are not supported. Blank lines
  are accepted around declarations; blank lines inside declaration bodies are not currently
  supported. Horizontal spacing is insignificant.

C++ backend types are mapped separately in `backend_cpp.map`:

```text
@include <cstddef>
@include "project/symbol.hpp"

identifier: std::string
number: long
index: std::size_t
type: project::type_id
```

Each mapping has a struct-gen type on the left and its C++ type spelling on the right.
`@include` accepts either a system header in `<...>` or a project header in `"..."`; these
headers are deduplicated and emitted into the generated model header. For a definition such
as `simple_lang.ndef`, the parser always looks for `backend_cpp.map` in the same directory.
See `examples/simple_lang.ndef` and `examples/backend_cpp.map` for complete examples.

## End-to-end C++ example

`examples/simple_lang_main.cpp` constructs a function definition containing several expression
nodes and writes its YAML-like dump to `std::cout`. `examples/CMakeLists.txt` defines the
`simple_lang_example` C++20 executable from the sample and generated translation units. The
example files are currently provided as a proof of concept; automated C++ compilation is not
yet part of the project checks.

## Requirements and decisions

This section is maintained as requirements are discovered or changed during development.

- The project requires Python 3.14 or newer and uses `uv` for environments, dependencies,
  locking, and command execution.
- A `.ndef` file contains exactly one module and must start with a module declaration.
- `.ndef` comments start with `//` and continue through the end of the current line; there is
  no multiline comment syntax.
- A module may contain `node`, `choice`, and `enum` declarations in source order.
- Node fields and choice alternatives reference types by name. Enums introduce values by
  name. This distinction prevents enum values from being mistaken for type references.
- Backend types and their C++ spellings live in the required `backend_cpp.map` file beside
  each parsed `.ndef` file. C++ is currently selected statically; no dynamic backend selection
  is supported yet.
- `backend_cpp.map` may declare generated model-header dependencies with `@include <header>`
  and `@include "header"`. Includes preserve declaration order and duplicates are removed.
- Generated `.hpp` and `.cpp` files use the `.ndef` basename and are written beside it. The
  module name is used directly as the C++ namespace.
- Definition names are converted from CamelCase to snake_case. Enum names additionally use
  a `_t` suffix. Enum fields are scalar; node and choice fields use `std::unique_ptr`; built-in
  fields use their mapped C++ spelling.
- Repeated fields use `std::vector` around the otherwise generated field type. For example,
  `*identifier` becomes `std::vector<std::string>` and `*Expr` becomes
  `std::vector<std::unique_ptr<expr>>`.
- Optional fields use `std::optional` around the otherwise generated value type. Missing
  optional values and null node pointers are both emitted as `null` by generated dumpers.
- Value fields require complete C++ types. The generator dependency-orders affected structs
  and rejects recursive value-member cycles. Built-in and enum fields are already values, so
  applying `value` to them has no additional effect.
- Choices are `std::variant` aliases. Node structs are forward-declared before choice aliases,
  then defined afterward. Choice-to-choice dependencies are ordered, and cycles between
  choice aliases are rejected because C++ aliases cannot be forward-declared.
- Parsing currently validates syntax only. Duplicate declarations, unresolved references,
  naming rules for generated C++, mapping conflicts, and recursive type constraints remain
  future semantic-validation decisions.
- Generated headers currently include `<memory>`, `<optional>`, `<string>`, `<variant>`, and
  `<vector>`, plus dependencies declared by the backend map.
- Dump support is generated separately as `_dump.hpp`, `_dump.ipp`, and `_dump.cpp`. The IPP
  contains template implementations and is included at the end of the dump header.
- Generated `dump` overloads emit YAML-like objects with four-space nesting, an artificial
  `_type` field, `.ndef` field names, lists for repeated fields, and `null` for null pointers.
  Strings are quoted and escaped, and enums use their original `.ndef` entry names.
- Scalar values pass through an inline generic `dump_value` customization point. Its default
  uses `operator<<`; context-sensitive custom types can provide a more-specific overload in
  the value type's namespace so it is found through argument-dependent lookup. A mapped type
  that is neither streamable nor customized produces a targeted compile-time diagnostic.
- Mutable visitor support is generated as `_visitor.hpp` and `_visitor.cpp`. Public `visit`
  overloads accept every node and choice as an entry point. Node traversal calls protected
  virtual `enter` and `leave` hooks around pointer-backed children; scalars and `value` fields
  are deliberately skipped. Definitions referenced exclusively through `value` fields are
  omitted from the visitor API, while unreferenced definitions remain possible entry points.
  Derived visitors can override only the hooks they need.

## Version control

The repository is initialized locally. To create the first commit:

```shell
git add .
git commit -m "Initial project scaffold"
```
