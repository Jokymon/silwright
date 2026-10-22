const vscode = require("vscode");
const path = require("node:path");
const { formatNdefText } = require("./src/formatter");
const { findStyleIssues } = require("./src/linter");
const {
  findBackendMappings,
  findDeclarations,
  findLocalDefinitionAtOffset,
  findTypeReferences,
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

      const text = document.getText();
      const name = document.getText(wordRange);
      const declaration = findLocalDefinitionAtOffset(text, document.offsetAt(position));
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
        const references = findTypeReferences(document.getText());
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
          } else if (reference.kind === "field" && map.mappings.has(reference.name)) {
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
  const formattingProvider = vscode.languages.registerDocumentFormattingEditProvider("ndef", {
    provideDocumentFormattingEdits(document) {
      return provideNdefFormattingEdits(document);
    },
  });

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
    formattingProvider,
    vscode.workspace.onDidOpenTextDocument(updateDiagnostics),
    vscode.workspace.onWillSaveTextDocument((event) => {
      if (
        event.document.languageId === "ndef" &&
        getNdefConfiguration(event.document).get("formatOnSave", false)
      ) {
        event.waitUntil(Promise.resolve(provideNdefFormattingEdits(event.document)));
      }
    }),
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
  const references = findTypeReferences(document.getText());
  const map = await readBackendMap(document);
  const nextDiagnostics = [];

  for (const reference of references) {
    if (
      declarations.has(reference.name) ||
      (reference.kind === "field" && map.mappings.has(reference.name))
    ) {
      continue;
    }

    const range = rangeFromOffsets(document, reference.start, reference.end);
    const message =
      reference.kind === "choiceAlternative"
        ? `Unknown Silwright choice alternative '${reference.name}'. It is not declared in this .ndef file.`
        : reference.kind === "trait"
          ? `Unknown Silwright trait '${reference.name}'. It is not declared in this .ndef file.`
          : map.exists
          ? `Unknown Silwright type '${reference.name}'. It is neither declared in this .ndef file nor mapped in backend_cpp.map.`
          : `Unknown Silwright type '${reference.name}'. No sibling backend_cpp.map file was found.`;
    nextDiagnostics.push(
      new vscode.Diagnostic(range, message, vscode.DiagnosticSeverity.Error),
    );
  }

  if (getNdefConfiguration(document).get("lint.style.enabled", true)) {
    for (const issue of findStyleIssues(document.getText())) {
      const diagnostic = new vscode.Diagnostic(
        rangeFromOffsets(document, issue.start, issue.end),
        issue.message,
        vscode.DiagnosticSeverity.Warning,
      );
      diagnostic.code = issue.code;
      diagnostic.source = "Silwright NDEF";
      nextDiagnostics.push(diagnostic);
    }
  }

  diagnostics.set(document.uri, nextDiagnostics);
}

/**
 * @param {vscode.TextDocument} document
 * @returns {vscode.TextEdit[]}
 */
function provideNdefFormattingEdits(document) {
  if (!getNdefConfiguration(document).get("formatter.enabled", true)) {
    return [];
  }

  const text = document.getText();
  const formatted = formatNdefText(text);
  if (formatted === text) {
    return [];
  }

  const fullRange = new vscode.Range(
    document.positionAt(0),
    document.positionAt(text.length),
  );
  return [vscode.TextEdit.replace(fullRange, formatted)];
}

/**
 * @param {vscode.TextDocument} document
 * @returns {vscode.WorkspaceConfiguration}
 */
function getNdefConfiguration(document) {
  return vscode.workspace.getConfiguration("silwrightNdef", document.uri);
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
