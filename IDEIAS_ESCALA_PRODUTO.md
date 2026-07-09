# SpedGenerator — Ideias de Escala e Produto (07/07/2026)

> Brainstorm completo pedido pelo dono do projeto: como escalar nos próximos
> meses e como transformar isso num produto vendável para outras empresas que
> geram SPEDs em massa (contabilidades, redes de postos, BPOs fiscais).

---

## 1. FUNDAÇÃO (fazer antes de escalar qualquer coisa)

1. **Git + backups automáticos do código.** O incidente de 07/07 provou: sem
   versionamento, um `del` apaga o negócio. `git init` + commit a cada mudança
   + push para repositório privado (GitHub) + tarefa diária que zipa a pasta.
2. **Serviço Windows + watchdog.** Hoje o daemon é um python.exe solto. Virar
   serviço (NSSM/sc.exe) com restart automático, healthcheck (se
   `daemon_state.json` não atualiza há X min → reinicia e alerta).
3. **Alertas ativos.** Telegram/WhatsApp/e-mail quando: erro definitivo, fila
   parada > 30 min, disco < 50 GB, backup diário falhou, daemon caiu. Hoje o
   erro só aparece se alguém abrir o monitor.
4. **Métricas históricas.** Gravar por geração: duração, tentativas, tamanho do
   banco, resultado. Isso vira o dashboard de SLA e o argumento de venda
   ("98,5% de geração automática, tempo médio 22 min").
5. **Validador de SPED pós-geração.** Checagem tipo PVA antes de entregar:
   bloco 0 e 9999 coerentes, contadores de registros, CNPJ, período. Pega
   arquivo quebrado ANTES do contador reclamar.

## 2. ESCALA TÉCNICA (crescer de dezenas para centenas de postos)

6. **Matar a fragilidade nº 1: gerar o SPED sem o ACS.** O layout SPED
   Fiscal/Contribuições é público (Guia Prático da EFD). Uma engine Python que
   lê o banco `_local` e escreve o TXT direto elimina GUI, popups, NAT, telas
   presas — o ponto mais frágil do sistema inteiro. Estratégia segura:
   construir por bloco e validar byte a byte contra a saída do ACS nos mesmos
   bancos até bater 100%; aí trocar. É o maior investimento e o maior retorno.
7. **Plano B: perguntar à ACS se o Gerente tem modo CLI/parâmetros de linha de
   comando** para exportação. Se existir, adeus automação de tela.
8. **Paralelizar a geração GUI enquanto ela existir:** múltiplas sessões
   Windows (RDP/VM leve), 1 ACS por sessão, fila distribuída — 3 sessões ≈ 3x
   o throughput sem tocar no código de automação.
9. **Backup incremental em vez de pg_dump de 6 GB:** réplica lógica ou
   pgBackRest/WAL streaming por cliente. Elimina a fila serial de dump (hoje o
   maior gargalo de latência) e dá RPO de minutos em vez de 1 dia.
10. **Cache inteligente de restore:** hash do backup → se o banco `_local` já
    corresponde ao mesmo dump, pular restore (hoje sempre dropa/recria).
11. **Fila com prioridade real e SLA:** hoje é lista com prioridade simples.
    Com volume, usar fila persistente (a própria tabela no Postgres local) com
    deadline por competência fiscal (dia 20 aperta).
12. **Hardening da máquina:** conta de serviço dedicada, ACL restritiva nas
    pastas de produção, AppLocker/WDAC para bloquear deletes acidentais de
    agentes, e um segundo servidor standby (o snapshot já é o começo).

## 3. PRODUTO / VENDER PARA FORA

13. **SaaS para contabilidades de postos.** O Supabase já é multi-empresa; o
    salto é multi-TENANT: portal onde cada contabilidade cadastra seus postos,
    aponta o banco (ou sobe backup), clica "liberar" e recebe o SPED pronto +
    relatório de auditoria. Cobrança por CNPJ/mês (ex.: R$ 49-99/CNPJ) +
    setup. 100 CNPJs = receita recorrente relevante com o MESMO robô.
