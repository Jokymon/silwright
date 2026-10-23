# Language reference

Silwright has two small input languages. NDEF files describe the structure of a node model,
while backend map files connect otherwise external attribute types to a generation backend.
NDEF does not assign a target-language representation, and the map language preserves target
type spellings without interpreting them. The currently implemented
[C++ backend](cpp_backend.md) defines how both inputs are represented.

## NDEF language reference

### Files

- A node-definition file uses the `.ndef` suffix.
- One `.ndef` file contains exactly one module.
- The module declaration must be the first declaration in the file.
- Definitions may refer to declarations that occur later in the same file.

### Lexical rules

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
module node trait choice enum end with allwith value transient fixed
```

`*`, `?`, `:`, `|`, and `,` are syntax operators or separators. Keywords are contextual in
some name positions—`value`, for example, remains a legal field name—but keyword names should
not be used as referenced types where they would be parsed as modifiers.

### Grammar overview

The following EBNF is descriptive. `newline` is significant because declarations and fields
are line-oriented.

```text
file           = { newline }, module, newline, { definition } ;
module         = "module", name ;

definition     = node | trait | choice | enum ;

node           = "node", name, [ trait-list ], newline,
                 { field }, "end", newline ;
trait-list     = "with", name, { ",", name } ;

trait          = "trait", name, newline,
                 { field }, "end", newline ;

field          = name, ":",
                 [ "fixed" ], [ "*" | "?" ], [ "value" ], [ "transient" ],
                 name, newline ;

choice         = "choice", name, [ all-trait-list ], newline,
                 option-list, newline, "end", newline ;
all-trait-list = "allwith", name, { ",", name } ;

enum           = "enum", name, newline,
                 option-list, newline, "end", newline ;

option-list    = name, { "|", name } ;
```

Within an option list, a newline may appear directly before or after `|`. Inline, leading-pipe,
trailing-pipe, and mixed layouts are accepted. A trailing `|` without another option is invalid.

### Modules

```text
module expressions
```

A module contains all declarations in the file and gives the model a name. How that name is
represented in generated output is a backend concern.

### Nodes and fields

A node declares a structured type consisting of named fields:

```text
node BinaryExpression
    op: BinaryOp
    left: Expr
    right: Expr
end
```

A field type may name a node, choice, or enum declared in the module, or an external attribute
type supplied by a backend map. Traits are applied with `with` and cannot be used as ordinary
field types.

#### Field modifiers

Modifiers have the fixed order shown below:

```text
field: [fixed] [* | ?] [value] [transient] Type
```

- `*` makes a field repeated.
- `fixed` marks a repeated field whose element count must be preserved by structural
  transformations. It is valid only together with `*`.
- `?` makes a field optional. `*` and `?` are mutually exclusive.
- `value` requests value storage for node and choice fields instead of the backend's default
  relationship representation. Backend-mapped types and enums are already values, so the
  modifier has no additional effect on them.
- `transient` keeps the field in the generated in-memory model but excludes it from structural
  dumping, visiting, and transformation.

Examples:

```text
names: *identifier
arguments: fixed *Expr
metadata: ?value Metadata
function_scope: transient scope
```

The concrete representation of repetition, optionality, value storage, and ordinary node
relationships is defined by each backend.

### Choices

```text
choice Expr allwith Location, Attributes
    Number | BinaryExpression
    | FunctionCall
end
```

A choice declares a sum of nodes or other choices. A node may be listed as a direct alternative
of at most one choice in a module; nesting one choice inside another does not give the nested
nodes another direct membership. Cyclic choice aliases are invalid.

An `allwith` list applies its traits to every node reachable through the choice alternatives.
Propagation is transitive through nested choices and affects uses of those nodes outside the
annotated choice as well. Explicit node traits are ordered before inferred choice traits;
inferred traits follow choice declaration order and their order within each `allwith` list.
Repeated applications, including overlap with an explicit `with`, are deduplicated at the first
occurrence.

### Enums

```text
enum BinaryOp
    Plus | Minus | Multiply
end
```

An enum declares a distinct type and introduces the listed values. The values are names, not
references to other declarations. Enum option lists use the same flexible layout as choices.

### Traits

```text
trait Location
    location: source_range
end

node FunctionHead with Location
    name: identifier
end
```

A trait declares reusable fields. A node applies one or more comma-separated traits with
`with`, and a choice can propagate traits with `allwith`. Traits cannot inherit from other
traits or appear as choice alternatives. Repeated applications are deduplicated; field-name
collisions between applied traits or between a trait and a node are invalid.

### Semantic validation

Validation and generation diagnostics are errors-only: a failure stops the workflow, and
accepted input does not produce warnings. The CLI renders known failures as numbered,
source-aware diagnostics with a one-based `file:line:column` location, source line, and caret
marker.

Semantic analysis rejects:

- Duplicate declarations, fields, enum entries, and choice alternatives.
- Unknown field types, traits, and choice alternatives.
- Traits used as ordinary field types or choice alternatives.
- A node listed as a direct alternative of more than one choice.
- Invalid modifier combinations.
- Cyclic choices and recursive by-value node dependencies.
- Field collisions introduced through traits.

A field type that is neither declared in the NDEF module nor provided by the backend map is
unknown. The analyzer cannot distinguish a misspelled declaration from a missing backend
mapping. Backends may impose additional naming and representation restrictions.

### Language versioning

NDEF files do not declare a language version. Version syntax is deliberately deferred because
the format currently has limited distribution and no demonstrated compatibility need.

## Backend map language reference

### Purpose

A backend map associates external NDEF attribute types with target representations. This keeps
target-language type spellings and dependencies out of the structural NDEF model.

For example, the following model uses the external types `identifier` and `source_range`:

```text
node NameExpression
    name: identifier
    location: source_range
end
```

A backend map must supply those types before a backend can generate the model:

```text
identifier: target-specific string type
source_range: target-specific source-range type
```

The text to the right of `:` is opaque to the map language. Its syntax and meaning belong to
the selected backend.

### Syntax

A map file is line-oriented and contains type mappings and dependency directives:

```text
map-file   = { newline | mapping | dependency } ;
mapping    = name, ":", target-spelling, newline ;
dependency = "@include", include-spelling, newline ;
```

Names follow the same ASCII identifier rule as NDEF names. A target spelling is the trimmed
remainder of its line up to `#` or the newline. It may contain spaces and punctuation. Map-file
comments begin with `#` and continue through the end of the line.

### Type mappings

```text
identifier: target-specific string type
index: target-specific size type
```

The left side is the type name used by NDEF fields. The right side is passed to the backend as
the requested target representation. Duplicate mapping names are invalid; unused mappings are
allowed.

If a mapping and an NDEF declaration have the same name, the current implementation gives the
mapping precedence when resolving fields. Definitions should avoid this collision until that
behavior receives an explicit design decision.

### Dependency directives

```text
@include <system-dependency>
@include "project-dependency"
```

`@include` records a backend dependency. Its spelling must be enclosed in either angle brackets
or double quotes and is otherwise preserved. The selected backend determines what inclusion
means, where the dependency is emitted, and whether duplicate dependencies are retained. The
directive name and delimiters reflect the currently implemented format; they do not prescribe
how future backends must represent dependencies in their target languages.

### Backend selection and file discovery

The map language itself does not select a backend or prescribe a filename. Those are integration
decisions made by the command-line workflow or embedding application. The current
[C++ backend](cpp_backend.md#inputs-and-generated-files) uses a sibling file named
`backend_cpp.map` and gives `@include` its C++ header meaning.
