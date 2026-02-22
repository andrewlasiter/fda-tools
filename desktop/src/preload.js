/**
 * FDA-254  [DESK-001] Electron preload script
 * ============================================
 * Runs in the renderer context with Node.js access BEFORE the page loads,
 * but with contextIsolation=true so the renderer cannot access Node directly.
 *
 * Exposes a minimal, allowlisted API surface via `contextBridge` so the
 * Next.js frontend can:
 *  - Call native dialogs (open/save file, message box)
 *  - Read/write app settings (theme, supabase sync, etc.)
 *  - Discover the embedded API base URL
 *
 * Security model
 * --------------
 * Only the listed IPC channel names are forwarded.  Arbitrary IPC channel
 * invocation from the renderer is blocked by this allowlist.
 */

const { contextBridge, ipcRenderer } = require("electron");

// ── Allowlisted IPC invoke channels ──────────────────────────────────────────

const ALLOWED_INVOKE = new Set([
  "get-api-url",
  "get-setting",
  "set-setting",
  "show-open-dialog",
  "show-save-dialog",
  "show-message-box",
]);

// ── Expose to renderer as window.mdrp ────────────────────────────────────────

contextBridge.exposeInMainWorld("mdrp", {
  /**
   * Invoke an IPC channel by name.
   * Rejects with an error if the channel is not allowlisted.
   */
  invoke(channel, ...args) {
    if (!ALLOWED_INVOKE.has(channel)) {
      return Promise.reject(new Error(`IPC channel "${channel}" is not allowed`));
    }
    return ipcRenderer.invoke(channel, ...args);
  },

  /** Convenience: get the embedded API base URL. */
  getApiUrl() {
    return ipcRenderer.invoke("get-api-url");
  },

  /** Convenience: read a persistent setting. */
  getSetting(key) {
    return ipcRenderer.invoke("get-setting", key);
  },

  /** Convenience: write a persistent setting. */
  setSetting(key, value) {
    return ipcRenderer.invoke("set-setting", key, value);
  },

  /** Convenience: show a native open-file dialog. */
  showOpenDialog(options) {
    return ipcRenderer.invoke("show-open-dialog", options);
  },

  /** Convenience: show a native save-file dialog. */
  showSaveDialog(options) {
    return ipcRenderer.invoke("show-save-dialog", options);
  },

  /** Convenience: show a native message box. */
  showMessageBox(options) {
    return ipcRenderer.invoke("show-message-box", options);
  },

  /** True when running inside Electron, false when in browser (SaaS). */
  isElectron: true,
});
