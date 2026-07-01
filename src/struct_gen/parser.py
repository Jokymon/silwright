"""Parsers for node definitions and C++ backend mappings."""

from pathlib import Path

from lark import Lark, Token, Transformer, v_args

from struct_gen.model import (
    Choice,
    CppBackendConfig,
    Definition,
    Enum,
    Field,
    Module,
    Node,
    ParsedDefinitionFile,
    TypeMapping,
)

_NDEF_GRAMMAR = r"""
    start: _NL* module_decl _NL+ definition*
    module_decl: "module" NAME

    ?definition: node_def | choice_def | enum_def
    node_def: "node" NAME _NL+ field* "end" _NL+
    field: NAME ":" STAR? VALUE? NAME _NL+
    choice_def: "choice" NAME _NL+ choice_option_list _NL+ "end" _NL+
    enum_def: "enum" NAME _NL+ flexible_option_list _NL+ "end" _NL+
    choice_option_list: flexible_option_list
    flexible_option_list: NAME (_CHOICE_SEPARATOR NAME)*

    NAME: /[A-Za-z_][A-Za-z0-9_]*/
    STAR: "*"
    VALUE.2: "value"
    _CHOICE_SEPARATOR.2: /\|[ \t]*(?:\r?\n[ \t]*)?|\r?\n[ \t]*\|[ \t]*(?:\r?\n[ \t]*)?/
    _NL: /\r?\n/
    %import common.WS_INLINE
    %ignore WS_INLINE
    %ignore /(?m:^[ \t]*\/\/[^\r\n]*(?:\r?\n|$))/
    %ignore /\/\/[^\r\n]*/
"""

_MAP_GRAMMAR = r"""
    start: _NL* entry*
    ?entry: include | mapping
    include: "@include" INCLUDE _NL+
    mapping: NAME ":" CPP_TYPE _NL+

    NAME: /[A-Za-z_][A-Za-z0-9_]*/
    INCLUDE: /<[^>\r\n]+>|"[^"\r\n]+"/
    CPP_TYPE: /[^\r\n#]+/
    _NL: /\r?\n/
    %import common.WS_INLINE
    %ignore WS_INLINE
    %ignore /#[^\r\n]*/
"""

_NDEF_PARSER = Lark(_NDEF_GRAMMAR, parser="lalr")
_MAP_PARSER = Lark(_MAP_GRAMMAR, parser="lalr")


def _text(token: Token) -> str:
    return str(token)


@v_args(inline=True)
class _NodeTransformer(Transformer[Token, object]):
    def module_decl(self, name: Token) -> str:
        return _text(name)

    def field(self, name: Token, *type_parts: Token) -> Field:
        type_name = _text(type_parts[-1])
        modifiers = {part.type for part in type_parts[:-1]}
        return Field(
            name=_text(name),
            type_name=type_name,
            multiple="STAR" in modifiers,
            by_value="VALUE" in modifiers,
        )

    def node_def(self, name: Token, *fields: Field) -> Node:
        return Node(name=_text(name), fields=tuple(fields))

    def flexible_option_list(self, *names: Token) -> tuple[str, ...]:
        return tuple(map(_text, names))

    def choice_option_list(self, names: tuple[str, ...]) -> tuple[str, ...]:
        return names

    def choice_def(self, name: Token, alternatives: tuple[str, ...]) -> Choice:
        return Choice(name=_text(name), alternatives=alternatives)

    def enum_def(self, name: Token, values: tuple[str, ...]) -> Enum:
        return Enum(name=_text(name), values=values)

    def start(self, module_name: str, *definitions: Definition) -> Module:
        return Module(name=module_name, definitions=tuple(definitions))


@v_args(inline=True)
class _MappingTransformer(Transformer[Token, object]):
    def include(self, spelling: Token) -> str:
        return _text(spelling)

    def mapping(self, source_type: Token, cpp_type: Token) -> TypeMapping:
        return TypeMapping(source_type=_text(source_type), cpp_type=_text(cpp_type).strip())

    def start(self, *entries: TypeMapping | str) -> CppBackendConfig:
        return CppBackendConfig(
            type_mappings=tuple(entry for entry in entries if isinstance(entry, TypeMapping)),
            includes=tuple(entry for entry in entries if isinstance(entry, str)),
        )


def parse_definitions(source: str) -> Module:
    """Parse the contents of one .ndef file."""
    result = _NodeTransformer().transform(_NDEF_PARSER.parse(_terminated(source)))
    assert isinstance(result, Module)
    return result


def parse_type_mappings(source: str) -> tuple[TypeMapping, ...]:
    """Parse the contents of one .map file."""
    return parse_cpp_backend_config(source).type_mappings


def parse_cpp_backend_config(source: str) -> CppBackendConfig:
    """Parse mappings and include directives from backend_cpp.map content."""
    result = _MappingTransformer().transform(_MAP_PARSER.parse(_terminated(source)))
    assert isinstance(result, CppBackendConfig)
    return result


def parse_definition_file(path: Path) -> ParsedDefinitionFile:
    """Parse a .ndef file and the sibling backend_cpp.map file."""
    if path.suffix != ".ndef":
        raise ValueError(f"definition file must use the .ndef suffix: {path}")

    mapping_path = path.parent / "backend_cpp.map"
    module = parse_definitions(path.read_text(encoding="utf-8"))
    backend = parse_cpp_backend_config(mapping_path.read_text(encoding="utf-8"))
    return ParsedDefinitionFile(
        module=module,
        type_mappings=backend.type_mappings,
        backend_includes=backend.includes,
    )


def _terminated(source: str) -> str:
    """Normalize the grammar's line-oriented input terminator."""
    return source if source.endswith(("\n", "\r")) else f"{source}\n"
