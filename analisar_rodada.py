# -*- coding: utf-8 -*-
"""
Analisador de Picks - Protocolo Final
Uso: python analisar_rodada.py
Informe os jogos da rodada e o script retorna os picks aprovados.
"""

import pandas as pd
import requests
import os
from datetime import datetime

CSV_PATH    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dados", "BRA.csv")
CSV_URL     = "https://www.football-data.co.uk/new/BRA.csv"
ODD_MIN_OVER15   = 1.55
ODD_MIN_UNDER25  = 1.75

# ── padronizacao de nomes (igual etapa1) ─────────────────────────────────────
NOMES = {
    'atletico mg': 'Atletico Mineiro', 'atletico-mg': 'Atletico Mineiro',
    'atletico mineiro': 'Atletico Mineiro', 'galo': 'Atletico Mineiro',
    'atletico go': 'Atletico GO', 'atletico-go': 'Atletico GO',
    'atletico goianiense': 'Atletico GO',
    'atletico pr': 'Atletico Paranaense', 'atletico-pr': 'Atletico Paranaense',
    'athletico': 'Atletico Paranaense', 'athletico pr': 'Atletico Paranaense',
    'athletico paranaense': 'Atletico Paranaense',
    'flamengo': 'Flamengo', 'flamengo rj': 'Flamengo',
    'fluminense': 'Fluminense',
    'vasco': 'Vasco', 'vasco da gama': 'Vasco',
    'botafogo': 'Botafogo', 'botafogo rj': 'Botafogo',
    'palmeiras': 'Palmeiras',
    'corinthians': 'Corinthians',
    'santos': 'Santos',
    'sao paulo': 'Sao Paulo', 'são paulo': 'Sao Paulo',
    'gremio': 'Gremio', 'grêmio': 'Gremio',
    'internacional': 'Internacional',
    'cruzeiro': 'Cruzeiro',
    'bahia': 'Bahia',
    'fortaleza': 'Fortaleza',
    'sport': 'Sport Recife', 'sport recife': 'Sport Recife',
    'ceara': 'Ceara', 'ceará': 'Ceara',
    'coritiba': 'Coritiba',
    'goias': 'Goias', 'goiás': 'Goias',
    'bragantino': 'Bragantino', 'rb bragantino': 'Bragantino',
    'red bull bragantino': 'Bragantino',
    'juventude': 'Juventude',
    'criciuma': 'Criciuma', 'cricíuma': 'Criciuma',
    'cuiaba': 'Cuiaba', 'cuiabá': 'Cuiaba',
    'america mg': 'America Mineiro', 'america mineiro': 'America Mineiro',
    'america-mg': 'America Mineiro',
    'chapecoense': 'Chapecoense',
    'vitoria': 'Vitoria', 'vitória': 'Vitoria',
    'avai': 'Avai', 'avaí': 'Avai',
    'ponte preta': 'Ponte Preta',
    'figueirense': 'Figueirense',
    'nautico': 'Nautico', 'náutico': 'Nautico',
    'portuguesa': 'Portuguesa',
    'parana': 'Parana', 'paraná': 'Parana',
    'santa cruz': 'Santa Cruz',
    'mirassol': 'Mirassol',
    'lanterna': 'Lanterna',
    'remo': 'Remo',
    'chapecoense': 'Chapecoense-SC', 'chapecoense sc': 'Chapecoense-SC',
    'chapecoense-sc': 'Chapecoense-SC',
}

def padronizar(nome):
    return NOMES.get(nome.strip().lower(), nome.strip().title())

def times_disponiveis(df):
    times = sorted(set(df['Home'].unique()) | set(df['Away'].unique()))
    return times

