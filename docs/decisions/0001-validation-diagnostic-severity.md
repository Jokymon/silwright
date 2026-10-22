# Validation diagnostic severity

**Date:** 2026-07-20

**Status:** active

## Context

Semantic analysis and generation need a clear contract for invalid definitions. A warning
channel would require users and tooling to decide whether generation may continue, which
warnings are acceptable in CI, and whether generated output after warnings is supported.

## Decision

Silwright validation and generation diagnostics are errors-only. If an input problem makes the
definition invalid, semantic analysis or generation rejects it and no later workflow step should
continue. If a construct is accepted, Silwright does not emit a warning for it.

Redundant but supported spelling, such as `?` on pointer-backed node or choice fields, remains
accepted and quiet. If a currently accepted construct later proves harmful or ambiguous, it
should be promoted to a validation error through an explicit compatibility decision rather than
introduced as a warning.

## Alternatives considered

### Add semantic warnings

Warnings could flag redundant or suspicious definitions while still generating C++. This was
rejected for now because the current workflow has no demonstrated need for advisory diagnostics,
and continuing after warnings would weaken the simple contract that generation either succeeds
from a valid model or fails before producing output.
