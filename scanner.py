import requests
import pandas as pd
import streamlit as st
from datetime import datetime, date
import pytz
import statistics

st.set_page_config(page_title="Scanner V8 PRO", layout="wide")

st.title("🚀 Scanner V8 PRO (VALOR ESPERADO)")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# =============================
# DATA
# =============================
data_input = st.date_input("📅 Data:", value=date.today())
data_alvo = data_input.strftime('%Y-%m-%d')

st.write(f"🔎 Data analisada: **{data_alvo}**")

# =============================
# ODDS (INPUT MANUAL)
# =============================
st.sidebar.title("🎯 Odds do mercado")

def get_odds(key):
    return st.sidebar.number_input(f"Odd {key}", value=2.0, step=0.01)

# =============================
# JOGOS
# =============================
@st.cache_data(ttl=600)
def get_matches(data_alvo):
    try:
        url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{data_alvo}"
        data = requests.get(url, headers=HEADERS).json()

        matches = []

        for event in data.get("events", []):
            try:
                matches.append({
                    "home_id": event["homeTeam"]["id"],
                    "away_id": event["awayTeam"]["id"],
                    "home": event["homeTeam"]["name"],
                    "away": event["awayTeam"]["name"],
                    "tournament": event["tournament"]["name"]
                })
            except:
                continue

        return matches

    except:
        return []

# =============================
# DADOS TIMES
# =============================
@st.cache_data(ttl=600)
def get_last_matches(team_id):
    try:
        url = f"https://api.sofascore.com/api/v1/team/{team_id}/events/last/10"
        data = requests.get(url, headers=HEADERS).json()

        events = data.get("events", [])

        wins = 0
        total = 0

        goals_scored = []
        goals_conceded = []

        for i, e in enumerate(events):
            weight = 1 - (i * 0.05)

            hs = e["homeScore"]["current"]
            as_ = e["awayScore"]["current"]

            if e["homeTeam"]["id"] == team_id:
                goals_scored.append(hs)
                goals_conceded.append(as_)
                if hs > as_:
                    wins += weight
            else:
                goals_scored.append(as_)
                goals_conceded.append(hs)
                if as_ > hs:
                    wins += weight

            total += weight

        win_rate = wins / total if total > 0 else 0.5

        avg_scored = sum(goals_scored)/len(goals_scored) if goals_scored else 1
        avg_conceded = sum(goals_conceded)/len(goals_conceded) if goals_conceded else 1

        consistency = 1 / (1 + statistics.pvariance(goals_scored + goals_conceded)) if len(goals_scored) > 1 else 0.5

        return {
            "win_rate": win_rate,
            "avg_scored": avg_scored,
            "avg_conceded": avg_conceded,
            "consistency": consistency
        }

    except:
        return {
            "win_rate": 0.5,
            "avg_scored": 1,
            "avg_conceded": 1,
            "consistency": 0.5
        }

# =============================
# SCORE
# =============================
def calculate_score(home, away):
    score = 50

    score += (home["win_rate"] - away["win_rate"]) * 35
    score += (home["avg_scored"] - away["avg_scored"]) * 10
    score += (away["avg_conceded"] - home["avg_conceded"]) * 10
    score += (home["consistency"] - away["consistency"]) * 10

    return max(0, min(100, score))

# =============================
# PROBABILIDADE
# =============================
def score_to_prob(score):
    return score / 100

# Odd justa
def fair_odds(prob):
    return 1 / prob if prob > 0 else 0

# EV (Valor Esperado)
def expected_value(prob, odd):
    return (prob * odd) - 1

# =============================
# DECISÃO
# =============================
def decision(ev):
    if ev > 0.05:
        return "🔥 Valor"
    elif ev > 0:
        return "✅ Margem"
    return "❌ Ruim"

# =============================
# EXECUÇÃO
# =============================
matches = get_matches(data_alvo)

results = []

st.write(f"📊 Jogos encontrados: {len(matches)}")

for i, m in enumerate(matches):
    home = get_last_matches(m["home_id"])
    away = get_last_matches(m["away_id"])

    score = calculate_score(home, away)
    prob = score_to_prob(score)
    odd_justa = fair_odds(prob)

    # odds input (exemplo simples por jogo)
    odd = st.sidebar.number_input(f"{m['home']} x {m['away']}", value=2.0 + (i*0.1))

    ev = expected_value(prob, odd)

    results.append({
        "Jogo": f"{m['home']} x {m['away']}",
        "Prob (%)": round(prob*100, 2),
        "Odd Justa": round(odd_justa, 2),
        "Odd Mercado": round(odd, 2),
        "EV": round(ev, 3),
        "Status": decision(ev)
    })

# =============================
# OUTPUT
# =============================
df = pd.DataFrame(results)

st.subheader("📊 Análise Completa")
st.dataframe(df, use_container_width=True)

st.subheader("💰 Apenas Valor")
st.dataframe(df[df["Status"] == "🔥 Valor"], use_container_width=True)
