/**
 * FDA Validate Tool
 *
 * Tool for validating FDA device numbers against official databases.
 * Supports K-numbers (510(k)), P-numbers (PMA), DEN-numbers (De Novo),
 * and N-numbers with enrichment from all pipeline data sources.
 *
 * @module tools/fda_validate
 * @version 1.0.0
 */

import { BridgeClient, BridgeClientError } from '../bridge/client';
import type { Tool, ToolContext } from '../bridge/types';

const client = new BridgeClient();

/**
 * K-number pattern: K followed by 6 digits (e.g., K240001)
 */
const K_NUMBER_PATTERN = /^K\d{6}$/i;

/**
 * P-number pattern: P followed by 6 digits (e.g., P210012)
 */
const P_NUMBER_PATTERN = /^P\d{6}$/i;

/**
 * DEN-number pattern: DEN followed by digits (e.g., DEN200043)
 */
const DEN_NUMBER_PATTERN = /^DEN\d{6}$/i;

/**
 * FDA Validate tool for device number verification and enrichment.
 *
 * @example
 * User: "Validate K240001"
 * Tool executes: validate K240001
 *
 * @example
 * User: "Check these devices: K240001 K230456 K220789"
 * Tool executes: validate K240001 K230456 K220789
 */
export const fdaValidateTool: Tool = {
  name: 'fda_validate',
  description:
    'Validate FDA device numbers (K-numbers, P-numbers, DEN-numbers) against ' +
    'official FDA databases. Returns device details, applicant info, clearance ' +
    'dates, predicate chains, and enrichment from all available pipeline data.',

  parameters: {
    numbers: {
      type: 'string',
      required: true,
      description:
        'One or more FDA device numbers separated by spaces. ' +
        'Formats: K-number (K240001), P-number (P210012), DEN-number (DEN200043). ' +
        'Can also be a search query with --search flag.',
    },
    project_name: {
      type: 'string',
      required: false,
      description:
        'Project name to cross-reference validation results with project data.',
    },
    search_mode: {
      type: 'boolean',
      required: false,
      description:
        'Enable search mode to find devices by name, applicant, or product code ' +
        'instead of validating specific numbers.',
      default: false,
    },
    product_code: {
      type: 'string',
      required: false,
      description:
        '3-letter product code to filter search results (used with search_mode).',
    },
    year_range: {
      type: 'string',
      required: false,
      description:
        'Year range filter for search results (e.g., "2020-2024").',
    },
    limit: {
      type: 'number',
      required: false,
      description:
        'Maximum number of results to return in search mode. Default: 10.',
      default: 10,
    },
  },

  async execute(
    params: Record<string, unknown>,
    context: ToolContext
  ): Promise<string> {
    const numbers = params.numbers as string;
    const argParts: string[] = [];

    if (params.search_mode) {
      // Search mode: use --search flag
      argParts.push(`--search "${numbers.replace(/"/g, '\\"')}"`);

      if (params.product_code) {
        argParts.push(`--product-code ${params.product_code as string}`);
      }
      if (params.year_range) {
        argParts.push(`--year ${params.year_range as string}`);
      }
      if (params.limit) {
        argParts.push(`--limit ${params.limit as number}`);
      }
    } else {
      // Validation mode: pass numbers directly
      // Validate format of each number
      const deviceNumbers = numbers.trim().split(/\s+/);
      const validNumbers: string[] = [];
      const invalidNumbers: string[] = [];

      for (const num of deviceNumbers) {
        const upper = num.toUpperCase();
        if (
          K_NUMBER_PATTERN.test(upper) ||
          P_NUMBER_PATTERN.test(upper) ||
          DEN_NUMBER_PATTERN.test(upper)
        ) {
          validNumbers.push(upper);
        } else {
          invalidNumbers.push(num);
        }
      }

      if (invalidNumbers.length > 0 && validNumbers.length === 0) {
        return (
          `[FORMAT ERROR] None of the provided numbers match FDA device number formats:\n` +
          `  Invalid: ${invalidNumbers.join(', ')}\n\n` +
          `Expected formats:\n` +
          `  K-number: K followed by 6 digits (e.g., K240001)\n` +
          `  P-number: P followed by 6 digits (e.g., P210012)\n` +
          `  DEN-number: DEN followed by 6 digits (e.g., DEN200043)\n\n` +
          `Or use search_mode=true to search by name, applicant, or product code.`
        );
      }

      if (invalidNumbers.length > 0) {
        context.warn(
          `Skipping invalid numbers: ${invalidNumbers.join(', ')}. ` +
            `Only validating: ${validNumbers.join(', ')}`
        );
      }

      argParts.push(validNumbers.join(' '));
    }

    if (params.project_name) {
      argParts.push(`--project ${params.project_name as string}`);
    }

    const args = argParts.join(' ');

    try {
      const response = await client.execute({
        command: 'validate',
        args,
        user_id: context.user_id,
        session_id: context.session_id,
        channel: context.channel || 'file',
      });

      if (response.warnings && response.warnings.length > 0) {
        context.warn(response.warnings.join('\n'));
      }

      if (!response.success) {
        return (
          `[ERROR] Validation failed.\n` +
          `Error: ${response.error}\n\n` +
          `Make sure the FDA Bridge Server is running and the device numbers ` +
          `are in the correct format.`
        );
      }

      context.updateSession({
        session_id: response.session_id,
        last_command: 'validate',
      });

      return response.result ?? '(No validation results returned)';
    } catch (error) {
      if (error instanceof BridgeClientError) {
        if (error.errorType === 'CONNECTION_REFUSED') {
          return (
            `[CONNECTION ERROR] The FDA Bridge Server is not running.\n\n` +
            `Start it with: python3 bridge/server.py\n` +
            `The server must be running on http://localhost:18790.`
          );
        }
        return `[ERROR] Validation failed: ${error.message}`;
      }
      throw error;
    }
  },
};
