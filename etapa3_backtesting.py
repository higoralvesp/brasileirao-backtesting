"""
ETAPA 3 v5.0 — Grid Search de Thresholds + Backtesting Otimizado
Projeto: Backtesting Futebol

Metodologia:
  1. Testa todas as combinacoes de thresholds NO TREINO (2012-2019)
  2. Escolhe automaticamente os melhores (ROI maximo com min. 30 apostas)
  3. Valida os melhores no TESTE (2022-2026) — sem ajuste pos-teste
  4. Gera CSVs para o relatorio Excel
"""

import pandas as pd
import numpy as np
from itertools import product
import os
from datetime import datetime

PASTA_BASE      = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_STATS   = os.path.join(PASTA_BASE, "dados", "BRA_stats.csv")
ARQUIVO_RESULT  = os.path.join(PASTA_BASE, "dados", "BRA_resultado_v50.csv")
ARQUIVO_APOSTAS = os.path.join(PASTA_BASE, "dados", "apostas_aprovadas_v50.csv")
ARQUIVO_METR    = os.path.join(PASTA_BASE, "dados", "metricas_resumo_v50.csv")
ARQUIVO_BENCH   = os.path.join(PASTA_BASE, "dados", "benchmarks_v50.csv")
ARQUIVO_GRID    = os.path.join(PASTA_BASE, "dados", "grid_search_v50.csv")
ARQUIVO_LOG     = os.path.join(PASTA_BASE, "log.txt")

APOSTA_VALOR = 2.0
MIN_APOSTAS  = 30   # minimo de apostas para resultado ser valido


# ─── Utilitarios ─────────────────────────────────────────────────────────────

linhas_log = []

def log(msg):
    texto = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(texto)
    linhas_log.append(texto)

def salvar_log():
    with open(ARQUIVO_LOG, "a", encoding="utf-8") as f:
        f.write("\n".join(linhas_log) + "\n")

def calcular_roi(resultados_bool, odds):
    n   = len(resultados_bool)
    if n == 0:
        return None, None, None
    ac  = sum(resultados_bool)
    inv = n * APOSTA_VALOR
    ret = sum(o * APOSTA_VALOR if ok else 0 for ok, o in zip(resultados_bool, odds))
    roi = (ret - inv) / inv * 100
    return n, round(ac / n * 100, 1), round(roi, 1)

def calcular_sequencias(serie):
    max_ac = max_er = cur_ac = cur_er = 0
    for ok in serie:
        if ok:
            cur_ac += 1; cur_er = 0
        else:
            cur_er += 1; cur_ac = 0
        max_ac = max(max_ac, cur_ac)
        max_er = max(max_er, cur_er)
    return max_ac, max_er


# ─── GRID SEARCH — testa combinacoes de thresholds no treino ─────────────────

def grid_under25(df_tr, df_te):
    """
    Variaveis testadas:
      u25_min     : Under25_pct de AMBOS acima de X
      media_max   : soma media_marc (mandante+visitante) abaixo de X
    CS_pct e FTS_pct REMOVIDOS — mostraram efeito negativo nos dados
    """
    u25_opcoes   = [55, 60, 65, 70]
    media_opcoes = [None, 2.2, 2.0, 1.8, 1.5]

    linhas = []
    for u25_min, media_max in product(u25_opcoes, media_opcoes):
        for periodo, df in [("treino", df_tr), ("teste", df_te)]:
            mascara = (df["m_Under25_pct"] > u25_min) & (df["v_Under25_pct"] > u25_min)
            if media_max is not None:
                mascara &= (df["m_media_marc"] + df["v_media_marc"]) < media_max
            sub = df[mascara]
            ok  = ((sub["HG"] + sub["AG"]) < 3).tolist()
            n, taxa, roi = calcular_roi(ok, [1.80] * len(ok))
            linhas.append({
                "mercado": "Under25", "periodo": periodo,
                "u25_min": u25_min, "media_max": media_max if media_max else "sem",
                "apostas": n, "acerto_pct": taxa, "roi": roi,
                "descricao": f"U25>{u25_min}%"
                             + (f" + media<{media_max}" if media_max else ""),
            })
    return pd.DataFrame(linhas)


