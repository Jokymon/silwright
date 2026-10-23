# Silwright

[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue?logo=github)](https://jokymon.github.io/silwright/)
[![PyPI](https://img.shields.io/pypi/v/silwright)](https://pypi.org/project/silwright/)

Silwright is a tool to work with programming language independent definitions of node
tree structures. The goal is, to be able to focus tree structure definitions to the
very essence of these trees rather than having to deal with programming language
specific details. The definitions and the generated code are intended for use in
compilers as the foundation of AST and IR structures. However other use cases might
be feasible as well.

The current implementation also features a converter to turn such definitions into
C++ code. 

## Installation

Install the command-line tool from PyPI:

```shell
pip install silwright
```

Alternatively, run it in an isolated environment without installing it permanently:

```shell
uvx silwright path/to/module.ndef
```

Silwright requires Python 3.14 or newer. Generated C++ currently requires C++20; in particular,
the generated model and dump support use `std::variant` and C++20 constraints.

## Project status

Silwright is beta software. Its current language and C++ generation workflow are usable, but
the project is still pre-1.0, has limited external production validation, and may make
compatibility-affecting changes while its contracts are finalized.

## Usage

Generate C++ from the example node definition:

```shell
uv run silwright examples/simple_lang.ndef
```

The command automatically loads the required `backend_cpp.map` from the same directory, then
writes the model `.hpp`/`.cpp`, dump `_dump.hpp`/`_dump.ipp`/`_dump.cpp`, visitor
`_visitor.hpp`/`_visitor.cpp`, and transformer `_transformer.hpp`/`_transformer.cpp` files
beside `simple_lang.ndef`. Existing generated output files are replaced. Known syntax,
validation, and generation failures are reported as numbered diagnostics with source location,
source line, and a caret marker.

Library users can call `silwright.parse_definition_file(path)` for the same combined lookup
behavior. `silwright.parse_definitions(text)` and `silwright.parse_type_mappings(text)` are
available when parsing already-loaded content independently.

`silwright.analyze(parsed)` performs centralized semantic validation and returns a
`ValidatedModel` containing resolved declarations, backend mappings, flattened trait fields,
dependency order, and visitor reachability. The model, dump, visitor, and transformer
generators all accept this validated model; passing raw parsed input remains supported and
invokes the same analysis boundary automatically.

The [language reference](docs/language-reference.md) documents NDEF and backend-map syntax.
The [C++ backend reference](docs/cpp_backend.md) documents the generated representation,
dumping, visitors, and transformers.

## Definition language

One `.ndef` file describes one module. Its required first declaration is `module <name>`.

```text
module expressions

node Variable
    name: identifier
end

node Number
    value: number
end

choice Expr
    Variable | Number
end

enum Op
    Add | Subtract | Multiply | Divide | Modulus
end

node BinaryExpression
    op: Op
    left: Expr
    right: Expr
end

node FunctionDefinition
    head: value FunctionHead
    code: *Expr
end
```

Nodes, traits, choices, enums, field modifiers, and backend-map files are specified in the
[language reference](docs/language-reference.md). See `examples/simple_lang.ndef` and
`examples/backend_cpp.map` for complete inputs. Their C++ interpretation and the end-to-end
example are described in the [C++ backend reference](docs/cpp_backend.md).

## Development setup

Prerequisites:

- Git
- [uv](https://docs.astral.sh/uv/)
- Python 3.14 or newer; `uv` can install the requested interpreter when necessary

Clone the repository and create the locked development environment:

```shell
uv sync
```

Run all project checks:

```shell
uv run pytest
uv run ruff check .
uv run mypy
```

The package uses a `src` layout. Runtime dependencies and development tools are declared in
`pyproject.toml`; exact resolved versions are committed in `uv.lock`. Add dependencies with
`uv add <package>` and development dependencies with `uv add --dev <package>`.

This project is setup for development with the help of coding agents with further details
and project conventions defined in `AGENTS.md`.

### VS Code extension development

The VS Code extension lives in `vscode/silwright-ndef-language-support`. Open that directory
in Visual Studio Code and press `F5` to launch an Extension Development Host. Open an `.ndef`
file in that window to exercise the extension.

The extension has no build step or runtime dependencies. Run its unit tests with:

```shell
cd vscode/silwright-ndef-language-support
npm test
```

The Marketplace icon is committed as `icon.png`; `icon.svg` is the editable source for future
icon iterations and is excluded from the packaged VSIX through `.vscodeignore`.

To package it after installing `@vscode/vsce`:

```shell
cd vscode/silwright-ndef-language-support
vsce package
```

## Documentation

The project documentation can be previewed locally with:

```shell
uv sync --group docs
uv run mkdocs serve
```

The GitHub Pages workflow publishes the documentation from `master` when its source files
change. The built `site/` directory is local output and is not version controlled.

## Releasing

Python package releases use `v<version>` tags and are independent of VS Code extension
releases. Before creating a release, update the version in `pyproject.toml`, move the relevant
entries in `CHANGELOG.md` into a matching version section, and commit both changes. Then create
and push the matching tag; for version 0.1.0 this is:

```shell
git tag v0.1.0
git push origin v0.1.0
```

The release workflow verifies that the tag, project version, and changelog agree before it
builds and publishes the distributions to PyPI.

VS Code extension releases use `vscode-v<version>` tags and are independent of Python package
releases. Before creating a release, update the `version` in
`vscode/silwright-ndef-language-support/package.json`, move the relevant entries in
`vscode/silwright-ndef-language-support/CHANGELOG.md` into a matching version section, and
commit those changes. Then create and push the matching tag; for version 0.7.0 this is:

```shell
git tag vscode-v0.7.0
git push origin vscode-v0.7.0
```

The VS Code extension release workflow runs the tests, packages the `.vsix`, and attaches it
to a dedicated GitHub Release. The workflow rejects a tag when its version does not match
`package.json`.
