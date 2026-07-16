# ANDY BI-5 Redacted Private Config Dry Run

Data: 2026-07-07

## Objetivo

Validar um arquivo privado real de configuracao corporativa antes de qualquer conexao remota, mantendo relatorio redigido e sem expor URL, host, path, senha, token ou segredo.

## Comando

```powershell
.\.venv\Scripts\python.exe scripts\check_andy_bi_private_config_dry_run.py --config config\andy_bi_corporate_intake.private.json
```

Modo estrito:

```powershell
.\.venv\Scripts\python.exe scripts\check_andy_bi_private_config_dry_run.py --config config\andy_bi_corporate_intake.private.json --strict
```

## O que valida

- arquivo privado existe;
- JSON e objeto valido;
- arquivo privado nao esta versionado;
- arquivo privado esta ignorado pelo Git quando dentro do repo;
- secoes `identity_provider` e `https_security` existem;
- regras HTTPS/TLS passam;
- endpoint summaries ficam redigidos;
- relatorio nao imprime URLs cruas.

## O que nao faz

- nao conecta em rede;
- nao valida certificado remoto;
- nao autentica usuario;
- nao chama IdP;
- nao ativa enforcement operacional;
- nao altera engine analitica.

## Saidas

- `reports/ANDY_BI_PRIVATE_CONFIG_DRY_RUN.md`
- `reports/ANDY_BI_PRIVATE_CONFIG_DRY_RUN.json`

## Estado esperado sem arquivo privado

Sem `config/andy_bi_corporate_intake.private.json`, o gate retorna:

```text
waiting_for_private_config
```

Isso e esperado ate a TI fornecer os dados oficiais.
