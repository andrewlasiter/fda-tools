/**
 * FDA Generic Tool
 *
 * Universal wrapper for all 68 FDA commands. This tool provides access
 * to any FDA command through a simple command + args interface,
 * complementing the specialized tools (research, validate, analyze, draft)
 * that offer structured parameters for the most common commands.
 *
 * When the AI agent cannot match a user request to a specialized tool,
 * it falls back to this generic tool which can execute any command.
 *
 * @module tools/fda_generic
 * @version 1.0.0
 */

import { BridgeClient, BridgeClientError } from '../bridge/client';
import type {
  Tool,
  ToolContext,
  CommandInfo,
  DataClassification,
} from '../bridge/types';

const client = new BridgeClient();

/**
 * Cache for available commands (refreshed on first use and periodically).
 */
let commandCache: CommandInfo[] | null = null;
let commandCacheTime: number = 0;
const CACHE_TTL_MS = 300_000; // 5 minutes

/**
 * Commands known to access CONFIDENTIAL data.
 * Used to pre-warn users on messaging channels.
 */
const CONFIDENTIAL_COMMANDS = new Set([
  'draft',
  'assemble',
  'export',
  'consistency',
  'pre-check',
  'review',
  'import',
  'pipeline',
  'data-pipeline',
  'submission-outline',
  'test-plan',
  'compare-se',
  'traceability',
  'pccp',
]);

/**
 * FDA Generic Command tool for executing any of the 68 available commands.
 *
 * @example
 * User: "Check the safety profile for product code GEI"
 * Tool executes: command=safety, args="--product-code GEI"
 *
 * @example
 * User: "Show me FDA guidance for electrosurgical devices"
 * Tool executes: command=guidance, args="--product-code GEI"
 *
 * @example
 * User: "Calculate shelf life with Q10=2, Taa=55, Trt=25, Trt_time=2"
 * Tool executes: command=calc, args="shelf-life --q10 2 --taa 55 --trt 25 --time 2"
 */
export const fdaGenericTool: Tool = {
  name: 'fda_command',
  description:
    'Execute any FDA command from the 68 available commands. Use this when ' +
    'the specialized tools (fda_research, fda_validate, fda_analyze, fda_draft) ' +
    'do not match the request. Common commands include: safety, warnings, ' +
    'trials, guidance, standards, udi, compare-se, consistency, pre-check, ' +
    'assemble, export, lineage, monitor, calc, dashboard, portfolio, ' +
    'batchfetch, pathway, presub, pccp, and more.',

  parameters: {
    command: {
      type: 'string',
      required: true,
      description:
        'FDA command name. Examples: safety, warnings, trials, guidance, ' +
        'standards, udi, compare-se, consistency, pre-check, assemble, ' +
        'export, lineage, monitor, calc, dashboard, portfolio, batchfetch, ' +
        'pathway, presub, pccp, pma-search, pma-compare, pma-intelligence, ' +
        'pma-timeline, pma-risk, predict-review-time, approval-probability, ' +
        'competitive-dashboard, search-predicates, smart-predicates.',
    },
    args: {
      type: 'string',
      required: false,
      description:
        'Command arguments as a single string. ' +
        'Examples: "--product-code DQY --years 2024", ' +
        '"K240001 K230456", "--project my-device --section device-description". ' +
        'Use the FDA Bridge Server\'s GET /commands endpoint to see ' +
        'argument hints for each command.',
    },
    project_name: {
      type: 'string',
      required: false,
      description:
        'Project name to add as --project flag. Convenience parameter ' +
        'that appends "--project <name>" to args.',
    },
  },

  async execute(
    params: Record<string, unknown>,
    context: ToolContext
  ): Promise<string> {
    const command = (params.command as string).toLowerCase().trim();
    let args = (params.args as string | undefined) ?? '';

    // Append project name if provided and not already in args
    if (params.project_name && !args.includes('--project')) {
      args = `${args} --project ${params.project_name as string}`.trim();
    }

    // Pre-warn about confidential commands on messaging channels
    if (
      CONFIDENTIAL_COMMANDS.has(command) &&
      context.channel !== 'file'
    ) {
      context.warn(
        `Command '${command}' typically accesses CONFIDENTIAL project data. ` +
          `It may be blocked on '${context.channel}' channel. ` +
          `Use file output for confidential operations.`
      );
    }

    try {
      // Validate command exists (use cache if available)
      const commands = await getCommandList();
      if (commands && commands.length > 0) {
        const found = commands.find(
          (c) => c.name.toLowerCase() === command
        );
        if (!found) {
          // Command not found -- suggest similar commands
          const suggestions = findSimilarCommands(command, commands);
          return (
            `[ERROR] Command '${command}' not found.\n\n` +
            (suggestions.length > 0
              ? `Did you mean:\n${suggestions.map((s) => `  - ${s.name}: ${s.description}`).join('\n')}\n\n`
              : '') +
            `Use "list all FDA commands" to see all ${commands.length} available commands.`
          );
        }
      }

      if (context.progress) {
        context.progress(`Running ${command}...`, 10);
      }

      const response = await client.execute({
        command,
        args: args || undefined,
        user_id: context.user_id,
        session_id: context.session_id,
        channel: context.channel || 'file',
      });

      if (context.progress) {
        context.progress('Complete', 100);
      }

      if (response.warnings && response.warnings.length > 0) {
        context.warn(response.warnings.join('\n'));
      }

      if (!response.success) {
        return formatErrorResponse(command, args, response, context);
      }

      context.updateSession({
        session_id: response.session_id,
        last_command: command,
      });

      return response.result ?? '(No results returned)';
    } catch (error) {
      if (error instanceof BridgeClientError) {
        return formatBridgeError(error, command);
      }
      throw error;
    }
  },
};

