# Choice-wide trait propagation

**Date:** 2026-07-30

**Status:** active

## Context

All node alternatives reachable through a choice sometimes need the same data-bearing trait.
Repeating that trait on every node obscures the choice-wide invariant and is easy to miss when
new alternatives are added. Code working with the generated choice also needs a uniform way to
access the shared trait through nested variants.

## Decision

Use choice-level `allwith` lists to apply traits to all transitively reachable node alternatives:

```text
trait Location
    location: source_range
end

choice Expr allwith Location
    Name | Literal | FunctionHead
end
```

The choice remains a `std::variant` alias and does not itself inherit or store common members.
Because node types are global, propagation also affects uses of those nodes outside the choice.
Explicit and propagated traits remain separate in the parsed model, and semantic analysis
computes effective node traits. Explicit traits come first, followed by propagated traits in
choice declaration and `allwith` list order. Overlapping applications are deduplicated at their
first occurrence. Generation rejects unknown traits and any field-name collision among effective
traits and local node fields.

Generated model headers containing an `allwith` choice provide mutable and const
`as_trait<Trait>(choice)` function templates. These recursively visit nested `std::variant`
choices and convert the concrete node reference to its public trait base. The first
implementation deliberately leaves validity to template instantiation: it does not constrain
the accessor to traits guaranteed by the choice.

## Alternatives considered

### Repeat `with` on every node

Explicit node traits remain useful for node-specific characteristics, but repetition does not
state or maintain a choice-wide invariant when alternatives change.

### Make the choice itself contain the trait

The generated choice is a `std::variant` alias rather than an object with its own storage.
Attaching the trait to every reachable node keeps the data with each concrete value and makes
the choice-wide, transitive application explicit.
