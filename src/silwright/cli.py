"""Generate C++ from a Silwright node definition file."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from silwright.dump_generator import generate_dump_cpp
from silwright.generated_file import GeneratedFile, write_generated_files
from silwright.generator import generate_cpp
from silwright.parser import parse_definition_file
from silwright.semantic import analyze
from silwright.transformer_generator import generate_transformer_cpp
from silwright.visitor_generator import generate_visitor_cpp


def main(argv: Sequence[str] | None = None) -> int:
    """Generate C++ files from a node definition."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("definition", type=Path, help="path to a .ndef file")
    args = parser.parse_args(argv)
    definition: Path = args.definition
    if definition.suffix != ".ndef":
        parser.error("definition file must use the .ndef suffix")
    validated = analyze(parse_definition_file(definition))
    stem = definition.stem
    model_header_path = definition.with_suffix(".hpp")
    model_source_path = definition.with_suffix(".cpp")
    dump_header_path = definition.with_name(f"{stem}_dump.hpp")
    dump_implementation_path = definition.with_name(f"{stem}_dump.ipp")
    dump_source_path = definition.with_name(f"{stem}_dump.cpp")
    visitor_header_path = definition.with_name(f"{stem}_visitor.hpp")
    visitor_source_path = definition.with_name(f"{stem}_visitor.cpp")
    transformer_header_path = definition.with_name(f"{stem}_transformer.hpp")
    transformer_source_path = definition.with_name(f"{stem}_transformer.cpp")

    model = generate_cpp(validated, model_header_path.name)
    dump = generate_dump_cpp(
        validated,
        model_header_path.name,
        dump_header_path.name,
        dump_implementation_path.name,
    )
    visitor = generate_visitor_cpp(
        validated,
        model_header_path.name,
        visitor_header_path.name,
    )
    transformer = generate_transformer_cpp(
        validated,
        model_header_path.name,
        transformer_header_path.name,
    )
    generated = write_generated_files(
        (
            GeneratedFile(model_header_path, model.header),
            GeneratedFile(model_source_path, model.source),
            GeneratedFile(dump_header_path, dump.header),
            GeneratedFile(dump_implementation_path, dump.implementation),
            GeneratedFile(dump_source_path, dump.source),
            GeneratedFile(visitor_header_path, visitor.header),
            GeneratedFile(visitor_source_path, visitor.source),
            GeneratedFile(transformer_header_path, transformer.header),
            GeneratedFile(transformer_source_path, transformer.source),
        ),
        definition,
    )
    print(f"generated {', '.join(map(str, generated))}")
    return 0
