const { app, BrowserWindow, ipcMain, shell, clipboard, dialog, Tray, Menu } = require('electron')
const { autoUpdater } = require('electron-updater')
// electron-log v5: o processo main usa 'electron-log/main'; fallback p/ raiz se necessário
let log
try {
  log = require('electron-log/main')
  if (typeof log.initialize === 'function') log.initialize()
} catch (e) {
  log = require('electron-log')
}
const path = require('path')
const fs = require('fs')
const crypto = require('crypto')

let mainWindow
let splashWindow = null
let tray = null
let isQuitting = false

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 1024,
    minHeight: 600,
    show: false, // Hidden until ready
    title: 'SPEEDSPED - SiteGenTech',
    frame: false, // Frameless window
    titleBarStyle: 'hidden',
    icon: fs.existsSync(path.join(__dirname, 'assets/icons/icon.ico')) 
      ? path.join(__dirname, 'assets/icons/icon.ico') 
      : path.join(__dirname, 'icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  })

  mainWindow.setMenuBarVisibility(false)
  mainWindow.loadFile('index.html')

  // Wait for the window to be ready, then destroy the splash and show main window
  mainWindow.once('ready-to-show', () => {
    setTimeout(() => {
      if (splashWindow) {
        splashWindow.destroy()
        splashWindow = null
      }
      mainWindow.show()
    }, 2500) // Perfect match with the 2.5s progress bar animation!
  })

  // Prevent closing entirely, hide instead
  mainWindow.on('close', (event) => {
    if (!isQuitting) {
      event.preventDefault()
      mainWindow.hide()
      return false
    }
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

// Window control handlers
ipcMain.on('window-minimize', () => {
  if (mainWindow) mainWindow.minimize()
})
ipcMain.on('window-maximize', () => {
  if (mainWindow) {
    if (mainWindow.isMaximized()) mainWindow.unmaximize()
    else mainWindow.maximize()
  }
})
ipcMain.on('window-close', () => {
  if (mainWindow) mainWindow.close() // Triggers 'close' event above
})

ipcMain.on('shell-open', (event, url) => {
  shell.openExternal(url)
})

// ----------------------------------------------------
// IPC Handlers - Secure File Operations & System Integrations
// ----------------------------------------------------

// Safe Path resolver helper
function resolveSafePath(basePath, relativeFile) {
  if (!basePath) return null
  const cleanBase = path.normalize(basePath)
  const resolved = path.normalize(path.join(cleanBase, relativeFile))
  // Basic path traversal protection
  if (!resolved.startsWith(cleanBase)) {
    throw new Error('Acesso a caminho não autorizado')
  }
  return resolved
}

// Handler to check if path exists
ipcMain.handle('dir-exists', async (event, folderPath) => {
  try {
    const stat = await fs.promises.stat(folderPath)
    return stat.isDirectory()
  } catch (error) {
    return false
  }
})

// Handler to read JSON files safely
ipcMain.handle('read-json', async (event, { configPath, fileName }) => {
  try {
    const fullPath = resolveSafePath(configPath, fileName)
    if (!fullPath) {
      return { success: false, error: 'Acesso a caminho não autorizado' }
    }
    const rawData = await fs.promises.readFile(fullPath, 'utf8')
    const parsedData = JSON.parse(rawData)
    return { success: true, data: parsedData }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

// Handler to read the last N lines of a log file
ipcMain.handle('read-log', async (event, { configPath, fileName, maxLines = 200 }) => {
  try {
    const fullPath = resolveSafePath(configPath, fileName)
    if (!fullPath) {
      return { success: false, error: 'Acesso a caminho não autorizado' }
    }

    // Read file contents asynchronously
    const rawData = await fs.promises.readFile(fullPath, 'utf8')
    const lines = rawData.split(/\r?\n/)
    
    // Slice last N lines
    const lastLines = lines.slice(-maxLines)
    return { success: true, lines: lastLines }
  } catch (error) {
    return { success: false, error: error.message }
  }
})


// Handler to open directory in Explorer
ipcMain.handle('open-explorer', async (event, folderPath) => {
  try {
    if (fs.existsSync(folderPath)) {
      await shell.openPath(folderPath)
      return { success: true }
    } else {
      return { success: false, error: 'Caminho não existe no sistema.' }
    }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

// Handler to copy text to clipboard
ipcMain.handle('copy-to-clipboard', async (event, text) => {
  try {
    clipboard.writeText(text)
    return { success: true }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

// Handler to highlight a file in Explorer
ipcMain.handle('show-item-in-folder', async (event, filePath) => {
  try {
    if (fs.existsSync(filePath)) {
      shell.showItemInFolder(filePath)
      return { success: true }
    } else {
      // Try to open the parent folder if the file itself is not there yet
      const parentDir = path.dirname(filePath)
      if (fs.existsSync(parentDir)) {
        await shell.openPath(parentDir)
        return { success: true, warning: 'Arquivo não encontrado, mas pasta aberta.' }
      }
      return { success: false, error: 'Caminho do arquivo ou pasta pai não encontrado.' }
    }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

// Handler to show native OS notifications
ipcMain.on('show-notification', (event, { title, body }) => {
  try {
    const { Notification } = require('electron')
    if (Notification.isSupported()) {
      new Notification({
        title: title,
        body: body,
        icon: path.join(__dirname, 'icon.png')
      }).show()
    }
  } catch (error) {
    console.error('Falha ao mostrar notificação nativa:', error)
  }
})

// ----------------------------------------------------
// IPC Handlers - Command System (write commands for Python daemon)
// ----------------------------------------------------

// Write a command JSON file to configPath/comandos/
ipcMain.handle('write-command', async (event, { configPath, command }) => {
  try {
    const comandosDir = path.join(configPath, 'comandos')
    if (!fs.existsSync(comandosDir)) {
      fs.mkdirSync(comandosDir, { recursive: true })
    }

    // Generate unique ID
    const cmdId = crypto.randomUUID()
    const cmdData = {
      id: cmdId,
      acao: command.acao,
      params: command.params || {},
      timestamp: new Date().toISOString(),
      status: 'pendente',
      origem: require('os').hostname(),
    }

    const filePath = path.join(comandosDir, `${cmdId}.json`)
    const tmpPath = filePath + '.tmp'
    fs.writeFileSync(tmpPath, JSON.stringify(cmdData, null, 2), 'utf8')
    fs.renameSync(tmpPath, filePath)

    return { success: true, id: cmdId }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

// List all command files with their current status
ipcMain.handle('list-commands', async (event, configPath) => {
  try {
    const comandosDir = path.join(configPath, 'comandos')
    if (!fs.existsSync(comandosDir)) {
      return { success: true, commands: [] }
    }

    const files = fs.readdirSync(comandosDir)
    const commands = []

    for (const fname of files) {
      if (!fname.endsWith('.json')) continue
      const fpath = path.join(comandosDir, fname)
      try {
        const raw = fs.readFileSync(fpath, 'utf8')
        const cmd = JSON.parse(raw)
        commands.push(cmd)
      } catch (e) {
        // skip corrupted files
      }
    }

    // Sort by timestamp descending (newest first)
    commands.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))

    return { success: true, commands }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

// ----------------------------------------------------
// IPC Handlers - File Downloads & Folder Operations
// ----------------------------------------------------

// Open native folder picker dialog
ipcMain.handle('select-folder', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory'],
    title: 'Escolha onde salvar os arquivos'
  })
  if (result.canceled || result.filePaths.length === 0) {
    return { success: false, canceled: true }
  }
  return { success: true, path: result.filePaths[0] }
})

// Copy a folder recursively
ipcMain.handle('copy-folder', async (event, { source, destination }) => {
  try {
    if (!fs.existsSync(source)) {
      return { success: false, error: 'Pasta de origem não encontrada.' }
    }

    // Create destination if needed
    if (fs.existsSync(destination)) {
      fs.rmSync(destination, { recursive: true, force: true })
    }

    // Recursive copy
    fs.cpSync(source, destination, { recursive: true })
    return { success: true }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

// List subfolders in configPath (for SPED file browser)
ipcMain.handle('list-subfolders', async (event, configPath) => {
  try {
    try {
      await fs.promises.access(configPath)
    } catch {
      return { success: true, folders: [] }
    }

    const entries = await fs.promises.readdir(configPath, { withFileTypes: true })
    const folders = []

    for (const entry of entries) {
      if (!entry.isDirectory()) continue
      if (entry.name === 'erros' || entry.name === 'comandos') continue

      const folderPath = path.join(configPath, entry.name)
      const subEntries = await fs.promises.readdir(folderPath, { withFileTypes: true })
      
      const files = []
      for (const subEntry of subEntries) {
        if (!subEntry.isFile()) continue
        const fp = path.join(folderPath, subEntry.name)
        const stat = await fs.promises.stat(fp)
        files.push({
          name: subEntry.name,
          size: stat.size,
          mtime: stat.mtime.toISOString(),
          path: fp
        })
      }

      const totalSize = files.reduce((sum, f) => sum + f.size, 0)

      folders.push({
        name: entry.name,
        path: folderPath,
        files,
        totalSize,
        fileCount: files.length,
      })
    }

    folders.sort((a, b) => a.name.localeCompare(b.name))
    return { success: true, folders }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

// ----------------------------------------------------
// IPC Handlers - System Info & File Save
// ----------------------------------------------------

// Get system info (disk space, IP, hostname)
ipcMain.handle('get-system-info', async () => {
  try {
    const os = require('os')

    // Local IP
    const nets = os.networkInterfaces()
    let localIp = 'N/A'
    for (const name of Object.keys(nets)) {
      for (const net of nets[name]) {
        if (net.family === 'IPv4' && !net.internal) {
          localIp = net.address
          break
        }
      }
      if (localIp !== 'N/A') break
    }

    // Disk space (C:)
    let diskFree = 0, diskTotal = 0
    try {
      const { execSync } = require('child_process')
      const output = execSync('wmic logicaldisk where "DeviceID=\'C:\'" get FreeSpace,Size /format:csv', { encoding: 'utf8', timeout: 5000 })
      const lines = output.trim().split('\n').filter(l => l.trim() && l.includes(','))
      if (lines.length > 0) {
        const parts = lines[lines.length - 1].split(',')
        if (parts.length >= 3) {
          diskFree = parseInt(parts[1]) || 0
          diskTotal = parseInt(parts[2]) || 0
        }
      }
    } catch (e) { /* ignore disk errors */ }

    return {
      success: true,
      ip: localIp,
      hostname: os.hostname(),
      diskFreeGB: (diskFree / (1024 ** 3)).toFixed(1),
      diskTotalGB: (diskTotal / (1024 ** 3)).toFixed(1),
      diskUsedPercent: diskTotal > 0 ? ((1 - diskFree / diskTotal) * 100).toFixed(0) : '0',
    }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

// Save file with native dialog
ipcMain.handle('save-file-dialog', async (event, { content, defaultName, filters }) => {
  try {
    const result = await dialog.showSaveDialog({
      defaultPath: defaultName,
      filters: filters || [{ name: 'All Files', extensions: ['*'] }]
    })
    if (result.canceled) return { success: false, canceled: true }
    fs.writeFileSync(result.filePath, content, 'utf8')
    return { success: true, path: result.filePath }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

// ----------------------------------------------------
// IPC Handler - Enviar arquivos SPED via Outlook
// ----------------------------------------------------

// Codifica texto como encoded-word RFC 2047 quando tem caractere fora do ASCII
function mimeEncodeHeader(text) {
  if (/^[\x20-\x7e]*$/.test(text)) return text
  return `=?UTF-8?B?${Buffer.from(text, 'utf8').toString('base64')}?=`
}

// Abre o seletor de arquivos em C:\ACS_Exporta, monta um rascunho .eml
// (X-Unsent: 1) com os anexos e abre no cliente de e-mail padrão.
// O Outlook "Nova Versão" (olk.exe) não expõe COM/MAPI, então o .eml de
// rascunho é a única integração que preenche destinatário+assunto+anexos.
ipcMain.handle('send-outlook-email', async (event, { basePath, recipient }) => {
  try {
    const startDir = basePath && fs.existsSync(basePath) ? basePath : 'C:\\ACS_Exporta'
    const result = await dialog.showOpenDialog(mainWindow, {
      title: 'Selecione os arquivos SPED para enviar',
      defaultPath: startDir,
      properties: ['openFile', 'multiSelections'],
      filters: [
        { name: 'Arquivos SPED (*.txt)', extensions: ['txt'] },
        { name: 'Todos os arquivos', extensions: ['*'] },
      ],
    })
    if (result.canceled || result.filePaths.length === 0) {
      return { success: false, canceled: true }
    }

    const files = result.filePaths
    const folderName = path.basename(path.dirname(files[0]))
    const subject = `SPED | ${folderName}`

    // Monta o .eml (MIME multipart/mixed) com os anexos em base64
    const boundary = '----=_SPED_' + crypto.randomUUID().replace(/-/g, '')
    const lines = [
      'X-Unsent: 1',
      `To: ${recipient}`,
      `Subject: ${mimeEncodeHeader(subject)}`,
      'MIME-Version: 1.0',
      `Content-Type: multipart/mixed; boundary="${boundary}"`,
      '',
      `--${boundary}`,
      'Content-Type: text/plain; charset=utf-8',
      'Content-Transfer-Encoding: 7bit',
      '',
      '',
    ]
    for (const fp of files) {
      const name = path.basename(fp)
      const data = await fs.promises.readFile(fp)
      const b64 = data.toString('base64').replace(/(.{76})/g, '$1\r\n')
      lines.push(
        `--${boundary}`,
        `Content-Type: application/octet-stream; name="${mimeEncodeHeader(name)}"`,
        'Content-Transfer-Encoding: base64',
        `Content-Disposition: attachment; filename="${mimeEncodeHeader(name)}"`,
        '',
        b64,
        ''
      )
    }
    lines.push(`--${boundary}--`, '')

    const emlDir = path.join(app.getPath('temp'), 'speedsped-email')
    await fs.promises.mkdir(emlDir, { recursive: true })
    const emlPath = path.join(emlDir, `${subject.replace(/[\\/:*?"<>|]/g, '_')}_${Date.now()}.eml`)
    await fs.promises.writeFile(emlPath, lines.join('\r\n'))

    const openError = await shell.openPath(emlPath)
    if (openError) {
      return { success: false, error: `Não foi possível abrir o Outlook: ${openError}. Verifique se o Outlook está instalado e definido como cliente de e-mail padrão.` }
    }
    return { success: true, subject, fileCount: files.length }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

// ----------------------------------------------------
// App Lifecycle
// ----------------------------------------------------

app.whenReady().then(() => {
  // Setup Splash Screen first
  try {
    splashWindow = new BrowserWindow({
      width: 500,
      height: 300,
      transparent: true,
      frame: false,
      alwaysOnTop: true,
      icon: fs.existsSync(path.join(__dirname, 'assets/icons/icon.ico')) 
        ? path.join(__dirname, 'assets/icons/icon.ico') 
        : path.join(__dirname, 'icon.png'),
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true
      }
    })
    splashWindow.loadFile('splash.html')
  } catch (err) {
    console.error('Failed to create splash screen:', err)
  }

  // Create main window (hidden by default)
  createWindow()

  // Setup System Tray
  try {
    const trayIconPath = fs.existsSync(path.join(__dirname, 'assets/icons/icon.png')) 
      ? path.join(__dirname, 'assets/icons/icon.png') 
      : path.join(__dirname, 'icon.png')
    tray = new Tray(trayIconPath)
    
    const contextMenu = Menu.buildFromTemplate([
      { label: 'SPEEDSPED - SiteGenTech', enabled: false },
      { type: 'separator' },
      { label: 'Mostrar/Ocultar', click: () => {
          if (mainWindow.isVisible()) {
            mainWindow.hide()
          } else {
            mainWindow.show()
            mainWindow.focus()
          }
        }
      },
      { label: 'Reiniciar', click: () => {
          app.relaunch()
          app.exit()
        }
      },
      { label: 'Sair', click: () => {
          isQuitting = true
          app.quit()
        }
      }
    ])
    
    tray.setToolTip('SPEEDSPED - SiteGenTech')
    tray.setContextMenu(contextMenu)
    
    tray.on('double-click', () => {
      if (mainWindow) {
        mainWindow.show()
        mainWindow.focus()
      }
    })
    
    // Check if it's the first time running to show balloon
    const configDir = path.join(app.getPath('userData'), 'speedsped-config')
    if (!fs.existsSync(configDir)) fs.mkdirSync(configDir, { recursive: true })
    const balloonFlag = path.join(configDir, 'tray-notified.txt')
    if (!fs.existsSync(balloonFlag)) {
      tray.displayBalloon({
        title: 'SPEEDSPED - SiteGenTech',
        content: 'A aplicação continuará rodando em segundo plano aqui.',
        iconType: 'info'
      })
      fs.writeFileSync(balloonFlag, 'true')
    }
    
  } catch (err) {
    console.error('Tray not created', err)
  }

  // Auto-update via repositório PÚBLICO de releases (sem token).
  // O feed vem do app-update.yml gerado pelo electron-builder (publish config).
  autoUpdater.logger = log
  try { if (log.transports && log.transports.file) log.transports.file.level = 'info' } catch (e) {}
  autoUpdater.autoDownload = true
  log.info(`SPEEDSPED iniciado — versão ${app.getVersion()}`)

  // Repassa cada evento para a tela de Configurações (status visível)
  function sendUpdateStatus(status, info) {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('update-status', { status, info: info || null })
    }
  }

  autoUpdater.on('checking-for-update', () => { log.info('Checando atualização...'); sendUpdateStatus('checking') })
  autoUpdater.on('update-available', (i) => { log.info('Atualização disponível:', i.version); sendUpdateStatus('available', { version: i.version }) })
  autoUpdater.on('update-not-available', (i) => { log.info('Nenhuma atualização.'); sendUpdateStatus('not-available', { version: i && i.version }) })
  autoUpdater.on('download-progress', (p) => { sendUpdateStatus('downloading', { percent: Math.round(p.percent) }) })
  autoUpdater.on('error', (err) => { log.error('Erro no auto-update:', err == null ? 'desconhecido' : (err.message || err)); sendUpdateStatus('error', { message: err && err.message }) })

  autoUpdater.on('update-downloaded', (i) => {
    log.info('Atualização baixada:', i.version)
    sendUpdateStatus('downloaded', { version: i.version })
    dialog.showMessageBox(mainWindow, {
      type: 'info',
      title: 'Atualização pronta — SPEEDSPED',
      message: `A versão ${i.version} foi baixada.\nO app será reiniciado para instalar.`,
      buttons: ['Reiniciar agora', 'Depois']
    }).then(({ response }) => {
      if (response === 0) { isQuitting = true; autoUpdater.quitAndInstall() }
    })
  })

  // Checagem automática na abertura
  autoUpdater.checkForUpdatesAndNotify().catch((e) => log.error('checkForUpdatesAndNotify falhou:', e && e.message))

  // Verificação manual (botão "Verificar agora" em Configurações)
  ipcMain.handle('check-for-updates', async () => {
    try {
      const r = await autoUpdater.checkForUpdates()
      const latest = r && r.updateInfo ? r.updateInfo.version : null
      return { success: true, currentVersion: app.getVersion(), latestVersion: latest }
    } catch (e) {
      return { success: false, error: e && e.message, currentVersion: app.getVersion() }
    }
  })

  // Força baixar+instalar agora (caso o usuário queira atualizar na hora)
  ipcMain.handle('install-update-now', async () => {
    try { isQuitting = true; autoUpdater.quitAndInstall(); return { success: true } }
    catch (e) { return { success: false, error: e && e.message } }
  })

  ipcMain.handle('get-app-version', () => app.getVersion())

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    } else if (mainWindow) {
      mainWindow.show()
    }
  })
})

app.on('window-all-closed', () => {
  // Overridden: Don't quit, wait for tray explicit quit
  if (process.platform !== 'darwin' && isQuitting) {
    app.quit()
  }
})
