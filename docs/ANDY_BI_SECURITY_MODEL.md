# ANDY BI Security Model

Data: 2026-07-07

## Principios

- Senha nunca entra no ANDY.
- Token e sessao devem expirar.
- Exportacao exige identidade resolvida.
- Consulta passa por policy antes de acessar dados.
- Logs nao devem expor valores sensiveis ou paths privados completos.
- Arquivos privados ficam fora do Git.
- Dados reais nao entram em fixtures.

## Fluxo alvo

```text
Usuario
-> Provedor corporativo
-> token/claims
-> ANDY policy resolver
-> query autorizada
-> dashboard/export
-> HERMES audit
```

## Controles obrigatorios

- `default_decision = deny`.
- RBAC por papel.
- ABAC por estado/distribuidora/fonte.
- Redacao de paths e claims sensiveis em reports.
- Hash/manifest para exports relevantes.
- Suporte bundle sem dado operacional real.

## Eventos de auditoria

- login iniciado;
- login concluido;
- falha de autenticacao;
- fonte listada;
- consulta executada;
- filtro aplicado;
- export gerado;
- acesso negado;
- erro de policy;
- suporte bundle gerado.

## Riscos

| Risco | Severidade | Mitigacao |
|---|---|---|
| Senha persistida | Critica | SSO/token; checker bloqueia segredo em config |
| Usuario acessa outra distribuidora | Critica | Policy deny-by-default e testes de negacao |
| Export sem trilha | Alta | Export policy exige evento HERMES |
| Caminho real em Git | Alta | Templates example e .gitignore privado |
| Token tratado como verdade eterna | Alta | expiracao, refresh controlado e logout |

## Status desta fase

Preparado para configuracao futura. Nenhuma autenticacao real esta ativa.
