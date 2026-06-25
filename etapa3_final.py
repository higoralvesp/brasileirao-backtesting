"""
ETAPA 3 v5.0 FINAL — Backtesting com protocolo validado
Thresholds escolhidos por grid search sistematico no treino (2012-2019)
Validacao no teste (2022-2026) sem ajuste posterior

MERCADOS:
  1. Over 1.5        : O15_pct AMBOS > 65% + media_marc (um) > 1.5
  2. Mandante Dom.   : m_vitorias_pct >= 75% em casa (odd real Pinnacle)
  3. Resultado Forma : fav ganhou 5/5 no contexto + adv perdeu 2+ de 5
  4. Under 2.5 + H2H : h2h_under25 >= 60% + Under25_pct AMBOS > 60%
  5. Empate          : odd_D [2.40-3.00] + vitorias AMBOS < 60%
"""

import pandas as pd
import os
from datetime import datetime

PASTA_BASE      = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_STATS   = os.path.join(PASTA_BASE, "dados", "BRA_stats.csv")
ARQUIVO_APOSTAS = os.path.join(PASTA_BASE, "dados", "apostas_v50_final.csv")
ARQUIVO_METR    = os.path.join(PASTA_BASE, "dados", "metricas_v50_final.csv")
ARQUIVO_BENCH   = os.path.join(PASTA_BASE, "dados", "benchmarks_v50_final.csv")
ARQUIVO_LOG     = os.path.join(PASTA_BASE, "log.txt")

APOSTA_VALOR = 2.0

linhas_log = []
def log(msg):
    texto = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(texto)
    linhas_log.append(texto)

def salvar_log():
    with open(ARQUIVO_LOG, "a", encoding="utf-8") as f:
        f.write("\n".join(linhas_log) + "\n")

def wins_forma(s, n=5):
    return s[:n].count('W') if isinstance(s, str) else 0

def losses_forma(s, n=5):
    return s[:n].count('L') if isinstance(s, str) else 0

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

def linha_aposta(row, periodo, mercado, odd, acertou):
    lucro = (odd * APOSTA_VALOR - APOSTA_VALOR) if acertou else -APOSTA_VALOR
    return {
        "Season": row["Season"], "Date": row["Date"],
        "Home": row["Home"], "Away": row["Away"],
        "HG": row["HG"], "AG": row["AG"], "Res": row["Res"],
        "Gols_total": row["HG"] + row["AG"],
        "mercado": mercado, "odd": round(float(odd), 3),
        "acertou": bool(acertou), "lucro": round(lucro, 2),
        "periodo": periodo,
        "favorito": row["favorito"],
        "fonte_odd": row["fonte_odd"],
        "m_vitorias_pct": row["m_vitorias_pct"],
        "v_vitorias_pct": row["v_vitorias_pct"],
        "m_Over15_pct": row["m_Over15_pct"],
        "v_Over15_pct": row["v_Over15_pct"],
        "m_Under25_pct": row["m_Under25_pct"],
        "v_Under25_pct": row["v_Under25_pct"],
        "m_media_marc": row["m_media_marc"],
        "v_media_marc": row["v_media_marc"],
        "m_BTTS_pct": row["m_BTTS_pct"],
        "v_BTTS_pct": row["v_BTTS_pct"],
        "h2h_jogos": row["h2h_jogos"],
        "h2h_under25_pct": row["h2h_under25_pct"],
    }

