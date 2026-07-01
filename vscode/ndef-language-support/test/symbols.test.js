const assert = require("node:assert/strict");
const test = require("node:test");
const { findDeclarations } = require("../src/symbols");

test("finds node, choice, and enum declaration names", () => {
  const text = [
    "module sample",
    "node Number",
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

  assert.deepEqual([...declarations.keys()], ["Number", "Expr", "Op"]);
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
