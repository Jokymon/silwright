# Silwright

Silwright generates C++ tree data structures from declarative node descriptions. A module is
described in an `.ndef` file and its C++ backend types and includes are configured in a nearby
`backend_cpp.map` file.

Silwright is beta software. The current language and C++ generation workflow are usable, but
the project is still pre-1.0 and its contracts may change.

## Installation

Silwright requires Python 3.14 or newer.

```shell
pip install silwright
```

It can also be run without a permanent installation:

```shell
uvx silwright path/to/module.ndef
```

## Generate C++

From a source checkout, generate all C++ files for the included example with:

```shell
uv run silwright examples/simple_lang.ndef
```

The generated model, dump support, and visitor files are written beside the `.ndef` file.
Generated C++ currently requires C++20.

See the [language reference](language-reference.md) for the complete syntax and generation
contract. The [design decisions](design-decisions.md) record the alternatives considered for
important language and backend choices.
