# struct-gen

`struct-gen` is a Python 3.14 project for generating C++ code from declarative node
descriptions.

## Setup

Install [uv](https://docs.astral.sh/uv/), then run:

```shell
uv sync
uv run pytest
uv run ruff check .
uv run mypy
```

Run the initial example generator:

```shell
uv run struct-gen ExampleNode
```

The current implementation is deliberately small: it establishes the domain model,
generator boundary, command-line entry point, and test setup on which description parsing
and richer C++ generation can be built.

## Version control

The repository is initialized locally. To create the first commit:

```shell
git add .
git commit -m "Initial project scaffold"
```

