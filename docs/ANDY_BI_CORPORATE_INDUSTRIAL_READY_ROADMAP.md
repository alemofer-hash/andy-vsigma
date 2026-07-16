# ANDY BI Corporate Industrial Ready Roadmap

Data: 2026-07-08

## 1. Objetivo

Este roadmap define o que ainda falta para o ANDY BI sair do estado de
preparacao tecnica com dataset sintetico e virar um BI corporativo/industrial
pronto para uso governado na Equatorial.

Premissa central:

```text
ANDY calcula e valida.
BI corporativo apresenta e governa acesso.
Identidade corporativa autentica.
RLS/ABAC restringe.
Auditoria prova.
```

O ANDY nao deve criar login proprio, nao deve publicar dado real sem aceite e
nao deve mover regra analitica eletrica critica para DAX, Power Query, C#,
WPF ou camada visual sem contrato formal e teste de paridade.

## 2. Estado atual confirmado

O estado atual e tecnicamente promissor, mas ainda nao industrial.

Entregas ja preparadas:

- contrato de dataset ANDY -> BI;
- dataset builder com modo sintetico/publicavel;
- modelo semantico documentado;
- RLS/ABAC deny-by-default em camada Python;
- mock de identidade e claims;
- adapters/stubs para provider corporativo;
- readiness HTTPS;
- pacote TI/BI geravel localmente;
- relatorio piloto HTML sintetico;
- gates de hygiene, readiness, publicacao e safety;
- plano de commit seletivo sem artifacts/dados reais.

Limites atuais:

- nenhum workspace corporativo real foi configurado;
- nenhum provider real foi ativado;
- nenhum gateway/refresh corporativo foi validado;
- nenhum dataset real foi publicado;
- nenhum dado real foi versionado;
- o piloto atual e local/sintetico, nao relatorio Power BI/Fabric oficial;
- a arvore Git ainda precisa de revisao humana antes de commit;
- a plataforma BI oficial e seus processos precisam ser confirmados com TI/BI.

## 3. Definicao de pronto industrial

O ANDY BI sera considerado corporativo/industrial pronto quando cumprir todos
os criterios abaixo.

| Area | Criterio industrial | Status atual |
|---|---|---|
| Identidade | SSO corporativo oficial, sem senha local no ANDY | Preparado por contrato/stub |
| Autorizacao | RLS/ABAC por grupos corporativos revisados | Mock e policy local |
| Dataset | Dataset real governado, versionado e validado | Sintetico/publicavel |
| Semantica | Semantic model publicado em Dev/Homolog/Prod | Documentado localmente |
| Relatorio | BI Web piloto em workspace oficial | Piloto HTML local |
| Paridade | Desktop/XLSX vs BI com tolerancia e relatorio | Framework preparado |
| Refresh | Manual/agendado/incremental com owner | Estrategia documentada |
| Auditoria | Lote, hash, usuario, escopo, export e refresh rastreaveis | Contrato preparado |
| Seguranca | DLP/sensibilidade/RLS/gateway aprovados | Checklist preparado |
| Operacao | Runbook, suporte, rollback, SLA e monitoramento | Documentado, nao operado |
| Release | Dev -> Homolog -> Prod com aceite humano | Nao iniciado |

## 4. Fases restantes

### Fase IR-0 - Fechar baseline versionado

Objetivo: congelar o trabalho tecnico ja preparado antes de continuar.

Entregas:

- revisar os 107 arquivos staged;
- confirmar que nao ha artifacts, reports runtime, dados reais, secrets ou
  configs privadas staged;
- executar gates finais;
- fazer commits seletivos conforme `docs/ANDY_BI_WEB_COMMIT_PLAN.md`;
- manter residuos herdados fora do baseline.

Gate:

- Git safety passa;
- tracked safety passa;
- staged sem arquivos proibidos;
- commits revisados por humano.

Status: pendente de revisao humana/commit.

### Fase IR-1 - Decisao de plataforma BI oficial

Objetivo: confirmar formalmente qual plataforma sera usada para o piloto
corporativo.

Decisoes necessarias:

