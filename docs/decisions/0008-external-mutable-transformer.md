# External mutable transformer

**Date:** 2026-07-09

**Status:** active

## Context

Generated models need bottom-up tree rewriting without coupling data objects to transformation
logic. Rewrites must also support deletion, replacement, and expansion where field cardinality
allows them.

## Decision

Each module generates a `transformer` class in `_transformer.hpp` and `_transformer.cpp`.
Like the visitor, transformation remains external to the model structs. The transformer is
bottom-up: public `rewrite(std::unique_ptr<T>)` overloads rewrite all pointer-backed children
before dispatching to a protected virtual hook for the current concrete node.

Node hooks are split into `visit_single(T&)` and `visit_multiple(T&)`. A node uses
`visit_multiple` when it can appear in a repeated pointer-backed context, either directly or as
an alternative of a repeated choice. When a concrete node is a direct alternative of exactly one
transformable choice, its rewrite and hook return type is promoted to that choice type. This
lets a rewrite of a `Number` expression return any `Expr` replacement, not only another
`Number`. Multiple-capable status also propagates upward to choices that contain a
multiple-capable alternative, so choice rewrites have one coherent return type. Choice rewrites
dispatch through `std::visit`; generated hooks are only emitted for concrete nodes, not for
choices. Repeated choices return the generated `<choice>_list` alias.

This promotion relies on the language-wide rule that a node may be a direct alternative of at
most one choice. A promoted node also cannot be used directly in pointer-backed structural
fields; such fields could not assign a choice-typed replacement back into a concrete-node
member.

Default hook implementations move the mutable node reference into a newly allocated owning
pointer. Multiple hooks return a one-element replacement list. This keeps the base transformer
identity-preserving while allowing derived transformers to delete a node by returning no
replacement, replace it with one node, or expand it into several nodes when the type is
multiple-capable. If a single field targets a multiple-capable type, generated code asserts that
the replacement list contains at most one element before moving it back into the field.

The transformer traverses the same structural fields as the visitor: non-`value`,
non-`transient` pointer-backed node and choice fields. Scalar fields, enum fields, value fields,
transient fields, and trait fields are not rewritten.
