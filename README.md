# brasileirao-backtesting
Backtesting estatístico de 14 anos do Brasileirão Série A — metodologia de análise e validação de critérios para mercados esportivos
# ⚽ Brasileirão Backtesting — Análise Estatística de Apostas Esportivas

Sistema completo de backtesting estatístico aplicado ao Brasileirão Série A,
com pipeline de dados, cálculo de estatísticas históricas, grid search de
thresholds e validação de protocolo em dados fora da amostra.

## 🎯 Objetivo

Validar cientificamente se critérios estatísticos conseguem identificar
padrões reais em resultados de futebol — com metodologia rigorosa para
evitar overfitting e garantir que os resultados sejam replicáveis.

## 📊 Dataset

- **Fonte:** [football-data.co.uk](https://www.football-data.co.uk)
- **Cobertura:** Brasileirão Série A 2012–2026
- **Volume bruto:** 5.497 jogos
- **Após limpeza:** 4.086 jogos válidos
- **Com estatísticas calculadas:** 3.803 jogos
- **Exclusões justificadas:** temporadas 2020/2021 (COVID — distorção de mandante/visitante) e primeiras 5 rodadas de cada temporada (histórico insuficiente)

## 🔬 Metodologia

### Divisão treino/teste (anti-overfitting)
- **Treino:** 2012–2019 (2.405 jogos) — descoberta de critérios via grid search
- **Teste:** 2022–2026 (1.398 jogos) — validação final sem ajuste posterior

Todo threshold foi escolhido exclusivamente com base nos dados de treino.
O conjunto de teste foi usado apenas uma vez, para validação final.

### Pipeline de execução
etapa1_limpeza.py

↓ Remove duplicatas, padroniza times, trata datas

etapa2_estatisticas.py

↓ Calcula histórico dos últimos 10 jogos por contexto (casa/fora)

↓ Calcula H2H (confrontos diretos, últimos 5 jogos)

etapa3_backtesting.py

↓ Grid search de thresholds no treino

↓ Backtesting completo com protocolo validado

etapa4_relatorio.py

↓ Geração de relatório Excel com métricas, evolução de banca e conclusões

analisar_rodada.py

↓ Ferramenta ao vivo — analisa jogos da próxima rodada e retorna picks
### Estatísticas calculadas por time (janela: últimos 10 jogos no contexto)

Para cada jogo, o sistema calcula o histórico recente do mandante **em casa**
e do visitante **fora de casa** separadamente:

- % jogos com mais de 1 gol marcado (Over 1.5)
- % jogos com menos de 3 gols no total (Under 2.5)
- % vitórias, derrotas, clean sheets
- Média de gols marcados e sofridos
- Sequência de forma dos últimos 5 jogos
- H2H: média de gols e padrões nos confrontos diretos

## ✅ Resultados (teste 2022–2026)

| Mercado | Picks/ano | Acerto | ROI |
|---|---|---|---|
| Mercado A | ~78 | 71.0% | +10.1% |
| Mercado B | ~11 | 72.1% | +24.7% |
| Mercado C | ~14 | 63.0% | +13.3% |
| **TOTAL** | **~103** | **70.1%** | **+12.0%** |

**Benchmark (sempre no favorito Pinnacle):** 51.6% acerto | ROI -0.7%

Treino e teste alinhados: **70.2% vs 70.1% de acerto** — sinal de consistência
real, sem overfitting.

Simulação banca R$200 / R$2 por pick (2022–2026):
- Banca final: R$298,90 | Lucro: +R$98,90 | Queda máxima: 6,0%

## 🛠️ Tecnologias

- Python 3
- pandas (manipulação e análise dos dados)
- openpyxl (geração do relatório Excel)
- requests (download automático do dataset)

## 📁 Estrutura
├── dados/

│   ├── BRA.csv                  # Dataset bruto (football-data.co.uk)

│   ├── BRA_limpo.csv            # Após limpeza

│   └── BRA_stats.csv            # Com estatísticas históricas calculadas

├── resultados/

│   └── Backtesting_v50.xlsx     # Relatório final (métricas, banca, conclusões)

├── etapa1_limpeza.py

├── etapa2_estatisticas.py

├── etapa3_backtesting.py

├── etapa4_relatorio.py

├── analisar_rodada.py           # Ferramenta de análise pré-rodada

└── README.md
## ⚠️ Nota sobre os critérios

Os thresholds e critérios específicos do protocolo não estão publicados neste
repositório — fazem parte de um produto em desenvolvimento. O repositório
documenta a **metodologia, pipeline e resultados** do projeto.

## 📌 Aprendizados principais

- Separação rígida treino/teste é essencial — ajustar critérios olhando para
  o teste invalida qualquer resultado
- Contexto importa: histórico em casa ≠ histórico fora de casa
- Volume mínimo por mercado define o nível de confiança estatística
- Benchmark simples (sempre no favorito) é obrigatório para comparação honesta