// ============================================================
// Helper Functions
// ============================================================

/**
 * Get the list of available commands (cached).
 */
async function getCommandList(): Promise<CommandInfo[] | null> {
  const now = Date.now();

  if (commandCache && now - commandCacheTime < CACHE_TTL_MS) {
    return commandCache;
  }

  try {
    const response = await client.listCommands();
    commandCache = response.commands;
    commandCacheTime = now;
    return commandCache;
  } catch {
    // If we cannot reach the server, return cached data or null
    return commandCache;
  }
}

/**
 * Find commands with similar names for typo suggestions.
 * Uses simple Levenshtein-like prefix matching.
 */
function findSimilarCommands(
  input: string,
  commands: CommandInfo[]
): CommandInfo[] {
  const matches: Array<{ cmd: CommandInfo; score: number }> = [];

  for (const cmd of commands) {
    const name = cmd.name.toLowerCase();

    // Exact prefix match
    if (name.startsWith(input) || input.startsWith(name)) {
      matches.push({ cmd, score: 1 });
      continue;
    }

    // Contains match
    if (name.includes(input) || input.includes(name)) {
      matches.push({ cmd, score: 2 });
      continue;
    }

    // Simple character overlap scoring
    let overlap = 0;
    for (const char of input) {
      if (name.includes(char)) overlap++;
    }
    const similarity = overlap / Math.max(input.length, name.length);
    if (similarity > 0.5) {
      matches.push({ cmd, score: 3 });
    }
  }

  return matches
    .sort((a, b) => a.score - b.score)
    .slice(0, 5)
    .map((m) => m.cmd);
}

/**
 * Format an error response with actionable guidance.
 */
function formatErrorResponse(
  command: string,
  args: string,
  response: {
    success: boolean;
    error?: string;
    classification: DataClassification;
    llm_provider: string;
  },
  context: ToolContext
): string {
  if (response.classification === 'CONFIDENTIAL') {
    return (
      `[SECURITY BLOCK] Command '${command}' was blocked.\n\n` +
      `Classification: CONFIDENTIAL\n` +
      `Channel: ${context.channel} (not permitted for CONFIDENTIAL data)\n\n` +
      `This command accesses confidential project data that cannot be ` +
      `transmitted through messaging channels.\n\n` +
      `Options:\n` +
      `1. Use file output or a local terminal\n` +
      `2. Use the FDA Tools plugin directly in Claude Code\n` +
      `3. Configure local LLM (Ollama) for confidential processing`
    );
  }

  return (
    `[ERROR] Command '${command}' failed.\n` +
    `Arguments: ${args || '(none)'}\n` +
    `Classification: ${response.classification}\n` +
    `Error: ${response.error ?? 'Unknown error'}`
  );
}

/**
 * Format a BridgeClientError into a user-friendly message.
 */
function formatBridgeError(
  error: BridgeClientError,
  command: string
): string {
  switch (error.errorType) {
    case 'CONNECTION_REFUSED':
      return (
        `[CONNECTION ERROR] The FDA Bridge Server is not running.\n\n` +
        `To start it:\n` +
        `  cd /path/to/fda-tools\n` +
        `  python3 bridge/server.py\n\n` +
        `The bridge server must be accessible at http://localhost:18790.`
      );

    case 'AUTHENTICATION_REQUIRED':
      return (
        `[AUTHENTICATION ERROR] Missing or invalid API key.\n\n` +
        `The FDA Bridge Server requires authentication.\n` +
        `Set the FDA_BRIDGE_API_KEY environment variable:\n` +
        `  export FDA_BRIDGE_API_KEY="<your-bridge-api-key>"\n\n` +
        `The API key is displayed when the bridge server starts for the first time.\n` +
        `You can also retrieve it from the OS keyring.`
      );

    case 'RATE_LIMITED':
      return (
        `[RATE LIMITED] Too many requests for command '${command}'.\n` +
        `The bridge server is rate limiting requests. Wait a moment ` +
        `and try again.`
      );

    case 'TIMEOUT':
      return (
        `[TIMEOUT] Command '${command}' timed out after ${error.attempts} attempts.\n` +
        `This can happen with data-intensive commands. Try again or ` +
        `narrow your query parameters.`
      );

    case 'COMMAND_NOT_FOUND':
      return (
        `[NOT FOUND] Command '${command}' does not exist.\n` +
        `Use "list all FDA commands" to see available commands.`
      );

    case 'SECURITY_VIOLATION':
      return (
        `[SECURITY] Access denied for command '${command}'.\n` +
        `The SecurityGateway blocked this request. Check your ` +
        `channel and data classification settings.`
      );

    default:
      return (
        `[ERROR] Command '${command}' failed: ${error.message}\n` +
        `Error type: ${error.errorType}\n` +
        `Attempts: ${error.attempts}`
      );
  }
}
