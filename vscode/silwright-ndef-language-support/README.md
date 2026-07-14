# Silwright NDEF Language Support

Basic Visual Studio Code language support for Silwright `.ndef` and `backend_cpp.map` files.

## Features

- TextMate syntax highlighting for `module`, `node`, `trait`, `choice`, `enum`, `end`, `value`,
  `transient`, `fixed`, and `with`
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

## Releasing

The extension has an independent release cycle. Update the `version` in `package.json` and the
changelog, commit those changes, then create and push a matching `vscode-v<version>` tag:

```console
git tag vscode-v0.6.0
git push origin vscode-v0.6.0
```

The release workflow runs the tests, packages the `.vsix`, and attaches it to a dedicated
GitHub Release. The workflow rejects a tag when its version does not match `package.json`.
