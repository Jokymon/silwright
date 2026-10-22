"""Central semantic analysis for parsed Silwright modules."""

import re
from dataclasses import dataclass

from silwright.diagnostics import DiagnosticError, ErrorCode, SourceLocation
from silwright.model import (
    Choice,
    Definition,
    Enum,
    Field,
    Module,
    Node,
    ParsedDefinitionFile,
    Trait,
)
from silwright.naming import cpp_name

_CPP_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_CPP_KEYWORDS = frozenset(
    {
        "alignas", "alignof", "and", "and_eq", "asm", "auto", "bitand", "bitor",
        "bool", "break", "case", "catch", "char", "char8_t", "char16_t", "char32_t",
        "class", "compl", "concept", "const", "consteval", "constexpr", "constinit",
        "const_cast", "continue", "co_await", "co_return", "co_yield", "decltype",
        "default", "delete", "do", "double", "dynamic_cast", "else", "enum", "explicit",
        "export", "extern", "false", "float", "for", "friend", "goto", "if", "inline",
        "int", "long", "mutable", "namespace", "new", "noexcept", "not", "not_eq",
        "nullptr", "operator", "or", "or_eq", "private", "protected", "public", "register",
        "reinterpret_cast", "requires", "return", "short", "signed", "sizeof", "static",
        "static_assert", "static_cast", "struct", "switch", "template", "this",
        "thread_local", "throw", "true", "try", "typedef", "typeid", "typename", "union",
        "unsigned", "using", "virtual", "void", "volatile", "wchar_t", "while", "xor",
        "xor_eq",
    }
)


class SemanticError(DiagnosticError):
    """Raised when parsed definitions are not semantically valid."""

    def __init__(
        self,
        message: str,
        code: ErrorCode,
        location: SourceLocation | None = None,
    ) -> None:
        super().__init__(code, message, location)


@dataclass(frozen=True, slots=True)
class ValidatedModel:
    """A semantically valid module and the derived data needed by generators."""

    parsed: ParsedDefinitionFile
    declarations: dict[str, Definition]
    mappings: dict[str, str]
    node_traits: dict[str, tuple[str, ...]]
    node_fields: dict[str, tuple[Field, ...]]
    ordered_choices: tuple[Choice, ...]
    repeated_pointer_choices: tuple[Choice, ...]
    ordered_nodes: tuple[Node, ...]
    visitable_names: frozenset[str]
    transformer_multiple_names: frozenset[str]
    transformer_return_choices: dict[str, Choice]

    @property
    def module(self) -> Module:
        return self.parsed.module


def analyze(parsed: ParsedDefinitionFile) -> ValidatedModel:
    """Validate parsed input and compute all shared generator metadata."""
    declarations = _declarations_by_name(parsed.module)
    mappings = _mappings_by_name(parsed)
    _validate_member_uniqueness(parsed.module)
    _validate_modifiers(parsed.module, declarations)
    _validate_field_types(parsed.module, declarations, mappings)
    ordered_choices = _order_choices(parsed.module, declarations)
    _validate_node_choice_membership(parsed.module, declarations)
    node_traits = _resolve_node_traits(parsed.module, declarations)
    node_fields = _resolve_node_fields(parsed.module, declarations, node_traits)
    repeated_pointer_choices = _repeated_pointer_choices(
        parsed.module, declarations, ordered_choices
    )
    ordered_nodes = _order_nodes(parsed.module, declarations)
    _validate_cpp_names(parsed.module, repeated_pointer_choices)
    visitable_names = _visitable_definition_names(parsed.module, declarations)
    transformer_multiple_names = _transformer_multiple_definition_names(
        parsed.module, declarations, visitable_names
    )
    transformer_return_choices = _transformer_return_choices(
        parsed.module, declarations, visitable_names
    )
    _validate_transformer_return_choices(
        parsed.module, declarations, transformer_return_choices
    )
    return ValidatedModel(
        parsed=parsed,
        declarations=declarations,
        mappings=mappings,
        node_traits=node_traits,
        node_fields=node_fields,
        ordered_choices=ordered_choices,
        repeated_pointer_choices=repeated_pointer_choices,
        ordered_nodes=ordered_nodes,
        visitable_names=frozenset(visitable_names),
        transformer_multiple_names=frozenset(transformer_multiple_names),
        transformer_return_choices=transformer_return_choices,
    )


