# ANDY Threads Future Boundaries

## Objetivo

Mitigar o risco de implementar recursos futuros do ANDY Threads sem aceite
formal. Esta fase entrega apenas fundacao local. Store corporativo
multiusuario, UI PySide6, API local e notificacoes ficam bloqueados por gate.

## Boundary config

- `config/andy_threads_future_boundaries.example.json`

Esse arquivo publico deve manter:

- `mvp_mode=true`;
- `real_identity_provider_enabled=false`;
- `corporate_multiuser_store.enabled=false`;
- `pyside_desktop_ui.enabled=false`;
- `local_api.enabled=false`;
- `notifications.enabled=false`;
- `attachments.enabled=false`.

## Validador

```powershell
.\.venv\Scripts\python.exe scripts\check_andy_threads_future_boundaries.py
```

## Store corporativo multiusuario

So pode avancar apos:

- arquitetura aprovada por TI;
- owner de seguranca;
- dono do dado;
- RLS/ABAC corporativo;
- estrategia de retencao;
- threat model;
- backup/restore;
- trilha de auditoria.

## UI PySide6

So pode avancar apos:

- aceite visual;
- aceite do fluxo "Comentar este recorte";
- prova de que filtros/export/analise nao foram alterados;
- smoke test manual;
- teste de adapter de contexto.

## API local

So pode avancar apos:

- threat model;
- default loopback/local;
- autenticacao/authorization boundary;
- logs redigidos;
- testes de negacao.

## Notificacoes

Notificacoes Teams/Outlook, quando existirem, sao apenas alerta. Elas nao viram
fonte da verdade. A decisao final deve voltar para o ANDY Threads.

## Anexos

Anexos ficam fora do MVP ate DLP, retencao, malware scanning e politica de
classificacao de dados serem definidos.
