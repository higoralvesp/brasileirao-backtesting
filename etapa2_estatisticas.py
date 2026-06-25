"""
ETAPA 2 — Calculo de Estatisticas Historicas
Projeto: Backtesting Futebol — Brasileirão Série A

Para cada jogo calcula:
- Stats do mandante nos ultimos 10 jogos EM CASA anteriores
- Stats do visitante nos ultimos 10 jogos FORA anteriores
- H2H: ultimos 5 confrontos diretos
- Favorito (menor odd Pinnacle)
"""

import pandas as pd
import os
import sys
from datetime import datetime

# ─── Caminhos ────────────────────────────────────────────────────────────────
PASTA_BASE      = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_LIMPO   = os.path.join(PASTA_BASE, "dados", "BRA_limpo.csv")
ARQUIVO_STATS   = os.path.join(PASTA_BASE, "dados", "BRA_stats.csv")
ARQUIVO_PULADOS = os.path.join(PASTA_BASE, "dados", "jogos_pulados.csv")
ARQUIVO_LOG     = os.path.join(PASTA_BASE, "log.txt")
CHECKPOINT      = os.path.join(PASTA_BASE, "dados", "checkpoint_etapa2.csv")

# ─── Log ─────────────────────────────────────────────────────────────────────
linhas_log = []

def log(msg):
    texto = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(texto)
    linhas_log.append(texto)

def salvar_log():
    modo = "a" if os.path.exists(ARQUIVO_LOG) else "w"
    with open(ARQUIVO_LOG, modo, encoding="utf-8") as f:
        f.write("\n".join(linhas_log) + "\n")

# ─── Calcular stats de um time no contexto (casa ou fora) ────────────────────
def calcular_stats(jogos_contexto, data_limite, contexto):
    """
    Recebe o historico de jogos de um time no contexto dado (casa ou fora),
    filtra os anteriores a data_limite, pega os ultimos 10 e calcula as metricas.
    Retorna None se houver menos de 5 jogos disponiveis.
    """
    # Filtra apenas jogos ANTERIORES ao jogo atual
    anteriores = jogos_contexto[jogos_contexto["Date"] < data_limite]

    # Pega os ultimos 10 (mais recentes primeiro para o 'forma')
    ultimos = anteriores.sort_values("Date", ascending=False).head(10)
    n = len(ultimos)

    if n < 5:
        return None  # dados insuficientes

    if contexto == "casa":
        gols_marc  = ultimos["HG"].values
        gols_sof   = ultimos["AG"].values
        vitoria_res = "H"
        derrota_cond = lambda r: r.isin(["A", "D"])
        forma_map  = {"H": "W", "A": "L", "D": "D"}
    else:
        gols_marc  = ultimos["AG"].values
        gols_sof   = ultimos["HG"].values
        vitoria_res = "A"
        derrota_cond = lambda r: r.isin(["H", "D"])
        forma_map  = {"A": "W", "H": "L", "D": "D"}

    gols_totais = gols_marc + gols_sof

    # Forma: ultimos 5 jogos (ja estao ordenados do mais recente)
    forma_serie = ultimos.head(5)["Res"].map(forma_map)
    forma = "".join(forma_serie.tolist())

    return {
        "n_jogos":            n,
        "CS_pct":             round((gols_sof == 0).sum() / n * 100, 1),
        "FTS_pct":            round((gols_marc == 0).sum() / n * 100, 1),
        "BTTS_pct":           round(((gols_marc > 0) & (gols_sof > 0)).sum() / n * 100, 1),
        "Under25_pct":        round((gols_totais < 3).sum() / n * 100, 1),
        "Over15_pct":         round((gols_totais > 1).sum() / n * 100, 1),
        "Over25_pct":         round((gols_totais > 2).sum() / n * 100, 1),
        "media_gols_marc":    round(gols_marc.mean(), 2),
        "media_gols_sof":     round(gols_sof.mean(), 2),
        "vitorias_pct":       round((ultimos["Res"] == vitoria_res).sum() / n * 100, 1),
        "derrotas_pct":       round(derrota_cond(ultimos["Res"]).sum() / n * 100, 1),
        "forma":              forma,
    }

# ─── Calcular H2H entre dois times ───────────────────────────────────────────
def calcular_h2h(df_todos, mandante, visitante, data_limite):
    """
    Ultimos 5 confrontos diretos entre os dois times, qualquer contexto.
    Retorna dados insuficientes se menos de 3 confrontos.
    """
    mask = (
        ((df_todos["Home"] == mandante) & (df_todos["Away"] == visitante)) |
        ((df_todos["Home"] == visitante) & (df_todos["Away"] == mandante))
    ) & (df_todos["Date"] < data_limite)

    h2h = df_todos[mask].sort_values("Date", ascending=False).head(5)
    n = len(h2h)

    if n < 3:
        return {
            "h2h_jogos":       n,
            "h2h_suficiente":  False,
            "h2h_media_gols":  None,
            "h2h_under25_pct": None,
            "h2h_btts_pct":    None,
        }

    gols_totais = h2h["HG"] + h2h["AG"]
    btts = ((h2h["HG"] > 0) & (h2h["AG"] > 0)).sum()

    return {
        "h2h_jogos":       n,
        "h2h_suficiente":  True,
        "h2h_media_gols":  round(gols_totais.mean(), 2),
        "h2h_under25_pct": round((gols_totais < 3).sum() / n * 100, 1),
        "h2h_btts_pct":    round(btts / n * 100, 1),
    }