def buscar_time(nome_input, df):
    """Tenta encontrar o time no DataFrame, com sugestoes se nao achar."""
    padronizado = padronizar(nome_input)
    todos = times_disponiveis(df)
    if padronizado in todos:
        return padronizado
    # busca parcial
    sugestoes = [t for t in todos if nome_input.lower() in t.lower() or
                 t.lower() in nome_input.lower()]
    if len(sugestoes) == 1:
        return sugestoes[0]
    if sugestoes:
        print(f"  '{nome_input}' nao encontrado. Sugestoes:")
        for i, s in enumerate(sugestoes[:5], 1):
            print(f"    {i}. {s}")
        escolha = input("  Digite o numero ou o nome exato: ").strip()
        if escolha.isdigit() and 1 <= int(escolha) <= len(sugestoes):
            return sugestoes[int(escolha)-1]
        return padronizar(escolha)
    print(f"  '{nome_input}' nao encontrado no historico.")
    print(f"  Times disponíveis: {', '.join(todos[:10])}...")
    return None

# ── download e limpeza ────────────────────────────────────────────────────────

def baixar_csv():
    print("Atualizando dados do Brasileirao...")
    try:
        r = requests.get(CSV_URL, timeout=15)
        r.raise_for_status()
        with open(CSV_PATH, 'wb') as f:
            f.write(r.content)
        print("  Dados atualizados com sucesso.")
    except Exception as e:
        print(f"  Nao foi possivel atualizar ({e}). Usando arquivo local.")

def carregar_e_limpar():
    df = pd.read_csv(CSV_PATH, encoding='utf-8', on_bad_lines='skip')
    df = df.dropna(subset=['HG', 'AG', 'Home', 'Away'])
    df['HG'] = pd.to_numeric(df['HG'], errors='coerce')
    df['AG'] = pd.to_numeric(df['AG'], errors='coerce')
    df = df.dropna(subset=['HG', 'AG'])
    df['HG'] = df['HG'].astype(int)
    df['AG'] = df['AG'].astype(int)
    df['Gols'] = df['HG'] + df['AG']
    df['Season'] = df['Season'].astype(int)

    # excluir COVID
    df = df[~df['Season'].isin([2020, 2021])]

    # padronizar nomes
    df['Home'] = df['Home'].apply(padronizar)
    df['Away'] = df['Away'].apply(padronizar)

    # converter data
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Date'])
    df = df.sort_values(['Season', 'Date']).reset_index(drop=True)

    # excluir primeiras 5 rodadas de cada time por temporada (contexto insuficiente)
    # sera tratado no calculo de estatisticas com minimo de 5 jogos

    return df

# ── calculo de estatisticas ───────────────────────────────────────────────────

def stats_mandante(df, time, data_corte, n=10, min_jogos=5):
    """Ultimos n jogos do time EM CASA antes da data de corte."""
    historico = df[
        (df['Home'] == time) &
        (df['Date'] < data_corte)
    ].tail(n)

    if len(historico) < min_jogos:
        return None

    gols_m = historico['HG'].mean()
    gols_sof = historico['AG'].mean()
    over15 = (historico['Gols'] > 1).mean() * 100
    under25 = (historico['Gols'] < 3).mean() * 100
    vitorias = (historico['HG'] > historico['AG']).mean() * 100
    wins5 = (historico.tail(5)['HG'] > historico.tail(5)['AG']).sum()
    losses5 = (historico.tail(5)['HG'] < historico.tail(5)['AG']).sum()

    return {
        'n': len(historico),
        'media_marc': round(gols_m, 2),
        'media_sof': round(gols_sof, 2),
        'over15_pct': round(over15, 1),
        'under25_pct': round(under25, 1),
        'vitorias_pct': round(vitorias, 1),
        'wins5': int(wins5),
        'losses5': int(losses5),
    }

def stats_visitante(df, time, data_corte, n=10, min_jogos=5):
    """Ultimos n jogos do time FORA antes da data de corte."""
    historico = df[
        (df['Away'] == time) &
        (df['Date'] < data_corte)
    ].tail(n)

    if len(historico) < min_jogos:
        return None

    gols_m = historico['AG'].mean()
    gols_sof = historico['HG'].mean()
    over15 = (historico['Gols'] > 1).mean() * 100
    under25 = (historico['Gols'] < 3).mean() * 100
    vitorias = (historico['AG'] > historico['HG']).mean() * 100
    wins5 = (historico.tail(5)['AG'] > historico.tail(5)['HG']).sum()
    losses5 = (historico.tail(5)['AG'] < historico.tail(5)['HG']).sum()

    return {
        'n': len(historico),
        'media_marc': round(gols_m, 2),
        'media_sof': round(gols_sof, 2),
        'over15_pct': round(over15, 1),
        'under25_pct': round(under25, 1),
        'vitorias_pct': round(vitorias, 1),
        'wins5': int(wins5),
        'losses5': int(losses5),
    }

