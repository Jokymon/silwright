# Silwright NDEF Language Support

Basic Visual Studio Code language support for Silwright `.ndef` and `backend_cpp.map` files.

## Features

- TextMate syntax highlighting for `module`, `node`, `trait`, `choice`, `enum`, `end`, `value`,
  `transient`, `fixed`, `with`, and `allwith`
- Highlighting for `*` and `|` operators and `//` line comments
- Declaration-name and field-name highlighting
- Basic highlighting for `backend_cpp.map` mappings and `@include` directives
- Semantic highlighting for NDEF field types and choice alternatives declared in the current
  `.ndef` file, plus field types mapped in the sibling `backend_cpp.map`
- Diagnostics for field types that are neither declared in the `.ndef` file nor mapped in the
  sibling `backend_cpp.map`, and for unknown choice alternatives
- Folding and automatic indentation for `node`, `trait`, `choice`, and `enum` blocks
- Toggle-line-comment support
- Go to Definition for node, trait, choice, and enum types in the current file, and for mapped
  field types in the sibling `backend_cpp.map`
- Document formatting for indentation, blank-line spacing, field colon placement, declaration
  spacing, trait-list commas, and `|` separator spacing
- Optional format-on-save support through `silwrightNdef.formatOnSave`
- Warning diagnostics for NDEF style conventions:
  - `node`, `choice`, `trait`, and `enum` definitions should use CamelCase
  - Node and trait field names should use snake_case

## Settings

- `silwrightNdef.formatter.enabled`: enables the NDEF document formatter. Defaults to `true`.
- `silwrightNdef.formatOnSave`: formats NDEF files before saving. Defaults to `false`.
- `silwrightNdef.lint.style.enabled`: enables naming-style warning diagnostics. Defaults to `true`.

## Notes

The extension resolves declarations and backend mappings within the currently opened `.ndef`
file and its sibling `backend_cpp.map`. It does not require a language server.
