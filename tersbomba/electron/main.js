// TERS BOMBA — masaüstü (EXE / Steam) penceresi
const { app, BrowserWindow, session } = require('electron');
const path = require('path');

function createWindow() {
  const win = new BrowserWindow({
    width: 1280, height: 720, fullscreen: true, backgroundColor: '#12142a',
    title: 'Ters Bomba', autoHideMenuBar: true, icon: path.join(__dirname, 'icon.png'),
    webPreferences: { contextIsolation: true, nodeIntegration: false, backgroundThrottling: false },
  });
  win.setMenu(null);
  win.loadFile(path.join(__dirname, '..', 'dist-web', 'index.html'));
  // F11: tam ekran aç/kapat
  win.webContents.on('before-input-event', (e, input) => {
    if (input.type === 'keyDown' && input.key === 'F11') { win.setFullScreen(!win.isFullScreen()); e.preventDefault(); }
  });
  // oyun dışı bağlantılar pencerenin içinde açılmasın
  win.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
}

app.whenReady().then(() => {
  // mikrofon (ters ses!), fare kilidi ve tam ekran izinleri sorulmadan verilir
  const OK = ['media', 'pointerLock', 'fullscreen', 'clipboard-sanitized-write'];
  session.defaultSession.setPermissionRequestHandler((wc, permission, cb) => cb(OK.includes(permission)));
  createWindow();
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
});
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
