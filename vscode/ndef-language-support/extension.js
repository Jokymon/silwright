const vscode = require("vscode");
const { findDeclarations } = require("./src/symbols");

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
  const provider = vscode.languages.registerDefinitionProvider("ndef", {
    provideDefinition(document, position) {
      const wordRange = document.getWordRangeAtPosition(
        position,
        /[A-Za-z_][A-Za-z0-9_]*/,
      );
      if (!wordRange) {
        return undefined;
      }

      const name = document.getText(wordRange);
      const declaration = findDeclarations(document.getText()).get(name);
      if (!declaration) {
        return undefined;
      }

      return new vscode.Location(
        document.uri,
        new vscode.Range(
          document.positionAt(declaration.start),
          document.positionAt(declaration.end),
        ),
      );
    },
  });

  context.subscriptions.push(provider);
}

function deactivate() {}

module.exports = { activate, deactivate };
