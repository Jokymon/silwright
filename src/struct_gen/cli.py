"""Command-line interface for struct-gen."""

import argparse
from collections.abc import Sequence

from struct_gen.generator import generate_header
from struct_gen.model import Node


def main(argv: Sequence[str] | None = None) -> int:
    """Generate a minimal C++ node declaration."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="C++ node name")
    args = parser.parse_args(argv)
    print(generate_header(Node(name=args.name)), end="")
    return 0

