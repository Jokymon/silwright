# NDEF language reference

This document describes the currently supported NDEF language and C++ backend-map contract.
It records existing behavior; incompatible extensions require an explicit design decision.

## Files and lookup

- A node-definition file uses the `.ndef` suffix.
- One `.ndef` file contains exactly one module.
- C++ generation requires `backend_cpp.map` in the same directory as the `.ndef` file.
- Backend selection and the backend-map filename are currently fixed.
- Generated files use the `.ndef` basename and are written beside it.

## Lexical rules

Names use ASCII letters, digits, and underscores and cannot begin with a digit:

```text
[A-Za-z_][A-Za-z0-9_]*
```

NDEF comments begin with `//` and continue through the end of the line. Multiline comments do
not exist. Horizontal whitespace is insignificant. Blank lines are supported around
declarations; blank lines inside declaration bodies are currently not supported. Comment-only
lines are allowed inside bodies.

The language keywords are:

```text
module node trait choice enum end with value transient fixed
```

`*`, `?`, `:`, `|`, and `,` are syntax operators or separators. Keywords are contextual in
some name positions—`value`, for example, remains a legal field name—but keyword names should
not be used as referenced types where they would be parsed as modifiers.

## Grammar overview

The following EBNF is descriptive. `newline` is significant because declarations and fields
are line-oriented.

```text
file          = { newline }, module, newline, { definition } ;
module        = "module", name ;

definition    = node | trait | choice | enum ;

node          = "node", name, [ trait-list ], newline,
                { field }, "end", newline ;
trait-list    = "with", name, { ",", name } ;

trait         = "trait", name, newline,
                { field }, "end", newline ;

field         = name, ":",
                [ "fixed" ], [ "*" | "?" ], [ "value" ], [ "transient" ],
                name, newline ;

choice        = "choice", name, newline,
                option-list, newline, "end", newline ;

enum          = "enum", name, newline,
                option-list, newline, "end", newline ;

option-list   = name, { "|", name } ;
```

Within an option list, a newline may appear directly before or after `|`. Inline, leading-pipe,
trailing-pipe, and mixed layouts are accepted. A trailing `|` without another option is invalid.

## Modules

```text
module expressions
```

The module name is emitted directly as the C++ namespace. It must therefore also be a valid,
non-keyword C++ identifier.

## Nodes and fields

```text
node BinaryExpression
    op: BinaryOp
    left: Expr
    right: Expr
end
```

A node generates a `snake_case` C++ struct. Fields resolve as follows:

- A backend-mapped type uses its configured C++ spelling.
- An enum is stored as its generated enum type.
- A node or choice reference normally uses `std::unique_ptr<T>`.
- A `value` node or choice reference embeds `T` directly.

### Field modifiers

Modifiers have the fixed order shown below:

```text
field: [fixed] [* | ?] [value] [transient] Type
```

- `*` generates `std::vector<T>` around the otherwise generated representation.
- `fixed` marks a repeated field whose element count must be preserved by generated
  transformers. It is valid only together with `*` and currently uses the same C++ storage as
  the corresponding non-fixed repeated field.
- `?` generates `std::optional<T>` for backend-mapped, enum, and `value` types. A pointer-backed
  node or choice remains `std::unique_ptr<T>`, which already represents absence.
- `value` embeds node and choice types instead of using `std::unique_ptr`.
- `transient` emits the C++ member but excludes it from dump and visitor structure.
- `*` and `?` are mutually exclusive.

Examples:

```text
names: *identifier
arguments: fixed *Expr
metadata: ?value Metadata
function_scope: transient scope
```

## Choices

```text
choice Expr
    Number | BinaryExpression
    | FunctionCall
end
```

A choice generates a `snake_case` `std::variant` alias. Alternatives must resolve to nodes or
other choices. Choice aliases are dependency-ordered; cyclic choice aliases are invalid.

When a choice is used by at least one repeated, pointer-backed field such as `code: *Expr`, the
C++ backend also generates one reusable list alias:

```cpp
using expr_list = std::vector<std::unique_ptr<expr>>;
```

Repeated pointer-backed choice fields use this alias in generated structs.
Repeated `value` choice fields do not generate this alias because their representation is
`std::vector<expr>` instead.

## Enums

```text
enum BinaryOp
    Plus | Minus | Multiply
end
```

An enum generates `enum class <snake_case_name>_t`. Enumerator spelling is preserved exactly.
Enum option lists use the same flexible layout as choices.

## Traits

```text
trait Location
    location: source_range
end

node FunctionHead with Location
    name: identifier
end
```

A trait generates a public C++ base struct. Nodes may apply one or more comma-separated traits.
Traits cannot inherit, appear in choices, or receive visitor overloads. Trait fields are
flattened into derived-node dump output. Duplicate applications and field collisions across
traits and local fields are invalid. Structured node or choice values cannot currently be
embedded by value inside traits because generated traits precede complete node definitions.

## Semantic validation

Before generation, semantic analysis rejects:

- Duplicate declarations, fields, enum entries, choice alternatives, traits, and mappings.
- Unknown field types, traits, and choice alternatives.
- Traits used as ordinary field types or choice alternatives.
- Invalid modifier combinations.
- Cyclic choice aliases and recursive by-value node dependencies.
- Invalid C++ identifiers, namespaces, and reserved keywords.
- Generated C++ name collisions, including snake_case and enum `_t` collisions.
- Collisions with reserved generated names such as `visitor` and `transformer`.

