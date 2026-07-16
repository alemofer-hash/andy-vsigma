# Frontend ANDY

Documentacao operacional do frontend do ANDY, com foco no aplicativo desktop PySide6 que hoje e a superficie primaria do produto.

Este README cobre:
- entrypoints e fluxo de boot;
- arquitetura do frontend;
- design system e identidade visual;
- telas e secoes principais;
- integracao com runtime, query e export;
- splash screen, icones e branding;
- testes, smoke e rebuild.

## 1. Escopo

O frontend principal do ANDY e o desktop nativo:
- entrypoint: [desktop_andy.py](/C:/Users/G05835236/Downloads/ANDY/desktop_andy.py)
- shell, layout, filtros e export: [main_window.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/main_window.py)
- tema visual da familia de apps: [theme.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/theme.py)
- splash cinematica: [splash.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/splash.py)
- icone e branding em runtime: [app_icon.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/app_icon.py)

Superficie secundaria:
- [andys_table_app.py](/C:/Users/G05835236/Downloads/ANDY/andys_table_app.py) continua existindo como UI de apoio para engenharia/dev, mas nao e a superficie operacional primaria.

## 2. Mapa rapido do frontend

Arquivos principais:
- [desktop_andy.py](/C:/Users/G05835236/Downloads/ANDY/desktop_andy.py): entrypoint do executavel desktop, erro amigavel de startup e AppUserModelID do Windows.
- [main_window.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/main_window.py): `AndyDesktopWindow`, splash bootstrap, setup page, cockpit principal, filtros, tabela, export e acoes de manutencao.
- [theme.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/theme.py): tokens visuais, palette Qt, stylesheet global e helpers de polish.
- [splash.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/splash.py): tela de ignicao premium com estagios reais de boot.
- [app_icon.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/app_icon.py): resolucao do `andy_vsigma.ico` em dev e no bundle empacotado.
- [runtime.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/runtime.py): adaptador do frontend para runtime local, bootstrap, source mode, cache compartilhado e reindex.
- [query_service.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/query_service.py): leitura do DuckDB para overview, filtros, pagina, recorte completo e pontos do XLSX.
- [export_service.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/export_service.py): CSV LONG, CSV WIDE, dashboard XLSX e auditoria pre-export.
- [filter_flow.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/filter_flow.py): semantica da cascata Ano -> Mes -> SE -> BAY -> Equipamento -> Terminal -> Dia -> Variaveis.
- [models.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/models.py): contratos de estado (`DesktopRuntimeState`, `QueryFilters`, `PageResult`, `ExportOptions`).
- [qt_models.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/qt_models.py): adaptador de DataFrame para `QTableView`.

## 3. Arquitetura do frontend

O frontend desktop segue uma arquitetura em 4 camadas:

1. Entry / bootstrap
- [desktop_andy.py](/C:/Users/G05835236/Downloads/ANDY/desktop_andy.py)
- define `WINDOWS_APP_USER_MODEL_ID`;
- captura erros muito cedo;
- abre dialogo nativo do Windows quando o startup falha.

2. Shell visual e fluxo de tela
- [main_window.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/main_window.py)
- monta toolbar, status bar, setup page, main page, secoes, tabela, exports e acoes.

3. Services de aplicacao
- [runtime.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/runtime.py)
- [query_service.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/query_service.py)
- [export_service.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/export_service.py)

4. Design system e branding
- [theme.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/theme.py)
- [splash.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/splash.py)
- [app_icon.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/app_icon.py)
- assets em [assets/icons](/C:/Users/G05835236/Downloads/ANDY/assets/icons)

Regra importante:
- `main_window.py` orquestra UX e estado visual;
- `query_service.py` e `export_service.py` concentram comportamento de dados;
- tema, splash e icone nao devem carregar logica de negocio.

## 4. Fluxo de boot

Fluxo atual:
1. [desktop_andy.py](/C:/Users/G05835236/Downloads/ANDY/desktop_andy.py) define AppUserModelID.
2. O app carrega [main_window.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/main_window.py).
3. `main()` cria `QApplication`, define nome do app, aplica tema e icone.
4. `bootstrap_desktop_window()` mostra [AndySplashScreen](/C:/Users/G05835236/Downloads/ANDY/desktop_app/splash.py).
5. A splash percorre estagios reais:
   - aquecendo runtime blindado;
   - forjando cockpit operacional;
   - sincronizando catalogo e interface;
   - pronto para entrar.
6. A janela principal aparece e a splash fecha com fade.

Regras do boot:
- nao ha atraso fake;
- em ambiente rapido, a splash respeita um minimo curto para nao piscar;
- em ambiente lento, ela acompanha o startup real;
- em erro, mostra estado de falha em vez de sumir silenciosamente.

