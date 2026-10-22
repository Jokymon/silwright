# User-facing diagnostic format

**Date:** 2026-07-24

**Status:** active

## Context

Parser, semantic-analysis, and generation failures are part of the normal authoring workflow.
Showing Python tracebacks for these failures leaks implementation details and makes it harder to
find the offending source construct.

## Decision

Silwright CLI diagnostics use a compiler-style format:

```text
simple_lang.ndef:42:12: error[SW1008]: unknown field type 'Foo' in Block
    child: Foo
           ^
```

Each user-facing diagnostic has a stable `SWxxxx` identifier. The CLI prints the source file,
one-based line and column, a concise message, the source line, and a caret at the primary error
position. Syntax diagnostics reuse Lark's parsing context support. Semantic diagnostics carry
source-location metadata from parsing; that metadata is excluded from dataclass equality so the
domain model remains convenient for tests and API callers.

Locations should point at the offending token where possible. For example, an unknown field type
points at the referenced type name, while a duplicate field points at the field name. Diagnostics
that currently identify only a broader declaration or field should still use the closest
available source location rather than falling back to a traceback.

## Alternatives considered

### Keep raw exceptions at the CLI boundary

Raw exceptions are useful during internal development, but they are noisy for users and do not
provide stable identifiers for tooling or documentation. They remain available to library callers
who invoke lower-level APIs directly.

### Add a third-party renderer immediately

A dedicated diagnostic-rendering package could provide richer spans and colors. This was deferred
because Lark already provides syntax-error context, and the current centralized renderer is small
and sufficient for the first source-aware diagnostic layer. A richer renderer can replace the
formatting implementation later while preserving error codes and locations.

### Store full source spans everywhere

Full spans would allow multi-character underlines such as `^^^`. The initial implementation
stores primary-token locations only, which keeps the data model simple and covers the most common
authoring errors. Multi-token spans remain a future extension.