# ─── Determinar favorito pelas odds Pinnacle ──────────────────────────────────
def calcular_favorito(psch, psca):
    """
    Favorito = time com MENOR odd para vitoria.
    Retorna: 'mandante', 'visitante' ou 'indefinido'
    """
    if pd.isna(psch) or pd.isna(psca):
        return "sem_odds"
    if psch < psca:
        return "mandante"
    elif psca < psch:
        return "visitante"
    else:
        return "indefinido"

# ─── Funcao principal ─────────────────────────────────────────────────────────
def executar_estatisticas():
    log("=" * 60)
    log("ETAPA 2 - CALCULO DE ESTATISTICAS HISTORICAS")
    log("=" * 60)

    # Carregar dados limpos
    log(f"Carregando: {ARQUIVO_LIMPO}")
    df = pd.read_csv(ARQUIVO_LIMPO, encoding="utf-8", parse_dates=["Date"])
    log(f"  {len(df)} jogos carregados")

    # Verificar checkpoint (retomar de onde parou se interrompido)
    inicio_idx = 0
    resultados = []
    pulados = []

    if os.path.exists(CHECKPOINT):
        df_check = pd.read_csv(CHECKPOINT, encoding="utf-8")
        inicio_idx = len(df_check)
        resultados = df_check.to_dict("records")
        log(f"  Checkpoint encontrado! Retomando do jogo {inicio_idx + 1}...")
    else:
        log("  Nenhum checkpoint encontrado. Iniciando do zero...")

    # Pre-construir indices por time para velocidade
    # Em vez de filtrar o df inteiro para cada jogo, filtramos sub-dfs menores
    log("  Pre-indexando jogos por time...")
    todos_times = sorted(set(df["Home"].unique()) | set(df["Away"].unique()))

    idx_casa = {}  # time -> DataFrame de jogos EM CASA, ordenado por data
    idx_fora = {}  # time -> DataFrame de jogos FORA, ordenado por data

    for time in todos_times:
        idx_casa[time] = df[df["Home"] == time].sort_values("Date").reset_index(drop=True)
        idx_fora[time] = df[df["Away"] == time].sort_values("Date").reset_index(drop=True)

    log(f"  {len(todos_times)} times indexados")
    log(f"  Processando {len(df)} jogos (a partir do jogo {inicio_idx + 1})...")
    log("")

    tempo_inicio = datetime.now()
    total = len(df)

    for idx, row in df.iloc[inicio_idx:].iterrows():
        num_jogo = idx + 1  # numero sequencial (1-based)
        mandante  = row["Home"]
        visitante = row["Away"]
        data      = row["Date"]

        # Progress a cada 100 jogos
        if (num_jogo - inicio_idx) % 100 == 1 or num_jogo == total:
            pct = num_jogo / total * 100
            elapsed = (datetime.now() - tempo_inicio).seconds
            log(f"  Processando jogo {num_jogo} de {total} ({pct:.1f}%)... [{elapsed}s]")

        # Stats do MANDANTE em casa
        stats_m = calcular_stats(idx_casa[mandante], data, "casa")

        # Stats do VISITANTE fora
        stats_v = calcular_stats(idx_fora[visitante], data, "fora")

        # Se algum time nao tem dados suficientes, pular o jogo
        if stats_m is None or stats_v is None:
            motivo_m = f"mandante {mandante}: {len(idx_casa[mandante][idx_casa[mandante]['Date'] < data])} jogos em casa"
            motivo_v = f"visitante {visitante}: {len(idx_fora[visitante][idx_fora[visitante]['Date'] < data])} jogos fora"
            pulados.append({
                "idx":      idx,
                "Date":     data.strftime("%d/%m/%Y"),
                "Home":     mandante,
                "Away":     visitante,
                "motivo":   f"Dados insuficientes - {motivo_m if stats_m is None else ''} {motivo_v if stats_v is None else ''}".strip()
            })
            continue

        # H2H
        h2h = calcular_h2h(df, mandante, visitante, data)

        # Favorito
        favorito = calcular_favorito(row.get("PSCH"), row.get("PSCA"))
        odd_fav = None
        if favorito == "mandante":
            odd_fav = row.get("PSCH")
        elif favorito == "visitante":
            odd_fav = row.get("PSCA")

        # Selecionar fonte das odds (Pinnacle > Bet365 > Media)
        psch  = row.get("PSCH");  pscd  = row.get("PSCD");  psca  = row.get("PSCA")
        b365h = row.get("B365CH"); b365d = row.get("B365CD"); b365a = row.get("B365CA")
        avgh  = row.get("AvgCH"); avgd  = row.get("AvgCD"); avga  = row.get("AvgCA")

        if pd.notna(psch) and pd.notna(psca):
            odd_h, odd_d, odd_a, fonte_odd = psch, pscd, psca, "Pinnacle"
        elif pd.notna(b365h) and pd.notna(b365a):
            odd_h, odd_d, odd_a, fonte_odd = b365h, b365d, b365a, "Bet365"
        else:
            odd_h, odd_d, odd_a, fonte_odd = avgh, avgd, avga, "Media"

        # Montar linha de resultado
        linha = {
            # Dados basicos do jogo
            "Season":     row["Season"],
            "Date":       data.strftime("%d/%m/%Y"),
            "Home":       mandante,
            "Away":       visitante,
            "HG":         row["HG"],
            "AG":         row["AG"],
            "Res":        row["Res"],
            "Gols_total": row["HG"] + row["AG"],

            # Odds usadas
            "fonte_odd":  fonte_odd,
            "odd_H":      odd_h,
            "odd_D":      odd_d,
            "odd_A":      odd_a,
            "favorito":   favorito,
            "odd_favorito": odd_fav,

            # Stats mandante (em casa)
            "m_n_jogos":       stats_m["n_jogos"],
            "m_CS_pct":        stats_m["CS_pct"],
            "m_FTS_pct":       stats_m["FTS_pct"],
            "m_BTTS_pct":      stats_m["BTTS_pct"],
            "m_Under25_pct":   stats_m["Under25_pct"],
            "m_Over15_pct":    stats_m["Over15_pct"],
            "m_Over25_pct":    stats_m["Over25_pct"],
            "m_media_marc":    stats_m["media_gols_marc"],
            "m_media_sof":     stats_m["media_gols_sof"],
            "m_vitorias_pct":  stats_m["vitorias_pct"],
            "m_derrotas_pct":  stats_m["derrotas_pct"],
            "m_forma":         stats_m["forma"],

            # Stats visitante (fora)
            "v_n_jogos":       stats_v["n_jogos"],
            "v_CS_pct":        stats_v["CS_pct"],
            "v_FTS_pct":       stats_v["FTS_pct"],
            "v_BTTS_pct":      stats_v["BTTS_pct"],
            "v_Under25_pct":   stats_v["Under25_pct"],
            "v_Over15_pct":    stats_v["Over15_pct"],
            "v_Over25_pct":    stats_v["Over25_pct"],
            "v_media_marc":    stats_v["media_gols_marc"],
            "v_media_sof":     stats_v["media_gols_sof"],
            "v_vitorias_pct":  stats_v["vitorias_pct"],
            "v_derrotas_pct":  stats_v["derrotas_pct"],
            "v_forma":         stats_v["forma"],

            # H2H
            "h2h_jogos":       h2h["h2h_jogos"],
            "h2h_suficiente":  h2h["h2h_suficiente"],
            "h2h_media_gols":  h2h["h2h_media_gols"],
            "h2h_under25_pct": h2h["h2h_under25_pct"],
            "h2h_btts_pct":    h2h["h2h_btts_pct"],
        }

        resultados.append(linha)

        # Salvar checkpoint a cada 100 jogos
        if len(resultados) % 100 == 0:
            pd.DataFrame(resultados).to_csv(CHECKPOINT, index=False, encoding="utf-8")

    # Salvar resultado final
    df_stats = pd.DataFrame(resultados)
    df_stats.to_csv(ARQUIVO_STATS, index=False, encoding="utf-8")

    # Salvar jogos pulados
    if pulados:
        pd.DataFrame(pulados).to_csv(ARQUIVO_PULADOS, index=False, encoding="utf-8")

    # Remover checkpoint (nao precisa mais)
    if os.path.exists(CHECKPOINT):
        os.remove(CHECKPOINT)

    # Resumo final
    tempo_total = (datetime.now() - tempo_inicio).seconds
    log("")
    log("=" * 60)
    log("RESUMO DA ETAPA 2")
    log("=" * 60)
    log(f"  Jogos processados com sucesso: {len(resultados)}")
    log(f"  Jogos pulados (dados insuf.):  {len(pulados)}")
    log(f"  Tempo total: {tempo_total}s")
    log(f"  Arquivo salvo: {ARQUIVO_STATS}")

    # Distribuicao por temporada
    log("\n  Jogos validos por temporada:")
    for season, grp in df_stats.groupby("Season"):
        log(f"    {season}: {len(grp)} jogos")

    # Info sobre favoritos
    log("\n  Distribuicao de favoritos:")
    for fav, cnt in df_stats["favorito"].value_counts().items():
        log(f"    {fav}: {cnt} ({cnt/len(df_stats)*100:.1f}%)")

    # Disponibilidade de odds
    log("\n  Fonte das odds usadas:")
    for fonte, cnt in df_stats["fonte_odd"].value_counts().items():
        log(f"    {fonte}: {cnt} ({cnt/len(df_stats)*100:.1f}%)")

    log("=" * 60)
    log("ETAPA 2 CONCLUIDA COM SUCESSO!")
    salvar_log()

if __name__ == "__main__":
    executar_estatisticas()
