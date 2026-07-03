"""Validate and inspect a struct-gen node definition file."""

import argparse
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from struct_gen.dump_generator import generate_dump_files
from struct_gen.generator import generate_cpp_files
from struct_gen.parser import parse_definition_file
from struct_gen.semantic import analyze
from struct_gen.visitor_generator import generate_visitor_files


def main(argv: Sequence[str] | None = None) -> int:
    """Generate C++ files from a node definition."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("definition", type=Path, help="path to a .ndef file")
    args = parser.parse_args(argv)
    definition: Path = args.definition
    if definition.suffix != ".ndef":
        parser.error("definition file must use the .ndef suffix")
    validated = analyze(parse_definition_file(definition))
    generated_at = datetime.now(UTC)
    header, source = generate_cpp_files(
        definition, generated_at=generated_at, validated=validated
    )
    dump_header, dump_implementation, dump_source = generate_dump_files(
        definition, generated_at=generated_at, validated=validated
    )
    visitor_header, visitor_source = generate_visitor_files(
        definition, generated_at=generated_at, validated=validated
    )
    generated = (
        header,
        source,
        dump_header,
        dump_implementation,
        dump_source,
        visitor_header,
        visitor_source,
    )
    print(f"generated {', '.join(map(str, generated))}")
    return 0
