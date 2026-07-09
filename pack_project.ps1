# pack_project.ps1 - Empacotador para o SpedGenerator
# Roda na máquina do desenvolvedor para gerar um ZIP limpo.

$projectName = "SpedGenerator"
$outputZip = "..\SpedGenerator_Deploy.zip"

Write-Host "=== Empacotando SpedGenerator ===" -ForegroundColor Cyan

# Lista de itens a excluir do pacote de deploy
$excludeList = @(
    "__pycache__",
    ".git",
    ".idea",
    ".vscode",
    ".env",
    "spedgenerator.log",
    "Bancos",
    "dist",
    "build",
    "*.spec",
    "*.png", 
    "*.zip"
)

# Cria pasta temporária
$tempDir = Join-Path $env:TEMP "spedgenerator_temp"
if (Test-Path $tempDir) { Remove-Item -Recurse -Force $tempDir }
New-Item -ItemType Directory -Path $tempDir | Out-Null

# Copiar arquivos do diretório atual recursivamente excluindo os itens da lista
Get-ChildItem -Path . -Recurse | Where-Object {
    $relativePath = $_.FullName.Substring((Get-Item .).FullName.Length + 1)
    $shouldExclude = $false
    foreach ($exclude in $excludeList) {
        if ($relativePath -like $exclude -or $_.Name -like $exclude) {
            $shouldExclude = $true
            break
        }
    }
    !$shouldExclude -and !$_.PSIsContainer
} | ForEach-Object {
    $targetPath = Join-Path $tempDir $_.FullName.Substring((Get-Item .).FullName.Length + 1)
    $parentDir = Split-Path $targetPath -Parent
    if (!(Test-Path $parentDir)) { New-Item -ItemType Directory -Path $parentDir | Out-Null }
    Copy-Item $_.FullName -Destination $targetPath -Force
}

# Garante cópia da pasta AHK se existir
if (Test-Path "AHK") {
    $targetAHK = Join-Path $tempDir "AHK"
    if (!(Test-Path $targetAHK)) { New-Item -ItemType Directory -Path $targetAHK | Out-Null }
    Copy-Item "AHK\*" -Destination $targetAHK -Force
}

# Gera o ZIP
if (Test-Path $outputZip) { Remove-Item -Force $outputZip }
Compress-Archive -Path "$tempDir\*" -DestinationPath $outputZip -Force

Write-Host "Sucesso! Pacote gerado em: $(Resolve-Path $outputZip)" -ForegroundColor Green
Write-Host "Envie o arquivo ZIP para o novo servidor." -ForegroundColor Yellow
