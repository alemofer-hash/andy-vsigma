# ANDY Threads MVP Roadmap

## THREADS-0 - Discovery e charter

- Objetivo: alinhar produto, setores e nao-objetivos.
- Entregavel: charter, perguntas setoriais e matriz inicial.
- Teste: docs existem e nao prometem chat generico.
- Risco: virar Teams dentro do ANDY.
- Aceite: toda thread exige referencia tecnica.

## THREADS-1 - Domain core

- Objetivo: criar modelos, referencias, lenses e responsabilidade.
- Entregavel: `andy_threads/` com dataclasses e roteamento.
- Teste: unitarios de modelo, referencia, sector_lens e responsibility.
- Risco: acoplar a engine.
- Aceite: cria referencia a partir de filtro sem alterar query builder.

## THREADS-2 - SQLite local store e audit

- Objetivo: persistir MVP local em runtime/validacao.
- Entregavel: store SQLite, audit, export JSON/Markdown.
- Teste: store cria thread, mensagem, decisao e export.
- Risco: armazenar dado bruto.
- Aceite: nao armazena DataFrame, Parquet, DuckDB ou path real completo.

## THREADS-3 - Policy deny-by-default

- Objetivo: garantir acesso por escopo e setor.
- Entregavel: policy local com mock user.
- Teste: deny-by-default, owner, consulted, resolver e export permission.
- Risco: acesso amplo demais.
- Aceite: usuario sem escopo nao le.

## THREADS-4 - Integracao com recorte do ANDY Desktop

- Objetivo: botao "Comentar este recorte" no Desktop PySide6.
- Entregavel: criacao de thread a partir de filtros ativos.
- Teste: smoke manual e teste de adapter.
- Risco: mexer em fluxo de filtro/export.
- Aceite: nenhuma matematica alterada.

## THREADS-5 - Painel lateral PySide6

- Objetivo: exibir threads do recorte.
- Entregavel: painel local read/write.
- Teste: abre, lista, comenta e exporta.
- Risco: excesso visual.
- Aceite: contexto do recorte fica visivel.

## THREADS-6 - Bridge para BI status-only

- Objetivo: expor status agregado de thread para BI.
- Entregavel: dataset/status sem texto sensivel.
- Teste: schema e redaction.
- Risco: vazar conversa.
- Aceite: BI recebe apenas status governado.

## THREADS-7 - API local

- Objetivo: separar UI de store.
- Entregavel: API local controlada.
- Teste: contratos e policy.
- Risco: virar servico inseguro.
- Aceite: loopback/local e sem provider real por padrao.

## THREADS-8 - Notificacoes corporativas

- Objetivo: alertar Teams/Outlook sem virar fonte da verdade.
- Entregavel: notificacao outbound.
- Teste: mock.
- Risco: decisao ficar fora do ANDY.
- Aceite: decisao volta para a thread.

## THREADS-9 - Store corporativo multiusuario

- Objetivo: persistencia governada corporativa.
- Entregavel: storage aprovado por TI.
- Teste: SSO/RLS/audit.
- Risco: privacidade e governanca.
- Aceite: homologacao institucional.