def stats_h2h(df, mandante, visitante, data_corte, n=5, min_h2h=3):
    """Ultimos n confrontos diretos entre os dois times."""
    h2h = df[
        (
            ((df['Home'] == mandante) & (df['Away'] == visitante)) |
            ((df['Home'] == visitante) & (df['Away'] == mandante))
        ) &
        (df['Date'] < data_corte)
    ].tail(n)

    if len(h2h) < min_h2h:
        return {'suficiente': False, 'n': len(h2h)}

    under25 = (h2h['Gols'] < 3).mean() * 100
    media_gols = h2h['Gols'].mean()

    return {
        'suficiente': True,
        'n': len(h2h),
        'under25_pct': round(under25, 1),
        'media_gols': round(media_gols, 2),
    }

# ── verificacao dos criterios ─────────────────────────────────────────────────

def verificar_over15(sm, sv):
    if sm is None or sv is None:
        return False, "historico insuficiente"
    crit1 = sm['over15_pct'] > 65 and sv['over15_pct'] > 65
    crit2 = sm['media_marc'] > 1.5 or sv['media_marc'] > 1.5
    if crit1 and crit2:
        return True, f"m_Over15={sm['over15_pct']}% | v_Over15={sv['over15_pct']}% | m_media={sm['media_marc']} | v_media={sv['media_marc']}"
    razao = []
    if not crit1:
        razao.append(f"Over15: m={sm['over15_pct']}% v={sv['over15_pct']}% (precisa >65% ambos)")
    if not crit2:
        razao.append(f"media_marc: m={sm['media_marc']} v={sv['media_marc']} (precisa >1.5 algum)")
    return False, " | ".join(razao)

def verificar_mandante_dom(sm):
    if sm is None:
        return False, "historico insuficiente"
    if sm['vitorias_pct'] >= 75:
        return True, f"m_vitorias={sm['vitorias_pct']}%"
    return False, f"m_vitorias={sm['vitorias_pct']}% (precisa >=75%)"

def verificar_resultado_forma(sm, sv, odd_m, odd_v):
    if sm is None or sv is None:
        return False, "historico insuficiente", None
    if odd_m is None or odd_v is None:
        return False, "odds nao informadas (necessario para identificar favorito)", None

    if odd_m < odd_v:
        favorito = 'mandante'
        wins_fav5   = sm['wins5']
        losses_adv5 = sv['losses5']
    else:
        favorito = 'visitante'
        wins_fav5   = sv['wins5']
        losses_adv5 = sm['losses5']

    if wins_fav5 >= 5 and losses_adv5 >= 2:
        return True, f"favorito={favorito} | wins_fav5={wins_fav5} | losses_adv5={losses_adv5}", favorito
    razao = []
    if wins_fav5 < 5:
        razao.append(f"wins_fav5={wins_fav5} (precisa >=5)")
    if losses_adv5 < 2:
        razao.append(f"losses_adv5={losses_adv5} (precisa >=2)")
    return False, " | ".join(razao), favorito

def verificar_under25_h2h(sm, sv, h2h):
    if sm is None or sv is None:
        return False, "historico insuficiente"
    if not h2h.get('suficiente', False):
        return False, f"H2H insuficiente ({h2h.get('n',0)} confrontos, precisa >=3)"
    crit1 = h2h['under25_pct'] >= 60
    crit2 = sm['under25_pct'] > 60 and sv['under25_pct'] > 60
    if crit1 and crit2:
        return True, f"H2H_U25={h2h['under25_pct']}% | m_U25={sm['under25_pct']}% | v_U25={sv['under25_pct']}%"
    razao = []
    if not crit1:
        razao.append(f"H2H_U25={h2h['under25_pct']}% (precisa >=60%)")
    if not crit2:
        razao.append(f"Under25: m={sm['under25_pct']}% v={sv['under25_pct']}% (precisa >60% ambos)")
    return False, " | ".join(razao)

