/**
 * FDA-257  [DESK-004] Offline-first sync (local-first, Supabase when online)
 * ===========================================================================
 * Manages the sync lifecycle between the local PostgreSQL instance (embedded)
 * and the Supabase cloud backend.
 *
 * Sync strategy
 * -------------
 * 1. **Local-first** — all reads and writes go to the local DB first.
 *    The app functions fully offline with zero degradation.
 * 2. **Opportunistic sync** — when the device comes online, a background
 *    worker pushes local changes to Supabase and pulls remote changes.
 * 3. **Conflict resolution** — last-write-wins (LWW) on `updated_at`
 *    timestamps.  Future: CRDTs for collaborative editing.
 * 4. **Never-sync data** — documents marked CONFIDENTIAL are excluded from
 *    cloud sync even when Supabase sync is enabled.
 *
 * This module runs in the Electron main process via IPC from the renderer.
 */

const electronLog = require("electron-log");

// ── Sync state ────────────────────────────────────────────────────────────────

const SyncStatus = {
  IDLE:    "IDLE",
  SYNCING: "SYNCING",
  ERROR:   "ERROR",
  OFFLINE: "OFFLINE",
};

let syncStatus     = SyncStatus.IDLE;
let syncTimer      = null;
let lastSyncAt     = null;
let syncErrors     = [];
const SYNC_INTERVAL_MS = 5 * 60 * 1000;  // 5 minutes

// ── Online detection ──────────────────────────────────────────────────────────

function isOnline() {
  // In production, check actual connectivity.
  // Node's `dns.lookup` is the most reliable cross-platform method.
  const dns = require("dns");
  return new Promise((resolve) => {
    dns.lookup("supabase.co", (err) => resolve(!err));
  });
}

// ── Sync execution ────────────────────────────────────────────────────────────

/**
 * Push local changes to Supabase, then pull remote changes.
 * No-op if:
 *  - supabaseSync setting is false
 *  - Device is offline
 *  - Another sync is already in progress
 */
async function runSync(store, mainWindow) {
  if (syncStatus === SyncStatus.SYNCING) {
    electronLog.info("[sync] Sync already in progress — skipping");
    return;
  }

  const supabaseEnabled = store.get("supabaseSync", false);
  if (!supabaseEnabled) {
    electronLog.info("[sync] Supabase sync disabled — skipping");
    return;
  }

  const online = await isOnline();
  if (!online) {
    syncStatus = SyncStatus.OFFLINE;
    notifyRenderer(mainWindow, { status: SyncStatus.OFFLINE });
    return;
  }

  syncStatus = SyncStatus.SYNCING;
  notifyRenderer(mainWindow, { status: SyncStatus.SYNCING });

  try {
    electronLog.info("[sync] Starting sync with Supabase...");

    // Phase 1: push local pending changes
    const pushed = await pushLocalChanges(store);
    electronLog.info(`[sync] Pushed ${pushed} records to Supabase`);

    // Phase 2: pull remote changes since last sync
    const pulled = await pullRemoteChanges(store);
    electronLog.info(`[sync] Pulled ${pulled} records from Supabase`);

    lastSyncAt = new Date().toISOString();
    store.set("lastSyncAt", lastSyncAt);
    syncErrors = [];
    syncStatus = SyncStatus.IDLE;
    notifyRenderer(mainWindow, { status: SyncStatus.IDLE, lastSyncAt, pushed, pulled });

  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    electronLog.error("[sync] Sync failed:", msg);
    syncErrors.push({ timestamp: new Date().toISOString(), error: msg });
    syncStatus = SyncStatus.ERROR;
    notifyRenderer(mainWindow, { status: SyncStatus.ERROR, error: msg });
  }
}

/**
 * Push all locally-modified records with sync_status='pending' to Supabase.
 * Returns the count of records pushed.
 *
 * Production implementation: query local PostgreSQL for pending records,
 * batch-upsert to Supabase via REST API, mark as synced on success.
 */
async function pushLocalChanges(_store) {
  // Stub: in production this calls the FastAPI /sync/push endpoint
  // which handles the local→Supabase upsert logic server-side.
  electronLog.debug("[sync] pushLocalChanges() — stub, no-op");
  return 0;
}

/**
 * Pull changes from Supabase that occurred after `lastSyncAt`.
 * Returns the count of records pulled.
 *
 * Production implementation: call Supabase REST API with
 * `updated_at > lastSyncAt`, apply LWW resolution, upsert into local DB.
 */
async function pullRemoteChanges(_store) {
  // Stub: in production this calls the FastAPI /sync/pull endpoint
  electronLog.debug("[sync] pullRemoteChanges() — stub, no-op");
  return 0;
}

// ── Renderer notification ─────────────────────────────────────────────────────

function notifyRenderer(mainWindow, payload) {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send("sync-status-changed", payload);
  }
}

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Start periodic sync timer.  Called from main.js after window creation.
 */
function startSyncTimer(store, mainWindow) {
  if (syncTimer) clearInterval(syncTimer);
  syncTimer = setInterval(() => runSync(store, mainWindow), SYNC_INTERVAL_MS);
  electronLog.info(`[sync] Periodic sync started (interval: ${SYNC_INTERVAL_MS / 1000}s)`);
}

/**
 * Stop periodic sync timer.  Called on app quit.
 */
function stopSyncTimer() {
  if (syncTimer) {
    clearInterval(syncTimer);
    syncTimer = null;
    electronLog.info("[sync] Periodic sync stopped");
  }
}

/**
 * Trigger an immediate sync (e.g., from IPC handler).
 */
function triggerSync(store, mainWindow) {
  return runSync(store, mainWindow);
}

/**
 * Return current sync state for IPC status queries.
 */
function getSyncState(store) {
  return {
    status:          syncStatus,
    lastSyncAt:      store.get("lastSyncAt", null),
    supabaseEnabled: store.get("supabaseSync", false),
    errors:          syncErrors.slice(-5),   // last 5 errors
  };
}

module.exports = {
  startSyncTimer,
  stopSyncTimer,
  triggerSync,
  getSyncState,
  SyncStatus,
};
