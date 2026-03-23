import requests
import pandas as pd
import streamlit as st
from datetime import datetime, date
import pytz

st.set_page_config(page_title="Scanner V5 PRO", layout="wide")

st.title("🌍 Scanner Automático V5 PRO (MODO DECISÃO)")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# =============================
# SELETOR DE DATA
# =============================
data_input = st.date_input(
    "📅 Selecione a data dos jogos:",
    value=date.today()
)

data_alvo = data_input.strftime('%Y-%m-%d')
st.write(f"🔎 Buscando jogos do dia: **{data_alvo}**")

# =============================
# BUSCAR JOGOS
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
                    "tournament": event["tournament"]["name"],
                    "country": event["tournament"]["category"]["name"]
                })
            except:
                continue

        return matches

    except:
        return []

# =============================
# DADOS DOS TIMES
# =============================
@st.cache_data(ttl=600)
def get_last_matches(team_id):
    url = f"https://api.sofascore.com/api/v1/team/{team_id}/events/last/10"
    try:
        data = requests.get(url, headers=HEADERS).json()
        events = data.get("events", [])

        wins = 0
        total_games = 0
        goals_scored = []
        goals_conceded = []

        for e in events:
            try:
                is_home = e["homeTeam"]["id"] == team_id
                hs = e["homeScore"]["current"] or 0
                as_ = e["awayScore"]["current"] or 0

                total_games += 1

                if is_home:
                    goals_scored.append(hs)
                    goals_conceded.append(as_)
                    if hs > as_:
                        wins += 1
                else:
                    goals_scored.append(as_)
                    goals_conceded.append(hs)
                    if as_ > hs:
                        wins += 1
            except:
                continue

        if not goals_scored:
            return {
                "win_rate": 0.5,
                "avg_scored": 1,
                "avg_conceded": 1,
                "consistency": 0.5,
                "form": 0.5
            }

        win_rate = wins / max(1, total_games)
        avg_scored = sum(goals_scored) / len(goals_scored)
        avg_conceded = sum(goals_conceded) / len(goals_conceded)

        goal_diff = [gs - gc for gs, gc in zip(goals_scored, goals_conceded)]

        mean = sum(goal_diff) / len(goal_diff)
        variance = sum((x - mean) ** 2 for x in goal_diff) / len(goal_diff)
        consistency = 1 / (1 + variance)

        recent = goal_diff[:5]
        form = sum(1 if x > 0 else 0 for x in recent) / max(1, len(recent))

        return {
            "win_rate": win_rate,
            "avg_scored": avg_scored,
            "avg_conceded": avg_conceded,
            "consistency": consistency,
            "form": form
        }

    except:
        return {
            "win_rate": 0.5,
            "avg_scored": 1,
            "avg_conceded": 1,
            "consistency": 0.5,
            "form": 0.5
        }

# =============================
# H2H
# =============================
@st.cache_data(ttl=600)
def get_h2h(home_id, away_id):
    try:
        url = f"https://api.sofascore.com/api/v1/team/{home_id}/h2h/{away_id}/events"
        data = requests.get(url, headers=HEADERS).json()

        events = data.get("events", [])[:5]

        home_wins = 0

        for e in events:
            try:
                if e["homeScore"]["current"] > e["awayScore"]["current"]:
                    home_wins += 1
            except:
                continue

        return home_wins / max(1, len(events))

    except:
        return 0.5

# =============================
# DESFALQUES
# =============================
def get_injuries(team_id):
    return 0.1

# =============================
# SCORE (CORRIGIDO)
# =============================
def calculate_score(home, away, h2h):

    forma = home["win_rate"] - away["win_rate"]
    ataque = home["avg_scored"] - away["avg_scored"]
    defesa = away["avg_conceded"] - home["avg_conceded"]
    momento = home["form"] - away["form"]
    consistencia = home["consistency"] - away["consistency"]

    h2h_factor = (h2h - 0.5)

    score = (
        forma * 30 +
        ataque * 20 +
        defesa * 20 +
        momento * 15 +
        consistencia * 10 +
        h2h_factor * 5
    )

    # normalização correta
    score = 50 + score

    # limitar entre 0 e 100
    if score > 100:
        score = 100
    if score < 0:
        score = 0

    return score

def score_to_probability(score):
    return round(score / 100, 2)

# =============================
# FILTRO
# =============================
def is_valid_bet(score, home, away):
    if 45 <= score <= 55:
        return False
    if home["consistency"] < 0.3 or away["consistency"] < 0.3:
        return False
    return True

# =============================
# DECISÃO
# =============================
def get_prediction(score):
    if score >= 60:
        return "Casa vence"
    elif score <= 40:
        return "Visitante vence"
    else:
        return "Sem aposta"

def get_strength(score):
    if score >= 75 or score <= 25:
        return "🔥 Forte"
    elif score >= 65 or score <= 35:
        return "✅ Boa"
    else:
        return "⚠️ Arriscada"

# =============================
# PROCESSAMENTO
# =============================
matches = get_matches(data_alvo)
results = []

for m in matches:

    home = get_last_matches(m["home_id"])
    away = get_last_matches(m["away_id"])

    h2h = get_h2h(m["home_id"], m["away_id"])

    home["injuries"] = get_injuries(m["home_id"])
    away["injuries"] = get_injuries(m["away_id"])

    score = calculate_score(home, away, h2h)

    # ajuste leve por desfalques
    score -= (away["injuries"] - home["injuries"]) * 5

    if not is_valid_bet(score, home, away):
        continue

    prob = score_to_probability(score)
    prediction = get_prediction(score)
    strength = get_strength(score)

    results.append({
        "Jogo": f"{m['home']} x {m['away']}",
        "Liga": m["tournament"],
        "Score": round(score, 1),
        "Probabilidade": prob,
        "Aposta": prediction,
        "Força": strength
    })

# =============================
# OUTPUT
# =============================
if results:
    df = pd.DataFrame(results)

    st.subheader("📊 Todos os Jogos (Filtrados)")
    st.dataframe(df, use_container_width=True)

    st.subheader("💰 Apostas Recomendadas")
    st.dataframe(
        df[(df["Aposta"] != "Sem aposta") & (df["Força"] != "⚠️ Arriscada")],
        use_container_width=True
    )
else:
    st.warning("Nenhum jogo válido encontrado (filtro V5).")
