# Transient tooling fields

**Date:** 2026-07-03

**Status:** active

## Context

Some fields are required by later compiler stages but are not structural node data. They need
to remain strongly typed and directly accessible without participating in structural operations.

## Decision

Use the `transient` modifier:

```text
node FunctionDefinition
    function_scope: transient scope
end
```

The field is emitted normally in the C++ struct, while dump generation and visitor traversal
ignore it. Its representation remains a backend concern; for example, `backend_cpp.map` may
map `scope` to `std::unique_ptr<scope>` and include the project header defining `scope`.

## Alternatives considered

Alternatives considered were an analysis-data trait, external side tables keyed by node
identity, handwritten derived wrappers, and generic type-erased attachment storage. Traits
would still need a non-structural marker, side tables add lifetime and synchronization costs,
derived wrappers interact poorly with variant values, and generic attachments lose static type
visibility. `transient` was selected as the smallest general mechanism that keeps tooling state
strongly typed and directly accessible without treating it as part of structural operations.
