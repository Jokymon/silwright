"""Validate and inspect a struct-gen node definition file."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from struct_gen.parser import parse_definitions


def main(argv: Sequence[str] | None = None) -> int:
    """Parse a node definition and print a short summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("definition", type=Path, help="path to a .ndef file")
    args = parser.parse_args(argv)
    definition: Path = args.definition
    if definition.suffix != ".ndef":
        parser.error("definition file must use the .ndef suffix")
    module = parse_definitions(definition.read_text(encoding="utf-8"))
    print(f"module {module.name}: {len(module.definitions)} definitions")
    return 0
