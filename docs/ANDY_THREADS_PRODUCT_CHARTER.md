# ANDY Threads Product Charter

## Frase guia

ANDY Threads transforma comunicacao tecnica em dado operacional governado.

## O que e

ANDY Threads e uma camada de comunicacao tecnica contextual vinculada a objetos
analiticos do ANDY: lote, filtro, medicao, equipamento, terminal, variavel,
periodo, anomalia, analise, dashboard, export ou decisao.

A conversa so tem valor se estiver presa ao dado.

## O que nao e

- Nao e Teams dentro do ANDY.
- Nao e Outlook.
- Nao e WhatsApp interno.
- Nao e DM.
- Nao e chat generico.
- Nao substitui comunicacao corporativa.
- Nao cria login proprio.
- Nao armazena anexos livres no MVP.
- Nao usa DuckDB como banco multiusuario de chat.

## Problema

Decisoes tecnicas ficam fora dos dados, dispersas em conversas, prints,
reunioes, planilhas soltas e memoria oral. Quando o recorte muda, o contexto se
perde; quando outra area entra na discussao, falta rastreabilidade.

## Solucao

Criar threads vinculadas a referencias tecnicas do ANDY, como filtros,
source_fingerprint, lote, dataset_version, ponto_id, source_cadence,
subestacao, alimentador, equipamento, terminal, variavel, periodo, evento de
fluxo, patamar, pagina BI ou export.

## Valor

- memoria decisoria;
- rastreabilidade;
- reducao de perda de contexto;
- centralizacao de escopo;
- melhor passagem entre setores;
- historico tecnico auditavel;
- suporte a BI corporativo web;
- base para decisoes operacionais documentadas.

## Lei do produto

Toda thread deve nascer de uma referencia tecnica. Thread sem referencia vira
chat generico e fica fora do escopo do ANDY Threads.

## MVP

O MVP e local, usa SQLite em runtime/validacao, nao possui anexos, nao possui
DM, nao possui notificacao, nao ativa provider real e nao publica nada.

## Fonte da verdade

A engine Python do ANDY continua sendo a fonte da verdade analitica. ANDY
Threads registra discussao, decisao e evidencia; nao recalcula MVA, FP, MW,
fluxo P/Q, inversao ou patamar.
