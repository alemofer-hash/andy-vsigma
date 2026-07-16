# ANDY Threads Implementation Report

Data-base: 2026-07-13

## Status

GO local.

O nucleo ANDY Threads/Ocorrencias foi restaurado como pacote versionavel
do produto, com dominio Python, store local, auditoria, policy,
ocorrencias, feedback humano tipo CAPTCHA, candidatos de eventos,
servico desktop para criar thread a partir de recorte tecnico e pacotes
Markdown sinteticos para revisao humana.

## Escopo implementado

- Pacote `andy_threads/` com modelos de dominio, referencias tecnicas,
  roteamento setorial, responsabilidade, politica de acesso, store local,
  auditoria, ocorrencias, intencao de notificacao, feedback humano e
  candidatos de evento.
- Configuracoes example `config/andy_threads_*.example.json`.
- Servico local `desktop_app/thread_service.py` para criar threads a
  partir de filtros/recortes do desktop sem acoplar a UI critica.
- Scripts de readiness, policy, store, ocorrencias, feedback, eventos,
  aceite setorial e demos sinteticas.
- Testes unitarios e checks operacionais para Threads.
- Documentacao de produto, contrato de dados, politica, roadmap,
  playbook emergencial, revisao humana, cenarios setoriais e limites de
  deteccao de manobras.

## Invariantes preservados

- A engine Python do ANDY continua sendo a fonte da verdade analitica.
- Nenhuma matematica eletrica critica foi movida para Threads.
- Threads nao altera ingestao, catalogo, filtros, parquet, DuckDB,
  analise eletrica, patamar, fluxo P/Q ou exportacao.
- Provider real permanece desligado.
- Notificacoes sao `NotificationIntent`, nao envio automatico.
- Dados reais nao sao usados nos testes ou demos.
- Outputs de demo ficam sob `.validation_tmp/`.
- Feedback humano vira label auditavel, mas nao treina modelo nem aplica
  decisao operacional automaticamente.
- Manobra/inversao sem SCADA ou evidencia operacional permanece
  candidato/revisao, nao evento confirmado.
- Politica de acesso e deny-by-default.
- Secrets, tokens, paths locais e UNC sao redigidos nos payloads de
  auditoria/exports.

## Validacoes executadas

```text
py -3.12 -m compileall -q andy_threads desktop_app\thread_service.py scripts\check_andy_threads_*.py scripts\run_andy_threads_*.py
py -3.12 scripts\check_andy_threads_readiness.py
py -3.12 -m pytest -q <19 arquivos tests/test_andy_threads_*.py>
```

Resultado:

```text
ANDY Threads readiness: passed
real_provider_enabled=false
store_scope=.validation_tmp
79 passed
```

## Residuos intencionais

- UI PySide6 completa para Threads ainda nao foi ativada como tela
  operacional. Existe servico desktop local para recorte tecnico.
- Store corporativo multiusuario ainda nao foi ativado.
- API local/corporativa ainda nao foi ativada.
- Notificacoes reais por e-mail/Teams/Outlook continuam desligadas.
- Matriz setorial real ainda requer revisao humana com Engenharia,
  Operacao, Medicao, Cadastro, SCADA, Obras, TI/BI e Gestao.

Esses residuos sao limites de seguranca, nao falhas do nucleo local.

## Proximo passo recomendado

1. Revisar os cinco cenarios sinteticos com Engenharia/Operacao.
2. Validar linguagem de ocorrencia, encaminhamento e setores.
3. Aprovar ou ajustar a matriz setorial.
4. So depois disso ativar UI desktop, store corporativo e provider real
   sob configuracao privada revisada.
