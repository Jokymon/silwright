# Silwright NDEF Language Support

Basic Visual Studio Code language support for Silwright `.ndef` and `backend_cpp.map` files.

## Features

- TextMate syntax highlighting for `module`, `node`, `trait`, `choice`, `enum`, `end`, `value`,
  `transient`, `fixed`, `with`, and `allwith`
- Highlighting for `*` and `|` operators and `//` line comments
- Declaration-name and field-name highlighting
- Basic highlighting for `backend_cpp.map` mappings and `@include` directives
- Semantic highlighting for NDEF field types declared in the current `.ndef` file or mapped in
  the sibling `backend_cpp.map`
- Diagnostics for field types that are neither declared in the `.ndef` file nor mapped in the
  sibling `backend_cpp.map`
- Folding and automatic indentation for `node`, `trait`, `choice`, and `enum` blocks
- Toggle-line-comment support
- Go to Definition for node, trait, choice, and enum types in the current file, and for mapped
  field types in the sibling `backend_cpp.map`

## Notes

The extension resolves declarations and backend mappings within the currently opened `.ndef`
file and its sibling `backend_cpp.map`. It does not require a language server.
