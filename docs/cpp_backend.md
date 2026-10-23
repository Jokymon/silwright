# C++ backend

The C++ backend translates an analyzed NDEF model and its backend map into C++20 model,
dumping, visitor, and transformer APIs. This document defines the C++-specific representation;
the input languages are documented in the [language reference](language-reference.md).

## Inputs and generated files

The current command-line workflow selects the C++ backend statically. For a definition such as
`simple_lang.ndef`, it requires `backend_cpp.map` in the same directory. Dynamic backend
selection and alternative map filenames are not currently supported.

```shell
uv run silwright examples/simple_lang.ndef
```

Generation writes these files beside the definition, using the `.ndef` basename:

- `<name>.hpp` and `<name>.cpp` for the model.
- `<name>_dump.hpp`, `<name>_dump.ipp`, and `<name>_dump.cpp` for dumping.
- `<name>_visitor.hpp` and `<name>_visitor.cpp` for mutable traversal.
- `<name>_transformer.hpp` and `<name>_transformer.cpp` for bottom-up rewriting.

Existing generated outputs are replaced. Generated C++ requires C++20; in particular, choices
and dump customization use `std::variant` and C++20 constraints.

The complete example consists of `examples/simple_lang.ndef`, `examples/backend_cpp.map`, and
`examples/simple_lang_main.cpp`. The example program constructs a function definition and
writes its YAML-like dump to `std::cout`. `examples/CMakeLists.txt` defines the C++20
`simple_lang_example` executable from the example and generated translation units. These files
are currently a proof of concept; generated C++ is not yet compiled by the automated project
checks.

## NDEF-to-C++ mapping overview

Definition names are converted from CamelCase to snake_case. Acronym boundaries are preserved;
for example, `HTTPServer` becomes `http_server`. Field names and enum-entry spellings are not
changed.

| NDEF concept | Generated C++ representation or behavior |
| --- | --- |
| `module Name` | Namespace named `Name` exactly as written. |
| `node Name` | `struct name`, with the definition name converted to snake_case. |
| `trait Name` | `struct name`; traits applied to a node become public base structs. |
| `with Trait` | Public inheritance from the generated trait struct. |
| `choice Name` | `using name = std::variant<...>` over its generated alternatives. |
| `allwith Trait` | Public trait inheritance on every transitively reachable node, plus `as_trait` accessors for the choice. |
| `enum Name` | `enum class name_t`; enum-entry spelling is preserved. |
| Backend-mapped type | The C++ type spelling from `backend_cpp.map`, emitted verbatim. |
| Ordinary enum field | The generated `name_t` value type. |
| Ordinary node or choice field | `std::unique_ptr<T>`. |
| `value Type` | A node or choice stored directly as `T` instead of `std::unique_ptr<T>`. |
| `*Type` | `std::vector<T>` around the otherwise generated representation. |
| Repeated pointer-backed choice | Generated `choice_list` alias for `std::vector<std::unique_ptr<choice>>`. |
| `fixed *Type` | The same storage as `*Type`, with element-count preservation enforced by transformers. |
| `?Type` | `std::optional<T>` for mapped, enum, and `value` types; pointer-backed node and choice fields remain `std::unique_ptr<T>`. |
| `transient Type` | A normal C++ member omitted from generated dumping, visiting, and transformation. |

Built-in and enum fields already have value representation, so applying `value` to them has no
additional effect. Modifiers compose: for example, `*value Parameter` becomes
`std::vector<parameter>`, while `?value Metadata` becomes `std::optional<metadata>`.

## Model declarations and ordering

The generated model header includes `<memory>`, `<optional>`, `<string>`, `<variant>`, and
`<vector>`, followed by dependencies from the backend map. It then emits enums, forward
declarations, traits, choices, optional choice-list aliases, and nodes in an order that satisfies
C++ completeness requirements. Order within otherwise independent groups remains stable.

Value members require complete types. Nodes affected by value dependencies are therefore
dependency-ordered, and recursive value-member cycles are rejected. Choice dependencies are
also ordered; cyclic choice aliases are invalid because C++ aliases cannot be forward-declared.

Traits generate public base structs. Their fields are flattened into derived-node dump output,
but trait types do not receive visitor or transformer entry points. Structured node or choice
values cannot currently be embedded by value inside traits because trait definitions precede
complete node definitions.

When a choice has `allwith`, the model header provides mutable and const
`as_trait<Trait>(choice)` overloads. They recursively unwrap nested choices and return the
requested trait reference:

```cpp
expr& value = /* ... */;
as_trait<location>(value).location = source_range{};

const expr& const_value = value;
const location& where = as_trait<location>(const_value);
```

