/**
 * FDA Draft Tool
 *
 * Tool for generating regulatory prose drafts for 510(k) submission
 * sections. Handles device descriptions, substantial equivalence
 * discussions, performance summaries, testing rationale, and
 * predicate justification.
 *
 * IMPORTANT: This tool typically accesses CONFIDENTIAL project data.
 * It will be blocked on messaging channels unless the SecurityGateway
 * is in permissive mode or the data classification is lower than expected.
 *
 * @module tools/fda_draft
 * @version 1.0.0
 */

import { BridgeClient, BridgeClientError } from '../bridge/client';
import type { Tool, ToolContext } from '../bridge/types';

const client = new BridgeClient();

/**
 * Valid submission sections that can be drafted.
 */
const VALID_SECTIONS = [
  'device-description',
  'intended-use',
  'se-discussion',
  'performance-summary',
  'testing-rationale',
  'predicate-justification',
  'software-description',
  'biocompatibility',
  'sterilization',
  'shelf-life',
  'electrical-safety',
  'emc',
  'human-factors',
  'reprocessing',
  'labeling',
  'cover-letter',
  'form-3881',
  'truthful-accuracy',
  'combination-product',
] as const;

type SubmissionSection = (typeof VALID_SECTIONS)[number];

/**
 * FDA Draft tool for regulatory prose generation.
 *
 * @example
 * User: "Draft the device description for project my-stent"
 * Tool executes: draft device-description --project my-stent
 *
 * @example
 * User: "Generate the SE discussion section for my project"
 * Tool executes: draft se-discussion --project <from_session>
 */
export const fdaDraftTool: Tool = {
  name: 'fda_draft',
  description:
    'Generate regulatory prose drafts for 510(k) submission sections. ' +
    'Supports device description, SE discussion, performance summary, ' +
    'testing rationale, software, biocompatibility, sterilization, shelf life, ' +
    'human factors, cover letter, and more. ' +
    'NOTE: This command typically accesses CONFIDENTIAL project data ' +
    'and may be blocked on messaging channels.',

  parameters: {
    section: {
      type: 'string',
      required: true,
      description:
        'Submission section to draft. Options: device-description, intended-use, ' +
        'se-discussion, performance-summary, testing-rationale, predicate-justification, ' +
        'software-description, biocompatibility, sterilization, shelf-life, ' +
        'electrical-safety, emc, human-factors, reprocessing, labeling, ' +
        'cover-letter, form-3881, truthful-accuracy, combination-product.',
    },
    project_name: {
      type: 'string',
      required: true,
      description:
        'Project name containing the device profile and data files. ' +
        'The project must exist at ~/fda-510k-data/projects/<name>/.',
    },
    device_description: {
      type: 'string',
      required: false,
      description:
        'Override device description text (used if device_profile.json is incomplete).',
    },
    intended_use: {
      type: 'string',
      required: false,
      description:
        'Override intended use statement (used if device_profile.json is incomplete).',
    },
    output_file: {
      type: 'string',
      required: false,
      description:
        'Output file path for the generated draft. If not specified, ' +
        'output goes to the project drafts directory.',
    },
  },

  async execute(
    params: Record<string, unknown>,
    context: ToolContext
  ): Promise<string> {
    const section = (params.section as string).toLowerCase();
    const projectName = params.project_name as string;

    // Validate section name
    if (!VALID_SECTIONS.includes(section as SubmissionSection)) {
      return (
        `[ERROR] Invalid section: "${section}"\n\n` +
        `Available sections:\n` +
        VALID_SECTIONS.map((s) => `  - ${s}`).join('\n') +
        `\n\nExample: "Draft the device-description section for project my-device"`
      );
    }

    // Build command arguments
    const argParts: string[] = [section];
    argParts.push(`--project ${projectName}`);

    if (params.device_description) {
      const desc = (params.device_description as string).replace(/"/g, '\\"');
      argParts.push(`--device-description "${desc}"`);
    }

    if (params.intended_use) {
      const use = (params.intended_use as string).replace(/"/g, '\\"');
      argParts.push(`--intended-use "${use}"`);
    }

    if (params.output_file) {
      argParts.push(`--output ${params.output_file as string}`);
    }

    const args = argParts.join(' ');

    // Pre-warn about potential security restrictions
    if (context.channel !== 'file') {
      context.warn(
        'Draft commands access CONFIDENTIAL project data. If this request ' +
          `is blocked on '${context.channel}', use file output instead.`
      );
    }

    try {
      if (context.progress) {
        context.progress(`Drafting ${section}...`, 20);
      }

      const response = await client.execute({
        command: 'draft',
        args,
        user_id: context.user_id,
        session_id: context.session_id,
        channel: context.channel || 'file',
      });

      if (context.progress) {
        context.progress('Draft complete', 100);
      }

      if (response.warnings && response.warnings.length > 0) {
        context.warn(response.warnings.join('\n'));
      }

      if (!response.success) {
        // Provide specific guidance for CONFIDENTIAL blocks
        if (response.classification === 'CONFIDENTIAL') {
          return (
            `[SECURITY BLOCK] Draft generation blocked.\n\n` +
            `The '${section}' section requires CONFIDENTIAL project data ` +
            `from project '${projectName}'. Messaging channels ` +
            `(${context.channel}) are not permitted for confidential data.\n\n` +
            `Options:\n` +
            `1. Use this command via a local terminal or file output\n` +
            `2. Use the FDA Tools plugin directly in Claude Code\n` +
            `3. Ask your administrator to configure local LLM (Ollama) ` +
            `for confidential data processing\n\n` +
            `Security classification: ${response.classification}\n` +
            `LLM provider: ${response.llm_provider}`
          );
        }

        return (
          `[ERROR] Draft generation failed.\n` +
          `Section: ${section}\n` +
          `Project: ${projectName}\n` +
          `Error: ${response.error}`
        );
      }

      context.updateSession({
        session_id: response.session_id,
        last_command: 'draft',
        last_section: section,
        last_project: projectName,
      });

      return response.result ?? '(No draft content generated)';
    } catch (error) {
      if (error instanceof BridgeClientError) {
        if (error.errorType === 'CONNECTION_REFUSED') {
          return (
            `[CONNECTION ERROR] The FDA Bridge Server is not running.\n` +
            `Start it with: python3 bridge/server.py`
          );
        }
        return `[ERROR] Draft generation failed: ${error.message}`;
      }
      throw error;
    }
  },
};
