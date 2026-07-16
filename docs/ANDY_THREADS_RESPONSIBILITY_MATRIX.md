# ANDY Threads Responsibility Matrix

## Regra geral

O dono inicial recebe a triagem. Setores consultados podem comentar quando o
escopo bate. Apenas setores autorizados podem encerrar ou criar decisao final.

| Evento detectado | Dono inicial | Consultados | Quem pode encerrar |
|---|---|---|---|
| Lacuna de medicao | Medicao / Dados | TI / BI, Engenharia | Medicao / Dados |
| Falha de cadencia | Medicao / Dados | Engenharia, TI / BI | Medicao / Dados |
| Terminal suspeito | Cadastro / Ativos | Engenharia, Medicao / Dados | Cadastro / Ativos |
| Variavel suspeita | Medicao / Dados | Cadastro / Ativos, Engenharia | Medicao / Dados ou Cadastro / Ativos |
| Inversao de fluxo | Engenharia | Operacao, Cadastro / Ativos | Engenharia |
| Fluxo de carga anomalo | Engenharia | Operacao, Protecao / Automacao | Engenharia |
| Manobra detectada | Operacao | Engenharia, Protecao / Automacao | Operacao |
| Alteracao pos-obra | Obras / Manutencao | Operacao, Engenharia | Obras / Manutencao |
| Transicao AT/BT inconsistente | Engenharia | Cadastro / Ativos | Engenharia |
| Erro em relatorio BI | TI / BI | Engenharia, Medicao / Dados | TI / BI |
| Divergencia Desktop vs BI | Engenharia | TI / BI | Engenharia ou TI / BI conforme causa |
| Calculo eletrico questionado | Engenharia | TI / BI para paridade | Engenharia |

## Observacoes

- Dado sem referencia tecnica nao deve abrir thread.
- Divergencia critica de calculo bloqueia publicacao.
- Export de thread exige permissao explicita.
- O MVP usa matriz inicial sintetica; a matriz corporativa real depende de
  revisao humana dos setores.
