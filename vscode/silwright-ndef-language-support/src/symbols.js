const DECLARATION_PATTERN =
  /^\s*(?:node|trait|choice|enum)\s+([A-Za-z_][A-Za-z0-9_]*)\b/gm;
const FIELD_TYPE_PATTERN =
  /^\s*[A-Za-z_][A-Za-z0-9_]*\s*:\s*(?:fixed\s+)?(?:[*?]\s*)?(?:value\s+)?(?:transient\s+)?([A-Za-z_][A-Za-z0-9_]*)\b/gm;
const CHOICE_BLOCK_PATTERN =
  /^\s*choice\s+[A-Za-z_][A-Za-z0-9_]*\b(?<body>[\s\S]*?)^\s*end\b/gm;
const NAME_PATTERN = /[A-Za-z_][A-Za-z0-9_]*/g;
const BACKEND_MAPPING_PATTERN = /^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:/gm;

/**
 * Find type declarations in an NDEF document.
 *
 * Offsets refer to the declaration name, not the declaration keyword.
 * The first declaration wins when malformed input contains duplicate names.
 *
 * @param {string} text
 * @returns {Map<string, {start: number, end: number}>}
 */
function findDeclarations(text) {
  const declarations = new Map();
  let match;

  while ((match = DECLARATION_PATTERN.exec(text)) !== null) {
    const name = match[1];
    if (declarations.has(name)) {
      continue;
    }

    const nameOffset = match[0].lastIndexOf(name);
    const start = match.index + nameOffset;
    declarations.set(name, { start, end: start + name.length });
  }

  return declarations;
}

/**
 * Find field type references in an NDEF document.
 *
 * Offsets refer to the referenced type name, not the complete field.
 *
 * @param {string} text
 * @returns {Array<{name: string, start: number, end: number}>}
 */
function findFieldTypeReferences(text) {
  const references = [];
  let match;

  while ((match = FIELD_TYPE_PATTERN.exec(stripNdefComments(text))) !== null) {
    const name = match[1];
    const nameOffset = match[0].lastIndexOf(name);
    const start = match.index + nameOffset;
    references.push({ name, start, end: start + name.length });
  }

  return references;
}

/**
 * Find choice alternative references in an NDEF document.
 *
 * Offsets refer to the referenced alternative name.
 *
 * @param {string} text
 * @returns {Array<{name: string, start: number, end: number, kind: "choiceAlternative"}>}
 */
function findChoiceAlternativeReferences(text) {
  const references = [];
  const stripped = stripNdefComments(text);
  let blockMatch;

  while ((blockMatch = CHOICE_BLOCK_PATTERN.exec(stripped)) !== null) {
    const body = blockMatch.groups.body;
    const bodyStart = blockMatch.index + blockMatch[0].indexOf(body);
    let nameMatch;

    NAME_PATTERN.lastIndex = 0;
    while ((nameMatch = NAME_PATTERN.exec(body)) !== null) {
      const name = nameMatch[0];
      const start = bodyStart + nameMatch.index;
      references.push({
        name,
        start,
        end: start + name.length,
        kind: "choiceAlternative",
      });
    }
  }

  return references;
}

/**
 * Find all type references in an NDEF document that editor features should resolve.
 *
 * @param {string} text
 * @returns {Array<{name: string, start: number, end: number, kind: "field" | "choiceAlternative"}>}
 */
function findTypeReferences(text) {
  return [
    ...findFieldTypeReferences(text).map((reference) => ({
      ...reference,
      kind: "field",
    })),
    ...findChoiceAlternativeReferences(text),
  ].sort((left, right) => left.start - right.start);
}

/**
 * Find C++ backend map type mappings.
 *
 * Offsets refer to the mapped Silwright type name.
 *
 * @param {string} text
 * @returns {Map<string, {start: number, end: number}>}
 */
function findBackendMappings(text) {
  const mappings = new Map();
  let match;

  while ((match = BACKEND_MAPPING_PATTERN.exec(stripMapComments(text))) !== null) {
    const name = match[1];
    if (mappings.has(name)) {
      continue;
    }

    const nameOffset = match[0].indexOf(name);
    const start = match.index + nameOffset;
    mappings.set(name, { start, end: start + name.length });
  }

  return mappings;
}

/**
 * @param {string} text
 * @returns {string}
 */
function stripNdefComments(text) {
  return text.replace(/\/\/[^\r\n]*/g, (match) => " ".repeat(match.length));
}

/**
 * @param {string} text
 * @returns {string}
 */
function stripMapComments(text) {
  return text.replace(/#[^\r\n]*/g, (match) => " ".repeat(match.length));
}

module.exports = {
  findBackendMappings,
  findChoiceAlternativeReferences,
  findDeclarations,
  findFieldTypeReferences,
  findTypeReferences,
};
