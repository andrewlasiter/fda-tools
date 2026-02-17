/**
 * FDA Tools OpenClaw Skill - Entry Point
 *
 * Registers the FDA Regulatory Intelligence skill with OpenClaw,
 * exposing FDA 510(k)/PMA tools via messaging platforms (WhatsApp,
 * Telegram, Slack, Discord) through the Phase 2 HTTP Bridge Server.
 *
 * Architecture:
 *   Messaging Platform --> OpenClaw Gateway --> This Skill --> Bridge Server --> FDA Tools
 *
 * The skill provides both specialized tools (research, validate, analyze, draft)
 * with structured parameters and a generic tool that wraps all 68 FDA commands.
 *
 * Security:
 *   All requests pass through the SecurityGateway which enforces:
 *   - 3-tier data classification (PUBLIC/RESTRICTED/CONFIDENTIAL)
 *   - LLM provider routing based on sensitivity
 *   - Channel whitelist enforcement
 *   - Immutable audit logging
 *
 * @module index
 * @version 1.0.0
 */

import type { Skill } from './bridge/types';
import { BridgeClient, BridgeClientError } from './bridge/client';
import { fdaResearchTool } from './tools/fda_research';
import { fdaValidateTool } from './tools/fda_validate';
import { fdaAnalyzeTool } from './tools/fda_analyze';
import { fdaDraftTool } from './tools/fda_draft';
import { fdaGenericTool } from './tools/fda_generic';

// ============================================================
// Skill Definition
// ============================================================

/**
 * FDA Tools OpenClaw Skill
 *
 * Provides regulatory intelligence tools for FDA medical device
 * submissions via messaging platforms with security enforcement.
 */
export const fdaToolsSkill: Skill = {
  name: 'fda-tools',
  version: '1.0.0',
  description:
    'FDA 510(k)/PMA regulatory intelligence -- predicate research, ' +
    'device validation, safety analysis, submission drafting, and 68 ' +
    'specialized commands for medical device regulatory workflows.',

  tools: [
    fdaResearchTool,
    fdaValidateTool,
    fdaAnalyzeTool,
    fdaDraftTool,
    fdaGenericTool,
  ],

  /**
   * Initialize the skill.
   *
   * Verifies that the FDA Bridge Server is accessible and logs
   * available capabilities. If the bridge is not running, logs
   * a warning but does not prevent skill registration (the bridge
   * may be started later).
   */
  async init(): Promise<void> {
    console.log('[FDA Tools] Initializing skill...');

    const client = new BridgeClient({
      timeout: 5_000, // Short timeout for health check
      retries: 1,     // Single attempt during init
    });

    try {
      const health = await client.health();

      console.log(`[FDA Tools] Bridge server connected (v${health.version})`);
      console.log(`[FDA Tools] Status: ${health.status}`);
      console.log(`[FDA Tools] Commands available: ${health.commands_available}`);
      console.log(`[FDA Tools] Active sessions: ${health.sessions_active}`);

      // Log LLM provider availability
      const providers: string[] = [];
      if (health.llm_providers.ollama?.available) {
        providers.push('ollama (local)');
      }
      if (health.llm_providers.anthropic?.available) {
        providers.push('anthropic (cloud)');
      }
      if (health.llm_providers.openai?.available) {
        providers.push('openai (cloud)');
      }

      if (providers.length > 0) {
        console.log(`[FDA Tools] LLM providers: ${providers.join(', ')}`);
      } else {
        console.warn(
          '[FDA Tools] WARNING: No LLM providers detected. ' +
            'Some commands may have limited functionality.'
        );
      }

      // Log security status
      if (health.security_config_hash) {
        console.log(
          `[FDA Tools] Security config hash: ${health.security_config_hash.substring(0, 16)}...`
        );
      } else {
        console.warn(
          '[FDA Tools] WARNING: No security config detected. ' +
            'Running in permissive mode (no security enforcement). ' +
            'Configure ~/.claude/fda-tools.security.toml for production use.'
        );
      }

      console.log('[FDA Tools] Skill initialized successfully.');
    } catch (error) {
      if (error instanceof BridgeClientError) {
        if (error.errorType === 'CONNECTION_REFUSED') {
          console.warn(
            '[FDA Tools] WARNING: Bridge server not running at http://localhost:18790.\n' +
              '[FDA Tools] Tools will not work until the bridge is started.\n' +
              '[FDA Tools] Start with: cd fda-predicate-assistant && python3 bridge/server.py'
          );
        } else {
          console.warn(
            `[FDA Tools] WARNING: Bridge health check failed: ${error.message}`
          );
        }
      } else {
        console.error(
          '[FDA Tools] ERROR: Unexpected initialization failure:',
          error
        );
      }

      // Do not throw -- skill should still register even if bridge is down.
      // Commands will return helpful error messages when invoked.
      console.log(
        '[FDA Tools] Skill registered (bridge connection pending).'
      );
    }
  },

  /**
   * Clean up skill resources.
   *
   * Currently a no-op since the BridgeClient is stateless (HTTP).
   * Sessions are managed server-side by the bridge.
   */
  async cleanup(): Promise<void> {
    console.log('[FDA Tools] Skill cleaned up.');
  },
};

// Default export for OpenClaw skill loader
export default fdaToolsSkill;
