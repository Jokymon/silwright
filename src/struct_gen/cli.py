"""Validate and inspect a struct-gen node definition file."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from struct_gen.parser import parse_definition_file


def main(argv: Sequence[str] | None = None) -> int:
    """Parse a node definition and print a short summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("definition", type=Path, help="path to a .ndef file")
    args = parser.parse_args(argv)
    definition: Path = args.definition
    if definition.suffix != ".ndef":
        parser.error("definition file must use the .ndef suffix")
    parsed = parse_definition_file(definition)
    print(
        f"module {parsed.module.name}: {len(parsed.module.definitions)} definitions, "
        f"{len(parsed.type_mappings)} built-in mappings"
    )
    return 0