# ── analise de um jogo ────────────────────────────────────────────────────────

def analisar_jogo(df, mandante, visitante, odd_m=None, odd_v=None, data_corte=None):
    if data_corte is None:
        data_corte = datetime.now()

    print(f"\n{'='*55}")
    print(f"  {mandante} x {visitante}")
    print(f"{'='*55}")

    sm  = stats_mandante(df, mandante, data_corte)
    sv  = stats_visitante(df, visitante, data_corte)
    h2h = stats_h2h(df, mandante, visitante, data_corte)

    if sm is None:
        print(f"  ATENCAO: {mandante} tem menos de 5 jogos em casa no historico recente.")
    if sv is None:
        print(f"  ATENCAO: {visitante} tem menos de 5 jogos fora no historico recente.")

    # verificar todos os criterios
    ok_over15, info_over15 = verificar_over15(sm, sv)
    ok_mand,   info_mand   = verificar_mandante_dom(sm)
    ok_forma,  info_forma, favorito_forma = verificar_resultado_forma(sm, sv, odd_m, odd_v)
    ok_under,  info_under  = verificar_under25_h2h(sm, sv, h2h)

    # aplicar prioridade (sem empate, sem mandante dom solo)
    mercados_ativos = []
    if ok_forma:  mercados_ativos.append(('ResultadoForma', info_forma))
    if ok_over15: mercados_ativos.append(('Over15',         info_over15))
    if ok_under:  mercados_ativos.append(('Under25H2H',     info_under))
    # MandanteDom: so entra se estiver sozinho como confirmacao interna
    # mas NAO e publicado solo — serve apenas para info
    if ok_mand and not mercados_ativos:
        pass  # MandanteDom solo: descartado pelo protocolo

    # pick final (primeiro da lista de prioridade)
    pick = mercados_ativos[0] if mercados_ativos else None

    # exibir resultado
    if pick:
        mercado, detalhe = pick
        print(f"\n  PICK APROVADO: {mercado}")
        print(f"  Detalhe: {detalhe}")
        if mercado == 'Over15':
            print(f"  Odd minima: {ODD_MIN_OVER15} | Verificar na casa antes de apostar")
        elif mercado == 'Under25H2H':
            print(f"  Odd minima: {ODD_MIN_UNDER25} | Verificar na casa antes de apostar")
        elif mercado == 'ResultadoForma':
            print(f"  Odd minima: qualquer (favorito: {favorito_forma})")
            if odd_m and odd_v:
                odd_usar = odd_m if favorito_forma == 'mandante' else odd_v
                print(f"  Odd atual do favorito: {odd_usar}")
        if len(mercados_ativos) > 1:
            outros = [m for m, _ in mercados_ativos[1:]]
            print(f"  (outros criterios tambem ativados mas descartados pela prioridade: {', '.join(outros)})")
    else:
        print(f"\n  Sem pick para este jogo.")
        # mostrar o que faltou para cada criterio
        print(f"  Over 1.5:       {info_over15}")
        print(f"  Resultado Forma: {info_forma}")
        print(f"  Under 2.5+H2H:  {info_under}")
        if ok_mand:
            print(f"  Mandante Dom.:  ATIVADO mas descartado (nao publicar solo)")

    # estatisticas detalhadas
    print(f"\n  --- Estatisticas do historico ---")
    if sm:
        print(f"  {mandante} (casa, {sm['n']} jogos):")
        print(f"    Over1.5={sm['over15_pct']}% | Under2.5={sm['under25_pct']}% | Vitorias={sm['vitorias_pct']}%")
        print(f"    Media marc={sm['media_marc']} | Wins5={sm['wins5']} | Losses5={sm['losses5']}")
    if sv:
        print(f"  {visitante} (fora, {sv['n']} jogos):")
        print(f"    Over1.5={sv['over15_pct']}% | Under2.5={sv['under25_pct']}% | Vitorias={sv['vitorias_pct']}%")
        print(f"    Media marc={sv['media_marc']} | Wins5={sv['wins5']} | Losses5={sv['losses5']}")
    if h2h.get('suficiente'):
        print(f"  H2H ({h2h['n']} jogos): Under2.5={h2h['under25_pct']}% | Media gols={h2h['media_gols']}")
    else:
        print(f"  H2H: insuficiente ({h2h.get('n',0)} confrontos encontrados)")

    return pick