14. **Nicho primeiro: combustíveis.** O sistema já entende as dores do setor
    (LMC, tanques, bicos, medições, ANP). Vender como "SPED automático para
    postos" é muito mais forte que "SPED genérico". Expandir depois.
15. **Drivers de ERP como módulos.** Hoje só ACS/Sintese. Cada ERP de posto
    (LinxPostos, CTF, EMSys, AutoSystem) vira um "driver" (extração do banco +
    geração). A arquitetura atual (backup → restore → gerar → validar) já é o
    esqueleto certo.
16. **Central do contador (multiusuário).** Login por contabilidade, trilha de
    auditoria por CNPJ, download dos arquivos, histórico por competência,
    botão de reprocessar. É o monitor web atual com autenticação e recorte por
    cliente — 70% já existe.
17. **Relatório de saúde fiscal mensal (upsell).** O robô já detecta CFOP sem
    cadastro, NCM inválido, alíquota errada, medição faltando. Empacotar isso
    num PDF mensal por posto = produto de compliance preventivo que o contador
    repassa ao cliente dele.
18. **Auto-fixers plugáveis (o diferencial técnico).** cfop_fixer e fix_nat
    provaram o conceito: erro conhecido → correção automática na cópia local →
    telemetria. Catalogar cada erro novo como um fixer versionado. Com o tempo
    isso vira a barreira de entrada: ninguém mais terá essa biblioteca de
    correções do mundo real.
19. **IA na triagem:** classificar automaticamente o erro da timeline
    (screenshot + log) e sugerir a ação — hoje esse trabalho é humano. Um LLM
    barato resolve 80% da triagem.
20. **Outros documentos fiscais na mesma esteira:** EFD-Reinf, Sintegra
    (estados que ainda exigem), DIEF regionais, inventário (bloco H) sob
    demanda. Mesmo pipeline, mais valor por CNPJ.
21. **Comercial pragmático:** (a) case interno com números reais (X postos, Y
    SPEDs/mês, Z% automático); (b) parceria com 2-3 contabilidades
    especializadas em combustíveis como early adopters com desconto
    vitalício; (c) demo gravada do monitor mostrando a esteira rodando.
22. **Licenciamento on-premise** para quem não quer nuvem: o pacote
    SpedGenerator + instalador + suporte, cobrado por ano. O produto já roda
    100% on-premise hoje — é o caminho de menor esforço para a primeira venda.

## 4. INTERFACE / EXPERIÊNCIA

23. **Monitor web → PWA** com notificação push no celular ("SABUGI concluído",
    "SANTA ROSA falhou 3x").
24. **Linha do tempo visual por empresa:** timeline.jsonl + screenshots num
    feed navegável (o dado já existe, falta a tela).
25. **Kanban da fila:** colunas aguardando/preparando/gerando/concluído/erro,
    arrastar para priorizar (hoje é comando).
26. **Modo TV:** tela cheia com a esteira e os KPIs do dia para pendurar na
    parede da contabilidade.
27. **Botão "diagnosticar" por empresa:** roda observar_startup_nat.py e anexa
    o resultado à timeline — transforma o diagnóstico manual de hoje em 1 clique.

## 5. ORDEM SUGERIDA (próximos 3 meses)

| Mês | Foco |
|-----|------|
| 1 | Fundação: git, serviço+watchdog, alertas, validador de SPED. Estabilizar pendências (H7conv, Santa Rosa, nomes). |
| 2 | Escala: 2ª sessão de geração paralela; métricas/dashboard; começar engine SPED própria pelo bloco mais simples (Contribuições ou 0/9999). |
| 3 | Produto: central do contador com login; relatório de saúde fiscal; 1ª contabilidade parceira usando de fora. |
