"""Generate C++ declarations from parsed node definitions."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from silwright.generated_file import GeneratedFile, write_generated_files
from silwright.model import Choice, Enum, Field, Node, ParsedDefinitionFile, Trait
from silwright.naming import cpp_name
from silwright.parser import parse_definition_file
from silwright.semantic import SemanticError, ValidatedModel, analyze, ensure_validated

GenerationError = SemanticError


@dataclass(frozen=True, slots=True)
class GeneratedCpp:
    """The header and source generated for one definition file."""

    header: str
    source: str


def generate_cpp(
    model: ParsedDefinitionFile | ValidatedModel, header_name: str
) -> GeneratedCpp:
    """Generate a C++ header and source for a parsed definition file."""
    validated = ensure_validated(model)
    parsed = validated.parsed
    module = parsed.module
    declarations = validated.declarations
    mappings = validated.mappings
    enums = tuple(item for item in module.definitions if isinstance(item, Enum))
    traits = tuple(item for item in module.definitions if isinstance(item, Trait))
    struct_types = tuple(
        item for item in module.definitions if isinstance(item, (Trait, Node))
    )
    choices = validated.ordered_choices

    sections: list[str] = []
    if enums:
        sections.append("\n\n".join(_render_enum(item) for item in enums))
    if struct_types:
        sections.append("\n".join(f"struct {cpp_name(item.name)};" for item in struct_types))
    if traits:
        sections.append(
            "\n\n".join(
                _render_struct(item.name, item.fields, declarations, mappings)
                for item in traits
            )
        )
    if choices:
        sections.append("\n\n".join(_render_choice(item, declarations) for item in choices))
    if validated.repeated_pointer_choices:
        sections.append(
            "\n\n".join(
                _render_choice_list_alias(item)
                for item in validated.repeated_pointer_choices
            )
        )
    ordered_nodes = validated.ordered_nodes
    if ordered_nodes:
        sections.append(
            "\n\n".join(
                _render_struct(
                    item.name,
                    item.fields,
                    declarations,
                    mappings,
                    item.traits,
                )
                for item in ordered_nodes
            )
        )

    rendered_body = "\n\n".join(sections)
    include_spellings = dict.fromkeys(
        (
            "<memory>",
            "<optional>",
            "<string>",
            "<variant>",
            "<vector>",
            *parsed.backend_includes,
        )
    )
    includes = "\n".join(f"#include {spelling}" for spelling in include_spellings)
    header = (
        "#pragma once\n\n"
        f"{includes}\n\n"
        f"namespace {module.name} {{\n\n"
        f"{rendered_body}\n\n"
        f"}}  // namespace {module.name}\n"
    )
    source = f'#include "{header_name}"\n'
    return GeneratedCpp(header=header, source=source)


def generate_cpp_files(
    definition_path: Path,
    *,
    generated_at: datetime | None = None,
    validated: ValidatedModel | None = None,
) -> tuple[Path, Path]:
    """Parse a definition and write sibling .hpp and .cpp files."""
    parsed = validated or analyze(parse_definition_file(definition_path))
    header_path = definition_path.with_suffix(".hpp")
    source_path = definition_path.with_suffix(".cpp")
    generated = generate_cpp(parsed, header_path.name)
    write_generated_files(
        (
            GeneratedFile(header_path, generated.header),
            GeneratedFile(source_path, generated.source),
        ),
        definition_path,
    )
    return header_path, source_path


def _render_enum(item: Enum) -> str:
    values = ",\n".join(f"    {value}" for value in item.values)
    return f"enum class {cpp_name(item.name)}_t {{\n{values}\n}};"


def _render_choice(
    item: Choice,
    declarations: dict[str, Node | Trait | Choice | Enum],
) -> str:
    alternatives: list[str] = []
    for name in item.alternatives:
        alternatives.append(cpp_name(name))
    return f"using {cpp_name(item.name)} = std::variant<{', '.join(alternatives)}>;"


def _render_choice_list_alias(item: Choice) -> str:
    name = cpp_name(item.name)
    return f"using {name}_list = std::vector<std::unique_ptr<{name}>>;"


def _render_struct(
    name: str,
    fields_to_render: tuple[Field, ...],
    declarations: dict[str, Node | Trait | Choice | Enum],
    mappings: dict[str, str],
    traits: tuple[str, ...] = (),
) -> str:
    fields: list[str] = []
    for field in fields_to_render:
        pointer_backed = False
        if field.type_name in mappings:
            field_type = mappings[field.type_name]
        else:
            target = declarations.get(field.type_name)
            if isinstance(target, Enum):
                field_type = f"{cpp_name(target.name)}_t"
            elif isinstance(target, (Node, Choice)):
                named_type = cpp_name(target.name)
                pointer_backed = not field.by_value
                field_type = named_type if field.by_value else f"std::unique_ptr<{named_type}>"
            else:
                raise AssertionError("validated field type is not C++ representable")
        if (
            field.multiple
            and not field.by_value
            and isinstance(declarations.get(field.type_name), Choice)
        ):
            field_type = f"{cpp_name(field.type_name)}_list"
        elif field.multiple:
            field_type = f"std::vector<{field_type}>"
        elif field.optional and not pointer_backed:
            field_type = f"std::optional<{field_type}>"
        fields.append(f"    {field_type} {field.name};")
    members = "\n".join(fields)
    bases = ""
    if traits:
        bases = " : " + ", ".join(f"public {cpp_name(trait)}" for trait in traits)
    return f"struct {cpp_name(name)}{bases} {{\n{members}\n}};"