def grid_over15(df_tr, df_te):
    """
    Variaveis testadas:
      o15_min      : Over15_pct de AMBOS acima de X
      media_marc   : pelo menos UM time com media_marc acima de X (ou sem filtro)
    """
    o15_opcoes   = [60, 65, 70, 75]
    media_opcoes = [None, 1.0, 1.5, 2.0]

    linhas = []
    for o15_min, media_min in product(o15_opcoes, media_opcoes):
        for periodo, df in [("treino", df_tr), ("teste", df_te)]:
            mascara = (df["m_Over15_pct"] > o15_min) & (df["v_Over15_pct"] > o15_min)
            if media_min is not None:
                mascara &= (df["m_media_marc"] > media_min) | (df["v_media_marc"] > media_min)
            sub = df[mascara]
            ok  = ((sub["HG"] + sub["AG"]) > 1).tolist()
            n, taxa, roi = calcular_roi(ok, [1.55] * len(ok))
            linhas.append({
                "mercado": "Over15", "periodo": periodo,
                "o15_min": o15_min, "media_min": media_min if media_min else "sem",
                "apostas": n, "acerto_pct": taxa, "roi": roi,
                "descricao": f"O15>{o15_min}%"
                             + (f" + media>{media_min}" if media_min else ""),
            })
    return pd.DataFrame(linhas)


def grid_resultado(df_tr, df_te):
    """
    Variaveis testadas:
      vit_min  : vitorias_pct do favorito acima de X
      der_min  : derrotas_pct do adversario acima de X
      odd_min  : odd minima do favorito
      odd_max  : odd maxima do favorito
    """
    vit_opcoes  = [50, 55, 60, 65]
    der_opcoes  = [40, 45, 50, 55]
    omin_opcoes = [1.40, 1.50, 1.60]
    omax_opcoes = [2.00, 2.10, 2.20, 2.50]

    linhas = []
    for vit_min, der_min, odd_min, odd_max in product(vit_opcoes, der_opcoes, omin_opcoes, omax_opcoes):
        if odd_min >= odd_max:
            continue
        for periodo, df in [("treino", df_tr), ("teste", df_te)]:
            df2 = df[df["favorito"].isin(["mandante", "visitante"]) &
                     pd.notna(df["odd_favorito"]) &
                     (df["odd_favorito"] >= odd_min) &
                     (df["odd_favorito"] <= odd_max)].copy()

            resultados = []
            odds_list  = []
            for _, row in df2.iterrows():
                if row["favorito"] == "mandante":
                    vit = row["m_vitorias_pct"]
                    der = row["v_derrotas_pct"]
                    acertou = row["Res"] == "H"
                else:
                    vit = row["v_vitorias_pct"]
                    der = row["m_derrotas_pct"]
                    acertou = row["Res"] == "A"
                if vit > vit_min and der > der_min:
                    resultados.append(acertou)
                    odds_list.append(row["odd_favorito"])

            n, taxa, roi = calcular_roi(resultados, odds_list)
            linhas.append({
                "mercado": "Resultado", "periodo": periodo,
                "vit_min": vit_min, "der_min": der_min,
                "odd_min": odd_min, "odd_max": odd_max,
                "apostas": n, "acerto_pct": taxa, "roi": roi,
                "descricao": f"vit>{vit_min}% der>{der_min}% odd[{odd_min}-{odd_max}]",
            })
    return pd.DataFrame(linhas)


def grid_btts_nao(df_tr, df_te):
    """
    Variavel testada:
      btts_max : BTTS_pct de AMBOS abaixo de X
    CS_pct REMOVIDO — mostrou efeito negativo nos dados
    """
    btts_opcoes = [40, 35, 30, 25]

    linhas = []
    for btts_max in btts_opcoes:
        for periodo, df in [("treino", df_tr), ("teste", df_te)]:
            mascara = (df["m_BTTS_pct"] < btts_max) & (df["v_BTTS_pct"] < btts_max)
            sub = df[mascara]
            ok  = ((sub["HG"] == 0) | (sub["AG"] == 0)).tolist()
            n, taxa, roi = calcular_roi(ok, [1.70] * len(ok))
            linhas.append({
                "mercado": "BTTS_nao", "periodo": periodo,
                "btts_max": btts_max,
                "apostas": n, "acerto_pct": taxa, "roi": roi,
                "descricao": f"BTTS<{btts_max}%",
            })
    return pd.DataFrame(linhas)