def resumo(df_ap, mercado, periodo="geral"):
    if periodo == "geral":
        sub = df_ap[df_ap["mercado"] == mercado]
    else:
        sub = df_ap[(df_ap["mercado"] == mercado) & (df_ap["periodo"] == periodo)]
    if len(sub) == 0:
        return None
    n   = len(sub); ac = sub["acertou"].sum()
    inv = n * APOSTA_VALOR
    ret = sub.apply(lambda r: r["odd"] * APOSTA_VALOR if r["acertou"] else 0, axis=1).sum()
    roi = (ret - inv) / inv * 100
    mac, mer = calcular_sequencias(sub["acertou"].tolist())
    lucro_acum = sub["lucro"].sum()
    return {
        "periodo": periodo, "mercado": mercado,
        "apostas": n, "acertos": int(ac),
        "taxa_acerto": round(ac / n * 100, 1),
        "odd_media": round(sub["odd"].mean(), 3),
        "investido": round(inv, 2),
        "retorno": round(ret, 2),
        "lucro": round(lucro_acum, 2),
        "roi": round(roi, 1),
        "max_acertos_seq": mac,
        "max_erros_seq": mer,
        "status": "APROVADO" if roi >= 10 and n >= 30 and mer < 5 else
                  "POSITIVO" if roi > 0 else "NEGATIVO",
    }

def benchmark_favorito(df):
    sub = df[df["favorito"].isin(["mandante", "visitante"]) &
             pd.notna(df["odd_favorito"])].copy()
    oks  = [r["Res"] == "H" if r["favorito"] == "mandante" else r["Res"] == "A"
            for _, r in sub.iterrows()]
    odds = sub["odd_favorito"].tolist()
    n = len(sub); ac = sum(oks); inv = n * APOSTA_VALOR
    ret = sum(o * APOSTA_VALOR if ok else 0 for o, ok in zip(odds, oks))
    mac, mer = calcular_sequencias(oks)
    return {"estrategia": "Sempre no Favorito", "apostas": n, "acertos": ac,
            "taxa_acerto": round(ac/n*100,1), "investido": round(inv,2),
            "retorno": round(ret,2), "lucro": round(ret-inv,2),
            "roi": round((ret-inv)/inv*100,1),
            "max_acertos_seq": mac, "max_erros_seq": mer}

