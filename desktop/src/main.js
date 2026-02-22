/**
 * FDA-254  [DESK-001] Electron main process
 * ==========================================
 * Entry point for the MDRP Desktop Edition.
 *
 * Architecture
 * ------------
 * 1. Main process starts the embedded FastAPI server as a child process
 *    (see `startApiServer`).  The server binds to localhost:18080 by default.
 * 2. A BrowserWindow loads the Next.js app:
 *    - In development: proxies to `next dev` on port 3000
 *    - In production:  loads from the bundled `.next` static export
 * 3. Auto-update (electron-updater) checks GitHub Releases on startup.
 * 4. All data stays local by default — no telemetry, no cloud sync unless
 *    the user explicitly enables Supabase sync in Settings.
 *
 * Security hardening
 * ------------------
 * - contextIsolation: true (default since Electron 12)
 * - nodeIntegration:  false  (renderer cannot access Node.js APIs directly)
 * - sandbox:          true   (renderer sandboxed like a browser tab)
 * - webSecurity:      true   (CSP enforced)
 * - All IPC exposed via preload.js (allowlisted channels only)
 */

const {
  app, BrowserWindow, ipcMain, shell, dialog, Menu,
} = require("electron");
const path         = require("path");
const { spawn }    = require("child_process");
const electronLog  = require("electron-log");
const Store        = require("electron-store");
const { autoUpdater } = require("electron-updater");

// ── Constants ─────────────────────────────────────────────────────────────────

const IS_DEV       = !app.isPackaged;
const API_PORT     = 18080;
const DEV_WEB_PORT = 3000;

const WEB_URL  = IS_DEV
  ? `http://localhost:${DEV_WEB_PORT}`
  : `file://${path.join(process.resourcesPath, "web", ".next", "server", "app", "index.html")}`;

// ── Persistent settings store ─────────────────────────────────────────────────

const store = new Store({
  defaults: {
    windowBounds:  { width: 1440, height: 900 },
    supabaseSync:  false,
    apiPort:       API_PORT,
    theme:         "system",
  },
});

// ── API server child process ──────────────────────────────────────────────────

let apiProcess = null;

/**
 * Start the embedded FastAPI server.
 * In development: assumes `uvicorn` is on PATH.
 * In production: uses the bundled Python interpreter in `resources/api/`.
 */
function startApiServer() {
  const pythonBin = IS_DEV
    ? "python3"
    : path.join(process.resourcesPath, "api", "bin", "python3");

  const uvicornArgs = [
    "-m", "uvicorn",
    "fda_tools.bridge.main:app",
    "--host", "127.0.0.1",
    "--port", String(store.get("apiPort", API_PORT)),
    "--log-level", "warning",
  ];

  electronLog.info(`Starting API server: ${pythonBin} ${uvicornArgs.join(" ")}`);

  apiProcess = spawn(pythonBin, uvicornArgs, {
    cwd:   IS_DEV ? path.join(__dirname, "..", "..", "plugins") : path.join(process.resourcesPath, "api"),
    stdio: ["ignore", "pipe", "pipe"],
    env:   {
      ...process.env,
      PYTHONPATH: IS_DEV
        ? path.join(__dirname, "..", "..", "plugins")
        : path.join(process.resourcesPath, "api"),
    },
  });

  apiProcess.stdout.on("data", (d) => electronLog.info("[api]", d.toString().trim()));
  apiProcess.stderr.on("data", (d) => electronLog.warn("[api]", d.toString().trim()));
  apiProcess.on("error",  (e) => electronLog.error("[api] spawn error:", e));
  apiProcess.on("exit",   (code) => {
    electronLog.warn(`[api] exited with code ${code}`);
    apiProcess = null;
  });
}

function stopApiServer() {
  if (apiProcess) {
    electronLog.info("Stopping embedded API server...");
    apiProcess.kill("SIGTERM");
    apiProcess = null;
  }
}

// ── Window management ─────────────────────────────────────────────────────────

let mainWindow = null;

