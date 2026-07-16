# ANDY Threads Engineering Emergency Roadmap

## Objetivo

Transformar o ANDY Threads em um sistema de comunicacao tecnica eficiente para
ambiente de engenharia emergencial, reduzindo o atraso causado por problemas em
softwares e fluxos que dependem de parametros eletricos.

## Norte de produto

O engenheiro nao deve precisar explicar do zero:

- qual fonte estava usando;
- qual filtro estava aplicado;
- qual medicao ou parametro falhou;
- qual dashboard/export divergente;
- quem precisa responder;
- qual decisao encerra o caso.

O ANDY deve levar esse contexto junto.

## Fases recomendadas

### THREADS-E0 - Readiness emergencial

Status: implementado nesta fase.

Entregas:

- taxonomia emergencial;
- severidade/SLA;
- readiness score;
- gap analysis;
- playbook inicial.

Gate:

- `scripts/check_andy_threads_emergency_readiness.py` passa.

### THREADS-E1 - Entrada controlada no Desktop PySide6

Objetivo: criar o botao "Comentar este recorte" no ponto onde o engenheiro ja
esta vendo filtro, preview, analise ou export.

Entregas:

- botao no Desktop PySide6;
- criacao de `AndyThreadReference` a partir dos filtros ativos;
- formulario minimo: titulo, tipo, severidade, comentario;
- grava em SQLite local;
- sem alterar engine, filtros, export ou matematica.

Aceite:

- o engenheiro abre uma thread em menos de 20 segundos;
- a thread nasce com SE/alimentador/equipamento/terminal/variavel/periodo quando
  disponiveis;
- nenhuma thread sem referencia tecnica e aceita.

### THREADS-E2 - Painel de historico do recorte

Objetivo: mostrar o historico tecnico associado ao recorte atual.

Entregas:

- painel lateral ou aba "Threads";
- lista por status/severidade;
- mensagens;
- decisoes;
- export Markdown/JSON.

Aceite:

- ao selecionar o mesmo recorte, o historico reaparece;
- decisao registrada fica visivel;
- sem anexos e sem DM.

### THREADS-E3 - Triagem emergencial e SLA

Objetivo: classificar prioridade e prazo de resposta.

Entregas:

- severidades S0 a S4;
- SLA de triagem/primeira resposta/decisao;
- rota por dominio: parametro eletrico, medicao, cadastro, BI, export, runtime,
  evento operacional;
- filtros para threads vencidas.

Aceite:

- S3/S4 exigem DecisionRecord;
- threads vencidas aparecem em destaque;
- owner/consultados sao sugeridos automaticamente.

### THREADS-E4 - Runbook e tabletop drill

Objetivo: testar o processo com cenarios reais simulados.

Cenarios minimos:

- FP/MW/MVA divergente;
- inversao de fluxo suspeita;
- terminal errado;
- lacuna 15 em 15 vs hora em hora;
- export XLSX divergente;
- runtime/catalogo quebrado;
- acesso/RLS incorreto no BI, quando BI voltar ao foco.

Aceite:

- cada cenario gera thread;
- cada thread tem dono;
- cada thread tem decisao ou pendencia explicita;
- delay observado e registrado.

### THREADS-E5 - Notificacao como alerta, nao fonte da verdade

Objetivo: reduzir tempo de resposta sem deslocar a decisao para fora do ANDY.

Entregas futuras:

- alerta Teams/Outlook;
- link/ID da thread;
- sem decisao fora do ANDY Threads.

Bloqueio:

- depende provider corporativo e revisao de seguranca.

### THREADS-E6 - Store corporativo multiusuario

Objetivo: escalar para varios usuarios e turnos.

Bloqueios:

- arquitetura aprovada;
- SSO/IdP;
- RLS/ABAC;
- retencao;
- backup/restore;
- auditoria corporativa.

## Prioridade imediata

Atacar THREADS-E1 e THREADS-E2 antes de notificacoes ou store corporativo.

Motivo: o gargalo atual e friccao de comunicacao no momento em que o problema e
encontrado. Sem botao/painel no fluxo real, a taxonomia existe, mas nao reduz
delay operacional.

## Definicao de pronto para uso emergencial local

```text
readiness_percent >= 75
botao Comentar este recorte funcionando
painel de historico funcionando
SLA visivel
DecisionRecord obrigatorio para S3/S4
export de thread auditavel
sem provider real
sem dados reais versionados
```
