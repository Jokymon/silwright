const vscode = require("vscode");
const path = require("node:path");
const {
  findBackendMappings,
  findDeclarations,
  findFieldTypeReferences,
} = require("./src/symbols");

const legend = new vscode.SemanticTokensLegend(
  ["type"],
  ["declaration", "defaultLibrary"],
);

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
  const diagnostics = vscode.languages.createDiagnosticCollection("silwright-ndef");
  const definitionProvider = vscode.languages.registerDefinitionProvider("ndef", {
    async provideDefinition(document, position) {
      const wordRange = document.getWordRangeAtPosition(
        position,
        /[A-Za-z_][A-Za-z0-9_]*/,
      );
      if (!wordRange) {
        return undefined;
      }

      const name = document.getText(wordRange);
      const declaration = findDeclarations(document.getText()).get(name);
      if (declaration) {
        return new vscode.Location(
          document.uri,
          new vscode.Range(
            document.positionAt(declaration.start),
            document.positionAt(declaration.end),
          ),
        );
      }

      const map = await readBackendMap(document);
      const mapping = map.mappings.get(name);
      if (!mapping || !map.uri) {
        return undefined;
      }

      return new vscode.Location(
        map.uri,
        new vscode.Range(
          map.positionAt(mapping.start),
          map.positionAt(mapping.end),
        ),
      );
    },
  });

  const semanticProvider = vscode.languages.registerDocumentSemanticTokensProvider(
    "ndef",
    {
      async provideDocumentSemanticTokens(document) {
        const builder = new vscode.SemanticTokensBuilder(legend);
        const declarations = findDeclarations(document.getText());
        const references = findFieldTypeReferences(document.getText());
        const map = await readBackendMap(document);

        for (const declaration of declarations.values()) {
          builder.push(
            rangeFromOffsets(document, declaration.start, declaration.end),
            "type",
            ["declaration"],
          );
        }

        for (const reference of references) {
          if (declarations.has(reference.name)) {
            builder.push(
              rangeFromOffsets(document, reference.start, reference.end),
              "type",
              [],
            );
          } else if (map.mappings.has(reference.name)) {
            builder.push(
              rangeFromOffsets(document, reference.start, reference.end),
              "type",
              ["defaultLibrary"],
            );
          }
        }

        return builder.build();
      },
    },
    legend,
  );

  const updateDiagnostics = (document) => {
    if (document.languageId !== "ndef") {
      return;
    }
    refreshDiagnostics(document, diagnostics);
  };
  const updateDiagnosticsAfterSave = (document) => {
    updateDiagnostics(document);
    if (path.basename(document.uri.fsPath) === "backend_cpp.map") {
      for (const openDocument of vscode.workspace.textDocuments) {
        if (
          openDocument.languageId === "ndef" &&
          path.dirname(openDocument.uri.fsPath) === path.dirname(document.uri.fsPath)
        ) {
          refreshDiagnostics(openDocument, diagnostics);
        }
      }
    }
  };

  for (const document of vscode.workspace.textDocuments) {
    updateDiagnostics(document);
  }

  context.subscriptions.push(
    diagnostics,
    definitionProvider,
    semanticProvider,
    vscode.workspace.onDidOpenTextDocument(updateDiagnostics),
    vscode.workspace.onDidSaveTextDocument(updateDiagnosticsAfterSave),
    vscode.workspace.onDidChangeTextDocument((event) => updateDiagnostics(event.document)),
  );
}

function deactivate() {}

module.exports = { activate, deactivate };

/**
 * @param {vscode.TextDocument} document
 * @param {vscode.DiagnosticCollection} diagnostics
 */
async function refreshDiagnostics(document, diagnostics) {
  const declarations = findDeclarations(document.getText());
  const references = findFieldTypeReferences(document.getText());
  const map = await readBackendMap(document);
  const nextDiagnostics = [];

  for (const reference of references) {
    if (declarations.has(reference.name) || map.mappings.has(reference.name)) {
      continue;
    }

    const range = rangeFromOffsets(document, reference.start, reference.end);
    const message = map.exists
      ? `Unknown Silwright type '${reference.name}'. It is neither declared in this .ndef file nor mapped in backend_cpp.map.`
      : `Unknown Silwright type '${reference.name}'. No sibling backend_cpp.map file was found.`;
    nextDiagnostics.push(
      new vscode.Diagnostic(range, message, vscode.DiagnosticSeverity.Error),
    );
  }

  diagnostics.set(document.uri, nextDiagnostics);
}

/**
 * @param {vscode.TextDocument} document
 * @returns {Promise<{exists: boolean, mappings: Map<string, {start: number, end: number}>, uri?: vscode.Uri, positionAt(offset: number): vscode.Position}>}
 */
async function readBackendMap(document) {
  if (document.uri.scheme !== "file") {
    return emptyBackendMap();
  }

  const uri = vscode.Uri.file(path.join(path.dirname(document.uri.fsPath), "backend_cpp.map"));
  try {
    const bytes = await vscode.workspace.fs.readFile(uri);
    const text = Buffer.from(bytes).toString("utf8");
    return {
      exists: true,
      mappings: findBackendMappings(text),
      uri,
      positionAt: positionAtFactory(text),
    };
  } catch {
    return emptyBackendMap();
  }
}

function emptyBackendMap() {
  return {
    exists: false,
    mappings: new Map(),
    positionAt: () => new vscode.Position(0, 0),
  };
}

/**
 * @param {vscode.TextDocument} document
 * @param {number} start
 * @param {number} end
 * @returns {vscode.Range}
 */
function rangeFromOffsets(document, start, end) {
  return new vscode.Range(document.positionAt(start), document.positionAt(end));
}

/**
 * @param {string} text
 * @returns {(offset: number) => vscode.Position}
 */
function positionAtFactory(text) {
  const lineStarts = [0];
  for (let index = 0; index < text.length; index += 1) {
    if (text[index] === "\n") {
      lineStarts.push(index + 1);
    }
  }

  return (offset) => {
    let low = 0;
    let high = lineStarts.length - 1;
    while (low <= high) {
      const mid = Math.floor((low + high) / 2);
      if (lineStarts[mid] <= offset) {
        low = mid + 1;
      } else {
        high = mid - 1;
      }
    }
    const line = Math.max(0, high);
    return new vscode.Position(line, offset - lineStarts[line]);
  };
}
