import requests
import pandas as pd
import streamlit as st
from datetime import date
import statistics

st.set_page_config(page_title="Scanner V6.6 SAFE", layout="wide")

st.title("🌍 Scanner Automático V6.6 (À PROVA DE ERRO)")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# =============================
# DATA
# =============================
data_input = st.date_input("📅 Data:", value=date.today())
data_alvo = data_input.strftime('%Y-%m-%d')

# =============================
# FUNÇÃO SEGURA REQUEST
# =============================
def safe_request(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        return r.json()
    except:
        return {}

# =============================
# MATCHES (COM FALLBACK)
# =============================
def get_matches(data_alvo):

    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{data_alvo}"
    data = safe_request(url)

    matches = []

    for event in data.get("events", []):
        try:
            matches.append({
                "home_id": event["homeTeam"]["id"],
                "away_id": event["awayTeam"]["id"],
                "home": event["homeTeam"]["name"],
                "away": event["awayTeam"]["name"]
            })
        except:
            continue

    # 🔥 FALLBACK CASO NÃO VENHA NADA
    if not matches:
        matches.append({
            "home_id": 1,
            "away_id": 2,
            "home": "Time A (fallback)",
            "away": "Time B (fallback)"
        })

    return matches

# =============================
# FORMA
# =============================
def get_form(team_id):
    url = f"https://api.sofascore.com/api/v1/team/{team_id}/events/last/10"
    data = safe_request(url)

    events = data.get("events", [])

    wins = 0
    goals = []

    for e in events:
        try:
            hs = e["homeScore"]["current"]
            as_ = e["awayScore"]["current"]

            goals.append(hs)

            if hs > as_:
                wins += 1
        except:
            continue

    if not goals:
        goals = [1]

    return {
        "win_rate": wins / max(1, len(events)),
        "avg_goals": sum(goals) / len(goals),
        "consistency": 1 / (1 + statistics.pvariance(goals)) if len(goals) > 1 else 0.5
    }

# =============================
# POSIÇÃO (SAFE)
# =============================
def get_position(team_id):
    url = f"https://api.sofascore.com/api/v1/team/{team_id}/standings/total"
    data = safe_request(url)

    try:
        rows = data.get("standings", [])[0].get("rows", [])
        for r in rows:
            if r["team"]["id"] == team_id:
                return r.get("position", 10)
    except:
        pass

    return 10

# =============================
# RATING
# =============================
def get_rating(team_id):
    url = f"https://api.sofascore.com/api/v1/team/{team_id}/players"
    data = safe_request(url)

    ratings = []

    for p in data.get("players", []):
        try:
            r = p.get("statistics", {}).get("rating")
            if isinstance(r, (int, float)):
                ratings.append(r)
        except:
            continue

    if not ratings:
        return 0.5

    return sum(ratings) / len(ratings)

# =============================
# DESFALQUES
# =============================
def get_injuries(team_id):
    url = f"https://api.sofascore.com/api/v1/team/{team_id}/squad"
    data = safe_request(url)

    players = data.get("players", [])

    if not players:
        return 0.0

    injured = sum(
        1 for p in players
        if p.get("injury", {}).get("active")
    )

    return injured / len(players)

# =============================
# FORÇA (ELO SIMPLES)
# =============================
def elo(position):
    if position <= 3:
        return 1.2
    elif position <= 6:
        return 1.1
    elif position <= 12:
        return 1.0
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
# RESULTADO
# =============================
def prediction(score):
    if score >= 60:
        return "Casa"
    elif score <= 40:
        return "Visitante"
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
        "rating": get_rating(m["home_id"]),
        "injuries": get_injuries(m["home_id"]),
        "elo": elo(home_pos)
    }

    away = {
        **get_form(m["away_id"]),
        "rating": get_rating(m["away_id"]),
        "injuries": get_injuries(m["away_id"]),
        "elo": elo(away_pos)
    }

    score = score_model(home, away)

    results.append({
        "Jogo": f"{m['home']} x {m['away']}",
        "Score": round(score, 1),
        "Pick": prediction(score)
    })

# =============================
# OUTPUT
# =============================
if results:
    df = pd.DataFrame(results)
    st.dataframe(df, use_container_width=True)
else:
    st.warning("Nenhum dado disponível — fallback ativado.")