- Power BI / Fabric, outro BI corporativo ou combinacao;
- workspace Dev/Homolog/Prod;
- gateway ou refresh cloud;
- capacidade/licenca;
- owner funcional;
- owner tecnico;
- dono do dado;
- aprovador de seguranca;
- regra de DLP/sensibilidade.

Entregas:

- `docs/ANDY_BI_WORKSPACE_REQUEST_CHECKLIST.md` preenchido em versao privada;
- owner matrix privada;
- escopo do piloto por distribuidora, fonte e periodo;
- classificacao de dado;
- criterio de publicacao em Dev.

Gate:

- sem workspace e owners, nao publicar nada.

### Fase IR-2 - Identidade corporativa real

Objetivo: trocar mock/stub por claims reais, mantendo deny-by-default.

Tarefas:

- receber especificacao do IdP corporativo;
- mapear claims oficiais: usuario, email/matricula, grupos, distribuidora,
  estado, area, perfil e permissoes;
- criar config privada nao versionada;
- validar provider real somente em ambiente controlado;
- manter fallback mock apenas para testes locais;
- registrar evidencias redigidas.

Entregas:

- provider real habilitavel por config privada;
- testes com claims redigidas;
- matriz grupo -> escopo;
- deny-by-default validado;
- relatorio de seguranca.

Gate:

- usuario sem grupo nao ve nada;
- admin tecnico nao ganha visao total por acidente;
- nenhuma credencial entra no repo.

### Fase IR-3 - Dataset real controlado e redigivel

Objetivo: produzir o primeiro dataset real governado sem publicar
automaticamente.

Tarefas:

- escolher fonte/pasta/periodo piloto aprovados;
- executar ingestao normal do ANDY em ambiente autorizado;
- gerar dataset BI a partir do lake/catalogo do ANDY, nao da fonte bruta
  diretamente;
- validar schema, manifest, hashes, row counts e quality flags;
- gerar amostra redigida quando necessario para revisao fora do ambiente;
- bloquear se houver caminho real, segredo ou dado sensivel em artifact
  publicavel.

Entregas:

- `artifacts/andy_bi_dataset/` real local, fora do Git;
- manifest real com lote/hash;
- relatorio de qualidade;
- relatorio de hygiene;
- decisao humana sobre promocao para Dev.

Gate:

- dataset real so pode ir para workspace Dev apos revisao de seguranca e owner.

### Fase IR-4 - Semantic model corporativo

Objetivo: transformar o contrato local em semantic model na plataforma BI.

Tarefas:

- criar tabelas fato e dimensoes conforme contrato;
- configurar relacionamentos e cardinalidades;
- ocultar chaves tecnicas;
- criar medidas permitidas de apresentacao;
- marcar medidas criticas como precomputadas pela engine Python;
- evitar DAX/Power Query para regra eletrica critica;
- criar testes de paridade quando qualquer medida for implementada no BI.

Entregas:

- semantic model em Dev;
- dicionario de dados;
- lista de medidas permitidas/proibidas;
- documentacao de linhagem.

Gate:

- nenhuma medida critica divergente da engine Python.

### Fase IR-5 - RLS/ABAC em workspace Dev

Objetivo: aplicar restricao real de acesso dentro da plataforma BI.

Tarefas:

- configurar roles por distribuidora/estado/fonte/SE/perfil;
- mapear grupos corporativos;
- testar usuarios ficticios/redigidos;
- validar "deny by default";
- validar usuario multi-distribuidora;
- validar auditor;
- validar owner sem bypass indevido.

Entregas:

- matriz RLS/ABAC;
- testes de acesso;
- evidencias redigidas;
- plano de excecoes.

Gate:

- publicar relatorio sem RLS aprovado e proibido.

### Fase IR-6 - Relatorio piloto industrial

Objetivo: reproduzir o piloto sintetico como BI Web real.

Paginas obrigatorias:

- Cockpit Executivo ANDY;
- Catalogo de Medicoes;
- Patamar e Carga;
- Fluxo P/Q e Inversao;
- Qualidade e Auditoria;
- Paridade ANDY Desktop.

