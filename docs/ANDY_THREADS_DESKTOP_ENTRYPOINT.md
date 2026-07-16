# ANDY Threads Desktop Entrypoint

## Objetivo

Adicionar ao Desktop PySide6 uma entrada controlada para registrar uma thread
tecnica a partir do recorte ativo do engenheiro.

Essa fase nao altera a engine Python, filtros, queries, exportacao, dashboard,
matematica eletrica ou persistencia operacional de medicoes.

## Superficie

O Desktop passa a expor a acao:

```text
Comentar este recorte
```

Ela fica no painel de resultados/exportacao, perto do contexto onde o engenheiro
normalmente percebe uma divergencia.

## Fluxo

1. O usuario seleciona um recorte tecnico no ANDY.
2. O usuario abre "Comentar este recorte".
3. O dialogo solicita:
   - titulo;
   - severidade;
   - dominio do problema;
   - comentario.
4. O ANDY cria uma `AndyThreadReference` a partir dos filtros ativos.
5. O ANDY grava a thread no SQLite local do runtime.
6. O ANDY mostra ID, referencia e caminho do store local.

## Store local

O store fica sob o workspace do runtime:

```text
<runtime workspace>/ANDY_THREADS/threads.sqlite
```

Em testes e checks locais, o store fica sob:

```text
.validation_tmp/andy_threads_desktop_entrypoint/
```

## Garantias

- Nao salva DataFrame.
- Nao salva valores brutos das medicoes.
- Nao escreve na fonte corporativa.
- Nao chama provider real.
- Nao envia notificacao.
- Nao altera dados de exportacao.
- Nao muda regra analitica.

## Validacao de contexto

A thread exige ao menos uma referencia tecnica ativa, como:

- ano;
- mes;
- SE;
- BAY/alimentador;
- equipamento;
- terminal;
- variavel;
- cadencia;
- ponto.

Sem recorte tecnico, o Desktop rejeita a criacao da thread.

## Arquivos

- `desktop_app/thread_service.py`
- `desktop_app/main_window.py`
- `scripts/check_andy_threads_desktop_entrypoint.py`
- `tests/test_desktop_thread_service.py`

## Limites atuais

Esta fase entrega apenas a entrada controlada.

Ainda falta:

- painel de historico por recorte;
- busca/listagem de threads no Desktop;
- decisao visivel no fluxo;
- SLA visual;
- export completo da thread pela UI;
- integracao futura com notificacoes, se aprovada.
