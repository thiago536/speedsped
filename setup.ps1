# setup.ps1 - Instalador Automatizado do SpedGenerator
# DEVE ser rodado como Administrador no Servidor de Destino.

# 1. Verifica privilégios de Administrador
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (!$isAdmin) {
    Write-Error "Este script PRECISA ser executado como Administrador. Clique com o botão direito no PowerShell e escolha 'Executar como Administrador'."
    exit
}

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " INSTALADOR AUTOMATIZADO - SPEDGENERATOR    " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# 2. Instalação de Programas via Winget
Write-Host "`n[1/5] Instalando dependências de sistema via Winget..." -ForegroundColor Yellow

$skipWinget = Read-Host "Deseja pular a instalacao de dependencias via Winget? (S/N) [Pressione Enter para Sim se ja instalou]"
if ($skipWinget -eq "" -or $skipWinget -eq "S" -or $skipWinget -eq "s") {
    Write-Host "-> Pulando Winget..." -ForegroundColor Green
} else {
    function Install-WingetApp {
        param (
            [string]$AppName,
            [string]$PackageId
        )
        Write-Host "Verificando/Instalando: $AppName..." -ForegroundColor DarkGray
        $check = winget list --id $PackageId -e 2>$null
        if ($check) {
            Write-Host "-> $AppName já está instalado." -ForegroundColor Green
        } else {
            Write-Host "-> Instalando $AppName silenciosamente..." -ForegroundColor Cyan
            winget install --id $PackageId --silent --accept-source-agreements --accept-package-agreements
            if ($LASTEXITCODE -eq 0) {
                Write-Host "-> $AppName instalado com sucesso!" -ForegroundColor Green
            } else {
                Write-Warning "Falha ao instalar $AppName via Winget. Prossiga com a instalação manual mais tarde se necessário."
            }
        }
    }

    Install-WingetApp "Python 3.11" "Python.Python.3.11"
    Install-WingetApp "PostgreSQL 15" "PostgreSQL.PostgreSQL.15"
    Install-WingetApp "AutoHotkey v2" "AutoHotkey.AutoHotkey"
}

# 3. Criação de pastas necessárias
Write-Host "`n[2/5] Criando estrutura de pastas..." -ForegroundColor Yellow
$folders = @(
    "C:\SpedGenerator",
    "C:\SpedGenerator\Bancos",
    "C:\ACS_Exporta",
    "C:\Backups_Novo"
)
foreach ($folder in $folders) {
    if (!(Test-Path $folder)) {
        New-Item -ItemType Directory -Path $folder | Out-Null
        Write-Host "-> Pasta criada: $folder" -ForegroundColor Green
    } else {
        Write-Host "-> Pasta já existe: $folder" -ForegroundColor DarkGray
    }
}

# 4. Copiar arquivos para C:\SpedGenerator se rodando da pasta extraída
Write-Host "`n[3/5] Configurando arquivos locais..." -ForegroundColor Yellow
if (Test-Path "main.py") {
    Write-Host "-> Copiando arquivos do instalador para C:\SpedGenerator..." -ForegroundColor Cyan
    Copy-Item "*.*" -Destination "C:\SpedGenerator" -Force -Exclude "setup.ps1"
    if (Test-Path "AHK") {
        Copy-Item "AHK" -Destination "C:\SpedGenerator" -Recurse -Force
    }
    Write-Host "-> Arquivos copiados!" -ForegroundColor Green
} else {
    Write-Warning "AVISO: Rode este script a partir da pasta onde os arquivos do SpedGenerator foram extraídos para copiá-los automaticamente."
}

# 5. Instalar dependências Python (PIP)
Write-Host "`n[4/5] Instalando dependências do Python (pip)..." -ForegroundColor Yellow
$envPath = "C:\Windows\System32"
# Localiza o executável do Python
$pythonCmd = "python"
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    # Tenta caminho padrão se o PATH ainda não atualizou na sessão atual
    $pythonCmd = "$env:USERPROFILE\AppData\Local\Programs\Python\Python311\python.exe"
    if (!(Test-Path $pythonCmd)) {
        $pythonCmd = "C:\Program Files\Python311\python.exe"
    }
}

