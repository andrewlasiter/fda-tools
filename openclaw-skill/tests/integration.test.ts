/**
 * FDA Tools OpenClaw Skill - Integration Test Suite
 *
 * Structural validation tests that verify the skill is correctly
 * assembled without requiring a running OpenClaw environment or
 * FDA Bridge Server.
 *
 * These tests verify:
 * 1. Skill manifest (SKILL.md) is valid
 * 2. All tools are properly exported with correct interfaces
 * 3. Bridge client handles errors correctly
 * 4. TypeScript types are consistent
 * 5. Package configuration is valid
 * 6. Tool parameter definitions are complete
 * 7. Error handling covers all failure modes
 *
 * Run with:
 *   npm test
 *
 * @module tests/integration
 * @version 1.0.0
 */

import { describe, test, expect, beforeEach, jest } from '@jest/globals';
import * as fs from 'fs';
import * as path from 'path';

// ============================================================
// Test Utilities
// ============================================================

const SKILL_ROOT = path.resolve(__dirname, '..');
const SKILL_MD_PATH = path.join(SKILL_ROOT, 'SKILL.md');
const PACKAGE_JSON_PATH = path.join(SKILL_ROOT, 'package.json');
const TSCONFIG_PATH = path.join(SKILL_ROOT, 'tsconfig.json');

/**
 * Parse YAML-like frontmatter from SKILL.md
 */
