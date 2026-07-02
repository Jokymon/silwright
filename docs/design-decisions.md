# Design decisions

This document records significant language and generation decisions, including alternatives
that may be reconsidered as the language develops.

## Value storage for structured fields

### Context

Node and choice fields normally generate owning `std::unique_ptr` members. Some structured
types, such as a function head or signature, are better embedded directly as value members.

### Decision

Use a `value` modifier at the field usage site:

```text
node FunctionDefinition
    head: value FunctionHead
    parameters: *value Parameter
end
```

This generates members equivalent to:

```cpp
function_head head;
std::vector<parameter> parameters;
```

The modifier affects node and choice references. Built-in and enum fields already use value
storage, so it is permitted but redundant for those types. `value` follows the optional `*`
modifier, allowing multiplicity and storage to remain separate concepts.

Value members require their C++ types to be complete. The generator therefore orders node
definitions according to value dependencies and rejects recursive value-member cycles.
Pointer-based recursive relationships remain supported.

### Alternatives considered

#### A separate value-oriented definition kind

A `record` declaration could distinguish value-like records from identity-bearing nodes.
References to records would always be embedded, while references to nodes would remain owned
pointers. This provides strong type-level semantics but expands the language and prevents the
same structured type from naturally using different storage at different usage sites.

#### General type expressions

Types could express representation explicitly, for example
`vector<value<Parameter>>`, `owned<Expr>`, or `optional<Type>`. This is extensible but adds a
substantial generic type system and exposes backend storage details throughout definitions.

#### Symbol-based usage modifiers

Symbols such as `&`, `@`, or `!` could mark embedded values. They are concise but less
self-documenting and carry unrelated meanings in C++ and other languages. The `value` keyword
was selected for clarity.

## Context-aware dump customization

### Context

Generated YAML-like dump functions need to handle ordinary scalar values while permitting
application-specific values, such as a `type_id`, to use external context during formatting.
The context type cannot be fixed by the generator.

### Decision

Generate `dump` and `dump_value` as function templates. The generic `dump_value` implementation
uses `operator<<`. Applications customize a value by defining a more-specific `dump_value`
overload in the value type's namespace; an unqualified generated call finds it through
argument-dependent lookup. This avoids runtime type erasure and lets compilers inline the
customization call. If a value is not stream-insertable and no overload is found, the generic
fallback issues a targeted compile-time diagnostic requesting a `dump_value` overload.

Template declarations live in `_dump.hpp`; definitions live in `_dump.ipp`, which the header
includes. A `_dump.cpp` file is still generated as the conventional translation-unit entry
point, but generic template implementations necessarily remain visible to header consumers.

Generated dump output uses four spaces per nesting level, quoted and escaped strings, `null`
for empty owning pointers, original enum entry names, and an artificial `_type` property on
every node object.

## C++ backend header dependencies

### Context

Mapped C++ types may require standard headers or project-specific definitions. Requiring every
consumer to include those dependencies before a generated model header would make that header
order-dependent and not self-contained.

### Decision

Allow explicit include directives in `backend_cpp.map`:

```text
@include <cstddef>
@include "project/symbol.hpp"

index: std::size_t
type: project::type_id
```

The `@` distinguishes backend configuration from type mappings and leaves room for future
backend directives. Both system and quoted project headers are accepted. The generator emits
the headers before model declarations, preserves their order, and removes duplicates. Backend
selection remains statically fixed to `backend_cpp.map`.

### Alternatives considered

- Associating a `from <header>` clause with each mapping would enable selective inclusion but
  complicate the intentionally free-form C++ type spelling and repeat shared headers.
- A separate TOML or include-list file would separate configuration from mappings but add
  another discovery convention and make dependencies less local.
- `.ndef` include declarations would permit module-specific dependencies but leak C++ backend
  concerns into the backend-neutral node language.
- CLI include flags would avoid format changes but make generation less reproducible and place
  required configuration in build scripts.
- Inferring headers from C++ spellings would be convenient for a few standard types but brittle
  and incapable of resolving project-specific definitions.

## Optional fields

The `?` field-type prefix represents an optional value and is mutually exclusive with the `*`
repetition prefix. Built-in types, enums, and structured fields marked `value` generate as
`std::optional<T>`. Node and choice references without `value` remain `std::unique_ptr<T>`;
wrapping those pointers in another optional layer would represent the same absent/present state
twice without a current semantic need. Generated dumpers emit both disengaged optionals and
null owning pointers as `null`.

## External mutable visitor

Each module generates a `visitor` class in `_visitor.hpp` and `_visitor.cpp`. Traversal remains
external to model structs, avoiding generated `accept` methods and coupling data objects to a
visitor hierarchy. Public nonvirtual `visit(T&)` overloads provide mutable entry points for
nodes and choices. Choice overloads dispatch with `std::visit`.

For each node type, protected virtual `enter(T&)` and `leave(T&)` hooks run before and after its
children. Their base implementations are empty, so derived passes override only relevant
events without reimplementing traversal. Only pointer-backed node and choice fields are
children: scalar fields and fields explicitly marked `value` are not traversed. The fixed class
name reserves the generated C++ name `visitor` within the module namespace.

Visitor overloads and hooks are omitted for definitions referenced exclusively through `value`
fields. A choice used only as a value also does not pull its alternatives into the visitor API.
Definitions with a non-value use remain visitable, and definitions with no incoming use remain
available as traversal roots. This keeps generated visitor APIs aligned with actual traversal
semantics without requiring another language annotation.

## Reusable node traits

Reusable data-bearing characteristics use `trait` declarations and node-level `with` lists:

```text
trait Location
    location: source_range
end

node FunctionHead with Location
    name: identifier
end
```

Traits generate public C++ base structs, while nodes generate public inheritance from each
listed trait. Traits cannot inherit, appear in choices, or receive visitor overloads. Their
fields are flattened into the derived node's dump output. Generation rejects unknown or
repeated traits and any field-name collision among applied traits and local node fields.

`trait` was selected over `interface` because traits carry data, and over `concept` because
that term has a distinct C++ meaning. `with` reads as capability application without suggesting
ordinary field composition. The trait can use a natural characteristic name such as `Location`;
this does not conflict with its lowercase `location` field because type and member names occupy
different generated contexts.
