# ANDY Threads Engineering Emergency Gap Analysis

## Objetivo

Mapear o que ainda falta para o ANDY Threads se tornar um sistema eficiente de
comunicacao tecnica em ambiente de engenharia emergencial, especialmente nos
casos em que softwares, dashboards, exports e analises dependem de parametros
eletricos corretos.

## Diagnostico

Hoje o maior atraso nao esta apenas no calculo. O atraso aparece quando uma
duvida tecnica perde contexto:

- qual recorte foi usado;
- qual fonte/lote estava ativo;
- qual SE, alimentador, equipamento, terminal ou variavel esta em discussao;
- se o problema e de medicao, cadastro, operacao, BI, export, runtime ou regra
  analitica;
- quem e o dono correto;
- quem precisa ser consultado;
- qual decisao encerra a discussao.

O ANDY Threads deve reduzir esse atraso fazendo a conversa nascer com contexto
tecnico, dono, severidade, SLA, evidencia e decisao.

## Status atual

Readiness estimado:

```text
status=MVP_FOUNDATION_READY
readiness_percent=50.0
score=50/100
routes=8
slas=5
```

Interpretacao:

- ja existe fundacao de dominio;
- ja existe referencia tecnica obrigatoria;
- ja existe policy deny-by-default;
- ja existe SQLite local MVP;
- ja existe audit/redaction;
- ja existe taxonomia emergencial;
- ainda falta superficie de uso no fluxo real do engenheiro.

## Gaps por capacidade

| Capacidade | Status | Por que importa | Proximo passo |
|---|---|---|---|
| Referencia tecnica obrigatoria | pronto | impede chat solto | preservar contrato |
| Roteamento por setor | pronto inicial | evita mandar problema ao dono errado | validar com setores |
| Policy local | pronto inicial | evita leitura/export sem escopo | manter deny-by-default |
| Store local SQLite | pronto MVP | permite historico local | definir retencao e backup |
| Auditoria/redaction | pronto inicial | reduz risco de vazamento | expandir quando entrar UI |
| Taxonomia emergencial | pronto inicial | padroniza severidade e SLA | revisar termos com Engenharia |
| Botao "Comentar este recorte" | pendente | tira friccao do uso real | implementar no Desktop PySide6 |
| Painel de threads do recorte | pendente | mostra historico e decisao sem procurar | implementar painel lateral |
| Aceite setorial | pendente | evita matriz errada virar processo | coletar aceite privado |
| Runbook operacional | pendente | define como agir em emergencia | executar tabletop drill |
| Notificacoes | bloqueado | pode reduzir tempo de resposta | depende provider corporativo |
| Store corporativo multiusuario | bloqueado | necessario para escala | depende arquitetura/seguranca |

## Principais causas de delay que o ANDY Threads deve atacar

1. `MISSING_CONTEXT`: falta de recorte tecnico completo.
2. `WRONG_OWNER`: problema cai no setor errado.
3. `UNVERIFIED_PARAMETER`: parametro eletrico sem confirmacao.
4. `AMBIGUOUS_CADASTRE`: terminal/equipamento/alimentador ambiguo.
5. `DATASET_OR_REFRESH_ISSUE`: dado ou refresh desatualizado.
6. `TOOL_RUNTIME_FAILURE`: ferramenta falha e a evidencia se perde.
7. `NO_DECISION_RECORD`: decisao fica em conversa externa.
8. `NO_ESCALATION_PATH`: ninguem sabe quando escalar.

## Conclusao

O ANDY Threads esta pronto como fundacao tecnica, mas ainda nao e uma ferramenta
eficiente de emergencia porque falta o ponto de entrada ergonomico no fluxo real
do engenheiro. A prioridade nao e BI nem WPF nativo agora; e encurtar o caminho:

```text
recorte tecnico -> thread -> dono correto -> evidencia -> decisao -> historico
```
