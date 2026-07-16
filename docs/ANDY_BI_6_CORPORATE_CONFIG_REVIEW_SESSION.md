# ANDY BI-6 Corporate Config Review Session

Data: 2026-07-07

## Objetivo

Revisar, de forma redigida e offline, se o ANDY esta pronto para receber uma configuracao corporativa privada antes de qualquer implementacao real de IdP, tenant policy, fonte corporativa ou auditoria remota.

## Escopo

Esta revisao combina:

- readiness dos templates BI;
- protecao de arquivos privados no Git;
- validacao offline de HTTPS/TLS;
- dry-run de configuracao privada;
- relatorio redigido para revisao humana.

## Comando

```powershell
.\.venv\Scripts\python.exe scripts\check_andy_bi_corporate_config_review.py
```

Com arquivo privado especifico:

```powershell
.\.venv\Scripts\python.exe scripts\check_andy_bi_corporate_config_review.py --config config\andy_bi_corporate_intake.private.json
```

Modo estrito:

```powershell
.\.venv\Scripts\python.exe scripts\check_andy_bi_corporate_config_review.py --config config\andy_bi_corporate_intake.private.json --strict
```

## Decisoes possiveis

- `waiting_for_private_config`: ambiente preparado, mas ainda sem dados privados reais da TI.
- `ready_for_human_security_review`: arquivo privado passou no dry-run redigido e deve ser revisado por humano antes de qualquer provider real.
- `blocked`: readiness, HTTPS/TLS, protecao de segredo ou redacao falhou.

## O que a revisao nao faz

- nao conecta em rede;
- nao chama IdP;
- nao autentica usuario;
- nao valida certificado remoto;
- nao imprime endpoint real;
- nao imprime host real;
- nao imprime segredo;
- nao ativa enforcement operacional real;
- nao altera engine analitica;
- nao altera exportacao.

## Saidas

- `reports/ANDY_BI_CORPORATE_CONFIG_REVIEW.md`
- `reports/ANDY_BI_CORPORATE_CONFIG_REVIEW.json`

## Politica de revisao humana

Mesmo quando o status for `ready_for_human_security_review`, o proximo passo nao e implementar automaticamente. Um revisor humano deve confirmar:

- se o tipo de IdP esta correto;
- se os endpoints pertencem ao dominio corporativo aprovado;
- se o fluxo de certificado/TLS atende a politica interna;
- se nenhum segredo foi colocado em arquivo local;
- se os grupos/claims necessarios existem;
- se a politica por distribuidora/estado esta clara;
- se auditoria e exportacao possuem destino aprovado.

## Estado atual esperado

Sem `config/andy_bi_corporate_intake.private.json`, o status correto e:

```text
waiting_for_private_config
```

Isso significa que o ANDY esta pronto para receber a configuracao privada, mas nenhuma revisao de provider real foi aprovada ainda.
