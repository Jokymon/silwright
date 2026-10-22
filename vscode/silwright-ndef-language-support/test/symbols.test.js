const assert = require("node:assert/strict");
const test = require("node:test");
const {
  findBackendMappings,
  findChoiceAlternativeReferences,
  findDeclarations,
  findFieldTypeReferences,
  findLocalDefinitionAtOffset,
  findTraitReferences,
  findTypeReferences,
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

test("finds choice alternative references with flexible separators", () => {
  const text = [
    "choice Expr allwith Location, Attributes",
    "    Number |",
    "    StringLiteral",
    "    | FunctionCall // ignored: FakeAlternative",
    "end",
    "enum Op",
    "    Add | Subtract",
    "end",
  ].join("\n");

  const references = findChoiceAlternativeReferences(text);

  assert.deepEqual(
    references.map((reference) => reference.name),
    ["Number", "StringLiteral", "FunctionCall"],
  );
  for (const reference of references) {
    assert.equal(reference.kind, "choiceAlternative");
    assert.equal(text.slice(reference.start, reference.end), reference.name);
  }
});

test("finds trait references in with and allwith lists", () => {
  const text = [
    "node Leaf with Location, Attributes // ignored: FakeTrait",
    "end",
    "choice Expr allwith Location, Attributes",
    "    Leaf",
    "end",
  ].join("\n");

  const references = findTraitReferences(text);

  assert.deepEqual(
    references.map((reference) => reference.name),
    ["Location", "Attributes", "Location", "Attributes"],
  );
  for (const reference of references) {
    assert.equal(reference.kind, "trait");
    assert.equal(text.slice(reference.start, reference.end), reference.name);
  }
});

test("resolves with and allwith trait references to their declarations", () => {
  const text = [
    "trait Location",
    "end",
    "trait Attributes",
    "end",
    "node Leaf with Location",
    "end",
    "choice Expr allwith Location, Attributes",
    "    Leaf",
    "end",
  ].join("\n");
  const declarationStart = text.indexOf("Location");
  const withReference = text.indexOf("Location", declarationStart + 1);
  const allwithLocation = text.indexOf("Location", withReference + 1);
  const allwithAttributes = text.lastIndexOf("Attributes");

  assert.deepEqual(findLocalDefinitionAtOffset(text, withReference + 1), {
    name: "Location",
    start: declarationStart,
    end: declarationStart + "Location".length,
  });
  assert.equal(
    findLocalDefinitionAtOffset(text, allwithLocation + 1).start,
    declarationStart,
  );
  assert.equal(
    findLocalDefinitionAtOffset(text, allwithAttributes + 1).start,
    text.indexOf("Attributes"),
  );
});

test("combines field and choice type references in source order", () => {
  const text = [
    "node Root",
    "    child: Expr",
    "end",
    "choice Expr",
    "    Leaf | Branch",
    "end",
  ].join("\n");

  const references = findTypeReferences(text);

  assert.deepEqual(
    references.map((reference) => [reference.name, reference.kind]),
    [
      ["Expr", "field"],
      ["Leaf", "choiceAlternative"],
      ["Branch", "choiceAlternative"],
    ],
  );
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
