# Changelog

All notable changes to Silwright are documented in this file.

The project follows [Semantic Versioning](https://semver.org/). Releases are identified by a
`v<version>` Git tag matching the version in `pyproject.toml`.

## [Unreleased]

### Added

- Generate C++ transformer classes for bottom-up pointer-backed node and choice rewrites.
- Add `fixed *Type` fields for repeated fields whose generated transformer rewrites must
  preserve element count.
- Add generated visitor replacement helpers for pointer-backed choice children.

## [0.2.0] - 2026-07-06

### Added

- Separate generated C++ struct definitions with an empty line for improved readability.
- Generate reusable `<choice>_list` aliases for choices used by repeated pointer-backed fields.

## [0.1.3] - 2026-07-04

### Fixed

- Corrected the PyPI release metadata and workflow configuration for the initial package
  publication.

## [0.1.0] - 2026-07-04

### Added

- Parser and semantic validation for modules, nodes, choices, enums, traits, comments, value
  fields, optional and repeated fields, and transient fields.
- Configurable C++ backend mappings and include directives.
- C++ model, YAML-style dump, and visitor generation.
- Command-line interface and Python API.
- Example language definition and end-to-end C++ example.
- Visual Studio Code language support for `.ndef` files.

[Unreleased]: https://github.com/Jokymon/silwright/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/Jokymon/silwright/releases/tag/v0.2.0
[0.1.3]: https://github.com/Jokymon/silwright/releases/tag/v0.1.3
[0.1.0]: https://github.com/Jokymon/silwright/releases/tag/v0.1.0