def executar():
    log("=" * 60)
    log("ETAPA 3 v5.0 FINAL — BACKTESTING PROTOCOLO v5.0")
    log("=" * 60)

    df = pd.read_csv(ARQUIVO_STATS, encoding="utf-8")
    log(f"  {len(df)} jogos carregados")

    df["m_wins5"]    = df["m_forma"].apply(wins_forma)
    df["m_losses5"]  = df["m_forma"].apply(losses_forma)
    df["v_wins5"]    = df["v_forma"].apply(wins_forma)
    df["v_losses5"]  = df["v_forma"].apply(losses_forma)

    df_tr = df[df["Season"].between(2012, 2019)]
    df_te = df[df["Season"].between(2022, 2026)]
    log(f"  Treino: {len(df_tr)} | Teste: {len(df_te)}")

    MERCADOS = ["Over15", "MandanteDom", "ResultadoForma", "Under25H2H", "Empate"]
    apostas_lista = []

    log("\n  Aplicando criterios v5.0...")

    for _, row in df.iterrows():
        periodo = "treino" if row["Season"] <= 2019 else "teste"

        # 1. OVER 1.5
        if (row["m_Over15_pct"] > 65 and row["v_Over15_pct"] > 65 and
                (row["m_media_marc"] > 1.5 or row["v_media_marc"] > 1.5)):
            acertou = (row["HG"] + row["AG"]) > 1
            apostas_lista.append(linha_aposta(row, periodo, "Over15", 1.55, acertou))

        # 2. MANDANTE DOMINANTE
        if row["m_vitorias_pct"] >= 75:
            odd_h = row.get("odd_H")
            if pd.notna(odd_h):
                acertou = row["Res"] == "H"
                apostas_lista.append(linha_aposta(row, periodo, "MandanteDom", float(odd_h), acertou))

        # 3. RESULTADO — FORMA
        fav = row["favorito"]
        if fav in ["mandante", "visitante"] and pd.notna(row["odd_favorito"]):
            if fav == "mandante":
                wins_fav   = row["m_wins5"]
                losses_adv = row["v_losses5"]
                acertou    = row["Res"] == "H"
            else:
                wins_fav   = row["v_wins5"]
                losses_adv = row["m_losses5"]
                acertou    = row["Res"] == "A"
            if wins_fav >= 5 and losses_adv >= 2:
                apostas_lista.append(linha_aposta(row, periodo, "ResultadoForma",
                                                  float(row["odd_favorito"]), acertou))

        # 4. UNDER 2.5 + H2H
        if (row["h2h_suficiente"] == True and
                pd.notna(row["h2h_under25_pct"]) and
                row["h2h_under25_pct"] >= 60 and
                row["m_Under25_pct"] > 60 and
                row["v_Under25_pct"] > 60):
            acertou = (row["HG"] + row["AG"]) < 3
            apostas_lista.append(linha_aposta(row, periodo, "Under25H2H", 1.80, acertou))

        # 5. EMPATE
        odd_d = row.get("odd_D")
        if pd.notna(odd_d) and 2.40 <= float(odd_d) <= 3.00:
            if row["m_vitorias_pct"] < 60 and row["v_vitorias_pct"] < 60:
                acertou = row["Res"] == "D"
                apostas_lista.append(linha_aposta(row, periodo, "Empate",
                                                  float(odd_d), acertou))

    df_apostas = pd.DataFrame(apostas_lista)
    df_apostas.to_csv(ARQUIVO_APOSTAS, index=False, encoding="utf-8")
    log(f"  {len(df_apostas)} apostas geradas")

    metricas = []
    for mercado in MERCADOS:
        for periodo in ["geral", "treino", "teste"]:
            m = resumo(df_apostas, mercado, periodo)
            if m:
                metricas.append(m)

    df_metr = pd.DataFrame(metricas)
    df_metr.to_csv(ARQUIVO_METR, index=False, encoding="utf-8")

    bench = benchmark_favorito(df)
    pd.DataFrame([bench]).to_csv(ARQUIVO_BENCH, index=False, encoding="utf-8")

    log("\n" + "=" * 60)
    log("RESULTADOS v5.0 — TREINO vs TESTE")
    log("=" * 60)

    nomes = {
        "Over15":         "Over 1.5",
        "MandanteDom":    "Mandante Dominante",
        "ResultadoForma": "Resultado (Forma)",
        "Under25H2H":     "Under 2.5 + H2H",
        "Empate":         "Empate",
    }

    for mercado in MERCADOS:
        log(f"\n  [{nomes[mercado]}]")
        for periodo in ["treino", "teste"]:
            label = "TREINO 2012-19" if periodo == "treino" else "TESTE  2022-26"
            sub = df_apostas[(df_apostas["mercado"] == mercado) &
                             (df_apostas["periodo"] == periodo)]
            if len(sub) == 0:
                log(f"    {label}: sem apostas")
                continue
            n  = len(sub); ac = sub["acertou"].sum()
            inv = n * APOSTA_VALOR
            ret = sub.apply(lambda r: r["odd"] * APOSTA_VALOR if r["acertou"] else 0, axis=1).sum()
            roi = (ret - inv) / inv * 100
            _, mer = calcular_sequencias(sub["acertou"].tolist())
            aviso = " << INSUFICIENTE" if n < 30 else ""
            if periodo == "teste":
                st = "APROVADO" if roi >= 10 and n >= 30 and mer < 5 else "REPROVADO"
                log(f"    {label}: {n:4d} apostas | {ac/n*100:.1f}% acerto | "
                    f"ROI {roi:+.1f}% | max_erros {mer} -> {st}{aviso}")
            else:
                log(f"    {label}: {n:4d} apostas | {ac/n*100:.1f}% acerto | ROI {roi:+.1f}%{aviso}")

    log(f"\n  Benchmark (sempre no favorito): {bench['taxa_acerto']}% acerto | ROI {bench['roi']:+.1f}%")
    log("\n" + "=" * 60)
    log("ETAPA 3 v5.0 FINAL CONCLUIDA!")
    log("=" * 60)
    salvar_log()

    return df_apostas, df_metr, pd.DataFrame([bench])

if __name__ == "__main__":
    executar()
