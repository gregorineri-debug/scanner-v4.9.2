import requests
import pandas as pd
import streamlit as st
from datetime import date
import statistics

st.set_page_config(page_title="Scanner V6.5 PRO", layout="wide")

st.title("🌍 Scanner Automático V6.5 PRO (ELITE MODE)")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# =============================
# DATA
# =============================
data_input = st.date_input("📅 Data dos jogos:", value=date.today())
data_alvo = data_input.strftime('%Y-%m-%d')

st.write(f"🔎 Jogos do dia: **{data_alvo}**")

# =============================
# MATCHES
# =============================
@st.cache_data(ttl=600)
def get_matches(data_alvo):
    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{data_alvo}"
    data = requests.get(url, headers=HEADERS).json()

    matches = []

    for event in data.get("events", []):
        matches.append({
            "home_id": event["homeTeam"]["id"],
            "away_id": event["awayTeam"]["id"],
            "home": event["homeTeam"]["name"],
            "away": event["awayTeam"]["name"],
            "tournament": event["tournament"]["name"]
        })

    return matches

# =============================
# FORMA
# =============================
@st.cache_data(ttl=600)
def get_form(team_id):
    url = f"https://api.sofascore.com/api/v1/team/{team_id}/events/last/10"
    data = requests.get(url, headers=HEADERS).json()
    events = data.get("events", [])

    wins = 0
    scored = []
    conceded = []

    for e in events:
        hs = e["homeScore"]["current"]
        as_ = e["awayScore"]["current"]

        if hs > as_:
            wins += 1

        scored.append(hs)
        conceded.append(as_)

    return {
        "win_rate": wins / max(1, len(events)),
        "avg_scored": sum(scored) / max(1, len(scored)),
        "avg_conceded": sum(conceded) / max(1, len(conceded)),
        "consistency": 1 / (1 + statistics.pvariance(scored)) if len(scored) > 1 else 0.5
    }

# =============================
# TABELA / POSIÇÃO
# =============================
@st.cache_data(ttl=600)
def get_position(team_id):
    try:
        url = f"https://api.sofascore.com/api/v1/team/{team_id}/standings/total"
        data = requests.get(url, headers=HEADERS).json()

        standings = data.get("standings", [])
        if standings:
            table = standings[0].get("rows", [])
            for team in table:
                if team["team"]["id"] == team_id:
                    return team["position"]
    except:
        pass

    return 10

# =============================
# RATING JOGADORES
# =============================
@st.cache_data(ttl=600)
def get_player_rating(team_id):
    try:
        url = f"https://api.sofascore.com/api/v1/team/{team_id}/players"
        data = requests.get(url, headers=HEADERS).json()

        ratings = []

        for p in data.get("players", []):
            r = p.get("statistics", {}).get("rating")
            if r:
                ratings.append(r)

        return sum(ratings) / len(ratings) if ratings else 0.5
    except:
        return 0.5

# =============================
# DESFALQUES
# =============================
@st.cache_data(ttl=600)
def get_injuries(team_id):
    try:
        url = f"https://api.sofascore.com/api/v1/team/{team_id}/squad"
        data = requests.get(url, headers=HEADERS).json()

        players = data.get("players", [])

        injured = sum(1 for p in players if p.get("injury", {}).get("active"))

        return injured / max(1, len(players))
    except:
        return 0.0

# =============================
# FORÇA ELO SIMPLIFICADO
# =============================
def team_strength(position):
    if position <= 3:
        return 1.2
    elif position <= 6:
        return 1.1
    elif position <= 12:
        return 1.0
    else:
        return 0.9

# =============================
# ODDS INPUT (SIMULADO)
# =============================
def get_odds():
    # você pode trocar por API depois
    return 2.00, 3.20  # casa, empate/visitante

# =============================
# SCORE
# =============================
def calculate_score(home, away):
    score = (
        (home["win_rate"] - away["win_rate"]) * 20 +
        (home["avg_scored"] - away["avg_scored"]) * 10 +
        (away["avg_conceded"] - home["avg_conceded"]) * 10 +
        (home["consistency"] - away["consistency"]) * 10 +
        (home["player_rating"] - away["player_rating"]) * 15 +
        (away["injuries"] - home["injuries"]) * 10 +
        (home["elo"] - away["elo"]) * 15
    )

    score = max(0, min(100, 50 + score))
    return score

# =============================
# PROBABILIDADE
# =============================
def probability(score):
    return score / 100

# =============================
# EXPECTED VALUE (EV)
# =============================
def expected_value(prob, odds):
    return (prob * odds) - 1

# =============================
# RESULTADO
# =============================
def prediction(score):
    if score >= 60:
        return "Casa vence"
    elif score <= 40:
        return "Visitante vence"
    else:
        return "Sem aposta"

# =============================
# EXECUÇÃO
# =============================
matches = get_matches(data_alvo)

results = []

for m in matches:

    home_pos = get_position(m["home_id"])
    away_pos = get_position(m["away_id"])

    home = {
        **get_form(m["home_id"]),
        "player_rating": get_player_rating(m["home_id"]),
        "injuries": get_injuries(m["home_id"]),
        "elo": team_strength(home_pos)
    }

    away = {
        **get_form(m["away_id"]),
        "player_rating": get_player_rating(m["away_id"]),
        "injuries": get_injuries(m["away_id"]),
        "elo": team_strength(away_pos)
    }

    score = calculate_score(home, away)
    prob = probability(score)

    home_odds, away_odds = get_odds()

    ev_home = expected_value(prob, home_odds)
    ev_away = expected_value(1 - prob, away_odds)

    results.append({
        "Jogo": f"{m['home']} x {m['away']}",
        "Score": round(score, 2),
        "Prob (%)": round(prob * 100, 1),
        "Odds Casa": home_odds,
        "EV Casa": round(ev_home, 2),
        "Odds Visitante": away_odds,
        "EV Visitante": round(ev_away, 2),
        "Pick": prediction(score)
    })

# =============================
# OUTPUT
# =============================
if results:
    df = pd.DataFrame(results)

    st.subheader("📊 Jogos")
    st.dataframe(df, use_container_width=True)

    st.subheader("💰 Melhores oportunidades (EV > 0)")
    st.dataframe(
        df[(df["EV Casa"] > 0) | (df["EV Visitante"] > 0)],
        use_container_width=True
    )
else:
    st.warning("Nenhum jogo encontrado.")
