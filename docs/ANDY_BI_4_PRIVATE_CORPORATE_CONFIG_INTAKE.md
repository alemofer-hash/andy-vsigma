# ANDY BI-4 Private Corporate Config Intake

Data: 2026-07-07

## Objetivo

Preparar a entrada segura de configuracoes corporativas privadas, adotando os protocolos de seguranca do ANDY dentro de HTTPS/TLS antes de qualquer integracao real.

## Regra central

O intake valida contrato, nao conecta em rede.

Ele deve:

- exigir `https://` para OIDC, SAML metadata, catalogo e auditoria;
- exigir `ldaps://` para LDAP;
- permitir `http://localhost` apenas para redirect local de app desktop;
- exigir verificacao de certificado TLS;
- bloquear certificado self-signed por padrao;
- bloquear segredo, senha, token e private key em arquivo de config;
- redigir hostnames, URLs e paths nos reports.

## Arquivos

- `config/andy_bi_corporate_intake.example.json`
- `andy_bi/https_security.py`
- `scripts/check_andy_bi_corporate_intake.py`
- `tests/test_andy_bi_corporate_intake.py`

## Arquivo privado futuro

Quando a TI fornecer dados oficiais:

```powershell
Copy-Item config\andy_bi_corporate_intake.example.json config\andy_bi_corporate_intake.private.json
```

Editar apenas o arquivo privado, que fica ignorado pelo Git.

## Saida de relatorio

O gate gera:

- `reports/ANDY_BI_CORPORATE_INTAKE.md`
- `reports/ANDY_BI_CORPORATE_INTAKE.json`

O report nao imprime hostname, URL completa, segredo, token, path real ou usuario real.

## Limites

- Sem IdP real.
- Sem chamada HTTPS real.
- Sem teste de certificado remoto.
- Sem login.
- Sem ativar enforcement operacional.
- Sem alterar engine analitica.
