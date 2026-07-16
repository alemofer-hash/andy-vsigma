# Sentinela

Esta pasta marca a mudanca de fase do produto antes chamado ANDY para **Sentinela 1.0**.

A partir desta versao, o produto desktop passa a se chamar Sentinela porque incorporou, no fluxo operacional do dashboard, a deteccao de inversao de fluxo e candidatos de manobra/transferencia entre alimentadores.

Regras desta pasta:

- guardar apenas metadados, notas de versao e referencias publicaveis das versoes do Sentinela;
- nao armazenar dados reais, exports, logs, DuckDB, Parquet, credenciais ou runtime;
- manter instaladores e artefatos pesados em `artifacts/`, seguindo a politica de hygiene do repositorio;
- preservar a engine Python como fonte da verdade analitica.

O runtime local historico ainda pode manter compatibilidade com caminhos antigos em `%LOCALAPPDATA%\ANDY` ate existir uma migracao revisada e segura de dados locais.
