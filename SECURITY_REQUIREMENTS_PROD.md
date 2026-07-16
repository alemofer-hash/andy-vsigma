# Security Requirements for Production

## 1. Objetivo
Este documento define os requisitos de seguranca para promover o aplicativo Andy's para producao corporativa, com foco em:
- protecao de dados sensiveis em transito e em repouso;
- prevencao de vazamento e exposicao indevida;
- reducao de superficie de ataque e risco de invasoes;
- rastreabilidade, resposta a incidentes e conformidade.

## 2. Escopo
- Aplicacao `andys_table_app.py` (Streamlit).
- Componentes de leitura e geracao de relatorios (`duckdb`, exportacao CSV/XLSX).
- Infraestrutura de execucao (servidor, rede, proxy reverso, autenticacao e observabilidade).

## 3. Premissas de Ameaca
- Usuario malicioso autenticado tentando exfiltrar dados.
- Tentativa de injecao SQL e abuso de filtros/inputs.
- Interceptacao de trafego em rede.
- Exposicao acidental de paths, mensagens de erro, stack traces e detalhes internos.
- Comprometimento por dependencia vulneravel.

## 4. Requisitos Obrigatorios

### 4.1 Transito de Dados
1. Todo trafego externo deve usar HTTPS com TLS 1.2+ (preferencia TLS 1.3).
2. Servidor Streamlit nao deve ser exposto diretamente na internet; usar proxy reverso com TLS.
3. HSTS habilitado no proxy.
4. Desabilitar ciphers e protocolos legados.
5. Trafego entre zonas de rede distintas deve usar canal protegido (TLS/mTLS conforme arquitetura).

### 4.2 Autenticacao e Autorizacao
1. Integracao com IdP corporativo (OIDC/SAML).
2. RBAC minimo: `viewer`, `exporter`, `admin`.
3. Menor privilegio para conta de execucao, sistema de arquivos e banco.
4. Timeout de sessao e revogacao de acesso.

### 4.3 Protecao de Dados e Privacidade
1. Classificacao de dados por sensibilidade.
2. Mascaramento de campos sensiveis quando aplicavel.
3. Logs sem dados pessoais/sensiveis em texto claro.
4. Politica de retencao para arquivos exportados.
5. Criptografia em repouso para volumes e backups.

### 4.4 Aplicacao Segura
1. SQL com parametros bind; proibido concatenar entrada de usuario em query.
2. Ordenacao e campos dinamicos somente por allowlist.
3. Em producao, nao exibir SQL interno, stack trace ou paths sensiveis na interface.
4. Configuracao sensivel por variaveis de ambiente/secret manager.
5. Validacao estrita de entradas (tipo, formato, intervalo e tamanho).

### 4.5 Infraestrutura e Operacao
1. Segmentacao de rede e firewall.
2. WAF/rate limiting no perimetro aplicavel.
3. Sistema operacional atualizado e hardening baseline.
4. Execucao com usuario sem privilegio administrativo.
5. Backups com teste de restauracao periodico.

### 4.6 Monitoramento e Resposta
1. Log centralizado com correlacao de usuario, horario e acao.
2. Auditoria obrigatoria para exportacoes (quem, quando, volume, filtro aplicado).
3. Alertas para padroes anomalos de acesso/exportacao.
4. Playbook de resposta a incidente e cadeia de escalonamento.

### 4.7 Supply Chain e Qualidade
1. Dependencias com versoes fixas e inventario (SBOM recomendado).
2. SAST, SCA e secret scanning no CI.
3. Atualizacao de dependencias com avaliacao de CVE.
4. Revisao de codigo obrigatoria para mudancas em seguranca.

## 5. Mudancas Minimas Necessarias no Aplicativo
1. Ativar modo producao por variavel de ambiente.
2. Bloquear configuracao livre de paths via UI em producao.
3. Usar SQL parametrizado para filtros e paginacao.
4. Restringir `ORDER BY` por allowlist.
5. Remover debug sensivel da tela em producao.
6. Sanitizar mensagens de erro para usuario final.

## 6. Variaveis de Ambiente Recomendadas
- `ANDYS_ENV=prod`
- `ANDYS_DB_PATH=<path absoluto do duckdb>`
- `ANDYS_EXPORT_DIR=<path absoluto para exportacao>`
- `ANDYS_ALLOWED_ROOT=<raiz permitida para db/export>`

Opcional (infra):
- `ANDYS_LOG_LEVEL=INFO`
- `ANDYS_AUDIT_LOG_PATH=<path do log de auditoria>`

## 7. Criterios de Aceite (Security Gate)
1. Todo acesso externo via HTTPS valido.
2. Sem exibicao de SQL/stack trace/path sensivel em producao.
3. Queries de tela e exportacao usando parametros bind.
4. RBAC ativo e testado com IdP corporativo.
5. Auditoria de exportacao habilitada e consultavel.
6. Sem vulnerabilidades criticas abertas no scan de dependencias.
7. Restore de backup testado e documentado.

## 8. Plano de Implantacao

### Fase 1 (Imediata)
- Hardening no codigo (P0): SQL parametrizado, modo producao, supressao de debug sensivel.
- Publicacao atras de proxy HTTPS interno.

### Fase 2 (Curto Prazo)
- Integracao SSO e RBAC.
- Auditoria de exportacao e monitoramento SIEM.
- Politica de retencao e limpeza automatica de exportacoes.

### Fase 3 (Maturidade)
- Pentest periodico.
- Automacao completa de seguranca no CI/CD.
- Revisao periodica de privilegios e conformidade.
