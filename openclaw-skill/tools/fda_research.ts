/**
 * FDA Research Tool
 *
 * High-level tool for the most frequently used FDA command: research.
 * Performs 510(k) predicate research including predicate selection,
 * testing strategy, IFU landscape analysis, regulatory intelligence,
 * and competitive analysis.
 *
 * This tool wraps the `research` command with structured parameters
 * for a better user experience compared to the generic tool.
 *
 * @module tools/fda_research
 * @version 1.0.0
 */

import { BridgeClient, BridgeClientError } from '../bridge/client';
import type { Tool, ToolContext } from '../bridge/types';

const client = new BridgeClient();

/**
 * FDA Research tool for predicate discovery and submission planning.
 *
 * @example
 * User: "I need to find predicates for a cardiovascular catheter DQY"
 * Tool executes: research --product-code DQY
 *
 * @example
 * User: "Research predicates for my spinal fusion cage project"
 * Tool executes: research --product-code OVE --device-description "spinal fusion cage"
 */
export const fdaResearchTool: Tool = {
  name: 'fda_research',
  description:
    'Research 510(k) predicates and plan a submission strategy for a medical device. ' +
    'Returns predicate candidates, testing strategy, IFU landscape, regulatory ' +
    'intelligence, and competitive analysis based on FDA databases.',

  parameters: {
    product_code: {
      type: 'string',
      required: true,
      description:
        '3-letter FDA product code (e.g., DQY for cardiovascular catheters, ' +
        'OVE for orthopedic cervical fusion, GEI for electrosurgical devices). ' +
        'This is the primary identifier used to search the FDA database.',
    },
    device_description: {
      type: 'string',
      required: false,
      description:
        'Brief device description to help narrow predicate results. ' +
        'Example: "balloon-expandable coronary stent" or "powered surgical stapler".',
    },
    intended_use: {
      type: 'string',
      required: false,
      description:
        'Intended use statement to improve predicate matching. ' +
        'Example: "intended for use in coronary artery revascularization procedures".',
    },
    project_name: {
      type: 'string',
      required: false,
      description:
        'Project name to load existing project data. If provided, the research ' +
        'command will integrate with existing device profile and review data.',
    },
    include_pma: {
      type: 'boolean',
      required: false,
      description:
        'Include PMA devices in the research results. Useful for understanding ' +
        'the competitive landscape and potential pathway changes.',
      default: false,
    },
    deep_analysis: {
      type: 'boolean',
      required: false,
      description:
        'Enable deep competitive analysis mode with extended data gathering.',
      default: false,
    },
  },

  async execute(
    params: Record<string, unknown>,
    context: ToolContext
  ): Promise<string> {
    // Build command arguments from structured parameters
    const argParts: string[] = [];

    const productCode = params.product_code as string;
    argParts.push(`--product-code ${productCode}`);

    if (params.device_description) {
      const desc = (params.device_description as string).replace(/"/g, '\\"');
      argParts.push(`--device-description "${desc}"`);
    }

    if (params.intended_use) {
      const use = (params.intended_use as string).replace(/"/g, '\\"');
      argParts.push(`--intended-use "${use}"`);
    }

    if (params.project_name) {
      argParts.push(`--project ${params.project_name as string}`);
    }

    if (params.include_pma) {
      argParts.push('--include-pma');
    }

    if (params.deep_analysis) {
      argParts.push('--competitor-deep');
    }

    const args = argParts.join(' ');

    try {
      const response = await client.execute({
        command: 'research',
        args,
        user_id: context.user_id,
        session_id: context.session_id,
        channel: context.channel || 'file',
      });

      // Display security warnings to the user
      if (response.warnings && response.warnings.length > 0) {
        context.warn(response.warnings.join('\n'));
      }

      // Handle security block
      if (!response.success && response.classification === 'CONFIDENTIAL') {
        return (
          `[SECURITY] This request was blocked because it accesses ` +
          `CONFIDENTIAL data (classification: ${response.classification}). ` +
          `Channel '${context.channel}' is not permitted for confidential data.\n\n` +
          `To access confidential project data, use file output or a local ` +
          `terminal session instead of messaging platforms.\n\n` +
          `Error: ${response.error}`
        );
      }

      // Handle other errors
      if (!response.success) {
        return (
          `[ERROR] Research command failed.\n` +
          `Classification: ${response.classification}\n` +
          `Error: ${response.error}\n\n` +
          `Try: "fda research for product code ${productCode}"`
        );
      }

      // Update session with research context
      context.updateSession({
        session_id: response.session_id,
        last_product_code: productCode,
        last_command: 'research',
      });

      // Report progress
      if (context.progress) {
        context.progress('Research complete', 100);
      }

      return response.result ?? '(No results returned)';
    } catch (error) {
      if (error instanceof BridgeClientError) {
        return formatBridgeError(error, 'research');
      }
      throw error;
    }
  },
};

/**
 * Format a BridgeClientError into a user-friendly message.
 */
function formatBridgeError(error: BridgeClientError, command: string): string {
  switch (error.errorType) {
    case 'CONNECTION_REFUSED':
      return (
        `[CONNECTION ERROR] The FDA Bridge Server is not running.\n\n` +
        `To start it:\n` +
        `  cd /path/to/fda-predicate-assistant\n` +
        `  python3 bridge/server.py\n\n` +
        `The bridge server must be running on http://localhost:18790 ` +
        `for FDA tools to work.`
      );

    case 'TIMEOUT':
      return (
        `[TIMEOUT] The '${command}' command took too long to complete.\n` +
        `This can happen with large dataset queries. ` +
        `Try narrowing your search parameters or try again later.`
      );

    case 'SECURITY_VIOLATION':
      return (
        `[SECURITY] Access denied by SecurityGateway.\n` +
        `The security policy does not allow this operation ` +
        `on the current channel. Use file output for sensitive data.`
      );

    default:
      return (
        `[ERROR] FDA command '${command}' failed: ${error.message}\n` +
        `Error type: ${error.errorType}\n` +
        `Attempts: ${error.attempts}`
      );
  }
}