def grid_empate(df_tr, df_te):
    """
    Variaveis testadas:
      odd_min / odd_max : range da odd Pinnacle do empate (PSCD)
      vit_max           : vitorias_pct AMBOS abaixo de X (times equilibrados)
    """
    omin_opcoes = [2.40, 2.50, 2.60, 2.70, 2.80]
    omax_opcoes = [2.90, 3.00, 3.10, 3.20, 3.50]
    vit_opcoes  = [None, 60, 55]   # limite de vitorias dos dois times

    linhas = []
    for odd_min, odd_max, vit_max in product(omin_opcoes, omax_opcoes, vit_opcoes):
        if odd_min >= odd_max:
            continue
        for periodo, df in [("treino", df_tr), ("teste", df_te)]:
            df2 = df[pd.notna(df["odd_D"]) &
                     (df["odd_D"] >= odd_min) &
                     (df["odd_D"] <= odd_max)].copy()
            if vit_max is not None:
                df2 = df2[(df2["m_vitorias_pct"] < vit_max) & (df2["v_vitorias_pct"] < vit_max)]

            ok   = (df2["Res"] == "D").tolist()
            odds = df2["odd_D"].tolist()
            n, taxa, roi = calcular_roi(ok, odds)
            linhas.append({
                "mercado": "Empate", "periodo": periodo,
                "odd_min": odd_min, "odd_max": odd_max, "vit_max": vit_max if vit_max else "sem",
                "apostas": n, "acerto_pct": taxa, "roi": roi,
                "descricao": f"odd[{odd_min}-{odd_max}]"
                             + (f" vit<{vit_max}%" if vit_max else ""),
            })
    return pd.DataFrame(linhas)


def melhor_treino(df_grid, mercado):
    """Retorna a combinacao com maior ROI no treino (minimo MIN_APOSTAS apostas)."""
    tr = df_grid[(df_grid["mercado"] == mercado) &
                 (df_grid["periodo"] == "treino") &
                 (df_grid["apostas"] >= MIN_APOSTAS)].copy()
    if tr.empty:
        return None
    return tr.loc[tr["roi"].idxmax()]

def top5_treino(df_grid, mercado):
    """Retorna as 5 melhores combinacoes no treino."""
    tr = df_grid[(df_grid["mercado"] == mercado) &
                 (df_grid["periodo"] == "treino") &
                 (df_grid["apostas"] >= MIN_APOSTAS)].copy()
    if tr.empty:
        return pd.DataFrame()
    return tr.nlargest(5, "roi")[["descricao", "apostas", "acerto_pct", "roi"]]


# ─── BACKTESTING com thresholds escolhidos ───────────────────────────────────

def aplicar_criterios_v50(df, params):
    """
    Aplica os criterios v5.0 (thresholds otimizados) em cada jogo.
    Retorna DataFrame de apostas aprovadas.
    """
    apostas = []
    p = params

    for _, row in df.iterrows():
        periodo = "treino" if row["Season"] <= 2019 else "teste"

        # ── Under 2.5 ──────────────────────────────────────────
        mascara_u25 = (row["m_Under25_pct"] > p["u25_min"] and
                       row["v_Under25_pct"] > p["u25_min"])
        if p["media_max"] is not None:
            mascara_u25 &= (row["m_media_marc"] + row["v_media_marc"]) < p["media_max"]
        if mascara_u25:
            acertou = (row["HG"] + row["AG"]) < 3
            apostas.append(_linha_aposta(row, periodo, "Under25", 1.80, acertou))

        # ── Over 1.5 ───────────────────────────────────────────
        mascara_o15 = (row["m_Over15_pct"] > p["o15_min"] and
                       row["v_Over15_pct"] > p["o15_min"])
        if p["media_marc_min"] is not None:
            mascara_o15 &= (row["m_media_marc"] > p["media_marc_min"] or
                            row["v_media_marc"] > p["media_marc_min"])
        if mascara_o15:
            acertou = (row["HG"] + row["AG"]) > 1
            apostas.append(_linha_aposta(row, periodo, "Over15", 1.55, acertou))

        # ── Resultado ──────────────────────────────────────────
        fav = row["favorito"]
        odd_fav = row["odd_favorito"]
        if fav in ["mandante", "visitante"] and pd.notna(odd_fav):
            if p["res_odd_min"] <= float(odd_fav) <= p["res_odd_max"]:
                if fav == "mandante":
                    vit = row["m_vitorias_pct"]; der = row["v_derrotas_pct"]
                    acertou = row["Res"] == "H"
                else:
                    vit = row["v_vitorias_pct"]; der = row["m_derrotas_pct"]
                    acertou = row["Res"] == "A"
                if vit > p["res_vit_min"] and der > p["res_der_min"]:
                    apostas.append(_linha_aposta(row, periodo, "Resultado", float(odd_fav), acertou))

        # ── BTTS Nao ───────────────────────────────────────────
        if (row["m_BTTS_pct"] < p["btts_max"] and
                row["v_BTTS_pct"] < p["btts_max"]):
            acertou = (row["HG"] == 0 or row["AG"] == 0)
            apostas.append(_linha_aposta(row, periodo, "BTTS_nao", 1.70, acertou))

        # ── Empate ─────────────────────────────────────────────
        odd_d = row.get("odd_D")
        if pd.notna(odd_d) and p["emp_odd_min"] <= float(odd_d) <= p["emp_odd_max"]:
            filtro_vit = True
            if p["emp_vit_max"] is not None:
                filtro_vit = (row["m_vitorias_pct"] < p["emp_vit_max"] and
                              row["v_vitorias_pct"] < p["emp_vit_max"])
            if filtro_vit:
                acertou = row["Res"] == "D"
                apostas.append(_linha_aposta(row, periodo, "Empate", float(odd_d), acertou))

    return pd.DataFrame(apostas)


