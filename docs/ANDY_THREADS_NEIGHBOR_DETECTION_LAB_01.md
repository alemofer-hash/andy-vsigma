# ANDY Threads - Neighbor Feeder Maneuver Detection Lab 01

## Objetivo

Implementar um laboratório isolado para detectar candidatos de transferência/manobra pela comparação de `IB_f(t)` versus `IB_g(t)` entre alimentadores distintos.

O detector principal não usa `P`, não reconstrói `IA/IC`, não duplica `IB` para simular sistema trifásico e não transforma `MVA` em dimensão independente. Todo evento permanece candidato até validação humana ou evidência SCADA.

## Fronteira Conceitual do Paper

O PDF do Teorema do Centroide foi usado como referência metodológica para deslocamento de centroide. A leitura visual das páginas de resultados/limitações mostra:

- a janela de 200 amostras do paper estava ligada a cadência média próxima de 46,3 s;
- nos XLSX deste laboratório, a cadência inferida é horária, então o detector usa janelas por duração física: 2 h, 4 h e 8 h;
- a parte multi-alimentador/Actor-Critic do paper é conceitual/sintética e requer timestamp SCADA, medições de múltiplos alimentadores reais, topologia e rótulos;
- portanto, o ANDY usa centroide como evidência estatística auxiliar, não como confirmação operacional.

## Isolamento

- Pacote criado em `andy_threads/neighbor_detection/`.
- Feature flag operacional: `ANDY_THREADS_NEIGHBOR_DETECTION_ENABLED=0`.
- CLI: `scripts/run_andy_threads_neighbor_detection.py`.
- Checker: `scripts/check_andy_threads_neighbor_detection.py`.
- Config exemplo: `config/andy_threads_feeder_neighborhood.example.json`.
- Outputs reais ficam em `.validation_tmp/andy_threads_neighbor_detection/`.

## Topologia

O exemplo versionável declara apenas:

- `MOS`: par vizinho configurado `AL3` x `AL4`, com `TR-1` como referência a montante.
- `OSO1`: sem pares confirmados; quando executado com `--all-pairs-exploratory`, os pares são exploratórios e não devem ser chamados de vizinhos físicos confirmados.

## Modelo de Detecção

Para cada par:

1. lê somente `DADOS_AGG` em modo read-only;
2. filtra `VAR == "IB"`;
3. parseia `KEY` no formato `SE|AL|EQUIP|TERMINAL|IB`;
4. sincroniza timestamps sem interpolação;
5. segmenta gaps;
6. detecta degraus robustos por mediana antes/depois;
7. calcula delta bruto, robust z, persistência, qualidade e proximidade de gaps;
8. combina alterações dos dois ALs;
9. calcula score transparente com direção oposta, balance, sincronismo, persistência e qualidade;
10. calcula deslocamento do centroide no espaço `[z(IB_f), z(IB_g)]`;
11. consulta `TR-1` como evidência auxiliar quando configurado;
12. funde candidatos próximos em episódios;
13. converte episódio em ocorrência Threads com `NotificationIntent` desligado.

## Classificações

- `LOAD_TRANSFER_CANDIDATE`: deltas em sentidos opostos e balance alto.
- `COMMON_MODE_EVENT_CANDIDATE`: deltas no mesmo sentido.
- `LOCAL_FEEDER_EVENT_CANDIDATE`: apenas um alimentador muda de forma robusta.
- `DATA_QUALITY_CANDIDATE`: cobertura, gap ou qualidade insuficiente.

## Resultado do Blind Run

Execução local em `.validation_tmp/andy_threads_neighbor_detection/20260713T151516Z`:

- entradas: 2 XLSX;
- candidatos: 1229;
- episódios consolidados: 276;
- pares analisados: 34;
- MOS `AL3-AL4` foi processado como par configurado;
- OSO1 foi processado em modo exploratório all-pairs;
- todo candidato ficou com `training_use=false`;
- nenhuma confirmação operacional foi aplicada.

Distribuição:

| Classe | Quantidade |
|---|---:|
| DATA_QUALITY_CANDIDATE | 630 |
| LOCAL_FEEDER_EVENT_CANDIDATE | 590 |
| COMMON_MODE_EVENT_CANDIDATE | 7 |
| LOAD_TRANSFER_CANDIDATE | 2 |

Top candidato configurado MOS `AL3-AL4`:

| Campo | Valor |
|---|---|
| Pico candidato | 2025-12-25T02:00:00 |
| Classificação | LOAD_TRANSFER_CANDIDATE |
| AL que caiu | AL4 |
| AL que subiu | AL3 |
| Balance score | 0.979 |
| Transfer score | 0.948 |
| Deslocamento de centroide | 5.520 |
| TR estável | true |
| Status humano | PENDING_HUMAN_REVIEW |

## Limitações

- O timestamp manual da manobra ainda não foi fornecido; a comparação com o evento manual fica aguardando reveal humano.
- OSO1 sem mapa de vizinhança real gera pares exploratórios, não vizinhança confirmada.
- O score ainda é laboratório estatístico, não decisão operacional.
- A quantidade de candidatos locais/data-quality mostra que a próxima fase precisa de rótulos SCADA e validação setorial.

## Próxima Fase

ANDY Threads - validar candidatos de transferência contra logs SCADA e labels operacionais.
