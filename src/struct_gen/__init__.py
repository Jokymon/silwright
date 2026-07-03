"""Parse node descriptions used to generate C++ code."""

from struct_gen.dump_generator import GeneratedDumpCpp, generate_dump_cpp
from struct_gen.generator import GeneratedCpp, GenerationError, generate_cpp
from struct_gen.model import (
    Choice,
    CppBackendConfig,
    Enum,
    Field,
    Module,
    Node,
    ParsedDefinitionFile,
    Trait,
    TypeMapping,
)
from struct_gen.naming import cpp_name
from struct_gen.parser import (
    parse_cpp_backend_config,
    parse_definition_file,
    parse_definitions,
    parse_type_mappings,
)
from struct_gen.semantic import SemanticError, ValidatedModel, analyze
from struct_gen.visitor_generator import GeneratedVisitorCpp, generate_visitor_cpp

__all__ = [
    "Choice",
    "CppBackendConfig",
    "Enum",
    "Field",
    "GeneratedCpp",
    "GeneratedDumpCpp",
    "GeneratedVisitorCpp",
    "GenerationError",
    "Module",
    "Node",
    "ParsedDefinitionFile",
    "SemanticError",
    "TypeMapping",
    "Trait",
    "ValidatedModel",
    "analyze",
    "cpp_name",
    "generate_cpp",
    "generate_dump_cpp",
    "generate_visitor_cpp",
    "parse_definition_file",
    "parse_cpp_backend_config",
    "parse_definitions",
    "parse_type_mappings",
]
