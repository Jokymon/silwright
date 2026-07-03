"""Central semantic analysis for parsed struct-gen modules."""

from dataclasses import dataclass

from struct_gen.model import (
    Choice,
    Definition,
    Enum,
    Field,
    Module,
    Node,
    ParsedDefinitionFile,
    Trait,
)
from struct_gen.naming import cpp_name


class SemanticError(ValueError):
    """Raised when parsed definitions are not semantically valid."""


@dataclass(frozen=True, slots=True)
class ValidatedModel:
    """A semantically valid module and the derived data needed by generators."""

    parsed: ParsedDefinitionFile
    declarations: dict[str, Definition]
    mappings: dict[str, str]
    node_fields: dict[str, tuple[Field, ...]]
    ordered_choices: tuple[Choice, ...]
    ordered_nodes: tuple[Node, ...]
    visitable_names: frozenset[str]

    @property
    def module(self) -> Module:
        return self.parsed.module


def analyze(parsed: ParsedDefinitionFile) -> ValidatedModel:
    """Validate parsed input and compute all shared generator metadata."""
    declarations = _declarations_by_name(parsed.module)
    mappings = _mappings_by_name(parsed)
    node_fields = _resolve_node_fields(parsed.module, declarations)
    _validate_field_types(parsed.module, declarations, mappings)
    ordered_choices = _order_choices(parsed.module, declarations)
    ordered_nodes = _order_nodes(parsed.module, declarations)
    _validate_generated_names(parsed.module)
    visitable_names = _visitable_definition_names(parsed.module, declarations)
    return ValidatedModel(
        parsed=parsed,
        declarations=declarations,
        mappings=mappings,
        node_fields=node_fields,
        ordered_choices=ordered_choices,
        ordered_nodes=ordered_nodes,
        visitable_names=frozenset(visitable_names),
    )


def ensure_validated(model: ParsedDefinitionFile | ValidatedModel) -> ValidatedModel:
    """Return an existing validated model or analyze raw parsed input."""
    return model if isinstance(model, ValidatedModel) else analyze(model)


def _declarations_by_name(module: Module) -> dict[str, Definition]:
    result: dict[str, Definition] = {}
    for declaration in module.definitions:
        if declaration.name in result:
            raise SemanticError(f"duplicate definition: {declaration.name}")
        result[declaration.name] = declaration
    return result


def _mappings_by_name(parsed: ParsedDefinitionFile) -> dict[str, str]:
    result: dict[str, str] = {}
    for mapping in parsed.type_mappings:
        if mapping.source_type in result:
            raise SemanticError(f"duplicate C++ backend mapping: {mapping.source_type}")
        result[mapping.source_type] = mapping.cpp_type
    return result


def _resolve_node_fields(
    module: Module,
    declarations: dict[str, Definition],
) -> dict[str, tuple[Field, ...]]:
    traits = {item.name: item for item in module.definitions if isinstance(item, Trait)}
    for trait in traits.values():
        _reject_duplicate_fields(trait.name, trait.fields)

    result: dict[str, tuple[Field, ...]] = {}
    for node in (item for item in module.definitions if isinstance(item, Node)):
        if len(set(node.traits)) != len(node.traits):
            raise SemanticError(f"duplicate trait on {node.name}")
        fields: list[Field] = []
        for trait_name in node.traits:
            target = declarations.get(trait_name)
            if target is None:
                raise SemanticError(f"unknown trait {trait_name!r} on {node.name}")
            if not isinstance(target, Trait):
                raise SemanticError(f"{trait_name!r} on {node.name} is not a trait")
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
            raise SemanticError(f"duplicate field {field.name!r} in {owner}")
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
                raise SemanticError(f"unknown field type {field.type_name!r} in {owner.name}")


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
            raise SemanticError(f"cyclic choice dependency involving {item.name}")
        if item.name in visited:
            return
        visiting.add(item.name)
        for alternative in item.alternatives:
            target = declarations.get(alternative)
            if target is None:
                raise SemanticError(
                    f"unknown choice alternative {alternative!r} in {item.name}"
                )
            if isinstance(target, Enum):
                raise SemanticError(f"enum {alternative!r} cannot be a choice alternative")
            if isinstance(target, Trait):
                raise SemanticError(f"trait {alternative!r} cannot be a choice alternative")
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
            raise SemanticError(f"cyclic value dependency involving {node.name}")
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


def _validate_generated_names(module: Module) -> None:
    if any(cpp_name(item.name) == "visitor" for item in module.definitions):
        raise SemanticError("definition name conflicts with generated visitor class")


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
