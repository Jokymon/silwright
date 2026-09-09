const assert = require("node:assert/strict");
const test = require("node:test");
const {
  findDeclarationNameIssues,
  findFieldNameIssues,
  findStyleIssues,
} = require("../src/linter");

test("warns when definition names are not CamelCase", () => {
  const text = [
    "module syntax",
    "node function_head",
    "end",
    "choice expr",
    "end",
    "",
  ].join("\n");

  const issues = findDeclarationNameIssues(text);

  assert.deepEqual(
    issues.map((issue) => [text.slice(issue.start, issue.end), issue.code]),
    [
      ["function_head", "ndef-style-declaration-camel-case"],
      ["expr", "ndef-style-declaration-camel-case"],
    ],
  );
});

test("warns when field names are not snake_case", () => {
  const text = [
    "node Item",
    "    ChildNode: Expr",
    "    child_node: Expr",
    "end",
    "",
  ].join("\n");

  const issues = findFieldNameIssues(text);

  assert.deepEqual(
    issues.map((issue) => [text.slice(issue.start, issue.end), issue.code]),
    [["ChildNode", "ndef-style-field-snake-case"]],
  );
});

test("ignores declaration and field-like text in comments", () => {
  const text = [
    "// node bad_name",
    "node Item",
    "    // BadField: Expr",
    "    child: Expr",
    "end",
    "",
  ].join("\n");

  assert.deepEqual(findStyleIssues(text), []);
});
