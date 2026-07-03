# NDEF Language Support

Basic Visual Studio Code language support for struct-gen `.ndef` files.

## Features

- TextMate syntax highlighting for `module`, `node`, `trait`, `choice`, `enum`, `end`, `value`,
  `transient`, and `with`
- Highlighting for `*` and `|` operators and `//` line comments
- Declaration-name and field-name highlighting
- Folding and automatic indentation for `node`, `trait`, `choice`, and `enum` blocks
- Toggle-line-comment support
- Go to Definition for node, trait, choice, and enum types in the current file

## Development

Open this directory in Visual Studio Code and press `F5` to launch an Extension Development Host. Open an `.ndef` file in that window to exercise the extension.

The extension has no build step or runtime dependencies. Run its unit tests with:

```console
npm test
```

To package it after installing `@vscode/vsce`:

```console
vsce package
```
