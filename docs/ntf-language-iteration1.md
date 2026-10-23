# NTF Language Iteration 1

This is a first formal sketch for an `.ntf` language that describes tree
transformations between Silwright `.ndef` modules. It is based on
`examples/simple.ntf` and the `ast` to `lir` lowering example in
`examples/iteration1.ntf`.

## Design Goals

- Prefer readable keywords over compact symbolic notation.
- Treat a transformation as a rule that says how one source node is turned into
  one target node, or into many target nodes.
- Make cardinality changes visible at rule declarations and at call sites.
- Keep comments identical to NDEF comments: `//` starts a line comment.
- Use `.` for one concept only: path selection through modules, values, and
  fields.

## File Structure

```text
transform ast to lir

alias ast as a
alias lir as l

rule Module from a.Module to l.Module
    set imports from map transform source.imports
end
```

An NTF file starts with one `transform` declaration, followed by optional aliases
and rule declarations.

TODO: Define how transformation files locate module definitions. Options are
module names only, explicit paths, or project-level module resolution.

## Rules

```text
rule ExprAsStatement from a.Expr to many l.Statement as statement
    ...
end
```

A rule has:

- a unique rule name,
- one source type after `from`,
- one target type after `to`,
- optional `many` before the target type when the rule emits zero or more
  target values,
- optional context name after `as`.

The implicit value `source` is bound to the current source node inside a rule.

Context names disambiguate rules that share a source type but produce different
views of that source, such as `a.Expr as statement`, `a.Expr as expression`, and
`a.Expr as place`.

TODO: Decide whether contexts are globally unique names or scoped to a
source-target pair.

## Field Assignments

Rule and constructor bodies assign target fields with `set` or `same`.

```text
set head from transform source.function_head
same location
```

`set <target-field> from <expression>` assigns a target field from an explicit
expression.

`same <field>` is shorthand for:

```text
set <field> from source.<field>
```

The shorthand is valid only when source and target both have that field and the
types are compatible without transformation.

TODO: Decide whether every target field must be assigned, except transient
fields, or whether constructors may rely on defaults.

## Expressions

The first iteration supports these expression forms:

```text
source
source.field
source.nested.field
true
false
[]
transform source.field
transform source.field as context
map transform source.items
map transform source.items as context
flat_map transform source.items as context
helper function_name(arg1, arg2)
TargetType
    set field from expression
end
```

`transform` applies another rule selected by source type, target type when it can
be inferred, and optional context.

`map transform` applies a one-to-one transformation over a repeated field.

`flat_map transform` applies a transformation that may return many values and
concatenates the results.

`helper name(args...)` calls an external helper. Helpers are an explicit escape
hatch for logic that is not tree construction, such as symbol-table lookups or
operator conversion.

TODO: Define helper declaration, typing, purity, error reporting, and backend
binding.

TODO: Decide whether the language needs constructor expressions as ordinary
arguments to helper calls. `examples/iteration1.ntf` currently avoids that and
keeps projection construction in helpers.

## Constructors And Emit

Rules with single targets may either assign fields directly in the rule body or
emit a target constructor in a match case. Rules with `many` targets emit zero or
more target constructors.

```text
emit l.ReturnStatement
    set expression from transform source.expression as expression
    same is_explicit
end
```

The constructor target type must be the declared target type or a valid choice
alternative of the declared target type.

TODO: Decide whether `emit` should be allowed in single-target rules outside
`match`, or whether direct field assignment should be the only top-level shape
for single-target rules.

## Matching

```text
match source
    case a.BinaryExpression when source.operation == Assignment
        emit l.StoreStatement
            ...
        end

    case _
        emit l.ExpressionStatement
            ...
        end
end
```

`match` dispatches on the runtime alternative of a choice or on the concrete node
type of a value. `case _` is the default case and must be last.

Supported guards in this iteration:

```text
source.field == Name
source.field != Name
source.field is TypeName
require <guard>
```

`when` guards refine one match case. `require` guards refine an entire rule.

TODO: Decide how names such as `Assignment` are resolved when they come from
backend scalar domains rather than NDEF enums.

## Conflict Policy

Multiple rules can have the same source type, target type, and context while
using different `require` guards. This is useful for specific cases such as
string assignment and record assignment.

The first iteration does not choose a final conflict policy.

TODO: Choose one rule-selection policy:

- source order with first matching rule,
- most-specific rule based on static guard structure,
- explicit `priority <number>` on rules,
- reject overlapping rules unless one rule explicitly extends another.

## Draft Grammar

This grammar is intentionally small and omits lexical trivia.

```ebnf
file            = transform_decl alias_decl* rule_decl* ;

transform_decl  = "transform" module_name "to" module_name ;
alias_decl      = "alias" module_name "as" alias_name ;

rule_decl       = "rule" rule_name "from" type_ref "to" cardinality? type_ref
                  context? rule_body "end" ;
cardinality     = "many" ;
context         = "as" identifier ;

rule_body       = statement* ;
statement       = assignment
                | same_assignment
                | emit_statement
                | match_statement
                | require_statement ;

assignment      = "set" field_path "from" expression ;
same_assignment = "same" field_name ;
emit_statement  = "emit" type_ref constructor_body? "end" ;
match_statement = "match" expression case_clause+ "end" ;
case_clause     = "case" pattern guard? statement* ;
require_statement = "require" guard_expression ;

constructor_body = statement* ;

expression      = path
                | literal
                | list_literal
                | transform_expression
                | map_expression
                | helper_call
                | constructor_expression ;

transform_expression = "transform" expression context? ;
map_expression       = ("map" | "flat_map") transform_expression ;
helper_call          = "helper" identifier "(" argument_list? ")" ;
constructor_expression = type_ref constructor_body "end" ;

pattern         = type_ref | "_" ;
guard           = "when" guard_expression ;
guard_expression = expression ("==" | "!=" | "is") expression ;

type_ref        = identifier ("." identifier)? ;
path            = identifier ("." identifier)* ;
field_path      = identifier ("." identifier)* ;
literal         = "true" | "false" | identifier | number ;
list_literal    = "[" "]" ;
argument_list   = expression ("," expression)* ;
```

TODO: Decide whether type references must always be module-qualified after alias
expansion. Requiring qualification makes examples noisier but avoids ambiguity.

## Validation Checks

A validator should eventually reject:

- unknown source modules, target modules, types, fields, and contexts,
- assignments to fields that do not exist on the target constructor,
- missing assignments for required target fields,
- incompatible direct copies in `same`,
- `map` over non-repeated source fields,
- `flat_map` when the selected rule is not `many`,
- `emit` of a target type that is neither the declared target nor a valid choice
  alternative,
- missing or duplicate default cases in exhaustive choice matches,
- ambiguous rule selection.

TODO: Decide whether unused source fields are language errors, lints, or ignored
by default.