def _linha_aposta(row, periodo, mercado, odd, acertou):
    lucro = (odd * APOSTA_VALOR - APOSTA_VALOR) if acertou else -APOSTA_VALOR
    return {
        "Season": row["Season"], "Date": row["Date"],
        "Home": row["Home"], "Away": row["Away"],
        "HG": row["HG"], "AG": row["AG"], "Res": row["Res"],
        "mercado": mercado, "odd": odd, "acertou": acertou,
        "lucro": lucro, "periodo": periodo,
        "favorito": row["favorito"], "fonte_odd": row["fonte_odd"],
    }


def resumo_metricas(df_apostas, mercado, periodo="geral"):
    if periodo == "geral":
        sub = df_apostas[df_apostas["mercado"] == mercado]
    else:
        sub = df_apostas[(df_apostas["mercado"] == mercado) &
                         (df_apostas["periodo"] == periodo)]
    if len(sub) == 0:
        return None
    n   = len(sub)
    ac  = sub["acertou"].sum()
    inv = n * APOSTA_VALOR
    ret = sub.apply(lambda r: r["odd"] * APOSTA_VALOR if r["acertou"] else 0, axis=1).sum()
    roi = (ret - inv) / inv * 100
    mac, mer = calcular_sequencias(sub["acertou"].tolist())
    return {
        "periodo": periodo, "mercado": mercado,
        "apostas": n, "acertos": int(ac),
        "taxa_acerto": round(ac / n * 100, 1),
        "odd_media": round(sub["odd"].mean(), 3),
        "investido": round(inv, 2), "retorno": round(ret, 2),
        "lucro": round(ret - inv, 2), "roi": round(roi, 1),
        "max_acertos_seq": mac, "max_erros_seq": mer,
    }


def benchmark_favorito(df):
    sub = df[df["favorito"].isin(["mandante", "visitante"]) &
             pd.notna(df["odd_favorito"])].copy()
    acertou_list = [r["Res"] == "H" if r["favorito"] == "mandante" else r["Res"] == "A"
                    for _, r in sub.iterrows()]
    n   = len(sub); ac = sum(acertou_list); inv = n * APOSTA_VALOR
    ret = sum(r["odd_favorito"] * APOSTA_VALOR if ok else 0
              for (_, r), ok in zip(sub.iterrows(), acertou_list))
    mac, mer = calcular_sequencias(acertou_list)
    return {"estrategia": "Sempre no Favorito", "periodo": "geral",
            "apostas": n, "acertos": ac, "taxa_acerto": round(ac / n * 100, 1),
            "investido": round(inv, 2), "retorno": round(ret, 2),
            "lucro": round(ret - inv, 2), "roi": round((ret - inv) / inv * 100, 1),
            "max_acertos_seq": mac, "max_erros_seq": mer}


# ─── EXECUCAO PRINCIPAL ───────────────────────────────────────────────────────

