# Checklist de Diagnóstico Rápido

Execute este checklist no início de cada sessão antes de qualquer ação.

## 1. Verificar Daemon

```powershell
# Daemon está vivo?
Get-Process -Id (Get-Content "C:\ACS_Exporta\spedgenerator.lock") -ErrorAction SilentlyContinue

# Estado atual
Get-Content "C:\ACS_Exporta\daemon_state.json"
```

**OK:** processo existe, `status: aguardando` ou `em_processo`  
**PROBLEMA:** processo não existe → reiniciar via `C:\SpedGenerator\iniciar_daemon.bat`

---

## 2. Verificar Lockfile Zumbi

```powershell
$pid = Get-Content "C:\ACS_Exporta\spedgenerator.lock" -ErrorAction SilentlyContinue
if ($pid -and -not (Get-Process -Id $pid -ErrorAction SilentlyContinue)) {
    Write-Host "ZUMBI DETECTADO — remover lockfile"
}
```

**Ação se zumbi:** `Remove-Item "C:\ACS_Exporta\spedgenerator.lock"`

---

## 3. Verificar Supabase

```powershell
# Ver se empresas liberadas aparecem no log
Get-Content "C:\ACS_Exporta\daemon.log" -Tail 30 | Select-String "liberadas|HTTP"
```

**OK:** `HTTP/2 200 OK` e lista de empresas no log  
**PROBLEMA:** erro de conexão → verificar SUPABASE_KEY no .env

---

## 4. Verificar Backups Disponíveis vs Necessários

```powershell
# Empresas liberadas no Supabase (ver log)
Get-Content "C:\ACS_Exporta\daemon.log" -Tail 50 | Select-String "base="

# Backups existentes e válidos (>1MB)
Get-ChildItem "C:\Backups_Novo\*.backup" | Where-Object {$_.Length -gt 1MB} |
    Select-Object Name, @{n='MB';e={[math]::Round($_.Length/1MB,1)}}
```

**Cruzar:** cada `base=X` no log precisa ter `X.backup` em C:\Backups_Novo

---

## 5. Ver Status das Empresas (gerados.json)

```powershell
$g = Get-Content "C:\ACS_Exporta\gerados.json" | ConvertFrom-Json
$g.PSObject.Properties | ForEach-Object {
    "$($_.Value.nome): $($_.Value.status) (tent=$($_.Value.tentativas))"
}
```

**Se todas com `tent=3`:** sistema bloqueado → ver seção "Reset de Emergência"

---

## 6. Verificar pg_restore

```powershell
& "C:\Program Files\PostgreSQL\15\bin\pg_restore.exe" --version
```

**OK:** `pg_restore (PostgreSQL) 15.18`

---

## Reset de Emergência (quando tudo travou)

> ⚠️ Só fazer DEPOIS de confirmar que os backups estão prontos em C:\Backups_Novo

```powershell
# Fazer backup do gerados.json antes
Copy-Item "C:\ACS_Exporta\gerados.json" "C:\ACS_Exporta\gerados.json.bak.$(Get-Date -Format 'yyyyMMdd_HHmmss')"

# Apagar para desbloquear retry
Remove-Item "C:\ACS_Exporta\gerados.json" -Force

# O daemon vai tentar novamente no próximo ciclo (~5 min)
```

---

## Verificar Conectividade ao Servidor Remoto

```powershell
# Testar TCP
$c = New-Object System.Net.Sockets.TcpClient
try { $c.Connect("pgsql.e-prosys.com", 5432); Write-Host "OK" } catch { Write-Host "FALHOU" }
finally { $c.Close() }

# Listar bancos disponíveis
$env:PGPASSWORD = "j0l0t1gT4nDpcaworrXlKQjuGcF7"
& "C:\Program Files\PostgreSQL\15\bin\psql.exe" -h pgsql.e-prosys.com -p 5432 -U postgres -c "\l"
```
