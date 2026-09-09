const assert = require("node:assert/strict");
const test = require("node:test");
const { formatNdefText } = require("../src/formatter");

test("formats indentation, declaration spacing, and field colons", () => {
  const text = [
    "module   syntax",
    "",
    "",
    "node   FunctionHead   with   Location,Documented",
    "name   :identifier",
    " parameters:   fixed   * value  Parameter",
    "end",
    "",
  ].join("\n");

  assert.equal(
    formatNdefText(text),
    [
      "module syntax",
      "",
      "node FunctionHead with Location, Documented",
      "    name: identifier",
      "    parameters: fixed *value Parameter",
      "end",
      "",
    ].join("\n"),
  );
});

test("formats choice and enum separator spacing without changing names", () => {
  const text = [
    "choice Expr",
    "Number|BinaryExpression",
    "| FunctionCall",
    "end",
    "",
  ].join("\n");

  assert.equal(
    formatNdefText(text),
    [
      "choice Expr",
      "    Number | BinaryExpression",
      "    | FunctionCall",
      "end",
      "",
    ].join("\n"),
  );
});

test("preserves line comments while formatting surrounding code", () => {
  const text = [
    "node  Item // declaration",
    "Value: Expr // field",
    "// body comment",
    "end",
    "",
  ].join("\n");

  assert.equal(
    formatNdefText(text),
    [
      "node Item // declaration",
      "    Value: Expr // field",
      "    // body comment",
      "end",
      "",
    ].join("\n"),
  );
});
