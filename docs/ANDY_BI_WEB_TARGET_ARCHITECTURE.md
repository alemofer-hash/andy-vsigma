# ANDY BI Web Target Architecture

## Arquitetura alvo

```mermaid
flowchart TD
    A["Fontes corporativas autorizadas / read-only"] --> B["ANDY Python Engine"]
    B --> C["Indexacao / Normalizacao / Parquet / DuckDB"]
    C --> D["Analise eletrica / Patamar / Fluxo P-Q / Qualidade / Auditoria"]
    D --> E["ANDY BI Dataset Builder"]
    E --> F["Data Contract + Manifest + Hash + Lote + Versao"]
    F --> G["Dataset governado para BI corporativo"]
    G --> H["Semantic Model: fatos + dimensoes + medidas seguras"]
    H --> I["RLS/ABAC via grupos corporativos"]
    I --> J["BI Web App: cockpit, filtros, patamar, fluxo, auditoria"]
    J --> K["Usuario corporativo via login/SSO/licenca existente"]
```

## Leis de arquitetura

- O BI nao acessa fonte bruta diretamente.
- O BI nao monta regra analitica critica.
- O BI consome dataset publicado pelo ANDY.
- O BI pode agregar valores precomputados, mas nao recalcular MVA, FP, MW,
  fluxo P/Q, inversao ou patamar sem teste de paridade.
- Toda publicacao tem lote, hash, schema version, periodo e audit trail.
- Provedor real de identidade so entra por configuracao privada revisada.

## Componentes criados nesta fase

- `andy_bi.data_contract`: contrato versionavel do dataset.
- `andy_bi.dataset_builder`: gerador local governado com fallback sintetico.
- `andy_bi.semantic_model`: relacoes e medidas seguras.
- `andy_bi.rls_policy`: politica deny-by-default para RLS/ABAC.
- `andy_bi.parity`: comparacao de dataset/desktop/XLSX em nivel de resumo.
- `andy_bi.refresh_plan`: contrato de refresh sem gateway real.
- `andy_bi.export_package`: pacote local para revisao de TI/BI.

## Estado atual

Esta arquitetura esta preparada para Dev/Homolog, mas nao publica em ambiente
corporativo. A publicacao depende de workspace, gateway, owners, grupos e
configuracoes privadas aprovadas.
