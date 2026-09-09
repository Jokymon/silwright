const INDENT = "    ";
const NAME = "[A-Za-z_][A-Za-z0-9_]*";
const DECLARATION_PATTERN = new RegExp(`^(node|trait|choice|enum)\\s+(${NAME})(.*)$`);
const FIELD_PATTERN = new RegExp(`^(${NAME})\\s*:\\s*(.*)$`);
const MODULE_PATTERN = new RegExp(`^module\\s+(${NAME})\\s*$`);

/**
 * Format an NDEF document conservatively.
 *
 * The formatter only changes whitespace and punctuation spacing. It does not
 * rename identifiers, reorder declarations, or rewrite comments.
 *
 * @param {string} text
 * @returns {string}
 */
function formatNdefText(text) {
  const eol = text.includes("\r\n") ? "\r\n" : "\n";
  const hasFinalNewline = /\r?\n$/.test(text);
  const lines = text.split(/\r\n|\n|\r/);
  if (hasFinalNewline) {
    lines.pop();
  }

  const output = [];
  let depth = 0;
  let pendingTopLevelBlank = false;

  for (const rawLine of lines) {
    const trimmedRight = rawLine.replace(/[ \t]+$/u, "");
    const { code, comment } = splitLineComment(trimmedRight);
    const trimmedCode = code.trim();

    if (trimmedCode.length === 0 && comment.length === 0) {
      if (depth === 0 && output.length > 0) {
        pendingTopLevelBlank = true;
      }
      continue;
    }

    if (/^end\b/u.test(trimmedCode)) {
      depth = Math.max(0, depth - 1);
    }

    const isTopLevel = depth === 0;
    if (isTopLevel && pendingTopLevelBlank && output.length > 0 && output.at(-1) !== "") {
      output.push("");
    }
    pendingTopLevelBlank = false;

    const formattedCode = formatCode(trimmedCode);
    const indent = isTopLevel ? "" : INDENT.repeat(depth);
    output.push(`${indent}${joinCodeAndComment(formattedCode, comment)}`.trimEnd());

    if (isModuleLine(trimmedCode) || /^end\b/u.test(trimmedCode)) {
      pendingTopLevelBlank = true;
    }

    if (/^(node|trait|choice|enum)\b/u.test(trimmedCode)) {
      depth += 1;
    }
  }

  return output.join(eol) + (hasFinalNewline || output.length > 0 ? eol : "");
}

/**
 * @param {string} code
 * @returns {string}
 */
function formatCode(code) {
  if (code.length === 0) {
    return "";
  }

  const moduleMatch = MODULE_PATTERN.exec(code);
  if (moduleMatch) {
    return `module ${moduleMatch[1]}`;
  }

  const declarationMatch = DECLARATION_PATTERN.exec(code);
  if (declarationMatch) {
    const [, keyword, name, rest] = declarationMatch;
    return `${keyword} ${name}${formatDeclarationSuffix(rest)}`;
  }

  const fieldMatch = FIELD_PATTERN.exec(code);
  if (fieldMatch) {
    const [, name, typeExpression] = fieldMatch;
    const formattedType = formatFieldType(typeExpression);
    return formattedType.length > 0 ? `${name}: ${formattedType}` : `${name}:`;
  }

  if (/^end\b/u.test(code)) {
    return "end";
  }

  return code.replace(/\s*\|\s*/gu, " | ").replace(/\s+/gu, " ").trim();
}

/**
 * @param {string} suffix
 * @returns {string}
 */
function formatDeclarationSuffix(suffix) {
  const trimmed = suffix.trim();
  if (trimmed.length === 0) {
    return "";
  }

  const withMatch = /^with\s+(.+)$/u.exec(trimmed);
  if (!withMatch) {
    return ` ${trimmed.replace(/\s+/gu, " ")}`;
  }

  const traits = withMatch[1]
    .split(",")
    .map((trait) => trait.trim())
    .filter((trait) => trait.length > 0)
    .join(", ");
  return traits.length > 0 ? ` with ${traits}` : "";
}

/**
 * @param {string} typeExpression
 * @returns {string}
 */
function formatFieldType(typeExpression) {
  const tokens = [...typeExpression.matchAll(/[A-Za-z_][A-Za-z0-9_]*|[*?]/gu)].map(
    (match) => match[0],
  );
  const formatted = [];

  for (let index = 0; index < tokens.length; index += 1) {
    const token = tokens[index];
    if ((token === "*" || token === "?") && tokens[index + 1]) {
      formatted.push(`${token}${tokens[index + 1]}`);
      index += 1;
    } else {
      formatted.push(token);
    }
  }

  return formatted.join(" ");
}

/**
 * @param {string} line
 * @returns {{code: string, comment: string}}
 */
function splitLineComment(line) {
  const commentStart = line.indexOf("//");
  if (commentStart === -1) {
    return { code: line, comment: "" };
  }
  return {
    code: line.slice(0, commentStart),
    comment: line.slice(commentStart).trim(),
  };
}

/**
 * @param {string} code
 * @param {string} comment
 * @returns {string}
 */
function joinCodeAndComment(code, comment) {
  if (comment.length === 0) {
    return code;
  }
  if (code.length === 0) {
    return comment;
  }
  return `${code} ${comment}`;
}

/**
 * @param {string} code
 * @returns {boolean}
 */
function isModuleLine(code) {
  return MODULE_PATTERN.test(code);
}

module.exports = {
  formatNdefText,
};
