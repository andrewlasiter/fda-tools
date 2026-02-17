/**
 * FDA Analyze Tool
 *
 * Tool for analyzing FDA data from any pipeline stage including
 * extraction results, download metadata, predicate relationships,
 * and device lookups. Adapts to whatever data sources are available.
 *
 * @module tools/fda_analyze
 * @version 1.0.0
 */

import { BridgeClient, BridgeClientError } from '../bridge/client';
import type { Tool, ToolContext } from '../bridge/types';

const client = new BridgeClient();

/**
 * FDA Analyze tool for multi-source data analysis.
 *
 * @example
 * User: "Analyze the data for my cardio-stent project"
 * Tool executes: analyze --project cardio-stent
 *
 * @example
 * User: "Analyze product code DQY"
 * Tool executes: analyze DQY
 */
export const fdaAnalyzeTool: Tool = {
  name: 'fda_analyze',
  description:
    'Analyze FDA data from any pipeline stage -- extraction results, download ' +
    'metadata, predicate relationships, device lookups, safety signals, and ' +
    'competitive intelligence. Adapts analysis to whatever data is available.',

  parameters: {
    target: {
      type: 'string',
      required: true,
      description:
        'Analysis target: a project name, product code, K-number, ' +
        'or file path. The command auto-detects the target type. ' +
        'Examples: "my-project", "DQY", "K240001", "/path/to/data.json".',
    },
    project_name: {
      type: 'string',
      required: false,
      description:
        'Explicit project name (overrides auto-detection from target).',
    },
    analysis_depth: {
      type: 'string',
      required: false,
      description:
        'Analysis depth level. Options: "quick" (summary only), ' +
        '"standard" (default analysis), "deep" (comprehensive with all sources).',
      enum: ['quick', 'standard', 'deep'],
      default: 'standard',
    },
  },

  async execute(
    params: Record<string, unknown>,
    context: ToolContext
  ): Promise<string> {
    const target = params.target as string;
    const argParts: string[] = [];

    // Determine if target is a project name, product code, or K-number
    if (params.project_name) {
      argParts.push(`--project ${params.project_name as string}`);
    }

    argParts.push(target);

    if (params.analysis_depth && params.analysis_depth !== 'standard') {
      argParts.push(`--depth ${params.analysis_depth as string}`);
    }

    const args = argParts.join(' ');

    try {
      // Report progress for potentially long-running analysis
      if (context.progress) {
        context.progress('Gathering data sources...', 10);
      }

      const response = await client.execute({
        command: 'analyze',
        args,
        user_id: context.user_id,
        session_id: context.session_id,
        channel: context.channel || 'file',
      });

      if (context.progress) {
        context.progress('Analysis complete', 100);
      }

      if (response.warnings && response.warnings.length > 0) {
        context.warn(response.warnings.join('\n'));
      }

      if (!response.success) {
        if (response.classification === 'CONFIDENTIAL') {
          return (
            `[SECURITY] Analysis blocked: this request accesses CONFIDENTIAL ` +
            `project data. Channel '${context.channel}' is not permitted.\n\n` +
            `Use file output or a local terminal for confidential analysis.`
          );
        }

        return (
          `[ERROR] Analysis failed.\n` +
          `Target: ${target}\n` +
          `Error: ${response.error}\n\n` +
          `Ensure the target exists. For projects, verify the project ` +
          `directory is at ~/fda-510k-data/projects/<name>/`
        );
      }

      context.updateSession({
        session_id: response.session_id,
        last_command: 'analyze',
        last_analysis_target: target,
      });

      return response.result ?? '(No analysis results returned)';
    } catch (error) {
      if (error instanceof BridgeClientError) {
        if (error.errorType === 'CONNECTION_REFUSED') {
          return (
            `[CONNECTION ERROR] The FDA Bridge Server is not running.\n` +
            `Start it with: python3 bridge/server.py`
          );
        }
        return `[ERROR] Analysis failed: ${error.message}`;
      }
      throw error;
    }
  },
};