# ── interface principal ───────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  ANALISADOR DE PICKS — PROTOCOLO FINAL")
    print("  Brasileirao Serie A")
    print("=" * 55)

    # atualizar dados
    atualizar = input("\nAtualizar BRA.csv agora? (s/n): ").strip().lower()
    if atualizar == 's':
        baixar_csv()

    print("Carregando dados...")
    df = carregar_e_limpar()
    print(f"  {len(df)} jogos carregados ({df['Season'].min()}-{df['Season'].max()})")
    print(f"  Times no historico: {df['Home'].nunique()}")

    picks_rodada = []

    print("\nInforme os jogos da rodada.")
    print("Formato: Mandante x Visitante (ou so Enter para terminar)")
    print("Para Resultado Forma, informe as odds: Mandante x Visitante | odd_m | odd_v")
    print("Exemplo: Flamengo x Palmeiras | 1.80 | 2.10\n")

    while True:
        entrada = input("Jogo: ").strip()
        if not entrada:
            break

        # parsear entrada
        odd_m = odd_v = None
        if '|' in entrada:
            partes = [p.strip() for p in entrada.split('|')]
            jogo_str = partes[0]
            try:
                odd_m = float(partes[1].replace(',', '.'))
                odd_v = float(partes[2].replace(',', '.'))
            except:
                print("  Odds invalidas. Continuando sem odds (Resultado Forma nao sera verificado).")
        else:
            jogo_str = entrada

        if ' x ' in jogo_str.lower():
            partes_jogo = jogo_str.lower().split(' x ')
            nome_m = partes_jogo[0].strip()
            nome_v = partes_jogo[1].strip()
        elif 'x' in jogo_str:
            partes_jogo = jogo_str.split('x')
            nome_m = partes_jogo[0].strip()
            nome_v = partes_jogo[1].strip()
        else:
            print("  Formato invalido. Use: Mandante x Visitante")
            continue

        mandante  = buscar_time(nome_m, df)
        visitante = buscar_time(nome_v, df)

        if mandante is None or visitante is None:
            print("  Jogo ignorado por time nao encontrado.")
            continue

        pick = analisar_jogo(df, mandante, visitante, odd_m, odd_v)
        if pick:
            picks_rodada.append((mandante, visitante, pick[0]))

    # resumo final
    print(f"\n{'='*55}")
    print(f"  RESUMO DA RODADA")
    print(f"{'='*55}")
    if picks_rodada:
        print(f"  {len(picks_rodada)} pick(s) aprovado(s):\n")
        for m, v, merc in picks_rodada:
            if merc == 'Over15':
                print(f"  -> {m} x {v} | OVER 1.5 | Odd minima: {ODD_MIN_OVER15}")
            elif merc == 'Under25H2H':
                print(f"  -> {m} x {v} | UNDER 2.5 | Odd minima: {ODD_MIN_UNDER25}")
            else:
                print(f"  -> {m} x {v} | RESULTADO FORMA | Qualquer odd")
        print(f"\n  Lembre-se: so aposte se a odd real >= odd minima.")
        print(f"  Registre na planilha: Registro_Picks_AoVivo.xlsx")
    else:
        print("  Nenhum pick aprovado nesta rodada.")
    print()

if __name__ == '__main__':
    main()