def executar():
    log("=" * 60)
    log("ETAPA 3 v5.0 — GRID SEARCH + BACKTESTING OTIMIZADO")
    log("=" * 60)

    df     = pd.read_csv(ARQUIVO_STATS, encoding="utf-8")
    df_tr  = df[df["Season"].between(2012, 2019)].copy()
    df_te  = df[df["Season"].between(2022, 2026)].copy()
    log(f"  Treino: {len(df_tr)} jogos (2012-2019)")
    log(f"  Teste : {len(df_te)} jogos (2022-2026)")

    # ── 1. GRID SEARCH ───────────────────────────────────────────
    log("\n  Rodando grid search por mercado...")

    log("    Under 2.5...")
    grd_u25 = grid_under25(df_tr, df_te)

    log("    Over 1.5...")
    grd_o15 = grid_over15(df_tr, df_te)

    log("    Resultado...")
    grd_res = grid_resultado(df_tr, df_te)

    log("    BTTS Nao...")
    grd_btt = grid_btts_nao(df_tr, df_te)

    log("    Empate...")
    grd_emp = grid_empate(df_tr, df_te)

    df_grid = pd.concat([grd_u25, grd_o15, grd_res, grd_btt, grd_emp], ignore_index=True)
    df_grid.to_csv(ARQUIVO_GRID, index=False, encoding="utf-8")
    log(f"  Grid salvo em: {ARQUIVO_GRID}")

    # ── 2. ESCOLHA DOS MELHORES THRESHOLDS (treino) ─────────────
    log("\n" + "=" * 60)
    log("MELHORES THRESHOLDS POR MERCADO (TREINO — min. 30 apostas)")
    log("=" * 60)

    melhor_u25 = melhor_treino(df_grid, "Under25")
    melhor_o15 = melhor_treino(df_grid, "Over15")
    melhor_res = melhor_treino(df_grid, "Resultado")
    melhor_btt = melhor_treino(df_grid, "BTTS_nao")
    melhor_emp = melhor_treino(df_grid, "Empate")

    def printar_top5(mercado):
        log(f"\n  TOP 5 — {mercado} (treino):")
        top = top5_treino(df_grid, mercado)
        for _, r in top.iterrows():
            log(f"    {r['descricao']:45s} | {r['apostas']:4.0f} apostas | "
                f"{r['acerto_pct']:5.1f}% | ROI {r['roi']:+.1f}%")

    for m in ["Under25", "Over15", "Resultado", "BTTS_nao", "Empate"]:
        printar_top5(m)

    # ── 3. PARAMETROS ESCOLHIDOS ─────────────────────────────────
    log("\n" + "=" * 60)
    log("PARAMETROS ESCOLHIDOS PARA v5.0")
    log("=" * 60)

    def extrair(melhor, campos):
        if melhor is None:
            return {}
        return {c: melhor[c] for c in campos if c in melhor.index}

    # Under 2.5
    u25  = melhor_u25 if melhor_u25 is not None else None
    p_u25_min    = float(u25["u25_min"])   if u25 is not None else 60
    p_media_max  = None if (u25 is None or str(u25.get("media_max", "sem")) == "sem") \
                        else float(u25["media_max"])

    # Over 1.5
    o15  = melhor_o15 if melhor_o15 is not None else None
    p_o15_min    = float(o15["o15_min"])   if o15 is not None else 65
    p_media_marc = None if (o15 is None or str(o15.get("media_min", "sem")) == "sem") \
                        else float(o15["media_min"])

    # Resultado
    res  = melhor_res if melhor_res is not None else None
    p_res_vit    = float(res["vit_min"])   if res is not None else 60
    p_res_der    = float(res["der_min"])   if res is not None else 50
    p_res_omin   = float(res["odd_min"])   if res is not None else 1.50
    p_res_omax   = float(res["odd_max"])   if res is not None else 2.20

    # BTTS Nao
    btt  = melhor_btt if melhor_btt is not None else None
    p_btts_max   = float(btt["btts_max"])  if btt is not None else 35

    # Empate
    emp  = melhor_emp if melhor_emp is not None else None
    p_emp_omin   = float(emp["odd_min"])   if emp is not None else 2.50
    p_emp_omax   = float(emp["odd_max"])   if emp is not None else 3.00
    p_emp_vit    = None if (emp is None or str(emp.get("vit_max", "sem")) == "sem") \
                        else float(emp["vit_max"])

    params = {
        "u25_min":       p_u25_min,
        "media_max":     p_media_max,
        "o15_min":       p_o15_min,
        "media_marc_min": p_media_marc,
        "res_vit_min":   p_res_vit,
        "res_der_min":   p_res_der,
        "res_odd_min":   p_res_omin,
        "res_odd_max":   p_res_omax,
        "btts_max":      p_btts_max,
        "emp_odd_min":   p_emp_omin,
        "emp_odd_max":   p_emp_omax,
        "emp_vit_max":   p_emp_vit,
    }

    log(f"  Under 2.5  : U25_pct AMBOS > {p_u25_min}%"
        + (f" | media_gols_comb < {p_media_max}" if p_media_max else ""))
    log(f"  Over 1.5   : O15_pct AMBOS > {p_o15_min}%"
        + (f" | media_marc (um) > {p_media_marc}" if p_media_marc else ""))
    log(f"  Resultado  : vit > {p_res_vit}% | der > {p_res_der}% | odd [{p_res_omin}-{p_res_omax}]")
    log(f"  BTTS Nao   : BTTS_pct AMBOS < {p_btts_max}%")
    log(f"  Empate     : odd_D [{p_emp_omin}-{p_emp_omax}]"
        + (f" | vit < {p_emp_vit}%" if p_emp_vit else ""))

    # ── 4. BACKTESTING COMPLETO COM OS PARAMETROS ESCOLHIDOS ─────
    log("\n  Aplicando criterios v5.0 em todos os jogos...")
    df_apostas = aplicar_criterios_v50(df, params)
    df_apostas.to_csv(ARQUIVO_APOSTAS, index=False, encoding="utf-8")
    log(f"  {len(df_apostas)} apostas aprovadas")

    # ── 5. METRICAS ──────────────────────────────────────────────
    MERCADOS = ["Under25", "Over15", "Resultado", "BTTS_nao", "Empate"]
    metricas = []
    for mercado in MERCADOS:
        for periodo in ["geral", "treino", "teste"]:
            m = resumo_metricas(df_apostas, mercado, periodo)
            if m:
                metricas.append(m)

    df_metr = pd.DataFrame(metricas)
    df_metr.to_csv(ARQUIVO_METR, index=False, encoding="utf-8")

    bench = [benchmark_favorito(df)]
    pd.DataFrame(bench).to_csv(ARQUIVO_BENCH, index=False, encoding="utf-8")

    # ── 6. RELATORIO FINAL ───────────────────────────────────────
    log("\n" + "=" * 60)
    log("RESULTADOS v5.0 — TREINO vs TESTE")
    log("=" * 60)

    STATUS_COMERCIAL = {"taxa": 45, "roi": 10, "apostas": 30, "max_erros": 5}

    for mercado in MERCADOS:
        log(f"\n  [{mercado}]")
        for periodo in ["treino", "teste"]:
            label = "TREINO 2012-19" if periodo == "treino" else "TESTE  2022-26"
            sub = df_apostas[(df_apostas["mercado"] == mercado) &
                             (df_apostas["periodo"] == periodo)]
            if len(sub) == 0:
                log(f"    {label}: sem apostas")
                continue
            n   = len(sub); ac = sub["acertou"].sum()
            inv = n * APOSTA_VALOR
            ret = sub.apply(lambda r: r["odd"] * APOSTA_VALOR if r["acertou"] else 0, axis=1).sum()
            roi = (ret - inv) / inv * 100
            _, mer = calcular_sequencias(sub["acertou"].tolist())
            aviso = " << INCONCLUSIVO" if n < 30 else ""

            if periodo == "teste":
                status = "APROVADO" if (roi >= 10 and n >= 30 and mer < 5) else "REPROVADO"
                log(f"    {label}: {n:4d} apostas | {ac/n*100:.1f}% acerto | "
                    f"ROI {roi:+.1f}% | max_erros {mer} -> {status}{aviso}")
            else:
                log(f"    {label}: {n:4d} apostas | {ac/n*100:.1f}% acerto | "
                    f"ROI {roi:+.1f}%{aviso}")

    log("\n" + "=" * 60)
    log("BENCHMARK: Sempre no Favorito")
    b = bench[0]
    log(f"  {b['apostas']} apostas | {b['taxa_acerto']}% acerto | ROI {b['roi']:+.1f}%")

    log("\n" + "=" * 60)
    log("ETAPA 3 v5.0 CONCLUIDA!")
    log(f"  Arquivos gerados em: {os.path.join(PASTA_BASE, 'dados')}")
    log("=" * 60)
    salvar_log()


if __name__ == "__main__":
    executar()