def ensure_validated(model: ParsedDefinitionFile | ValidatedModel) -> ValidatedModel:
    """Return an existing validated model or analyze raw parsed input."""
    return model if isinstance(model, ValidatedModel) else analyze(model)


def _declarations_by_name(module: Module) -> dict[str, Definition]:
    result: dict[str, Definition] = {}
    for declaration in module.definitions:
        if declaration.name in result:
            raise SemanticError(
                f"duplicate definition: {declaration.name}",
                ErrorCode.DUPLICATE_DEFINITION,
                declaration.location,
            )
        result[declaration.name] = declaration
    return result


def _mappings_by_name(parsed: ParsedDefinitionFile) -> dict[str, str]:
    result: dict[str, str] = {}
    for mapping in parsed.type_mappings:
        if mapping.source_type in result:
            raise SemanticError(
                f"duplicate C++ backend mapping: {mapping.source_type}",
                ErrorCode.DUPLICATE_BACKEND_MAPPING,
                mapping.location,
            )
        result[mapping.source_type] = mapping.cpp_type
    return result


def _validate_member_uniqueness(module: Module) -> None:
    for definition in module.definitions:
        if isinstance(definition, Enum):
            _reject_duplicate_names(
                definition.name,
                "enum entry",
                definition.values,
                definition.location,
            )
        elif isinstance(definition, Choice):
            _reject_duplicate_names(
                definition.name,
                "choice alternative",
                definition.alternatives,
                definition.location,
            )


def _reject_duplicate_names(
    owner: str,
    kind: str,
    names: tuple[str, ...],
    location: SourceLocation | None = None,
) -> None:
    seen: set[str] = set()
    for name in names:
        if name in seen:
            raise SemanticError(
                f"duplicate {kind} {name!r} in {owner}",
                ErrorCode.DUPLICATE_MEMBER,
                location,
            )
        seen.add(name)


def _validate_modifiers(
    module: Module, declarations: dict[str, Definition]
) -> None:
    for owner in module.definitions:
        if not isinstance(owner, (Node, Trait)):
            continue
        for field in owner.fields:
            if field.multiple and field.optional:
                raise SemanticError(
                    f"field {field.name!r} in {owner.name} cannot be multiple and optional",
                    ErrorCode.INVALID_FIELD_MODIFIER,
                    field.location,
                )
            if field.fixed and not field.multiple:
                raise SemanticError(
                    f"field {field.name!r} in {owner.name} cannot be fixed without "
                    "being multiple",
                    ErrorCode.INVALID_FIELD_MODIFIER,
                    field.location,
                )
            target = declarations.get(field.type_name)
            if isinstance(owner, Trait) and field.by_value and isinstance(
                target, (Node, Choice)
            ):
                raise SemanticError(
                    f"trait field {field.name!r} in {owner.name} cannot contain "
                    "a node or choice by value",
                    ErrorCode.INVALID_FIELD_MODIFIER,
                    field.location,
                )


def _resolve_node_traits(
    module: Module,
    declarations: dict[str, Definition],
) -> dict[str, tuple[str, ...]]:
    result = {
        node.name: list(dict.fromkeys(node.traits))
        for node in module.definitions
        if isinstance(node, Node)
    }

    def validate_traits(owner: Node | Choice, trait_names: tuple[str, ...]) -> None:
        for trait_name in trait_names:
            target = declarations.get(trait_name)
            if target is None:
                raise SemanticError(
                    f"unknown trait {trait_name!r} on {owner.name}",
                    ErrorCode.UNKNOWN_TRAIT,
                    owner.location,
                )
            if not isinstance(target, Trait):
                raise SemanticError(
                    f"{trait_name!r} on {owner.name} is not a trait",
                    ErrorCode.INVALID_TRAIT_REFERENCE,
                    owner.location,
                )

    for node in (item for item in module.definitions if isinstance(item, Node)):
        validate_traits(node, node.traits)

    def add_choice_traits(
        choice: Choice, traits: tuple[str, ...], visited: set[str]
    ) -> None:
        if choice.name in visited:
            return
        visited.add(choice.name)
        for alternative in choice.alternatives:
            target = declarations.get(alternative)
            if isinstance(target, Node):
                effective = result[target.name]
                effective.extend(trait for trait in traits if trait not in effective)
            elif isinstance(target, Choice):
                add_choice_traits(target, traits, visited)

    for choice in (item for item in module.definitions if isinstance(item, Choice)):
        validate_traits(choice, choice.all_traits)
        add_choice_traits(choice, tuple(dict.fromkeys(choice.all_traits)), set())

    return {name: tuple(traits) for name, traits in result.items()}


