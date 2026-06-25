"""
ETAPA 1 — Limpeza e Validação dos Dados
Projeto: Backtesting Futebol — Brasileirão Série A
"""

import pandas as pd
import os
from datetime import datetime

# ─── Caminhos ───────────────────────────────────────────────────────────────
PASTA_BASE    = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_CSV   = os.path.join(PASTA_BASE, "dados", "BRA.csv")
ARQUIVO_SAIDA = os.path.join(PASTA_BASE, "dados", "BRA_limpo.csv")
ARQUIVO_LOG   = os.path.join(PASTA_BASE, "log.txt")

# ─── Log ────────────────────────────────────────────────────────────────────
linhas_log = []

def log(msg):
    texto = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(texto)
    linhas_log.append(texto)

def salvar_log():
    with open(ARQUIVO_LOG, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas_log))

# ─── Dicionário de padronização de nomes dos times ──────────────────────────
# Mapeia variações encontradas no CSV para um nome único e limpo
NOMES_TIMES = {
    # Atlético Mineiro
    "Atletico MG":        "Atletico Mineiro",
    "Atletico-MG":        "Atletico Mineiro",
    "Atletico Mineiro":   "Atletico Mineiro",

    # Atlético Paranaense
    "Atletico PR":        "Atletico Paranaense",
    "Atletico-PR":        "Atletico Paranaense",
    "Athletico-PR":       "Atletico Paranaense",
    "Athletico PR":       "Atletico Paranaense",
    "Atletico Paranaense":"Atletico Paranaense",

    # Flamengo
    "Flamengo RJ":        "Flamengo",
    "Flamengo":           "Flamengo",

    # Botafogo
    "Botafogo RJ":        "Botafogo",
    "Botafogo":           "Botafogo",

    # Vasco
    "Vasco DA Gama":      "Vasco",
    "Vasco da Gama":      "Vasco",
    "Vasco":              "Vasco",

    # São Paulo
    "Sao Paulo":          "Sao Paulo",

    # Grêmio
    "Gremio":             "Gremio",

    # Sport
    "Sport Recife":       "Sport Recife",

    # Náutico
    "Nautico":            "Nautico",

    # América Mineiro
    "America MG":         "America Mineiro",
    "America Mineiro":    "America Mineiro",

    # Ceará
    "Ceara":              "Ceara",

    # Goiás
    "Goias":              "Goias",

    # Chapecoense
    "Chapecoense AF":     "Chapecoense",
    "Chapecoense":        "Chapecoense",
    "Chapecoense-SC":     "Chapecoense",

    # Figueirense
    "Figueirense":        "Figueirense",

    # Joinville
    "Joinville":          "Joinville",

    # Ponte Preta
    "Ponte Preta":        "Ponte Preta",

    # Portuguesa
    "Portuguesa":         "Portuguesa",

    # Vitória
    "Vitoria":            "Vitoria",

    # Avaí
    "Avai":               "Avai",

    # Coritiba
    "Coritiba":           "Coritiba",

    # Santos
    "Santos":             "Santos",

    # Corinthians
    "Corinthians":        "Corinthians",

    # Internacional
    "Internacional":      "Internacional",

    # Cruzeiro
    "Cruzeiro":           "Cruzeiro",

    # Fluminense
    "Fluminense":         "Fluminense",

    # Palmeiras
    "Palmeiras":          "Palmeiras",

    # Bahia
    "Bahia":              "Bahia",

    # Fortaleza
    "Fortaleza":          "Fortaleza",

    # Bragantino / RB Bragantino
    "RB Bragantino":      "Bragantino",
    "Bragantino":         "Bragantino",
    "Red Bull Bragantino":"Bragantino",

    # Cuiabá
    "Cuiaba":             "Cuiaba",

    # Juventude
    "Juventude":          "Juventude",

    # Criciúma
    "Criciuma":           "Criciuma",

    # Sampaio Corrêa
    "Sampaio Correa":     "Sampaio Correa",

    # Paraná
    "Parana":             "Parana",

    # EC Bahia / Esporte Clube Bahia
    "EC Bahia":           "Bahia",
}

def padronizar_nome(nome):
    if pd.isna(nome):
        return nome
    nome = str(nome).strip()
    return NOMES_TIMES.get(nome, nome)

