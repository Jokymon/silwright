const DECLARATION_PATTERN =
  /^\s*(node|trait|choice|enum)\s+([A-Za-z_][A-Za-z0-9_]*)\b/gm;
const FIELD_PATTERN = /^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:/gm;
const PASCAL_CASE_PATTERN = /^[A-Z][A-Za-z0-9]*$/u;
const SNAKE_CASE_PATTERN = /^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$/u;

/**
 * @param {string} text
 * @returns {Array<{start: number, end: number, message: string, code: string}>}
 */
function findStyleIssues(text) {
  return [
    ...findDeclarationNameIssues(text),
    ...findFieldNameIssues(text),
  ].sort((left, right) => left.start - right.start);
}

/**
 * @param {string} text
 * @returns {Array<{start: number, end: number, message: string, code: string}>}
 */
function findDeclarationNameIssues(text) {
  const issues = [];
  const stripped = stripNdefComments(text);
  let match;

  while ((match = DECLARATION_PATTERN.exec(stripped)) !== null) {
    const kind = match[1];
    const name = match[2];
    if (PASCAL_CASE_PATTERN.test(name)) {
      continue;
    }

    const nameOffset = match[0].lastIndexOf(name);
    const start = match.index + nameOffset;
    issues.push({
      start,
      end: start + name.length,
      message: `${kind} definitions should use CamelCase names.`,
      code: "ndef-style-declaration-camel-case",
    });
  }

  return issues;
}

/**
 * @param {string} text
 * @returns {Array<{start: number, end: number, message: string, code: string}>}
 */
function findFieldNameIssues(text) {
  const issues = [];
  const stripped = stripNdefComments(text);
  let match;

  while ((match = FIELD_PATTERN.exec(stripped)) !== null) {
    const name = match[1];
    if (SNAKE_CASE_PATTERN.test(name)) {
      continue;
    }

    const nameOffset = match[0].indexOf(name);
    const start = match.index + nameOffset;
    issues.push({
      start,
      end: start + name.length,
      message: "Node and trait field names should use snake_case.",
      code: "ndef-style-field-snake-case",
    });
  }

  return issues;
}

/**
 * @param {string} text
 * @returns {string}
 */
function stripNdefComments(text) {
  return text.replace(/\/\/[^\r\n]*/gu, (match) => " ".repeat(match.length));
}

module.exports = {
  findDeclarationNameIssues,
  findFieldNameIssues,
  findStyleIssues,
};