def _resolve_node_fields(
    module: Module,
    declarations: dict[str, Definition],
    node_traits: dict[str, tuple[str, ...]],
) -> dict[str, tuple[Field, ...]]:
    traits = {item.name: item for item in module.definitions if isinstance(item, Trait)}
    for trait in traits.values():
        _reject_duplicate_fields(trait.name, trait.fields)

    result: dict[str, tuple[Field, ...]] = {}
    for node in (item for item in module.definitions if isinstance(item, Node)):
        fields: list[Field] = []
        for trait_name in node_traits[node.name]:
            target = declarations[trait_name]
            assert isinstance(target, Trait)
            fields.extend(target.fields)
        fields.extend(node.fields)
        flattened = tuple(fields)
        _reject_duplicate_fields(node.name, flattened)
        result[node.name] = flattened
    return result


def _reject_duplicate_fields(owner: str, fields: tuple[Field, ...]) -> None:
    seen: set[str] = set()
    for field in fields:
        if field.name in seen:
            raise SemanticError(
                f"duplicate field {field.name!r} in {owner}",
                ErrorCode.DUPLICATE_FIELD,
                field.location,
            )
        seen.add(field.name)


def _validate_field_types(
    module: Module,
    declarations: dict[str, Definition],
    mappings: dict[str, str],
) -> None:
    for owner in module.definitions:
        if not isinstance(owner, (Node, Trait)):
            continue
        for field in owner.fields:
            if field.type_name in mappings:
                continue
            target = declarations.get(field.type_name)
            if not isinstance(target, (Node, Choice, Enum)):
                raise SemanticError(
                    f"unknown field type {field.type_name!r} in {owner.name}",
                    ErrorCode.UNKNOWN_FIELD_TYPE,
                    field.type_location,
                )


def _order_choices(
    module: Module,
    declarations: dict[str, Definition],
) -> tuple[Choice, ...]:
    choices = {item.name: item for item in module.definitions if isinstance(item, Choice)}
    ordered: list[Choice] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(item: Choice) -> None:
        if item.name in visiting:
            raise SemanticError(
                f"cyclic choice dependency involving {item.name}",
                ErrorCode.CYCLIC_CHOICE,
                item.location,
            )
        if item.name in visited:
            return
        visiting.add(item.name)
        for alternative in item.alternatives:
            target = declarations.get(alternative)
            if target is None:
                raise SemanticError(
                    f"unknown choice alternative {alternative!r} in {item.name}",
                    ErrorCode.UNKNOWN_CHOICE_ALTERNATIVE,
                    item.location,
                )
            if isinstance(target, Enum):
                raise SemanticError(
                    f"enum {alternative!r} cannot be a choice alternative",
                    ErrorCode.INVALID_CHOICE_ALTERNATIVE,
                    item.location,
                )
            if isinstance(target, Trait):
                raise SemanticError(
                    f"trait {alternative!r} cannot be a choice alternative",
                    ErrorCode.INVALID_CHOICE_ALTERNATIVE,
                    item.location,
                )
            if isinstance(target, Choice):
                visit(target)
        visiting.remove(item.name)
        visited.add(item.name)
        ordered.append(item)

    for choice in choices.values():
        visit(choice)
    return tuple(ordered)