if (Get-Command $pythonCmd -ErrorAction SilentlyContinue -or (Test-Path $pythonCmd)) {
    Write-Host "-> Atualizando pip..." -ForegroundColor Cyan
    & $pythonCmd -m pip install --upgrade pip --quiet
    
    if (Test-Path "C:\SpedGenerator\requirements.txt") {
        Write-Host "-> Instalando pacotes do requirements.txt..." -ForegroundColor Cyan
        & $pythonCmd -m pip install -r C:\SpedGenerator\requirements.txt
        Write-Host "-> Pacotes instalados com sucesso!" -ForegroundColor Green
    } else {
        Write-Host "-> requirements.txt não encontrado. Instalando pacotes básicos..." -ForegroundColor Cyan
        & $pythonCmd -m pip install python-dotenv supabase psutil pywinauto pyautogui psycopg2-binary Pillow pywin32 customtkinter pynput pygetwindow
        Write-Host "-> Pacotes básicos instalados!" -ForegroundColor Green
    }
} else {
    Write-Error "Python não foi localizado no sistema para instalar dependências do PIP. Verifique se o Python foi instalado corretamente no PATH."
}

# 6. Configuração interativa do .env
Write-Host "`n[5/5] Configurando o arquivo .env..." -ForegroundColor Yellow
$envFile = "C:\SpedGenerator\.env"
$skipEnv = $false
if (Test-Path $envFile) {
    $replace = Read-Host "O arquivo C:\SpedGenerator\.env já existe. Deseja sobrescrever? (S/N)"
    if ($replace -ne "S" -and $replace -ne "s") {
        Write-Host "-> Mantendo .env existente." -ForegroundColor Green
        $skipEnv = $true
    }
}

if (!$skipEnv) {
    $supabaseUrl = Read-Host "Digite a URL do Supabase"
    $supabaseKey = Read-Host "Digite a Service Role Key do Supabase (Chave Privada)"
    $pgPassword  = Read-Host "Digite a senha do PostgreSQL local (padrão '123')"
    if ($pgPassword -eq "") { $pgPassword = "123" }

    $envContent = @"
SUPABASE_URL=$supabaseUrl
SUPABASE_KEY=$supabaseKey
PG_PASSWORD=$pgPassword
BACKUP_DIR=C:\Backups_Novo
PG_BIN_DIR=C:\Program Files\PostgreSQL\15\bin
ACS_EXE_PATH=C:\ACSSoft\Sintese\Gerente SPED\gerente.exe
ACS_INI_PATH=C:\ACSSoft\Sintese\Gerente SPED\acsgerente.ini
LOCAL_BACKUP_DIR=C:\SpedGenerator\Bancos
SPED_EXPORT_DIR=C:\ACS_Exporta
"@
    Set-Content -Path $envFile -Value $envContent -Encoding utf8
    Write-Host "-> .env criado e salvo com sucesso em $envFile!" -ForegroundColor Green
}

Write-Host "`n=============================================" -ForegroundColor Green
Write-Host " INSTALAÇÃO CONCLUÍDA COM SUCESSO!" -ForegroundColor Green
Write-Host " Próximos Passos recomendados:" -ForegroundColor Yellow
Write-Host " 1. Instale o ACS Gerente (Sintese) se ainda não o fez." -ForegroundColor White
Write-Host " 2. Coloque os backups .backup na pasta C:\Backups_Novo." -ForegroundColor White
Write-Host " 3. Certifique-se de manter uma sessão de usuário Windows ativa no console." -ForegroundColor White
Write-Host " 4. Execute 'python C:\SpedGenerator\main.py --dry-run' para testar." -ForegroundColor White
Write-Host "=============================================" -ForegroundColor Green
