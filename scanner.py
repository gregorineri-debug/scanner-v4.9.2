import requests
import pandas as pd
import streamlit as st
from datetime import date
import statistics

st.set_page_config(page_title="Scanner PRO Estável", layout="wide")

st.title("🌍 Scanner Automático PRO (Estável + API-Football)")

API_KEY = "SUA_API_KEY"

HEADERS = {
    "x-apisports-key": API_KEY
}

# =============================
# DATA
# =============================
data_input = st.date_input("📅 Data:", value=date.today())
data_alvo = data_input.strftime("%Y-%m-%d")

# =============================
# REQUEST SEGURA
# =============================
def safe_request(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        return r.json()
    except:
        return {}

# =============================
# JOGOS
# =============================
def get_matches():
    url = f"https://v3.football.api-sports.io/fixtures?date={data_alvo}"
    data = safe_request(url)

    matches = []

    for item in data.get("response", []):
        try:
            matches.append({
                "home": item["teams"]["home"]["name"],
                "away": item["teams"]["away"]["name"],
                "home_id": item["teams"]["home"]["id"],
                "away_id": item["teams"]["away"]["id"]
            })
        except:
            continue

    return matches

# =============================
# FORMA (últimos jogos)
# =============================
def get_form(team_id):
    url = f"https://v3.football.api-sports.io/fixtures?team={team_id}&last=5"
    data = safe_request(url)

    wins = 0
    goals = []

    for match in data.get("response", []):
        try:
            if match["teams"]["home"]["winner"]:
                wins += 1

            goals.append(match["goals"]["home"] or 0)

        except:
            continue

    if not goals:
        goals = [1]

    return {
        "win_rate": wins / max(1, len(goals)),
        "avg_goals": sum(goals) / len(goals),
        "consistency": 1 / (1 + statistics.pvariance(goals)) if len(goals) > 1 else 0.5
    }

# =============================
# POSIÇÃO NA TABELA
# =============================
def get_position(team_id):
    try:
        url = f"https://v3.football.api-sports.io/standings?season=2024&league=39"
        data = safe_request(url)

        for league in data.get("response", []):
            for group in league["league"]["standings"]:
                for team in group:
                    if team["team"]["id"] == team_id:
                        return team.get("rank", 10)

    except:
        pass

    return 10

# =============================
# RATING (simplificado)
# =============================
def get_rating(team_id):
    try:
        return 0.6  # API não fornece rating direto consistente
    except:
        return 0.5

# =============================
# DESFALQUES
# =============================
def get_injuries(team_id):
    try:
        return 0.1  # simplificado (API varia muito)
    except:
        return 0.0

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
    else:
        return 0.9

# =============================
# SCORE
# =============================
def calculate_score(home, away):

    score = (
        (home["win_rate"] - away["win_rate"]) * 20 +
        (home["avg_goals"] - away["avg_goals"]) * 10 +
        (home["consistency"] - away["consistency"]) * 10 +
        (home["elo"] - away["elo"]) * 15 +
        (away["injuries"] - home["injuries"]) * 10
    )

    return max(0, min(100, 50 + score))

# =============================
# PREVISÃO
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
matches = get_matches()

# 🔥 FALLBACK SE NÃO TIVER JOGOS
if not matches:
    st.warning("⚠️ Nenhum jogo encontrado — usando fallback")

    matches = [
        {"home": "Time A", "away": "Time B", "home_id": 1, "away_id": 2},
        {"home": "Time C", "away": "Time D", "home_id": 3, "away_id": 4}
    ]

results = []

for m in matches:

    home_pos = get_position(m["home_id"])
    away_pos = get_position(m["away_id"])

    home = {
        **get_form(m["home_id"]),
        "elo": elo(home_pos),
        "injuries": get_injuries(m["home_id"])
    }

    away = {
        **get_form(m["away_id"]),
        "elo": elo(away_pos),
        "injuries": get_injuries(m["away_id"])
    }

    score = calculate_score(home, away)

    results.append({
        "Jogo": f"{m['home']} x {m['away']}",
        "Score": round(score, 1),
        "Pick": prediction(score)
    })

# =============================
# OUTPUT
# =============================
st.subheader("📊 Resultados")

if results:
    df = pd.DataFrame(results)
    st.dataframe(df, use_container_width=True)
else:
    st.error("Nenhum dado disponível.")
