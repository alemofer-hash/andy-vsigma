# ANDY BI-4 Report - Private Corporate Config Intake

Data: 2026-07-07

## Resumo executivo

Foi criada uma camada offline de intake seguro para configuracoes corporativas privadas. O foco foi preparar o ANDY para receber dados da TI usando criterios HTTPS/TLS, sem conectar em rede e sem expor dados sensiveis.

## Criado

- `andy_bi/https_security.py`
- `config/andy_bi_corporate_intake.example.json`
- `scripts/check_andy_bi_corporate_intake.py`
- `tests/test_andy_bi_corporate_intake.py`
- `docs/ANDY_BI_4_PRIVATE_CORPORATE_CONFIG_INTAKE.md`

## Regras implementadas

- HTTPS obrigatorio para endpoints corporativos.
- LDAPS obrigatorio para LDAP.
- HTTP somente para redirect localhost.
- TLS certificate verification obrigatoria.
- Self-signed bloqueado por padrao.
- Segredos em config bloqueados.
- Reports redigidos.

## Residuo proposital

- Nao ha validacao remota de certificado.
- Nao ha chamada de rede.
- Nao ha provider real habilitado.
- Nao ha segredo configurado.

## Proxima fase recomendada

**ANDY BI-5 - Redacted Private Config Dry Run**

Validar um arquivo privado real fornecido pela TI, ainda sem conectar em rede, gerando apenas relatorio redigido.
