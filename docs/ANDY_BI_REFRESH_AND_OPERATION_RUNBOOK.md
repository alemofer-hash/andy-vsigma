# ANDY BI Refresh and Operation Runbook

## Modos de refresh

- Manual: geracao sob demanda por operador autorizado.
- Agendado: definido no workspace corporativo depois da aprovacao.
- Incremental: por lote, fonte, ano/mes ou periodo.

## Regras

- Rebuild total apenas quando necessario.
- Publicacao automatica fica desativada nesta fase.
- Refresh real depende de gateway/config privada.
- Catalogo stale bloqueia publicacao quando a politica exigir.
- Todo lote deve ter manifest, hash, periodo, schema version e validation status.

## Rollback

1. Identificar lote anterior aprovado.
2. Validar manifest e hash.
3. Reverter semantic model/dataset no workspace conforme politica BI.
4. Registrar evento de rollback.
5. Comunicar owner funcional e tecnico.

## Suporte

- Conferir `manifest.json`.
- Conferir `validation_report.md`.
- Conferir paridade.
- Conferir RLS/ABAC.
- Conferir refresh/gateway.
- Abrir finding quando houver divergencia critica.
