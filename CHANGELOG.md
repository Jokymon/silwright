# Changelog

All notable changes to Silwright are documented in this file.

The project follows [Semantic Versioning](https://semver.org/). Releases are identified by a
`v<version>` Git tag matching the version in `pyproject.toml`.

## [Unreleased]

### Changed

- Generated files now use a stable Silwright/version banner without generation timestamps.

### Fixed

- Render all CLI outputs before writing, write changed outputs through temporary files, and leave
  unchanged generated files untouched so their modification timestamps are preserved.

### Added

- Add transitive choice trait propagation with `choice Name allwith Trait`, including
  deterministic deduplication with explicit and overlapping trait applications.
- Generate mutable and const `as_trait<Trait>(choice)` accessors for traits shared through
  `allwith`, including recursive access through nested choices.
- Highlight the `allwith` keyword in the VS Code extension.

## [0.3.0] - 2026-07-13

### Added

- Generate C++ transformer classes for bottom-up pointer-backed node and choice rewrites.
- Add `fixed *Type` fields for repeated fields whose generated transformer rewrites must
  preserve element count.
- Add generated visitor replacement helpers for pointer-backed choice children.
- Use generated `<choice>_list` aliases in struct fields for repeated pointer-backed choices.

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

[Unreleased]: https://github.com/Jokymon/silwright/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/Jokymon/silwright/releases/tag/v0.3.0
[0.2.0]: https://github.com/Jokymon/silwright/releases/tag/v0.2.0
[0.1.3]: https://github.com/Jokymon/silwright/releases/tag/v0.1.3
[0.1.0]: https://github.com/Jokymon/silwright/releases/tag/v0.1.0
