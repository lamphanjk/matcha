import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const require = createRequire(new URL('../frontend/package.json', import.meta.url));
const babel = createRequire(require.resolve('@vitejs/plugin-react'))('@babel/core');
const baseline = 'ba359123e3dd537ade3197b01a53390a73207bac';
const parse = source => babel.parseSync(source, {
  configFile: false, babelrc: false, parserOpts: { plugins: ['jsx'] },
});
const ignoredKeys = new Set(['start', 'end', 'loc', 'extra', 'leadingComments', 'trailingComments', 'innerComments']);
const serialize = node => JSON.stringify(node, (key, value) => ignoredKeys.has(key) ? undefined : value);

function functions(source) {
  const app = parse(source).program.body.find(node =>
    node.type === 'ExportNamedDeclaration' && node.declaration?.id?.name === 'AppProvider').declaration;
  const result = new Map();
  for (const node of app.body.body) {
    if (node.type === 'FunctionDeclaration') result.set(node.id.name, serialize(node));
    if (node.type !== 'VariableDeclaration') continue;
    for (const declaration of node.declarations) {
      if (declaration.id.type !== 'Identifier') continue;
      if (['ArrowFunctionExpression', 'FunctionExpression'].includes(declaration.init?.type)
          || declaration.init?.callee?.name === 'useCallback') {
        result.set(declaration.id.name, serialize(declaration.init));
      }
    }
  }
  return result;
}

const path = 'frontend/src/store/index.jsx';
const before = functions(execFileSync('git', ['show', `${baseline}:${path}`], { cwd: root, encoding: 'utf8' }));
const after = functions(readFileSync(new URL('../' + path, import.meta.url), 'utf8'));
const changed = [...new Set([...before.keys(), ...after.keys()])].filter(name => before.get(name) !== after.get(name));
if (changed.some(name => !['loadExceptions', 'changeDateFilter'].includes(name))) {
  throw new Error(`Unexpected store changes: ${changed.join(', ')}`);
}
console.log(`PASS: changed store functions: ${changed.join(', ')}`);
console.log(`PASS: ${[...before.keys()].filter(name => before.get(name) === after.get(name)).length} store functions match the baseline`);
console.log('Allocation, reconciliation, undo and exception-to-reconcile handlers are unchanged.');
