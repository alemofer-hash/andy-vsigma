# ANDY BI Product Charter

Data: 2026-07-07

## Objetivo

Preparar o ANDY para evoluir de ferramenta desktop de engenharia para BI corporativo do dominio eletrico, com governanca por usuario, distribuidora, estado, fonte e exportacao.

Esta fase nao implementa login real, nao conecta em rede corporativa e nao altera a engine analitica. Ela deixa contratos, templates e gates prontos para quando as informacoes oficiais forem recebidas.

## Produto alvo

O ANDY BI deve permitir:

- autenticar funcionarios por identidade corporativa;
- limitar escopo por distribuidora e estado;
- consultar catalogo e medicoes autorizadas;
- aplicar filtros cascatais;
- visualizar dashboards eletricos;
- gerar XLSX governado;
- registrar auditoria de consulta e exportacao.

## Decisoes abertas

- Provedor de identidade: OIDC, SAML, Kerberos ou LDAP.
- Modelo de distribuicao: desktop governado, web interno ou hibrido.
- Fonte oficial de grupos/perfis.
- Fonte oficial de catalogo multi-distribuidora.
- Destino oficial da trilha HERMES/auditoria.
- Politica de exportacao por perfil.

## Nao objetivos

- Armazenar senha de funcionario.
- Criar cadastro paralelo de usuarios.
- Conectar em rede real sem dados aprovados.
- Alterar calculos eletricos existentes.
- Publicar dados reais em fixtures, exemplos ou repositorio.

## Gates antes de implementar

- TI aprova modelo de identidade.
- Seguranca aprova modelo de token e logs.
- Engenharia aprova perfis de distribuidora.
- Produto aprova escopo piloto.
- Repositorio passa no gate `scripts/check_andy_bi_readiness.py`.
