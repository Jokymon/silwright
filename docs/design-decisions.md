# Design decisions

This document records significant language and generation decisions, including alternatives
that may be reconsidered as the language develops.

## Validation diagnostic severity

### Context

Semantic analysis and generation need a clear contract for invalid definitions. A warning
channel would require users and tooling to decide whether generation may continue, which
warnings are acceptable in CI, and whether generated output after warnings is supported.

### Decision

Silwright validation and generation diagnostics are errors-only. If an input problem makes the
definition invalid, semantic analysis or generation rejects it and no later workflow step should
continue. If a construct is accepted, Silwright does not emit a warning for it.

Redundant but supported spelling, such as `?` on pointer-backed node or choice fields, remains
accepted and quiet. If a currently accepted construct later proves harmful or ambiguous, it
should be promoted to a validation error through an explicit compatibility decision rather than
introduced as a warning.

### Alternatives considered

#### Add semantic warnings

Warnings could flag redundant or suspicious definitions while still generating C++. This was
rejected for now because the current workflow has no demonstrated need for advisory diagnostics,
and continuing after warnings would weaken the simple contract that generation either succeeds
from a valid model or fails before producing output.

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

## External mutable transformer

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

This promotion is intentionally conservative. If a concrete node is a direct alternative of
multiple transformable choices, generation is rejected because one `rewrite(std::unique_ptr<T>)`
overload cannot have different return types for different call sites. A promoted node also
cannot be used directly in pointer-backed structural fields; such fields could not assign a
choice-typed replacement back into a concrete-node member.

Default hook implementations move the mutable node reference into a newly allocated owning
pointer. Multiple hooks return a one-element replacement list. This keeps the base transformer
identity-preserving while allowing derived transformers to delete a node by returning no
replacement, replace it with one node, or expand it into several nodes when the type is
multiple-capable. If a single field targets a multiple-capable type, generated code asserts that
the replacement list contains at most one element before moving it back into the field.

The transformer traverses the same structural fields as the visitor: non-`value`,
non-`transient` pointer-backed node and choice fields. Scalar fields, enum fields, value fields,
transient fields, and trait fields are not rewritten.

## Fixed repeated fields

Repeated fields normally represent variable-length child collections. Generated transformers may
therefore remove one element by returning no replacement or expand one element into multiple
replacements. Some repeated fields, such as function-call arguments, are tied to an external
arity relationship and must preserve one output slot per input slot.

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

Alternatives considered were a separate `tuple` keyword, a symbolic modifier, or a dedicated
C++ wrapper type. `fixed *Expr` was selected because it keeps the existing `*` multiplicity
syntax visible while naming the additional cardinality constraint directly. A wrapper type may
be reconsidered later if the invariant needs to be enforced outside generated transformations.

## Reusable node traits

Reusable data-bearing characteristics use `trait` declarations, node-level `with` lists, and
choice-level `allwith` lists:

```text
trait Location
    location: source_range
end

node FunctionHead with Location
    name: identifier
end

choice Expr allwith Location
    Name | Literal | FunctionHead
end
```

Traits generate public C++ base structs, while nodes generate public inheritance from each
effective trait. `allwith` applies its traits to all transitively reachable node alternatives;
the choice remains a `std::variant` alias and does not itself inherit or store common members.
Because node types are global, propagation also affects uses of those nodes outside the choice.
Explicit and propagated traits remain separate in the parsed model and semantic analysis
computes effective node traits. Explicit traits come first, followed by propagated traits in
choice declaration and `allwith` list order. Overlapping applications are deduplicated at their
first occurrence. Traits cannot inherit, appear as choice alternatives, or receive visitor
overloads. Their fields are flattened into the derived node's dump output. Generation rejects
unknown traits and any field-name collision among effective traits and local node fields.

Generated model headers containing an `allwith` choice provide `as_trait<Trait>(choice)` mutable
and const function templates. These recursively visit nested `std::variant` choices and cast the
concrete node to its public trait base. The first implementation deliberately leaves validity to
template instantiation: it does not constrain the accessor to traits guaranteed by the choice.

`trait` was selected over `interface` because traits carry data, and over `concept` because
that term has a distinct C++ meaning. `with` reads as capability application without suggesting
ordinary field composition. `allwith` makes the choice-wide, transitive application explicit
without implying that the variant itself contains the trait. The trait can use a natural
characteristic name such as `Location`; this does not conflict with its lowercase `location`
field because type and member names occupy different generated contexts.

## Transient tooling fields

Fields that are required by later compiler stages but are not structural node data use the
`transient` modifier:

```text
node FunctionDefinition
    function_scope: transient scope
end
```

The field is emitted normally in the C++ struct, while dump generation and visitor traversal
ignore it. Its representation remains a backend concern; for example, `backend_cpp.map` may
map `scope` to `std::unique_ptr<scope>` and include the project header defining `scope`.

Alternatives considered were an analysis-data trait, external side tables keyed by node
identity, handwritten derived wrappers, and generic type-erased attachment storage. Traits
would still need a non-structural marker, side tables add lifetime and synchronization costs,
derived wrappers interact poorly with variant values, and generic attachments lose static type
visibility. `transient` was selected as the smallest general mechanism that keeps tooling state
strongly typed and directly accessible without treating it as part of structural operations.
