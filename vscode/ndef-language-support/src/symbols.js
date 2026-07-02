const DECLARATION_PATTERN =
  /^\s*(?:node|trait|choice|enum)\s+([A-Za-z_][A-Za-z0-9_]*)\b/gm;

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

module.exports = { findDeclarations };