## 5. Design system da familia de apps

O frontend desktop ja incorpora o design system da familia ANDY.

Nucleo visual:
- fundo `obsidian/steel blue`;
- energia `electric cyan`;
- contrastes tecnicos com prata e aco;
- secoes robustas, premium e controladas;
- sem visual gamer, sem glow exagerado.

Tokens principais em [theme.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/theme.py):
- cores: `bg_canvas`, `bg_frame`, `bg_elevated`, `accent_primary`, `accent_bright`, `success`, `warning`, `danger`
- tipografia:
  - corpo: `Segoe UI Variable Text`
  - heading: `Bahnschrift SemiBold`
- roles:
  - `heroPanel`
  - `heroEyebrow`
  - `heroTitle`
  - `heroBody`
  - `statusBadge`
  - `fieldLabel`
  - `valueLabel`
  - `sectionLead`
  - `sectionState`
  - `helpText`
- section metadata:
  - `sectionLevel=primary|secondary`
  - `sectionTone=status|analysis|action|export`
- button variants:
  - `primary`
  - `secondary`
  - `ghost`

Regra de manutencao:
- novos widgets devem entrar via tokens e `polish_widget(...)`;
- evite QSS inline local em componentes isolados;
- mantenha a hierarquia visual consistente com o logo e com o cockpit atual.

## 6. Branding, icone e identidade do app

Assets:
- [andy_vsigma.ico](/C:/Users/G05835236/Downloads/ANDY/assets/icons/andy_vsigma.ico)
- [andy_vsigma.png](/C:/Users/G05835236/Downloads/ANDY/assets/icons/andy_vsigma.png)

O fluxo de icone hoje cobre:
- topo da janela;
- taskbar;
- atalho criado pelo instalador;
- executavel empacotado.

Pontos tecnicos:
- [app_icon.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/app_icon.py) resolve o asset no source tree e no bundle PyInstaller.
- [main_window.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/main_window.py) aplica `setWindowIcon` em `QApplication` e `QMainWindow`.
- [desktop_andy.py](/C:/Users/G05835236/Downloads/ANDY/desktop_andy.py) define AppUserModelID do Windows.
- [andy_launcher.spec](/C:/Users/G05835236/Downloads/ANDY/andy_launcher.spec) embute o `.ico` no exe e tambem carrega o asset no bundle.

Se o Windows continuar mostrando icone antigo apos rebuild:
- desafixe e fixe novamente o app na barra;
- apague o atalho antigo da area de trabalho e deixe o setup recriar;
- reinstale/update o app para atualizar o `.lnk`.

## 7. Telas e secoes

### 7.1 Setup page

Implementada em `_build_setup_page()` em [main_window.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/main_window.py).

Objetivo:
- configurar fonte de dados;
- mostrar runtime local;
- permitir override para pasta local ou retorno a origem corporativa;
- oferecer primeira indexacao e recuperacao segura.

Blocos principais:
- `Fonte de dados`
- `Runtime local`
- acoes de bootstrap/configuracao

### 7.2 Main page

Implementada em `_build_main_page()` em [main_window.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/main_window.py).

Objetivo:
- cockpit operacional principal do ANDY.

Blocos principais:
- hero panel operacional;
- `Status do aplicativo`;
- `Filtros`;
- `Manutencao`;
- `Visao geral`;
- tabela principal com paginacao;
- `Exports`.

### 7.3 Splash screen

Implementada em [splash.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/splash.py).

Caracteristicas:
- frameless, translucida;
- painel central premium;
- orb energetico;
- foguete como simbolo de ignicao;
- barra de progresso elegante;
- fade-out suave;
- estado de erro com destaque claro.

## 8. Filtros e consulta

O frontend nao monta SQL diretamente na janela. Ele converte UI em `QueryFilters` e delega a leitura para [DesktopQueryService](/C:/Users/G05835236/Downloads/ANDY/desktop_app/query_service.py).

Fluxo:
1. `current_filters()` coleta selecoes dos widgets.
2. `refresh_context_options()` / `_refresh_progressive_filters()` recalculam a cascata.
3. `run_query()` executa pagina.
4. `_apply_page_result()` projeta resultado na tabela e atualiza readiness de export.

Capacidades do query service:
- `load_overview()`
- `load_day_options()`
- `query_page()`
- `query_full_long()`
- `resolve_points()`
- `effective_temporal_bounds()`

Regra atual importante:
- export nao deve habilitar so porque o contexto foi resolvido;
- ele habilita quando existe consulta com linhas exportaveis.

## 9. Painel de export e superficie funcional