function createWindow() {
  const { width, height } = store.get("windowBounds");

  mainWindow = new BrowserWindow({
    width,
    height,
    minWidth:  1024,
    minHeight: 700,
    show:      false,     // shown after ready-to-show to avoid white flash
    title:     "MDRP Desktop",
    icon:      path.join(__dirname, "..", "assets", "icon.png"),
    webPreferences: {
      preload:          path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration:  false,
      sandbox:          true,
      webSecurity:      true,
    },
  });

  // Save window size on resize
  mainWindow.on("resize", () => {
    store.set("windowBounds", mainWindow.getBounds());
  });

  mainWindow.on("ready-to-show", () => {
    mainWindow.show();
    if (IS_DEV) mainWindow.webContents.openDevTools({ mode: "detach" });
  });

  mainWindow.on("closed", () => { mainWindow = null; });

  // Open external links in default browser, not inside Electron
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  mainWindow.loadURL(WEB_URL);
}

// ── Application menu ──────────────────────────────────────────────────────────

function buildMenu() {
  const template = [
    {
      label: "File",
      submenu: [
        { role: "quit" },
      ],
    },
    {
      label: "Edit",
      submenu: [
        { role: "undo" }, { role: "redo" }, { type: "separator" },
        { role: "cut"  }, { role: "copy" }, { role: "paste" },
      ],
    },
    {
      label: "View",
      submenu: [
        { role: "reload" },
        { role: "toggleDevTools" },
        { type: "separator" },
        { role: "resetZoom" }, { role: "zoomIn" }, { role: "zoomOut" },
        { type: "separator" },
        { role: "togglefullscreen" },
      ],
    },
    {
      label: "Help",
      submenu: [
        {
          label: "MDRP Documentation",
          click: () => shell.openExternal("https://github.com/andrewlasiter/fda-tools#readme"),
        },
        { type: "separator" },
        {
          label: "Check for Updates",
          click: () => autoUpdater.checkForUpdatesAndNotify(),
        },
      ],
    },
  ];

  if (process.platform === "darwin") {
    template.unshift({
      label: app.name,
      submenu: [
        { role: "about" }, { type: "separator" }, { role: "quit" },
      ],
    });
  }

  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

// ── IPC handlers ──────────────────────────────────────────────────────────────

// Expose API base URL to renderer
ipcMain.handle("get-api-url", () => `http://localhost:${store.get("apiPort", API_PORT)}`);

// Settings read/write
ipcMain.handle("get-setting",    (_e, key)        => store.get(key));
ipcMain.handle("set-setting",    (_e, key, value) => { store.set(key, value); });

// Native dialogs
ipcMain.handle("show-open-dialog",  (_e, opts) => dialog.showOpenDialog(mainWindow, opts));
ipcMain.handle("show-save-dialog",  (_e, opts) => dialog.showSaveDialog(mainWindow, opts));
ipcMain.handle("show-message-box",  (_e, opts) => dialog.showMessageBox(mainWindow, opts));

// ── Auto-updater ──────────────────────────────────────────────────────────────

function initAutoUpdater() {
  autoUpdater.logger = electronLog;
  autoUpdater.checkForUpdatesAndNotify();

  autoUpdater.on("update-available", () => {
    electronLog.info("Update available — downloading...");
  });

  autoUpdater.on("update-downloaded", () => {
    dialog.showMessageBox(mainWindow, {
      type:    "info",
      title:   "Update Ready",
      message: "A new version of MDRP Desktop is ready to install. Restart now?",
      buttons: ["Restart", "Later"],
    }).then(({ response }) => {
      if (response === 0) autoUpdater.quitAndInstall();
    });
  });
}

// ── App lifecycle ─────────────────────────────────────────────────────────────

app.whenReady().then(() => {
  electronLog.info("MDRP Desktop starting...", { version: app.getVersion(), isDev: IS_DEV });

  startApiServer();
  buildMenu();
  createWindow();

  if (!IS_DEV) initAutoUpdater();

  app.on("activate", () => {
    // macOS: re-create window when dock icon clicked with no windows open
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  stopApiServer();
  if (process.platform !== "darwin") app.quit();
});

app.on("will-quit", stopApiServer);

// Prevent navigation to external URLs in the main window
app.on("web-contents-created", (_e, contents) => {
  contents.on("will-navigate", (event, url) => {
    if (!url.startsWith("http://localhost") && !url.startsWith("file://")) {
      event.preventDefault();
      shell.openExternal(url);
    }
  });
});