Tarefas:

- construir relatorio no workspace Dev;
- usar inicialmente dataset sintetico/publicavel;
- depois validar com dataset real aprovado;
- aplicar identidade visual ANDY sem copiar marca proprietaria de terceiros;
- implementar filtros cascatais;
- implementar narrativa de lote, periodo, cadencia, qualidade e escopo;
- separar visao executiva, engenharia e auditoria.

Entregas:

- relatorio Dev;
- checklist visual;
- evidencias de filtros/RLS;
- aceite de engenharia.

Gate:

- sem aceite visual/funcional, nao promover para Homolog.

### Fase IR-7 - Paridade Desktop/XLSX/BI

Objetivo: provar que o BI nao mudou a verdade analitica do ANDY.

Comparacoes minimas:

- contagens por periodo/fonte;
- min/max timestamp;
- SE/BAY/equipamento/terminal/variavel;
- MVA, MW, FP assinado;
- fluxo P/Q;
- inversao;
- patamar;
- quality flags;
- hashes/lote;
- linhas exportadas.

Entregas:

- relatorio de paridade;
- tolerancia configurada;
- lista de divergencias;
- decisao ACCEPTED/REVIEW/REJECTED por divergencia.

Gate:

- divergencia critica bloqueia publicacao.

### Fase IR-8 - Refresh, operacao e observabilidade

Objetivo: operar o BI sem depender de execucao manual artesanal.

Tarefas:

- definir refresh manual/agendado/incremental;
- registrar owner de refresh;
- definir janela de atualizacao;
- definir retencao de datasets;
- implementar rollback de lote;
- monitorar falha de refresh;
- emitir alerta para dataset stale;
- registrar eventos de publicacao/export/acesso quando disponivel.

Entregas:

- runbook operacional;
- estrategia de refresh;
- plano de rollback;
- matriz de suporte;
- SLA inicial.

Gate:

- sem rollback e owner, nao ir para Prod.

### Fase IR-9 - Homologacao corporativa

Objetivo: validar o uso real com engenharia, BI, seguranca e dono do dado.

Tarefas:

- rodar piloto com usuarios aprovados;
- validar RLS por perfis reais;
- validar entendimento dos indicadores;
- validar performance;
- validar exportacao;
- validar suporte;
- revisar riscos LGPD/DLP/confidencialidade;
- registrar aceite.

Entregas:

- termo de homologacao;
- backlog de ajustes;
- decisao GO/NO-GO para Prod.

Gate:

- sem aceite dos donos funcionais e seguranca, nao publicar app interno.

### Fase IR-10 - Producao controlada

Objetivo: liberar ANDY BI como app interno governado.

Tarefas:

- publicar em workspace Prod;
- liberar app interno para grupos autorizados;
- ativar refresh aprovado;
- publicar runbook;
- treinar usuarios-chave;
- iniciar monitoramento;
- planejar cadencia de release.

Entregas:

- app interno publicado;
- release notes;
- plano de suporte;
- dashboard de operacao;
- backlog pos-go-live.

Gate:

- producao com dados reais so sob repositorio privado, workspace aprovado,
  owners definidos e RLS validado.

## 5. Trilhas paralelas de trabalho

### Trilha A - Produto e governanca

- produto owner;
- escopo piloto;
- definicao de usuarios;
- matriz de responsabilidade;
- aceite executivo;
- comunicacao interna.

### Trilha B - Dados e engine

- fonte autorizada;
- dataset builder real;
- catalogo;
- qualidade;
- schema evolution;
- paridade.

### Trilha C - BI e semantica

- workspace;
- semantic model;
- relatorio;
- filtros;
- UX;
- performance.

### Trilha D - Seguranca

- IdP;
- grupos;
- RLS/ABAC;
- DLP;
- auditoria;
- redacao de evidencias.

### Trilha E - Operacao

- refresh;
- monitoramento;
- suporte;
- rollback;
- release;
- treinamento.

## 6. Backlog priorizado

### P0 - Bloqueadores industriais

