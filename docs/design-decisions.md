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