A field type that is neither a declared NDEF type nor backend-mapped is reported as unknown.
The analyzer cannot distinguish a misspelled declaration from a missing backend mapping.

## C++ name conversion and ordering

Definition names are converted from CamelCase to snake_case. Acronym boundaries are supported;
for example, `HTTPServer` becomes `http_server`. Field and enum-entry spellings are not changed.

Source order does not determine whether references are valid. Generation emits declarations in
an order required by C++ dependencies: enums, forward declarations, traits, dependency-ordered
choices, and dependency-ordered nodes. Order within otherwise independent groups remains stable.

## Visitor contract

Each module generates a mutable `visitor` class:

- Public `visit(T&)` overloads provide node and choice entry points.
- Choice visits dispatch with `std::visit`.
- Node visits call virtual `enter(T&)`, traverse children, then call virtual `leave(T&)`.
- Only non-`value`, non-`transient` node and choice fields are traversed.
- Null pointers are skipped; repeated pointer fields visit every non-null element.
- Pointer-backed choice fields support replacement requests from derived visitors. For each
  visitable choice, the visitor exposes protected `replace_<choice>(...)` helpers accepting
  either one `std::unique_ptr<choice>` or a choice-list replacement. The base visitor records
  explicit replacement state, consumes it immediately after the child visit, and then clears it.
- Single choice fields accept zero or one requested replacement; zero deletes the child and more
  than one trips an assertion. Repeated choice fields accept any number of replacements per
  child. Fixed repeated choice fields require exactly one replacement per non-null child.
- Definitions used exclusively through `value` or `transient` contexts are omitted, while
  unreferenced definitions remain available as roots.

## Transformer contract

Each module generates a mutable bottom-up `transformer` class:

- Public `rewrite(std::unique_ptr<T>)` overloads provide node and choice entry points.
- Choice rewrites dispatch with `std::visit` and wrap concrete node replacements back into
  the choice variant.
- Rewrites first rewrite children and then call a protected virtual node hook.
- Nodes that can appear in repeated pointer-backed contexts use `visit_multiple(T&)` and return
  `std::vector<std::unique_ptr<T>>`; repeated choices use the generated `<choice>_list` alias.
- Other pointer-backed nodes use `visit_single(T&)` and return `std::unique_ptr<T>`.
- If a concrete node is a direct alternative of exactly one transformable choice, its rewrite
  and hook return type is promoted to that choice type. For example, a `Number` alternative of
  `Expr` returns `std::unique_ptr<expr>` or `expr_list`, allowing replacements with any
  expression alternative.
- A concrete node that is a direct alternative of multiple transformable choices is rejected
  because its generic transformer return type would be ambiguous. Such nodes also cannot be
  used directly in pointer-backed structural fields; they must be reached through the choice
  type used as their transformer return type.
- Multiple-capable status propagates through choices: a repeated choice makes its alternatives
  multiple-capable, and a choice containing a multiple-capable alternative is also
  multiple-capable.
- Default hooks move the rewritten node into a new owning pointer, or into a one-element list
  for multiple-capable nodes.
- Only non-`value`, non-`transient` node and choice fields are rewritten. Trait fields are not
  traversed, matching the visitor implementation.
- Null single rewrites return `nullptr`; null multiple rewrites return an empty list.
- If a single field targets a multiple-capable type, zero replacements become `nullptr`, one
  replacement is moved back into the field, and more than one replacement trips an assertion.
- Fixed repeated fields preserve one output slot per input slot. Null input elements remain
  null elements; non-null elements must rewrite to exactly one replacement.

## Dump contract

Generated dump functions produce a YAML-like structural representation:

- Four spaces are used per nesting level.
- Every node begins with `_type` containing its original NDEF name.
- Field names use their original NDEF spelling.
- Repeated fields are lists; empty lists emit `[]`.
- Missing optionals and null pointers emit `null`.
- Strings are quoted and escaped.
- Enums emit original entry names.
- Trait fields are flattened into the node object.
- Transient fields are omitted.

Backend scalar values use the inline `dump_value` customization point. Streamable values use
`operator<<`; applications can provide a more-specific overload in the value type's namespace
for argument-dependent lookup and context-sensitive formatting.

Strict YAML compatibility is not yet guaranteed and remains a documented design question.

## C++ backend map

`backend_cpp.map` contains include directives and type mappings:

```text
@include <cstddef>
@include "project/scope.hpp"

index: std::size_t
scope: std::unique_ptr<scope>
```

Rules:

- `@include` accepts exactly `<...>` or `"..."` spelling.
- Includes are unconditional, retain declaration order, and are deduplicated against generated
  standard includes.
- A mapping uses `name: C++ type spelling`.
- C++ type spelling is the trimmed remainder of the line up to `#` or the newline.
- Backend-map comments begin with `#`, unlike NDEF `//` comments.
- Duplicate mapping names are invalid; unused mappings are allowed.
- The generated model header includes configured headers before emitting declarations.

One behavior requires a future explicit decision: if a backend mapping has the same name as a
declared NDEF type, current model generation gives the backend mapping precedence for fields.
Definitions should avoid this collision until the rule is resolved.

## Language versioning

NDEF files do not declare a language version. Version syntax is deliberately deferred because
the format currently has limited distribution and no demonstrated compatibility need.