O painel `Exports` vive em [main_window.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/main_window.py) e usa [DesktopExportService](/C:/Users/G05835236/Downloads/ANDY/desktop_app/export_service.py).

Formatos suportados:
- CSV LONG
- CSV WIDE
- XLSX dashboard

Superficie funcional atual do painel:
- botoes:
  - `Exportar CSV LONG`
  - `Exportar CSV WIDE`
  - `Gerar XLSX dashboard`
- parametros gerais:
  - limite de linhas
  - pretendo abrir no Excel
  - CSV com `DATA/HORA`
- parametros do dashboard XLSX:
  - `Agregacao`
  - `Time floor`
  - `Max timestamps`
  - `Slots de equipamento`
  - `Slots de variavel`
  - XLSX com `DATA/HORA`

Fluxo:
1. usuario resolve o contexto;
2. usuario roda a consulta;
3. `_apply_page_result()` habilita export se houver linhas;
4. o botao chama `export_csv_long()`, `export_csv_wide()` ou `export_xlsx_dashboard()`;
5. o handler monta `ExportOptions`;
6. a auditoria pre-export roda;
7. o app pede path de saida;
8. export e executado em background;
9. sucesso/erro sao projetados no log e em `QMessageBox`.

Regras de negocio:
- XLSX usa `resolve_points()` para derivar pontos do recorte atual;
- meses ou dias precisam estar definidos para export;
- sem pontos validos, o dashboard nao segue;
- a auditoria bloqueia cenarios que excedem limite fisico ou risco forte.

## 10. Runtime e integracao com dados

[DesktopRuntimeService](/C:/Users/G05835236/Downloads/ANDY/desktop_app/runtime.py) e o adaptador entre frontend e runtime instalado.

Principais responsabilidades:
- `load_state()`: estado efetivo do runtime;
- `activate_local_inbox_mode()`: mudar para inbox local explicita;
- `restore_corporate_default_source()`: voltar para a origem corporativa;
- `reindex_current_source()`: reindexar a fonte configurada;
- `sync_shared_snapshot()`: sincronizar cache global.

Contratos do frontend:
- `DesktopRuntimeState`: snapshot do runtime consumido pela UI;
- `QueryFilters`: estado canonico de filtros;
- `PageResult`: pagina da tabela;
- `ExportOptions`: contrato de export e auditoria.

## 11. Estado e principios de UX

Principios que o frontend atual segue:
- abrir rapido e com contexto visual forte;
- manter a UI responsiva durante tasks longas;
- nunca bloquear o usuario sem feedback;
- mostrar mensagens curtas no log interno e no status bar;
- degradar para setup/safe-mode quando o runtime falhar.

Pontos tecnicos importantes:
- `FunctionWorker` encapsula background tasks com `QThread`;
- `_run_background(...)` padroniza busy state e handlers de sucesso/falha;
- `_append_message(...)` registra feedback curto na UI;
- `_set_result_controls_enabled(...)` separa readiness de consulta e readiness de export.

## 12. Testes do frontend

Suites principais:
- [test_desktop_app_icon.py](/C:/Users/G05835236/Downloads/ANDY/tests/test_desktop_app_icon.py)
- [test_desktop_entrypoint.py](/C:/Users/G05835236/Downloads/ANDY/tests/test_desktop_entrypoint.py)
- [test_desktop_export_panel.py](/C:/Users/G05835236/Downloads/ANDY/tests/test_desktop_export_panel.py)
- [test_desktop_export_service.py](/C:/Users/G05835236/Downloads/ANDY/tests/test_desktop_export_service.py)
- [test_desktop_filter_flow.py](/C:/Users/G05835236/Downloads/ANDY/tests/test_desktop_filter_flow.py)
- [test_desktop_filter_widgets.py](/C:/Users/G05835236/Downloads/ANDY/tests/test_desktop_filter_widgets.py)
- [test_desktop_query_service.py](/C:/Users/G05835236/Downloads/ANDY/tests/test_desktop_query_service.py)
- [test_desktop_runtime.py](/C:/Users/G05835236/Downloads/ANDY/tests/test_desktop_runtime.py)
- [test_desktop_splash.py](/C:/Users/G05835236/Downloads/ANDY/tests/test_desktop_splash.py)
- [test_desktop_startup_flow.py](/C:/Users/G05835236/Downloads/ANDY/tests/test_desktop_startup_flow.py)
- [test_desktop_theme.py](/C:/Users/G05835236/Downloads/ANDY/tests/test_desktop_theme.py)
- [test_packaging_spec.py](/C:/Users/G05835236/Downloads/ANDY/tests/test_packaging_spec.py)

