"""Parse node descriptions used to generate C++ code."""

from struct_gen.dump_generator import GeneratedDumpCpp, generate_dump_cpp
from struct_gen.generator import GeneratedCpp, GenerationError, cpp_name, generate_cpp
from struct_gen.model import (
    Choice,
    CppBackendConfig,
    Enum,
    Field,
    Module,
    Node,
    ParsedDefinitionFile,
    TypeMapping,
)
from struct_gen.parser import (
    parse_cpp_backend_config,
    parse_definition_file,
    parse_definitions,
    parse_type_mappings,
)

__all__ = [
    "Choice",
    "CppBackendConfig",
    "Enum",
    "Field",
    "GeneratedCpp",
    "GeneratedDumpCpp",
    "GenerationError",
    "Module",
    "Node",
    "ParsedDefinitionFile",
    "TypeMapping",
    "cpp_name",
    "generate_cpp",
    "generate_dump_cpp",
    "parse_definition_file",
    "parse_cpp_backend_config",
    "parse_definitions",
    "parse_type_mappings",
]
