# Reusable node traits

**Date:** 2026-07-03

**Status:** active

## Context

Multiple node types need to share reusable, data-bearing characteristics without treating those
characteristics as ordinary composed fields or as visitable nodes.

## Decision

Reusable data-bearing characteristics use `trait` declarations and node-level `with` lists:

```text
trait Location
    location: source_range
end

node FunctionHead with Location
    name: identifier
end
```

Traits generate public C++ base structs, while nodes generate public inheritance from each
listed trait. Traits cannot inherit, appear in choices, or receive visitor overloads. Their
fields are flattened into the derived node's dump output. Generation rejects unknown or
repeated traits and any field-name collision among applied traits and local node fields.

## Alternatives considered

`trait` was selected over `interface` because traits carry data, and over `concept` because
that term has a distinct C++ meaning. `with` reads as capability application without suggesting
ordinary field composition. The trait can use a natural characteristic name such as `Location`;
this does not conflict with its lowercase `location` field because type and member names occupy
different generated contexts.
