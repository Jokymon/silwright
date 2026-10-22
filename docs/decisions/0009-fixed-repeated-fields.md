# Fixed repeated fields

**Date:** 2026-07-11

**Status:** active

## Context

Repeated fields normally represent variable-length child collections. Generated transformers may
therefore remove one element by returning no replacement or expand one element into multiple
replacements. Some repeated fields, such as function-call arguments, are tied to an external
arity relationship and must preserve one output slot per input slot.

## Decision

Use the `fixed` modifier before `*`:

```text
node FunctionCall
    arguments: fixed *Expr
end
```

`fixed` is valid only on repeated fields and does not currently change C++ storage, dump output,
or visitor traversal. The field still emits as the same vector representation as `*Expr`.
Generated transformer code changes its replacement policy: null input elements remain null
elements, and each non-null element must rewrite to exactly one replacement. The generated code
asserts this invariant before moving the replacement back into the field.

## Alternatives considered

A separate `tuple` keyword, a symbolic modifier, and a dedicated C++ wrapper type were
considered. `fixed *Expr` was selected because it keeps the existing `*` multiplicity syntax
visible while naming the additional cardinality constraint directly. A wrapper type may be
reconsidered later if the invariant needs to be enforced outside generated transformations.