def _order_nodes(
    module: Module,
    declarations: dict[str, Definition],
) -> tuple[Node, ...]:
    nodes = tuple(item for item in module.definitions if isinstance(item, Node))
    ordered: list[Node] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def choice_node_dependencies(choice: Choice, seen: set[str]) -> tuple[Node, ...]:
        if choice.name in seen:
            return ()
        seen.add(choice.name)
        dependencies: list[Node] = []
        for alternative in choice.alternatives:
            target = declarations[alternative]
            if isinstance(target, Node):
                dependencies.append(target)
            elif isinstance(target, Choice):
                dependencies.extend(choice_node_dependencies(target, seen))
        return tuple(dependencies)

    def visit(node: Node) -> None:
        if node.name in visiting:
            raise SemanticError(
                f"cyclic value dependency involving {node.name}",
                ErrorCode.CYCLIC_VALUE_DEPENDENCY,
                node.location,
            )
        if node.name in visited:
            return
        visiting.add(node.name)
        for field in node.fields:
            if not field.by_value:
                continue
            target = declarations.get(field.type_name)
            if isinstance(target, Node):
                visit(target)
            elif isinstance(target, Choice):
                for dependency in choice_node_dependencies(target, set()):
                    visit(dependency)
        visiting.remove(node.name)
        visited.add(node.name)
        ordered.append(node)

    for node in nodes:
        visit(node)
    return tuple(ordered)


def _validate_node_choice_membership(
    module: Module,
    declarations: dict[str, Definition],
) -> None:
    containing_choices: dict[str, Choice] = {}
    for choice in (item for item in module.definitions if isinstance(item, Choice)):
        for alternative in choice.alternatives:
            if not isinstance(declarations[alternative], Node):
                continue
            previous = containing_choices.get(alternative)
            if previous is not None:
                raise SemanticError(
                    f"node {alternative!r} is a member of multiple choices "
                    f"({previous.name!r} and {choice.name!r})",
                    ErrorCode.MULTIPLE_CHOICE_MEMBERSHIP,
                    choice.location,
                )
            containing_choices[alternative] = choice


def _repeated_pointer_choices(
    module: Module,
    declarations: dict[str, Definition],
    ordered_choices: tuple[Choice, ...],
) -> tuple[Choice, ...]:
    referenced = {
        field.type_name
        for definition in module.definitions
        if isinstance(definition, (Node, Trait))
        for field in definition.fields
        if field.multiple
        and not field.by_value
        and isinstance(declarations.get(field.type_name), Choice)
    }
    return tuple(choice for choice in ordered_choices if choice.name in referenced)


def _validate_cpp_names(
    module: Module, repeated_pointer_choices: tuple[Choice, ...]
) -> None:
    _validate_cpp_identifier("module", module.name, module.location)
    generated: dict[str, tuple[str, SourceLocation | None]] = {}
    for definition in module.definitions:
        generated_name = cpp_name(definition.name)
        if isinstance(definition, Enum):
            generated_name += "_t"
        _validate_cpp_identifier(
            f"definition {definition.name!r}", generated_name, definition.location
        )
        previous = generated.get(generated_name)
        if previous is not None:
            previous_name, _previous_location = previous
            raise SemanticError(
                f"C++ name collision: {previous_name!r} and {definition.name!r} "
                f"both generate {generated_name!r}",
                ErrorCode.CPP_NAME_COLLISION,
                definition.location,
            )
        generated[generated_name] = (definition.name, definition.location)

        if isinstance(definition, (Node, Trait)):
            for field in definition.fields:
                _validate_cpp_identifier(
                    f"field {field.name!r} in {definition.name}",
                    field.name,
                    field.location,
                )
        elif isinstance(definition, Enum):
            for value in definition.values:
                _validate_cpp_identifier(
                    f"enum entry {value!r} in {definition.name}",
                    value,
                    definition.location,
                )

    for choice in repeated_pointer_choices:
        alias_name = f"{cpp_name(choice.name)}_list"
        previous = generated.get(alias_name)
        if previous is not None:
            previous_name, _previous_location = previous
            raise SemanticError(
                f"C++ name collision: generated list alias for {choice.name!r} "
                f"conflicts with {previous_name!r} as {alias_name!r}",
                ErrorCode.CPP_NAME_COLLISION,
                choice.location,
            )
        generated[alias_name] = (f"{choice.name} list alias", choice.location)

    for reserved_name, description in (
        ("visitor", "generated visitor class"),
        ("transformer", "generated transformer class"),
        ("as_trait", "generated trait accessor"),
        ("as_trait_detail", "generated trait accessor implementation namespace"),
    ):
        if reserved_name in generated:
            raise SemanticError(
                f"definition name conflicts with {description}",
                ErrorCode.CPP_NAME_COLLISION,
                generated[reserved_name][1],
            )


