import requests
import pandas as pd
import streamlit as st
from datetime import date
import statistics

st.set_page_config(page_title="Scanner V6.5 Stable", layout="wide")

st.title("🌍 Scanner Automático V6.5 (ESTÁVEL)")

HEADERS = {"User-Agent": "Mozilla/5.0"}

data_input = st.date_input("📅 Data:", value=date.today())
data_alvo = data_input.strftime('%Y-%m-%d')

# =============================
# MATCHES
# =============================
@st.cache_data(ttl=600)
def get_matches(data_alvo):
    try:
        url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{data_alvo}"
        data = requests.get(url, headers=HEADERS).json()

        matches = []

        for event in data.get("events", []):
            matches.append({
                "home_id": event["homeTeam"]["id"],
                "away_id": event["awayTeam"]["id"],
                "home": event["homeTeam"]["name"],
                "away": event["awayTeam"]["name"],
            })

        return matches

    except:
        return []

# =============================
# FORMA
# =============================
@st.cache_data(ttl=600)
def get_form(team_id):
    try:
        url = f"https://api.sofascore.com/api/v1/team/{team_id}/events/last/10"
        data = requests.get(url, headers=HEADERS).json()

        events = data.get("events", [])

        wins = 0
        goals = []

        for e in events:
            hs = e["homeScore"]["current"]
            as_ = e["awayScore"]["current"]

            goals.append(hs)

            if hs > as_:
                wins += 1

        return {
            "win_rate": wins / max(1, len(events)),
            "avg_goals": sum(goals) / max(1, len(goals)),
            "consistency": 1 / (1 + statistics.pvariance(goals)) if len(goals) > 1 else 0.5
        }

    except:
        return {
            "win_rate": 0.5,
            "avg_goals": 1.0,
            "consistency": 0.5
        }

# =============================
# POSIÇÃO (SAFE)
# =============================
def get_position(team_id):
    try:
        url = f"https://api.sofascore.com/api/v1/team/{team_id}/standings/total"
        data = requests.get(url, headers=HEADERS).json()

        standings = data.get("standings", [])

        if standings:
            rows = standings[0].get("rows", [])

            for r in rows:
                if r["team"]["id"] == team_id:
                    return r.get("position", 10)

    except:
        pass

    return 10

# =============================
# RATING (SAFE)
# =============================
def get_player_rating(team_id):
    try:
        url = f"https://api.sofascore.com/api/v1/team/{team_id}/players"
        data = requests.get(url, headers=HEADERS).json()

        players = data.get("players", [])

        ratings = []

        for p in players:
            stats = p.get("statistics", {})
            r = stats.get("rating")

            if isinstance(r, (int, float)):
                ratings.append(r)

        return sum(ratings) / len(ratings) if ratings else 0.5

    except:
        return 0.5

# =============================
# DESFALQUES
# =============================
def get_injuries(team_id):
    try:
        url = f"https://api.sofascore.com/api/v1/team/{team_id}/squad"
        data = requests.get(url, headers=HEADERS).json()

        players = data.get("players", [])

        injured = sum(
            1 for p in players
            if p.get("injury", {}).get("active")
        )

        return injured / max(1, len(players))

    except:
        return 0.0

# =============================
# FORÇA (ELO SIMPLES)
# =============================
def elo_from_position(pos):
    if pos <= 3:
        return 1.2
    elif pos <= 6:
        return 1.1
    elif pos <= 12:
        return 1.0
    else:
        return 0.9

# =============================
# SCORE
# =============================
def score_model(home, away):
    score = (
        (home["win_rate"] - away["win_rate"]) * 20 +
        (home["avg_goals"] - away["avg_goals"]) * 10 +
        (home["consistency"] - away["consistency"]) * 10 +
        (home["rating"] - away["rating"]) * 10 +
        (away["injuries"] - home["injuries"]) * 10 +
        (home["elo"] - away["elo"]) * 10
    )

    return max(0, min(100, 50 + score))

# =============================
# PROBABILIDADE
# =============================
def prob(score):
    return score / 100

# =============================
# PREVISÃO
# =============================
def pick(score):
    if score >= 60:
        return "Casa"
    elif score <= 40:
        return "Visitante"
    return "Sem valor"

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
        "rating": get_player_rating(m["home_id"]),
        "injuries": get_injuries(m["home_id"]),
        "elo": elo_from_position(home_pos)
    }

    away = {
        **get_form(m["away_id"]),
        "rating": get_player_rating(m["away_id"]),
        "injuries": get_injuries(m["away_id"]),
        "elo": elo_from_position(away_pos)
    }

    score = score_model(home, away)
    p = prob(score)

    results.append({
        "Jogo": f"{m['home']} x {m['away']}",
        "Score": round(score, 1),
        "Probabilidade": round(p * 100, 1),
        "Pick": pick(score)
    })

# =============================
# OUTPUT
# =============================
if results:
    df = pd.DataFrame(results)
    st.dataframe(df, use_container_width=True)
else:
    st.warning("Nenhum jogo encontrado.")
