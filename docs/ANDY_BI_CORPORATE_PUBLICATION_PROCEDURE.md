# ANDY BI Corporate Publication Procedure

## Objetivo

Publicar o dataset/semantic model do ANDY em BI corporativo sem criar login
proprio, sem publicar automaticamente e sem expor dados sem RLS/ABAC.

## Procedimento

1. Confirmar a plataforma BI oficial.
2. Confirmar workspace Dev, Homolog e Prod.
3. Confirmar gateway ou mecanismo de refresh.
4. Confirmar owner funcional.
5. Confirmar owner tecnico.
6. Confirmar dono do dado.
7. Confirmar aprovador de seguranca.
8. Confirmar grupos corporativos.
9. Confirmar politica RLS/ABAC.
10. Criar dataset ANDY BI em Dev.
11. Publicar semantic model em Dev.
12. Validar com dataset sintetico/redigido.
13. Validar contra XLSX/desktop do ANDY.
14. Homologar com engenharia.
15. Publicar app interno.
16. Operar refresh, logs, rollback e suporte.

## Pre-condicoes bloqueantes

- RLS/ABAC aprovado.
- Workspace privado.
- Owner funcional e tecnico definidos.
- Configuracao privada revisada.
- Paridade contra ANDY aprovada.
- Nenhum segredo em repositorio.
- Nenhum dataset real em artefato versionavel.

## Comandos locais de preparacao

```powershell
.\.venv\Scripts\python.exe scripts\build_andy_bi_dataset.py --format both --out artifacts\andy_bi_dataset --synthetic
.\.venv\Scripts\python.exe scripts\check_andy_bi_publication_package.py
```

Nenhum comando acima publica no BI corporativo.