def _validate_cpp_identifier(
    subject: str, name: str, location: SourceLocation | None = None
) -> None:
    if _CPP_IDENTIFIER.fullmatch(name) is None:
        raise SemanticError(
            f"{subject} generates invalid C++ identifier {name!r}",
            ErrorCode.INVALID_CPP_IDENTIFIER,
            location,
        )
    if name in _CPP_KEYWORDS:
        raise SemanticError(
            f"{subject} generates reserved C++ keyword {name!r}",
            ErrorCode.RESERVED_CPP_KEYWORD,
            location,
        )


def _visitable_definition_names(
    module: Module,
    declarations: dict[str, Definition],
) -> set[str]:
    structured = {
        item.name: item for item in module.definitions if isinstance(item, (Node, Choice))
    }
    referenced: set[str] = set()
    visitable: set[str] = set()
    for item in module.definitions:
        if isinstance(item, Node):
            for field in item.fields:
                if field.type_name not in structured:
                    continue
                referenced.add(field.type_name)
                if not field.by_value and not field.transient:
                    visitable.add(field.type_name)
        elif isinstance(item, Choice):
            referenced.update(
                alternative for alternative in item.alternatives if alternative in structured
            )
    visitable.update(structured.keys() - referenced)
    pending = list(visitable)
    while pending:
        item = declarations[pending.pop()]
        if not isinstance(item, Choice):
            continue
        for alternative in item.alternatives:
            if alternative in structured and alternative not in visitable:
                visitable.add(alternative)
                pending.append(alternative)
    return visitable


def _transformer_multiple_definition_names(
    module: Module,
    declarations: dict[str, Definition],
    visitable_names: set[str],
) -> set[str]:
    structured = {
        item.name: item for item in module.definitions if isinstance(item, (Node, Choice))
    }
    multiple: set[str] = set()
    for item in module.definitions:
        if not isinstance(item, Node):
            continue
        for field in item.fields:
            if not field.multiple or field.by_value or field.transient:
                continue
            if field.type_name in structured and field.type_name in visitable_names:
                multiple.add(field.type_name)

    changed = True
    while changed:
        changed = False
        for name in tuple(multiple):
            item = declarations[name]
            if not isinstance(item, Choice):
                continue
            for alternative in item.alternatives:
                if alternative in structured and alternative not in multiple:
                    multiple.add(alternative)
                    changed = True
        for item in structured.values():
            if not isinstance(item, Choice) or item.name in multiple:
                continue
            if any(alternative in multiple for alternative in item.alternatives):
                multiple.add(item.name)
                changed = True
    return multiple


def _transformer_return_choices(
    module: Module,
    declarations: dict[str, Definition],
    visitable_names: set[str],
) -> dict[str, Choice]:
    result: dict[str, Choice] = {}
    for choice in (
        item
        for item in module.definitions
        if isinstance(item, Choice) and item.name in visitable_names
    ):
        for alternative in choice.alternatives:
            target = declarations[alternative]
            if not isinstance(target, Node) or alternative not in visitable_names:
                continue
            result[alternative] = choice
    return result


def _validate_transformer_return_choices(
    module: Module,
    declarations: dict[str, Definition],
    transformer_return_choices: dict[str, Choice],
) -> None:
    for item in module.definitions:
        if not isinstance(item, Node):
            continue
        for field in item.fields:
            target = declarations.get(field.type_name)
            if (
                field.by_value
                or field.transient
                or not isinstance(target, Node)
                or target.name not in transformer_return_choices
            ):
                continue
            choice = transformer_return_choices[target.name]
            raise SemanticError(
                f"field {field.name!r} in {item.name} references node {target.name!r} "
                f"directly, but transformer rewrites that node as choice {choice.name!r}",
                ErrorCode.DIRECT_TRANSFORMER_NODE_REFERENCE,
                field.location,
            )
