# Context-aware dump customization

**Date:** 2026-06-30

**Status:** active

## Context

Generated YAML-like dump functions need to handle ordinary scalar values while permitting
application-specific values, such as a `type_id`, to use external context during formatting.
The context type cannot be fixed by the generator.

## Decision

Generate `dump` and `dump_value` as function templates. The generic `dump_value` implementation
uses `operator<<`. Applications customize a value by defining a more-specific `dump_value`
overload in the value type's namespace; an unqualified generated call finds it through
argument-dependent lookup. This avoids runtime type erasure and lets compilers inline the
customization call. If a value is not stream-insertable and no overload is found, the generic
fallback issues a targeted compile-time diagnostic requesting a `dump_value` overload.

Template declarations live in `_dump.hpp`; definitions live in `_dump.ipp`, which the header
includes. A `_dump.cpp` file is still generated as the conventional translation-unit entry
point, but generic template implementations necessarily remain visible to header consumers.

Generated dump output uses four spaces per nesting level, quoted and escaped strings, `null`
for empty owning pointers, original enum entry names, and an artificial `_type` property on
every node object.
