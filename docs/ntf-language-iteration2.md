# NTF Language Iteration 2

Iteration 2 keeps the source-oriented rule model from iteration 1, but changes
target construction and field initialization to a constructor notation:

```text
l.ReturnStatement(
    expression = transform source.expression as expression,
    is_explicit = source.is_explicit,
)
```

This makes constructed target nodes visually cohesive and reduces procedural
noise from `set field from ...` blocks.

## Main Changes From Iteration 1

- `emit TargetType ... end` becomes `emit TargetType(...)`.
- `set field from value` becomes `field = value` inside constructors.
- Single-target rules may return one constructor expression after `=`.
- Match cases use `=>` to separate the matched source shape from the produced
  result.
- `same field` is removed from the core notation. It saved words, but it made
  constructors less uniform and hid the source of each value.

TODO: Decide whether a shorthand for same-name copies is still desirable inside
constructors, for example `.field` or `field` as sugar for
`field = source.field`. The first iteration of implementation should probably
avoid this sugar.

## Recommended Assignment Symbol

Use `=` for constructor fields.

`field = expr` reads as named argument initialization, which is the closest
mental model for this language. It is familiar from Python keyword arguments,
Kotlin named arguments, C# object initializers, TypeScript object literals, and
many configuration formats.

Avoid `:=` for now. It often means declaration or mutation in existing
languages, and NTF constructor fields should be single initialization slots.

Avoid `<-` for field initialization. It is useful when emphasizing data flow,
but it competes with transformation direction and assignment-direction
interpretations. Keeping `<-` unused leaves room for a future import, rewrite,
or reverse-mapping notation if needed.

## Rule Shape

```text
rule FunctionDefinition from a.FunctionDefinition to l.FunctionDefinition =
    l.FunctionDefinition(
        head = transform source.function_head,
        code = flat_map transform source.code as statement,
        attributes = helper attribute_names(source.attributes),
    )
end
```

A rule has:

- a unique rule name,
- a source type after `from`,
- a target type after `to`,
- optional `many` before the target type,
- optional context after `as`,
- a body introduced by `=`.

The body of a single-target rule is an expression. Usually that expression is a
constructor or a `match`.

The body of a `many` rule may be a `match` or one or more `emit`
statements. `emit` is retained because it clearly marks that a many-rule appends
one output value.

TODO: Decide whether a `many` rule should also allow returning list literals,
such as `[l.A(...), l.B(...)]`, instead of using `emit`.

## Constructors

```text
TypeName(
    field = expression,
    nested = OtherType(
        value = source.value,
    ),
)
```

A constructor names a target node type and initializes fields by name.

Rules:

- field order should not matter semantically,
- duplicate fields are invalid,
- missing required target fields are invalid unless the field is transient or
  has a declared default,
- fields may be nested constructor expressions,
- optional trailing commas are allowed.

TODO: Decide whether constructors may include comments between fields and after
commas. The examples assume yes.

## Match Expressions

```text
match source
    case a.Number =>
        l.Number(value = source.number, assigned_type = source.assigned_type)

    case a.BinaryExpression when source.operation != Assignment =>
        l.BinaryExpression(
            op = helper binary_op(source.operation),
            left = transform source.left as expression,
            right = transform source.right as expression,
            assigned_type = source.assigned_type,
        )
end
```

`match` is an expression in single-target rules and a statement-like dispatcher
in `many` rules. The syntax is intentionally the same in both contexts.

TODO: Decide whether `case _` is mandatory for choice matches or whether the
language should allow explicitly partial rules.

## Expressions

The first implementation target for iteration 2 should support:

```text
source
source.field
source.nested.field
true
false
[]
TypeName(field = value)
transform source.field
transform source.field as context
map transform source.items
map transform source.items as context
flat_map transform source.items as context
helper function_name(arg1, arg2)
match source ... end
```

TODO: Define string, numeric, enum, and backend-scalar literal syntax. The
examples currently use symbolic names such as `Assignment` and `Lhs` without
formal declaration.

## Draft Grammar

This grammar is a compact sketch, not an implementation grammar.

```ebnf
file             = transform_decl alias_decl* rule_decl* ;

transform_decl   = "transform" module_name "to" module_name ;
alias_decl       = "alias" module_name "as" alias_name ;

rule_decl        = "rule" rule_name "from" type_ref "to" cardinality? type_ref
                   context? require_clause* "=" rule_result "end" ;
cardinality      = "many" ;
context          = "as" identifier ;
require_clause   = "require" guard_expression ;

rule_result      = expression | many_body ;
many_body        = (emit_statement | match_expression)+ ;

emit_statement   = "emit" constructor ;

expression       = path
                 | literal
                 | list_literal
                 | constructor
                 | transform_expression
                 | map_expression
                 | helper_call
                 | match_expression ;

constructor      = type_ref "(" field_init_list? ")" ;
field_init_list  = field_init ("," field_init)* ","? ;
field_init       = field_name "=" expression ;

match_expression = "match" expression case_clause+ "end" ;
case_clause      = "case" pattern guard? "=>" case_result ;
case_result      = expression | emit_statement+ ;

transform_expression = "transform" expression context? ;
map_expression       = ("map" | "flat_map") transform_expression ;
helper_call          = "helper" identifier "(" argument_list? ")" ;

pattern          = type_ref | "_" ;
guard            = "when" guard_expression ;
guard_expression = expression ("==" | "!=" | "is") expression ;

type_ref         = identifier ("." identifier)? ;
path             = identifier ("." identifier)* ;
literal          = "true" | "false" | identifier | number ;
list_literal     = "[" "]" ;
argument_list    = expression ("," expression)* ","? ;
```

TODO: Refine `rule_result` and `case_result`. A real grammar may want separate
single-result and many-result syntactic categories to make cardinality errors
easier to report.

## Open Design Points

- Rule overlap and priority for specific cases such as string assignment versus
  generic assignment.
- Partial rule syntax for source alternatives that are invalid in a given
  context.
- Helper declaration and type checking.
- Module resolution for referenced `.ndef` files.
- Whether ignored source fields should be explicit.
- Whether transient target fields are excluded from constructor completeness.

