const assert = require("node:assert/strict");
const test = require("node:test");
const {
  findBackendMappings,
  findDeclarations,
  findFieldTypeReferences,
} = require("../src/symbols");

test("finds node, trait, choice, and enum declaration names", () => {
  const text = [
    "module sample",
    "node Number",
    "end",
    "trait Location",
    "end",
    "choice Expr",
    "    Number",
    "end",
    "enum Op",
    "    Add | Subtract",
    "end",
    "",
  ].join("\n");

  const declarations = findDeclarations(text);

  assert.deepEqual([...declarations.keys()], ["Number", "Location", "Expr", "Op"]);
  for (const [name, range] of declarations) {
    assert.equal(text.slice(range.start, range.end), name);
  }
});

test("ignores declarations in comments and unrelated words", () => {
  const text = [
    "// node CommentedOut",
    "field: node NotADeclaration",
    "node Real // choice AlsoNotADeclaration",
    "end",
  ].join("\n");

  assert.deepEqual([...findDeclarations(text).keys()], ["Real"]);
});

test("keeps the first declaration when a name is duplicated", () => {
  const text = "node Same\nend\nchoice Same\nend\n";

  const declaration = findDeclarations(text).get("Same");

  assert.equal(declaration.start, text.indexOf("Same"));
});

test("finds field type references with modifiers", () => {
  const text = [
    "node FunctionCall",
    "    target: Expr",
    "    arguments: fixed *Expr",
    "    metadata: ?value Metadata",
    "    cache: transient scope // ignored comment: Fake",
    "end",
  ].join("\n");

  const references = findFieldTypeReferences(text);

  assert.deepEqual(
    references.map((reference) => reference.name),
    ["Expr", "Expr", "Metadata", "scope"],
  );
  for (const reference of references) {
    assert.equal(text.slice(reference.start, reference.end), reference.name);
  }
});

test("finds backend map mappings", () => {
  const text = [
    "@include <string>",
    "identifier: std::string",
    "number: long # mapped scalar",
    "# ignored: value",
    "identifier: duplicate",
    "",
  ].join("\n");

  const mappings = findBackendMappings(text);

  assert.deepEqual([...mappings.keys()], ["identifier", "number"]);
  assert.equal(mappings.get("identifier").start, text.indexOf("identifier"));
});
