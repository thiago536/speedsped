const { contextBridge, ipcRenderer } = require('electron')

// Expose safe, specific APIs to the renderer process
contextBridge.exposeInMainWorld('electronAPI', {
  // --- Janela Customizada ---
  windowMinimize: () => ipcRenderer.send('window-minimize'),
  windowMaximize: () => ipcRenderer.send('window-maximize'),
  windowClose: () => ipcRenderer.send('window-close'),
  shellOpen: (url) => ipcRenderer.send('shell-open', url),

  // --- Leitura ---
  dirExists: (folderPath) => ipcRenderer.invoke('dir-exists', folderPath),
  readJson: (configPath, fileName) => ipcRenderer.invoke('read-json', { configPath, fileName }),
  readLog: (configPath, fileName, maxLines) => ipcRenderer.invoke('read-log', { configPath, fileName, maxLines }),

  // --- Sistema ---
  openExplorer: (folderPath) => ipcRenderer.invoke('open-explorer', folderPath),
  copyToClipboard: (text) => ipcRenderer.invoke('copy-to-clipboard', text),
  showItemInFolder: (filePath) => ipcRenderer.invoke('show-item-in-folder', filePath),

  // --- Comandos (controle remoto) ---
  writeCommand: (configPath, command) => ipcRenderer.invoke('write-command', { configPath, command }),
  listCommands: (configPath) => ipcRenderer.invoke('list-commands', configPath),

  // --- Download de pastas ---
  copyFolder: (source, destination) => ipcRenderer.invoke('copy-folder', { source, destination }),
  selectFolder: () => ipcRenderer.invoke('select-folder'),
  listSubfolders: (configPath) => ipcRenderer.invoke('list-subfolders', configPath),

  // --- Sistema extra ---
  getSystemInfo: () => ipcRenderer.invoke('get-system-info'),
  saveFile: (content, defaultName, filters) => ipcRenderer.invoke('save-file-dialog', { content, defaultName, filters }),
  showNotification: (title, body) => ipcRenderer.send('show-notification', { title, body }),

  // --- Auto-update ---
  checkForUpdates: () => ipcRenderer.invoke('check-for-updates'),
  installUpdateNow: () => ipcRenderer.invoke('install-update-now'),
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),
  onUpdateStatus: (callback) => ipcRenderer.on('update-status', (event, data) => callback(data)),
})
