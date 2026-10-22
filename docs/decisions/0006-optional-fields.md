# Optional fields

**Date:** 2026-07-01

**Status:** active

## Context

Optional values need a field syntax and a representation that does not duplicate the
absent/present state already provided by owning pointers.

## Decision

The `?` field-type prefix represents an optional value and is mutually exclusive with the `*`
repetition prefix. Built-in types, enums, and structured fields marked `value` generate as
`std::optional<T>`. Node and choice references without `value` remain `std::unique_ptr<T>`;
wrapping those pointers in another optional layer would represent the same absent/present state
twice without a current semantic need. Generated dumpers emit both disengaged optionals and
null owning pointers as `null`.
