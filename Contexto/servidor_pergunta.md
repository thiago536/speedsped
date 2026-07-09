---
timestamp: 2026-06-04 11:30:00
status: PENDENTE — OBSERVACAO VISUAL NECESSARIA
prioridade: URGENTE
ref: ACS morre silenciosamente após 200s de geração sem criar arquivo
---

## Situação

Todos os fixes de automação estão funcionando:
- Login: OK
- Formulário SPED Fiscal: OK
- Confirmação (termos): OK
- "Dados do SPED": OK
- Início da geração: OK (ACS ativo por ~200s)

**Mas então o processo gerente.exe simplesmente desaparece. Sem arquivo em C:\ACS_Exporta.**

Testado com BELL (249MB) e LAISXII (708MB). Mesmo comportamento nos dois.

---

## AÇÃO NECESSÁRIA — Observação visual durante geração

### Próxima geração: POSTO O TEIMOSAO (base=laisxii_local)
O sistema vai processar esse posto em breve (próximo ciclo).

**Enquanto o ACS estiver gerando SPED:**

1. Olha a tela do servidor via LogMeIn
2. O ACS vai estar aberto na tela de "Exportação para o SPED"
3. Quando aparecer "Dados do SPED" e você clicar OK, a geração começa
4. **O que acontece nos próximos 3-4 minutos?**
   - O ACS fecha a janela de exportação?
   - O ACS mostra algum dialog ou mensagem?
   - Aparece algo com "Erro" ou "Information" ou qualquer texto?
   - A janela principal do ACS continua aberta?
   - O processo gerente.exe fecha?

5. **Verifica em C:\ACS_Exporta** — aparece algum arquivo .txt durante a geração?

---

## Pergunta específica sobre o ACS local

Ainda válida da pergunta anterior: no ambiente LOCAL (desenvolvimento),
quando você gera SPED manualmente para qualquer posto:

- O processo gerente.exe fecha após a geração ou fica aberto?
- Quanto tempo leva para um banco de ~250MB?
- Aparece algum arquivo .txt em C:\ACS_Exporta ou em outro lugar?

---

## Hipótese mais provável atual

O ACS no servidor está encontrando um erro DURANTE a geração do SPED
(possivelmente query SQL que falha na tabela `prestacao`) e fechando sem
mostrar dialog e sem criar arquivo.

Evidência: `AjustaEstrutura_04062026.txt` mostra:
```
Erro: column "p" of relation "prestacao" does not exist
```

Esse erro ocorre ao startup para bell_local. Se uma query similar falha
DURANTE a geração (mas sem ser logada), o ACS pode estar crashando silenciosamente.

---

## Pergunta sobre a tabela prestacao

No banco LOCAL (bell_local ou qualquer banco de posto), a tabela `prestacao`
tem alias em queries UPDATE? O erro `column "p" of relation "prestacao" does not exist`
é normal no local ou é exclusivo do servidor?