1. Fechar baseline Git seguro.
2. Confirmar plataforma BI oficial.
3. Confirmar workspace Dev/Homolog/Prod.
4. Confirmar owners e dono do dado.
5. Confirmar IdP/grupos/claims.
6. Definir escopo piloto com dado real autorizado.
7. Publicar apenas dataset sintetico em Dev.
8. Validar RLS/ABAC real.
9. Validar paridade antes de qualquer uso real.

### P1 - Necessario para piloto corporativo

1. Implementar semantic model na plataforma BI.
2. Construir relatorio piloto industrial.
3. Configurar refresh Dev.
4. Gerar pacote de evidencias para seguranca.
5. Validar UX com engenharia.
6. Validar performance com volume real.

### P2 - Necessario para producao

1. Homologacao com multiplos perfis.
2. Rollback de lote.
3. Monitoramento de refresh.
4. Runbook de suporte.
5. Treinamento.
6. Politica de versionamento do semantic model.
7. Processo formal de mudanca.

### P3 - Evolucao futura

1. Multi-distribuidora completa.
2. Incremental refresh por lote/mes/fonte.
3. Data mart corporativo dedicado.
4. Linhagem automatizada.
5. Alertas de anomalia.
6. Certificacao do dataset.
7. Catalogo corporativo integrado.

## 7. Dependencias externas

Estas informacoes precisam vir da Equatorial/TI/BI antes de uma implantacao
industrial real:

- plataforma BI oficial e tenant;
- workspace Dev/Homolog/Prod;
- modelo de licenciamento;
- gateway e politica de refresh;
- grupos corporativos;
- claims disponiveis;
- responsaveis funcionais e tecnicos;
- classificacao de dados;
- regras de DLP/sensibilidade;
- politica de retencao;
- processo de publicacao;
- processo de suporte;
- aprovacao do dono do dado.

## 8. Riscos principais

| Risco | Impacto | Mitigacao |
|---|---|---|
| Publicar sem RLS | Exposicao indevida de dados | Deny-by-default e gate de RLS |
| Recalcular regra critica no BI | Divergencia analitica | Engine Python como fonte da verdade |
| Dataset real sem owner | Falha de governanca | Owner matrix obrigatoria |
| Refresh sem rollback | Indisponibilidade ou dado ruim | Lote/hash/rollback |
| Claims mal mapeadas | Usuario ve escopo errado | Testes com perfis reais/redigidos |
| Artifact com path/segredo | Vazamento operacional | Git safety, tracked safety, hygiene |
| Performance insuficiente | Rejeicao operacional | Agregacoes, incremental refresh e teste de carga |
| Relatorio bonito mas sem paridade | BI enganoso | Gate de paridade Desktop/XLSX/BI |

## 9. Comandos locais uteis

Gerar dataset sintetico:

```powershell
.\.venv\Scripts\python.exe scripts\build_andy_bi_dataset.py --format both --out artifacts\andy_bi_dataset --synthetic
```

Gerar piloto local:

```powershell
.\.venv\Scripts\python.exe scripts\build_andy_bi_pilot_report.py --dataset artifacts\andy_bi_dataset --out artifacts\andy_bi_pilot_report
```

Validar piloto:

```powershell
.\.venv\Scripts\python.exe scripts\check_andy_bi_pilot_report.py
```

Validar pacote:

```powershell
.\.venv\Scripts\python.exe scripts\check_andy_bi_publication_package.py
```

Validar safety:

```powershell
.\.venv\Scripts\python.exe scripts\check_andy_git_safety.py
.\.venv\Scripts\python.exe scripts\check_andy_tracked_safety.py
.\.venv\Scripts\python.exe scripts\check_reports_hygiene.py
```

## 10. Proxima acao recomendada

Executar a fase IR-0:

```text
Fechar baseline Git seguro do pacote ANDY BI Web e do piloto sintetico.
```

Depois disso, executar a fase IR-1:

```text
Preparar pacote de solicitacao para workspace Dev e publicacao inicial com
dataset sintetico na plataforma BI corporativa oficial.
```

Somente apos IR-1 e IR-2 o trabalho deve tocar provider real, workspace real ou
dataset real.
