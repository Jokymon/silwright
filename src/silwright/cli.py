"""Generate C++ from a Silwright node definition file."""

import argparse
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from silwright.dump_generator import generate_dump_files
from silwright.generator import generate_cpp_files
from silwright.parser import parse_definition_file
from silwright.semantic import analyze
from silwright.transformer_generator import generate_transformer_files
from silwright.visitor_generator import generate_visitor_files


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
    transformer_header, transformer_source = generate_transformer_files(
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
        transformer_header,
        transformer_source,
    )
    print(f"generated {', '.join(map(str, generated))}")
    return 0