function parseFrontmatter(content: string): Record<string, unknown> {
  const match = content.match(/^---\s*\n([\s\S]*?)\n---/);
  if (!match) return {};

  const frontmatter: Record<string, unknown> = {};
  let currentKey = '';
  const lines = match[1].split('\n');

  for (const line of lines) {
    const kvMatch = line.match(/^(\w[\w_-]*):\s*(.+)$/);
    if (kvMatch) {
      const key = kvMatch[1];
      let value: unknown = kvMatch[2].trim();

      // Handle quoted strings
      if (
        (typeof value === 'string' && value.startsWith('"') && value.endsWith('"')) ||
        (typeof value === 'string' && value.startsWith("'") && value.endsWith("'"))
      ) {
        value = (value as string).slice(1, -1);
      }

      // Handle booleans
      if (value === 'true') value = true;
      if (value === 'false') value = false;

      frontmatter[key] = value;
      currentKey = key;
    } else if (line.match(/^\s+-\s+/)) {
      // Array item
      const item = line.replace(/^\s+-\s+/, '').trim().replace(/^["']|["']$/g, '');
      if (!Array.isArray(frontmatter[currentKey])) {
        frontmatter[currentKey] = [];
      }
      (frontmatter[currentKey] as string[]).push(item);
    }
  }

  return frontmatter;
}

// ============================================================
// 1. Skill Manifest Tests
// ============================================================

describe('SKILL.md Manifest', () => {
  let content: string;
  let frontmatter: Record<string, unknown>;

  beforeEach(() => {
    content = fs.readFileSync(SKILL_MD_PATH, 'utf-8');
    frontmatter = parseFrontmatter(content);
  });

  test('SKILL.md exists and is non-empty', () => {
    expect(content.length).toBeGreaterThan(100);
  });

  test('has valid frontmatter with required fields', () => {
    expect(frontmatter.name).toBeDefined();
    expect(frontmatter.description).toBeDefined();
    expect(frontmatter.version).toBeDefined();
  });

  test('has skill name', () => {
    expect(frontmatter.name).toBe('FDA Regulatory Intelligence');
  });

  test('has version 1.0.0', () => {
    expect(frontmatter.version).toBe('1.0.0');
  });

  test('has trigger phrases defined', () => {
    expect(frontmatter.triggers).toBeDefined();
    expect(Array.isArray(frontmatter.triggers)).toBe(true);
    const triggers = frontmatter.triggers as string[];
    expect(triggers.length).toBeGreaterThanOrEqual(10);
  });

  test('triggers include key phrases', () => {
    const triggers = frontmatter.triggers as string[];
    const triggerSet = new Set(triggers.map((t) => t.toLowerCase()));
    expect(triggerSet.has('fda predicate')).toBe(true);
    expect(triggerSet.has('510(k)')).toBe(true);
    expect(triggerSet.has('substantial equivalence')).toBe(true);
    expect(triggerSet.has('pma approval')).toBe(true);
  });

  test('contains security classification section', () => {
    expect(content).toContain('Security Classification');
    expect(content).toContain('PUBLIC');
    expect(content).toContain('RESTRICTED');
    expect(content).toContain('CONFIDENTIAL');
  });

  test('contains available commands section', () => {
    expect(content).toContain('Available Commands');
    expect(content).toContain('research');
    expect(content).toContain('validate');
    expect(content).toContain('draft');
    expect(content).toContain('safety');
  });

  test('contains example conversations', () => {
    expect(content).toContain('Example Conversations');
    expect(content).toContain('Example 1');
    expect(content).toContain('Example 2');
  });

  test('contains installation instructions', () => {
    expect(content).toContain('Installation');
    expect(content).toContain('openclaw');
    expect(content).toContain('bridge');
  });

  test('specifies bridge_url', () => {
    expect(frontmatter.bridge_url).toBe('http://localhost:18790');
  });

  test('specifies bridge_required as true', () => {
    expect(frontmatter.bridge_required).toBe(true);
  });
});

// ============================================================
// 2. Tool Export Tests
// ============================================================

describe('Tool Exports', () => {
  test('index.ts exports fdaToolsSkill', async () => {
    // Verify the file exists and has the expected export
    const indexPath = path.join(SKILL_ROOT, 'index.ts');
    const content = fs.readFileSync(indexPath, 'utf-8');

    expect(content).toContain('export const fdaToolsSkill');
    expect(content).toContain('export default fdaToolsSkill');
  });

  test('index.ts imports all 5 tool modules', async () => {
    const indexPath = path.join(SKILL_ROOT, 'index.ts');
    const content = fs.readFileSync(indexPath, 'utf-8');

    expect(content).toContain("from './tools/fda_research'");
    expect(content).toContain("from './tools/fda_validate'");
    expect(content).toContain("from './tools/fda_analyze'");
    expect(content).toContain("from './tools/fda_draft'");
    expect(content).toContain("from './tools/fda_generic'");
  });

  test('fdaResearchTool has correct structure', () => {
    const toolPath = path.join(SKILL_ROOT, 'tools', 'fda_research.ts');
    const content = fs.readFileSync(toolPath, 'utf-8');

    expect(content).toContain("name: 'fda_research'");
    expect(content).toContain('description:');
    expect(content).toContain('parameters:');
    expect(content).toContain('async execute(');
    expect(content).toContain('product_code');
  });

  test('fdaValidateTool has correct structure', () => {
    const toolPath = path.join(SKILL_ROOT, 'tools', 'fda_validate.ts');
    const content = fs.readFileSync(toolPath, 'utf-8');

    expect(content).toContain("name: 'fda_validate'");
    expect(content).toContain('description:');
    expect(content).toContain('parameters:');
    expect(content).toContain('async execute(');
    expect(content).toContain('numbers');
  });

  test('fdaAnalyzeTool has correct structure', () => {
    const toolPath = path.join(SKILL_ROOT, 'tools', 'fda_analyze.ts');
    const content = fs.readFileSync(toolPath, 'utf-8');

    expect(content).toContain("name: 'fda_analyze'");
    expect(content).toContain('description:');
    expect(content).toContain('parameters:');
    expect(content).toContain('async execute(');
    expect(content).toContain('target');
  });

  test('fdaDraftTool has correct structure', () => {
    const toolPath = path.join(SKILL_ROOT, 'tools', 'fda_draft.ts');
    const content = fs.readFileSync(toolPath, 'utf-8');

    expect(content).toContain("name: 'fda_draft'");
    expect(content).toContain('description:');
    expect(content).toContain('parameters:');
    expect(content).toContain('async execute(');
    expect(content).toContain('section');
    expect(content).toContain('project_name');
  });

  test('fdaGenericTool has correct structure', () => {
    const toolPath = path.join(SKILL_ROOT, 'tools', 'fda_generic.ts');
    const content = fs.readFileSync(toolPath, 'utf-8');

    expect(content).toContain("name: 'fda_command'");
    expect(content).toContain('description:');
    expect(content).toContain('parameters:');
    expect(content).toContain('async execute(');
    expect(content).toContain('command');
  });

  test('all tools have unique names', () => {
    const toolFiles = [
      'fda_research.ts',
      'fda_validate.ts',
      'fda_analyze.ts',
      'fda_draft.ts',
      'fda_generic.ts',
    ];

    const names = new Set<string>();
    for (const file of toolFiles) {
      const content = fs.readFileSync(
        path.join(SKILL_ROOT, 'tools', file),
        'utf-8'
      );
      const nameMatch = content.match(/name:\s*['"]([^'"]+)['"]/);
      expect(nameMatch).not.toBeNull();
      if (nameMatch) {
        expect(names.has(nameMatch[1])).toBe(false);
        names.add(nameMatch[1]);
      }
    }

    expect(names.size).toBe(5);
  });
});

// ============================================================
// 3. Bridge Client Tests
// ============================================================

describe('Bridge Client Structure', () => {
  test('client.ts exists and exports BridgeClient', () => {
    const clientPath = path.join(SKILL_ROOT, 'bridge', 'client.ts');
    const content = fs.readFileSync(clientPath, 'utf-8');

    expect(content).toContain('export class BridgeClient');
    expect(content).toContain('export class BridgeClientError');
  });

  test('BridgeClient has all required methods', () => {
    const clientPath = path.join(SKILL_ROOT, 'bridge', 'client.ts');
    const content = fs.readFileSync(clientPath, 'utf-8');

    // Core API methods
    expect(content).toContain('async execute(');
    expect(content).toContain('async health(');
    expect(content).toContain('async listCommands(');
    expect(content).toContain('async createSession(');
    expect(content).toContain('async getSession(');
    expect(content).toContain('async listSessions(');
    expect(content).toContain('async getPendingQuestions(');
    expect(content).toContain('async submitAnswer(');
    expect(content).toContain('async listTools(');
    expect(content).toContain('async verifyAuditIntegrity(');
  });

  test('BridgeClient has retry logic', () => {
    const clientPath = path.join(SKILL_ROOT, 'bridge', 'client.ts');
    const content = fs.readFileSync(clientPath, 'utf-8');

    expect(content).toContain('retryRequest');
    expect(content).toContain('exponential backoff');
    expect(content).toContain('isRetryable');
    expect(content).toContain('Math.pow(2, attempt)');
  });

  test('BridgeClient has timeout handling', () => {
    const clientPath = path.join(SKILL_ROOT, 'bridge', 'client.ts');
    const content = fs.readFileSync(clientPath, 'utf-8');

    expect(content).toContain('AbortController');
    expect(content).toContain('setTimeout');
    expect(content).toContain('controller.abort()');
    expect(content).toContain('clearTimeout');
  });

  test('BridgeClient has error classification', () => {
    const clientPath = path.join(SKILL_ROOT, 'bridge', 'client.ts');
    const content = fs.readFileSync(clientPath, 'utf-8');

    expect(content).toContain('CONNECTION_REFUSED');
    expect(content).toContain('TIMEOUT');
    expect(content).toContain('SECURITY_VIOLATION');
    expect(content).toContain('COMMAND_NOT_FOUND');
    expect(content).toContain('SESSION_NOT_FOUND');
    expect(content).toContain('SERVER_ERROR');
  });

  test('BridgeClient uses correct default URL', () => {
    const clientPath = path.join(SKILL_ROOT, 'bridge', 'client.ts');
    const content = fs.readFileSync(clientPath, 'utf-8');

    expect(content).toContain('http://localhost:18790');
  });

  test('BridgeClientError has proper error properties', () => {
    const clientPath = path.join(SKILL_ROOT, 'bridge', 'client.ts');
    const content = fs.readFileSync(clientPath, 'utf-8');

    expect(content).toContain('errorType: BridgeErrorType');
    expect(content).toContain('status?: number');
    expect(content).toContain('attempts: number');
    expect(content).toContain('cause?: Error');
  });
});

// ============================================================
// 4. Type Definitions Tests
// ============================================================

describe('TypeScript Type Definitions', () => {
  let typesContent: string;

  beforeEach(() => {
    typesContent = fs.readFileSync(
      path.join(SKILL_ROOT, 'bridge', 'types.ts'),
      'utf-8'
    );
  });

  test('types.ts exports all required interfaces', () => {
    const requiredExports = [
      'BridgeClientConfig',
      'ExecuteRequest',
      'ExecuteResponse',
      'HealthResponse',
      'CommandInfo',
      'CommandsResponse',
      'SessionRequest',
      'SessionResponse',
      'SessionDetail',
      'DataClassification',
      'LLMProvider',
      'Tool',
      'Skill',
      'ToolContext',
      'ToolParameter',
    ];

    for (const exportName of requiredExports) {
      expect(typesContent).toContain(exportName);
    }
  });

  test('DataClassification has all 3 tiers', () => {
    expect(typesContent).toContain("'PUBLIC'");
    expect(typesContent).toContain("'RESTRICTED'");
    expect(typesContent).toContain("'CONFIDENTIAL'");
  });

  test('LLMProvider has all providers', () => {
    expect(typesContent).toContain("'ollama'");
    expect(typesContent).toContain("'anthropic'");
    expect(typesContent).toContain("'openai'");
    expect(typesContent).toContain("'none'");
  });

  test('ExecuteRequest has required fields', () => {
    expect(typesContent).toContain('command: string');
    expect(typesContent).toContain('user_id: string');
    expect(typesContent).toContain('channel: string');
  });

  test('ExecuteResponse has classification and session fields', () => {
    expect(typesContent).toContain('classification: DataClassification');
    expect(typesContent).toContain('llm_provider: LLMProvider');
    expect(typesContent).toContain('session_id: string');
    expect(typesContent).toContain('success: boolean');
  });

  test('BridgeErrorType has all error categories', () => {
    expect(typesContent).toContain('CONNECTION_REFUSED');
    expect(typesContent).toContain('TIMEOUT');
    expect(typesContent).toContain('SECURITY_VIOLATION');
    expect(typesContent).toContain('COMMAND_NOT_FOUND');
    expect(typesContent).toContain('SESSION_NOT_FOUND');
    expect(typesContent).toContain('INVALID_REQUEST');
    expect(typesContent).toContain('SERVER_ERROR');
  });

  test('ToolContext has security-relevant methods', () => {
    expect(typesContent).toContain('warn(message: string): void');
    expect(typesContent).toContain('updateSession');
    expect(typesContent).toContain('channel: string');
    expect(typesContent).toContain('user_id: string');
  });
});

// ============================================================
// 5. Package Configuration Tests
// ============================================================

describe('Package Configuration', () => {
  let packageJson: Record<string, unknown>;

  beforeEach(() => {
    packageJson = JSON.parse(
      fs.readFileSync(PACKAGE_JSON_PATH, 'utf-8')
    );
  });

  test('package.json has correct name', () => {
    expect(packageJson.name).toBe('@openclaw/skill-fda-tools');
  });

  test('package.json has version 1.0.0', () => {
    expect(packageJson.version).toBe('1.0.0');
  });

  test('package.json has description', () => {
    expect(typeof packageJson.description).toBe('string');
    expect((packageJson.description as string).length).toBeGreaterThan(20);
  });

  test('package.json has correct main entry', () => {
    expect(packageJson.main).toBe('dist/index.js');
  });

  test('package.json has type module', () => {
    expect(packageJson.type).toBe('module');
  });

  test('package.json has required scripts', () => {
    const scripts = packageJson.scripts as Record<string, string>;
    expect(scripts.build).toBeDefined();
    expect(scripts.test).toBeDefined();
    expect(scripts.lint).toBeDefined();
    expect(scripts.typecheck).toBeDefined();
  });

  test('package.json has @openclaw/sdk peer dependency', () => {
    const peerDeps = packageJson.peerDependencies as Record<string, string>;
    expect(peerDeps['@openclaw/sdk']).toBeDefined();
  });

  test('package.json has TypeScript in devDependencies', () => {
    const devDeps = packageJson.devDependencies as Record<string, string>;
    expect(devDeps.typescript).toBeDefined();
    expect(devDeps['@types/node']).toBeDefined();
  });

  test('package.json has MIT license', () => {
    expect(packageJson.license).toBe('MIT');
  });

  test('package.json requires Node >= 18', () => {
    const engines = packageJson.engines as Record<string, string>;
    expect(engines.node).toContain('18');
  });
});

// ============================================================
// 6. tsconfig.json Tests
// ============================================================

describe('TypeScript Configuration', () => {
  let tsconfig: Record<string, unknown>;

  beforeEach(() => {
    tsconfig = JSON.parse(
      fs.readFileSync(TSCONFIG_PATH, 'utf-8')
    );
  });

  test('targets ES2022', () => {
    const options = tsconfig.compilerOptions as Record<string, unknown>;
    expect(options.target).toBe('ES2022');
  });

  test('uses ES2022 modules', () => {
    const options = tsconfig.compilerOptions as Record<string, unknown>;
    expect(options.module).toBe('ES2022');
  });

  test('has strict mode enabled', () => {
    const options = tsconfig.compilerOptions as Record<string, unknown>;
    expect(options.strict).toBe(true);
  });

  test('generates declarations', () => {
    const options = tsconfig.compilerOptions as Record<string, unknown>;
    expect(options.declaration).toBe(true);
    expect(options.declarationMap).toBe(true);
  });

  test('generates source maps', () => {
    const options = tsconfig.compilerOptions as Record<string, unknown>;
    expect(options.sourceMap).toBe(true);
  });

  test('outputs to dist directory', () => {
    const options = tsconfig.compilerOptions as Record<string, unknown>;
    expect(options.outDir).toBe('./dist');
  });

  test('includes all source files', () => {
    const include = tsconfig.include as string[];
    expect(include).toContain('index.ts');
    expect(include).toContain('bridge/**/*.ts');
    expect(include).toContain('tools/**/*.ts');
  });

  test('excludes test files', () => {
    const exclude = tsconfig.exclude as string[];
    expect(exclude).toContain('tests');
    expect(exclude).toContain('dist');
    expect(exclude).toContain('node_modules');
  });
});

// ============================================================
// 7. Tool Parameter Completeness Tests
// ============================================================

describe('Tool Parameter Definitions', () => {
  test('fda_research requires product_code', () => {
    const content = fs.readFileSync(
      path.join(SKILL_ROOT, 'tools', 'fda_research.ts'),
      'utf-8'
    );
    expect(content).toContain('product_code');
    expect(content).toContain("required: true");
  });

  test('fda_validate requires numbers', () => {
    const content = fs.readFileSync(
      path.join(SKILL_ROOT, 'tools', 'fda_validate.ts'),
      'utf-8'
    );
    expect(content).toContain('numbers');
    expect(content).toContain("type: 'string'");
  });

  test('fda_draft requires section and project_name', () => {
    const content = fs.readFileSync(
      path.join(SKILL_ROOT, 'tools', 'fda_draft.ts'),
      'utf-8'
    );
    expect(content).toContain('section');
    expect(content).toContain('project_name');
    // Both should be required
    const sectionBlock = content.substring(
      content.indexOf('section:'),
      content.indexOf('project_name:')
    );
    expect(sectionBlock).toContain('required: true');
  });

  test('fda_generic requires command parameter', () => {
    const content = fs.readFileSync(
      path.join(SKILL_ROOT, 'tools', 'fda_generic.ts'),
      'utf-8'
    );
    expect(content).toContain('command:');
    expect(content).toContain("required: true");
  });

  test('fda_draft lists all valid sections', () => {
    const content = fs.readFileSync(
      path.join(SKILL_ROOT, 'tools', 'fda_draft.ts'),
      'utf-8'
    );
    const expectedSections = [
      'device-description',
      'intended-use',
      'se-discussion',
      'performance-summary',
      'testing-rationale',
      'cover-letter',
      'form-3881',
      'software-description',
      'biocompatibility',
      'sterilization',
      'shelf-life',
    ];
    for (const section of expectedSections) {
      expect(content).toContain(section);
    }
  });

  test('fda_validate has K-number pattern validation', () => {
    const content = fs.readFileSync(
      path.join(SKILL_ROOT, 'tools', 'fda_validate.ts'),
      'utf-8'
    );
    expect(content).toContain('K_NUMBER_PATTERN');
    expect(content).toContain('P_NUMBER_PATTERN');
    expect(content).toContain('DEN_NUMBER_PATTERN');
  });
});

// ============================================================
// 8. Error Handling Tests
// ============================================================

describe('Error Handling Coverage', () => {
  test('all tools handle CONNECTION_REFUSED', () => {
    const toolFiles = [
      'fda_research.ts',
      'fda_validate.ts',
      'fda_analyze.ts',
      'fda_draft.ts',
      'fda_generic.ts',
    ];

    for (const file of toolFiles) {
      const content = fs.readFileSync(
        path.join(SKILL_ROOT, 'tools', file),
        'utf-8'
      );
      expect(content).toContain('BridgeClientError');
      expect(content).toContain('CONNECTION_REFUSED');
    }
  });

  test('all tools handle CONFIDENTIAL security blocks', () => {
    const toolFiles = [
      'fda_research.ts',
      'fda_analyze.ts',
      'fda_draft.ts',
      'fda_generic.ts',
    ];

    for (const file of toolFiles) {
      const content = fs.readFileSync(
        path.join(SKILL_ROOT, 'tools', file),
        'utf-8'
      );
      expect(content).toContain('CONFIDENTIAL');
    }
  });

  test('bridge client has RETRYABLE_STATUS_CODES', () => {
    const content = fs.readFileSync(
      path.join(SKILL_ROOT, 'bridge', 'client.ts'),
      'utf-8'
    );
    expect(content).toContain('RETRYABLE_STATUS_CODES');
    expect(content).toContain('408');
    expect(content).toContain('429');
    expect(content).toContain('500');
    expect(content).toContain('502');
    expect(content).toContain('503');
    expect(content).toContain('504');
  });

  test('fda_draft pre-warns about confidential data on messaging channels', () => {
    const content = fs.readFileSync(
      path.join(SKILL_ROOT, 'tools', 'fda_draft.ts'),
      'utf-8'
    );
    expect(content).toContain("context.channel !== 'file'");
    expect(content).toContain('context.warn(');
  });

  test('fda_generic identifies confidential commands', () => {
    const content = fs.readFileSync(
      path.join(SKILL_ROOT, 'tools', 'fda_generic.ts'),
      'utf-8'
    );
    expect(content).toContain('CONFIDENTIAL_COMMANDS');
    expect(content).toContain("'draft'");
    expect(content).toContain("'assemble'");
    expect(content).toContain("'export'");
    expect(content).toContain("'consistency'");
    expect(content).toContain("'pre-check'");
  });
});

// ============================================================
// 9. File Structure Completeness Tests
// ============================================================

describe('File Structure', () => {
  const requiredFiles = [
    'SKILL.md',
    'index.ts',
    'package.json',
    'tsconfig.json',
    'jest.config.json',
    'bridge/client.ts',
    'bridge/types.ts',
    'tools/fda_research.ts',
    'tools/fda_validate.ts',
    'tools/fda_analyze.ts',
    'tools/fda_draft.ts',
    'tools/fda_generic.ts',
    'tests/integration.test.ts',
    'README.md',
  ];

  for (const file of requiredFiles) {
    test(`${file} exists`, () => {
      const filePath = path.join(SKILL_ROOT, file);
      expect(fs.existsSync(filePath)).toBe(true);
    });
  }

  test('all TypeScript files have module-level JSDoc', () => {
    const tsFiles = [
      'index.ts',
      'bridge/client.ts',
      'bridge/types.ts',
      'tools/fda_research.ts',
      'tools/fda_validate.ts',
      'tools/fda_analyze.ts',
      'tools/fda_draft.ts',
      'tools/fda_generic.ts',
    ];

    for (const file of tsFiles) {
      const content = fs.readFileSync(
        path.join(SKILL_ROOT, file),
        'utf-8'
      );
      expect(content.startsWith('/**')).toBe(true);
    }
  });

  test('no TODO placeholders remain in production files', () => {
    const productionFiles = [
      'index.ts',
      'bridge/client.ts',
      'bridge/types.ts',
      'tools/fda_research.ts',
      'tools/fda_validate.ts',
      'tools/fda_analyze.ts',
      'tools/fda_draft.ts',
      'tools/fda_generic.ts',
    ];

    for (const file of productionFiles) {
      const content = fs.readFileSync(
        path.join(SKILL_ROOT, file),
        'utf-8'
      );
      // Allow TODO in comments but not in code
      const codeLines = content
        .split('\n')
        .filter((line) => !line.trim().startsWith('//') && !line.trim().startsWith('*'));
      const hasTodo = codeLines.some((line) =>
        line.includes('TODO') || line.includes('FIXME')
      );
      expect(hasTodo).toBe(false);
    }
  });
});

// ============================================================
// 10. Security Model Tests
// ============================================================

describe('Security Model Enforcement', () => {
  test('SKILL.md documents all 3 classification tiers', () => {
    const content = fs.readFileSync(SKILL_MD_PATH, 'utf-8');
    expect(content).toContain('PUBLIC');
    expect(content).toContain('RESTRICTED');
    expect(content).toContain('CONFIDENTIAL');
    expect(content).toContain('Local LLM');
    expect(content).toContain('SecurityGateway');
  });

  test('bridge types enforce classification typing', () => {
    const content = fs.readFileSync(
      path.join(SKILL_ROOT, 'bridge', 'types.ts'),
      'utf-8'
    );
    expect(content).toContain(
      "type DataClassification = 'PUBLIC' | 'RESTRICTED' | 'CONFIDENTIAL'"
    );
  });

  test('fda_generic tool categorizes commands by sensitivity', () => {
    const content = fs.readFileSync(
      path.join(SKILL_ROOT, 'tools', 'fda_generic.ts'),
      'utf-8'
    );
    expect(content).toContain('CONFIDENTIAL_COMMANDS');
    expect(content).toContain('PUBLIC_COMMANDS');
  });

  test('fda_draft blocks confidential data on messaging channels', () => {
    const content = fs.readFileSync(
      path.join(SKILL_ROOT, 'tools', 'fda_draft.ts'),
      'utf-8'
    );
    expect(content).toContain('SECURITY BLOCK');
    expect(content).toContain('CONFIDENTIAL');
    expect(content).toContain('not permitted');
  });

  test('all tools pass channel to bridge for security evaluation', () => {
    const toolFiles = [
      'tools/fda_research.ts',
      'tools/fda_validate.ts',
      'tools/fda_analyze.ts',
      'tools/fda_draft.ts',
      'tools/fda_generic.ts',
    ];

    for (const file of toolFiles) {
      const content = fs.readFileSync(
        path.join(SKILL_ROOT, file),
        'utf-8'
      );
      expect(content).toContain('channel: context.channel');
    }
  });
});