The accessor assumes that the trait is present on every reachable node. Requesting a trait that
is not common to the choice produces a C++ template compilation error.

## Backend map interpretation

The C++ backend treats each mapping value as a C++ type spelling:

```text
@include <cstddef>
@include "project/scope.hpp"

index: std::size_t
scope: std::unique_ptr<scope>
```

An `@include` entry becomes a preprocessor `#include` in the generated model header. System
headers use `<...>` and project headers use `"..."`. Dependencies retain declaration order and
are deduplicated against the backend's generated standard includes.

The mapping value is the trimmed remainder of the line up to `#` or the newline and is emitted
as the field's C++ type. The backend does not infer required headers from that spelling; every
non-generated dependency must be listed explicitly.

## Mutable visitor

Each module generates an external mutable `visitor` class:

- Public `visit(T&)` overloads provide node and choice entry points.
- Choice visits dispatch with `std::visit`.
- Node visits call virtual `enter(T&)`, traverse children, and then call virtual `leave(T&)`.
- Only non-`value`, non-`transient` node and choice fields are traversed. Trait fields are not
  traversed.
- Null pointers are skipped; repeated pointer fields visit every non-null element.
- Definitions used exclusively through `value` or `transient` contexts are omitted, while
  unreferenced definitions remain available as roots.

For every visitable choice, protected `replace_<choice>(...)` helpers accept either one
`std::unique_ptr<choice>` or a choice-list replacement. The visitor consumes replacement state
immediately after visiting the child and then clears it. A single choice field accepts zero or
one replacement; zero deletes the child and more than one triggers an assertion. A repeated
choice accepts any number of replacements for each child. A fixed repeated choice requires
exactly one replacement for each non-null child.

## Mutable transformer

Each module generates an external mutable bottom-up `transformer` class:

- Public `rewrite(std::unique_ptr<T>)` overloads provide node and choice entry points.
- Choice rewrites dispatch with `std::visit` and wrap concrete replacements back into the
  choice variant.
- Rewrites process children before calling a protected virtual node hook.
- Nodes that can occur in repeated pointer-backed contexts use `visit_multiple(T&)` and return
  `std::vector<std::unique_ptr<T>>`; repeated choices use their generated `<choice>_list` alias.
- Other pointer-backed nodes use `visit_single(T&)` and return `std::unique_ptr<T>`.
- Default hooks move the rewritten node into a new owning pointer, or into a one-element list
  for multiple-capable nodes.
- Only non-`value`, non-`transient` node and choice fields are rewritten. Trait fields are not
  traversed, matching the visitor.

If a concrete node is a direct alternative of a transformable choice, its rewrite and hook
return type is promoted to that choice type. This allows replacing the node with any alternative
of the same choice. Exclusive direct choice membership makes that promoted return type
unambiguous. A promoted node cannot also be used directly in a pointer-backed structural field;
it must be reached through its choice.

Multiple-capable status propagates through choices. A repeated choice makes its alternatives
multiple-capable, and a choice containing a multiple-capable alternative is itself
multiple-capable. Null single rewrites return `nullptr`; null multiple rewrites return an empty
list. If a single field targets a multiple-capable type, zero replacements become `nullptr`, one
is moved back into the field, and more than one triggers an assertion.

Fixed repeated fields preserve one output slot for each input slot. Null input elements remain
null; each non-null element must produce exactly one replacement.

## Dumping

Generated `dump` overloads produce a YAML-like structural representation:

- Four spaces are used per nesting level.
- Every node starts with `_type` containing its original NDEF name.
- Field names use their original NDEF spelling.
- Repeated fields are lists; empty lists emit `[]`.
- Missing optionals and null pointers emit `null`.
- Strings are quoted and escaped.
- Enums emit their original entry names.
- Trait fields are flattened into the node object.
- Transient fields are omitted.

Strict YAML compatibility is not guaranteed. Dump declarations live in `_dump.hpp`; template
implementations live in `_dump.ipp`, which the header includes; `_dump.cpp` is the conventional
translation-unit entry point.

Mapped scalar values use the inline `dump_value` customization point. Its default uses
`operator<<`. Applications can provide a more-specific overload in the value type's namespace,
where argument-dependent lookup finds it and permits context-sensitive formatting. A mapped
type that is neither streamable nor customized produces a targeted compile-time diagnostic.

## C++-specific validation

In addition to the language-level checks, the C++ backend rejects:

- Module and declaration names that are invalid C++ identifiers or reserved keywords.
- Generated name collisions after CamelCase-to-snake_case conversion, including enum `_t`
  collisions.
- Collisions with reserved generated names such as `visitor` and `transformer`.
- Structured value fields in traits.
- Dependency cycles that cannot be represented using C++ declarations.
