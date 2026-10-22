# C++ backend header dependencies

**Date:** 2026-06-30

**Status:** active

## Context

Mapped C++ types may require standard headers or project-specific definitions. Requiring every
consumer to include those dependencies before a generated model header would make that header
order-dependent and not self-contained.

## Decision

Allow explicit include directives in `backend_cpp.map`:

```text
@include <cstddef>
@include "project/symbol.hpp"

index: std::size_t
type: project::type_id
```

The `@` distinguishes backend configuration from type mappings and leaves room for future
backend directives. Both system and quoted project headers are accepted. The generator emits
the headers before model declarations, preserves their order, and removes duplicates. Backend
selection remains statically fixed to `backend_cpp.map`.

## Alternatives considered

- Associating a `from <header>` clause with each mapping would enable selective inclusion but
  complicate the intentionally free-form C++ type spelling and repeat shared headers.
- A separate TOML or include-list file would separate configuration from mappings but add
  another discovery convention and make dependencies less local.
- `.ndef` include declarations would permit module-specific dependencies but leak C++ backend
  concerns into the backend-neutral node language.
- CLI include flags would avoid format changes but make generation less reproducible and place
  required configuration in build scripts.
- Inferring headers from C++ spellings would be convenient for a few standard types but brittle
  and incapable of resolving project-specific definitions.