# ─── Função principal ────────────────────────────────────────────────────────
def executar_limpeza():
    log("=" * 60)
    log("ETAPA 1 — LIMPEZA E VALIDAÇÃO DOS DADOS")
    log("=" * 60)

    # 1. Carregar o CSV
    log(f"Carregando arquivo: {ARQUIVO_CSV}")
    try:
        df = pd.read_csv(ARQUIVO_CSV, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(ARQUIVO_CSV, encoding="latin-1")
        log("  Encoding latin-1 usado (arquivo contém caracteres especiais)")

    total_original = len(df)
    log(f"  Total de jogos carregados: {total_original}")

    # 2. Verificar e remover duplicatas
    duplicatas = df.duplicated().sum()
    df = df.drop_duplicates()
    log(f"  Duplicatas removidas: {duplicatas}")

    # 3. Verificar linhas com dados essenciais faltando
    colunas_essenciais = ["Date", "Home", "Away", "HG", "AG", "Res"]
    antes = len(df)
    df = df.dropna(subset=colunas_essenciais)
    incompletas = antes - len(df)
    log(f"  Linhas com dados essenciais faltando removidas: {incompletas}")

    # 4. Padronizar formato da data
    log("  Padronizando datas...")
    df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%Y", dayfirst=True)
    df["Season"] = df["Season"].astype(int)
    log(f"  Temporadas encontradas: {sorted(df['Season'].unique())}")

    # 5. Excluir temporadas COVID (2020 e 2021)
    antes = len(df)
    df = df[~df["Season"].isin([2020, 2021])]
    covid = antes - len(df)
    log(f"  Jogos excluídos (temporadas 2020/2021 COVID): {covid}")

    # 6. Padronizar nomes dos times
    log("  Padronizando nomes dos times...")
    nomes_antes_home = set(df["Home"].unique())
    nomes_antes_away = set(df["Away"].unique())

    df["Home"] = df["Home"].apply(padronizar_nome)
    df["Away"] = df["Away"].apply(padronizar_nome)

    todos_times = sorted(set(df["Home"].unique()) | set(df["Away"].unique()))
    log(f"  Times únicos após padronização: {len(todos_times)}")
    log(f"  Times: {todos_times}")

    # 7. Identificar rodadas e remover primeiras 5 por temporada
    log("  Identificando rodadas para excluir as 5 primeiras por temporada...")
    df = df.sort_values(["Season", "Date"]).reset_index(drop=True)

    # Numera os jogos sequencialmente dentro de cada temporada (0, 1, 2, ...)
    # A cada 10 jogos = 1 rodada (Brasileirao tem 20 times, 10 jogos/rodada)
    df["seq_jogo"] = df.groupby("Season").cumcount() + 1
    df["rodada_num"] = ((df["seq_jogo"] - 1) // 10) + 1

    antes = len(df)
    df_sem_inicio = df[df["rodada_num"] > 5].copy()
    primeiras5 = antes - len(df_sem_inicio)
    log(f"  Jogos removidos (primeiras 5 rodadas de cada temporada): {primeiras5}")

    df = df_sem_inicio

    # 8. Converter HG e AG para inteiro
    df["HG"] = df["HG"].astype(int)
    df["AG"] = df["AG"].astype(int)

    # 9. Verificar disponibilidade das odds
    log("  Verificando disponibilidade das odds...")
    pinnacle_ok = df[["PSCH", "PSCD", "PSCA"]].notna().all(axis=1).sum()
    bet365_ok   = df[["B365CH", "B365CD", "B365CA"]].notna().all(axis=1).sum()
    avg_ok      = df[["AvgCH", "AvgCD", "AvgCA"]].notna().all(axis=1).sum()
    log(f"    Pinnacle disponível em: {pinnacle_ok} jogos de {len(df)}")
    log(f"    Bet365 disponível em:   {bet365_ok} jogos de {len(df)}")
    log(f"    Odds médias disponíveis:{avg_ok} jogos de {len(df)}")

    # 10. Remover colunas auxiliares de rodada
    df = df.drop(columns=["seq_jogo", "rodada_num"])

    # 11. Salvar arquivo limpo
    df.to_csv(ARQUIVO_SAIDA, index=False, encoding="utf-8")
    log(f"\nArquivo limpo salvo em: {ARQUIVO_SAIDA}")

    # 12. Resumo final
    removidos_total = total_original - len(df)
    log("\n" + "=" * 60)
    log("RESUMO DA LIMPEZA")
    log("=" * 60)
    log(f"  Jogos originais:              {total_original}")
    log(f"  Duplicatas:                  -{duplicatas}")
    log(f"  Dados essenciais faltando:   -{incompletas}")
    log(f"  COVID (2020/2021):           -{covid}")
    log(f"  Primeiras 5 rodadas:         -{primeiras5}")
    log(f"  ---------------------------------")
    log(f"  Total removidos:             -{removidos_total}")
    log(f"  JOGOS VÁLIDOS PARA ANÁLISE:   {len(df)}")
    log("\nTemporadas disponíveis:")
    for season, grupo in df.groupby("Season"):
        log(f"  {season}: {len(grupo)} jogos")
    log("=" * 60)
    log("ETAPA 1 CONCLUÍDA COM SUCESSO!")

    salvar_log()

if __name__ == "__main__":
    executar_limpeza()
