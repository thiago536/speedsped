# Problemas Conhecidos e Soluções

## [RESOLVIDO] bancos_nomes.json com IP antigo

**Sintoma:** `backup_manager.py` falha com `code=1` imediatamente ao tentar pg_dump  
**Causa:** Todos os ~75 entries tinham `host: "131.100.25.4"` (inacessível). DNS correto é `pgsql.e-prosys.com`  
**Resolvido em:** 2026-06-03  
**Fix:** Mass replace via PowerShell — todos os hosts agora são `pgsql.e-prosys.com`  
**Verificar:** `Select-String -Path "C:\SpedGenerator\bancos_nomes.json" -Pattern "131\.100\.25\.4"` → deve retornar 0 resultados

---

## [PENDENTE] POSTO SAO FRANCISCO BELEM sem nome_base

**Sintoma:** `tracking: 'POSTO SAO FRANCISCO BELEM' registrado como erro. motivo: nome_base ou data_liberacao vazio`  
**Causa:** Empresa foi liberada no Supabase com campo `nome_base = null`  
**Fix:** Definir `nome_base` na tabela `empresas` (id=72) no Supabase  
**Impacto:** Esta empresa nunca vai gerar SPED até corrigir

---

## [PENDENTE] ACS versões alternativas ausentes

**Sintoma:** Se empresa tiver "DM" ou "659" em `informacoes_sped`, o sistema vai tentar `C:\ACSSoft\Sintese\GerenteDM\gerente.exe` que não existe  
**Fix:** Instalar os executáveis nos caminhos configurados em `acs_versoes.json`, ou remover as entradas se não forem usadas

---

## [PADRÃO DE FALHA] Daemon re-trava após reset de gerados.json

**Sintoma:** Apago `gerados.json`, daemon tenta as empresas, mas backups ainda estão baixando → 3 tentativas falham → trava de novo  
**Causa:** Race condition entre download (lento, minutos) e ciclos do daemon (a cada 5 min)  
**Solução correta:** Só apagar `gerados.json` APÓS confirmar que TODOS os backups necessários estão em `C:\Backups_Novo` com tamanho > 1MB

```powershell
# Verificar antes de fazer o reset:
$liberadas = @("H7conv","Bilosao","Boavista","Brasil","Santafe","Cordeiro","Belavista","Marka","SG","Cajazeiras","Maerainha","Guerra","Angicos","Remigio","Alle","Sousa","Casanova")
foreach ($b in $liberadas) {
    $f = "C:\Backups_Novo\$b.backup"
    $mb = if (Test-Path $f) { [math]::Round((Get-Item $f).Length/1MB,1) } else { 0 }
    Write-Host "$b`: $mb MB"
}
```

---

## [PADRÃO] Backups 0-byte em C:\Backups_Novo

**Sintoma:** Arquivo `.backup` existe mas tem 0 bytes — pg_restore falha com "end of file"  
**Causa:** Download foi interrompido ou banco não existe no servidor remoto  
**Fix:** `Remove-Item "C:\Backups_Novo\X.backup"` e re-baixar  
**Verificar:** `Get-ChildItem "C:\Backups_Novo\*.backup" | Where-Object {$_.Length -eq 0}`

---

## [PADRÃO] $host é variável reservada no PowerShell

**Sintoma:** Script PowerShell com `$host = "pgsql.e-prosys.com"` falha silenciosamente — pg_dump recebe o objeto `InternalHost` como hostname  
**Fix:** Usar `$pgHost` ou `$servidor` em vez de `$host`

---

## [PADRÃO] python não está no PATH em processos filhos

**Sintoma:** `Start-Process powershell -ArgumentList "python script.py"` falha com "python não reconhecido"  
**Fix:** Usar caminho absoluto: `C:\Users\SERVIDOR SPED\AppData\Local\Programs\Python\Python313\python.exe`