Suite curta recomendada para frontend:

```powershell
.\.venv\Scripts\python.exe -m pytest -q `
  tests\test_desktop_app_icon.py `
  tests\test_desktop_entrypoint.py `
  tests\test_desktop_export_panel.py `
  tests\test_desktop_export_service.py `
  tests\test_desktop_query_service.py `
  tests\test_desktop_runtime.py `
  tests\test_desktop_splash.py `
  tests\test_desktop_startup_flow.py `
  tests\test_desktop_theme.py `
  tests\test_packaging_spec.py
```

## 13. Smoke em desenvolvimento

Rodar o frontend pelo source tree:

```powershell
Set-Location 'C:\Users\G05835236\Downloads\ANDY'
.\.venv\Scripts\python.exe desktop_andy.py
```

Smoke visual recomendado:
- splash abre com progressao real;
- icone correto no topo da janela;
- hero e secoes com hierarquia clara;
- cascata de filtros responde;
- consulta pagina corretamente;
- painel `Exports` aparece com corpo funcional completo;
- `Gerar XLSX dashboard` aparece e habilita so apos consulta exportavel.

## 14. Packaging e rebuild do frontend

Rebuild do executavel desktop:

```powershell
Set-Location 'C:\Users\G05835236\Downloads\ANDY'
powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1 -Profile lite
powershell -ExecutionPolicy Bypass -File .\scripts\verify_packaged_runtime.ps1
```

Gerar setup e update:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_installer.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\build_update.ps1
```

Artefatos relevantes:
- [dist/ANDY](/C:/Users/G05835236/Downloads/ANDY/dist/ANDY)
- [artifacts/installer](/C:/Users/G05835236/Downloads/ANDY/artifacts/installer)
- [artifacts/updates](/C:/Users/G05835236/Downloads/ANDY/artifacts/updates)

## 15. Convencoes para evoluir o frontend

Ao alterar a UI:
- preserve o design system em [theme.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/theme.py);
- evite logica de negocio complexa em widgets;
- mantenha services separados de shell visual;
- sempre prefira reusar contratos de [models.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/models.py);
- trate splash, icone, export e filtros como subsistemas de primeira classe;
- teste o estado vazio, o estado exportavel e o estado de erro;
- valide o comportamento do app empacotado quando a alteracao tocar branding, startup ou runtime.

Checklist de revisao:
- o novo widget parece filho do logo e do cockpit atual?
- a hierarquia visual ficou mais clara, nao mais barulhenta?
- o fluxo continua responsivo?
- o comportamento no source tree e no bundle empacotado continua equivalente?
- o estado disabled continua legivel?
- a mudanca esta coberta por teste?

## 16. Troubleshooting do frontend

### Icone generico
- verifique [app_icon.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/app_icon.py), [andy_launcher.spec](/C:/Users/G05835236/Downloads/ANDY/andy_launcher.spec) e [installer/ANDY.iss](/C:/Users/G05835236/Downloads/ANDY/installer/ANDY.iss);
- rebuild e reinstale/update;
- limpe atalhos antigos ou refixe a taskbar.

### Splash nao aparece direito
- verifique [splash.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/splash.py);
- confira se o boot esta usando `bootstrap_desktop_window()`;
- rode [test_desktop_splash.py](/C:/Users/G05835236/Downloads/ANDY/tests/test_desktop_splash.py).

### Exports parecem vazios ou sem corpo
- verifique a montagem em [main_window.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/main_window.py);
- rode [test_desktop_export_panel.py](/C:/Users/G05835236/Downloads/ANDY/tests/test_desktop_export_panel.py);
- confirme se a consulta retornou linhas exportaveis.

### Consulta funciona, mas export nao habilita
- verifique `_apply_page_result()` e `_set_result_controls_enabled()` em [main_window.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/main_window.py);
- confirme se `page.total > 0`.

## 17. Resumo executivo

O frontend atual do ANDY nao e apenas uma janela Qt com filtros. Ele ja esta organizado como um cockpit desktop com:
- design system proprio;
- splash de ignicao;
- branding coerente;
- runtime local governado;
- query/export desacoplados da shell visual;
- superficie de export completa;
- testes especificos para startup, tema, icone, splash e export.

Se voce estiver entrando no projeto agora, comece por estes arquivos:
- [desktop_andy.py](/C:/Users/G05835236/Downloads/ANDY/desktop_andy.py)
- [main_window.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/main_window.py)
- [theme.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/theme.py)
- [runtime.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/runtime.py)
- [query_service.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/query_service.py)
- [export_service.py](/C:/Users/G05835236/Downloads/ANDY/desktop_app/export_service.py)
