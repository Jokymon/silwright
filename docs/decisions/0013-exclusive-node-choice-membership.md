# Exclusive node choice membership

**Date:** 2026-10-22

**Status:** active

## Context

A node listed directly in more than one choice has more than one possible choice-level identity.
This is ambiguous for generated operations such as transformers, where a node rewrite needs one
choice return type. Previously, semantic analysis rejected this only when both choices
participated in transformer generation, leaving the validity of the same declaration structure
dependent on how the choices were used.

## Decision

A node may be listed as a direct alternative of at most one choice in a module. Semantic
analysis rejects multiple direct memberships regardless of whether the choices are used by
pointer, by value, or not referenced by a field.

Choices may still contain other choices. A node reachable through a nested choice does not count
as a second direct membership unless that node is also explicitly listed by another choice.

## Alternatives considered

### Enforce the restriction only for generated transformers

This preserves models that do not currently generate an ambiguous transformer return type, but
makes semantic validity depend on usage and allows a later field change to invalidate otherwise
unchanged choices.

### Allow multiple memberships with explicit transformation annotations

Annotations could choose a return type for each transformation context, but would add language
and generator complexity for a relationship that currently has no demonstrated use case.
