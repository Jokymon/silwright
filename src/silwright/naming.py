"""Target-independent naming helpers used during analysis and generation."""

import re


def cpp_name(name: str) -> str:
    """Convert a definition name from CamelCase to snake_case."""
    with_word_boundaries = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", with_word_boundaries).lower()
