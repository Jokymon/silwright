# External mutable visitor

**Date:** 2026-07-02

**Status:** active

## Context

Generated models need mutable tree traversal without coupling data objects to a visitor
hierarchy. Traversal also needs to distinguish structural pointer-backed children from values
that should not be visited.

## Decision

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

Visitors also support localized replacement of pointer-backed choice children. For each
visitable choice, the generated visitor owns replacement state and exposes protected
`replace_<choice>(...)` helpers. A derived `leave(T&)` hook can request replacement with either
one choice pointer or a list of choice pointers. The parent traversal consumes that state
immediately after visiting the child and then clears it. The state includes an explicit flag so
an empty replacement list is distinct from no replacement request; this allows deletion where
the surrounding field permits it.

Replacement support is intentionally limited to choice fields. Single choice fields accept at
most one requested replacement. Repeated choice fields can delete, replace, or expand an
element. Fixed repeated choice fields preserve cardinality and require exactly one replacement
for each non-null visited child.
