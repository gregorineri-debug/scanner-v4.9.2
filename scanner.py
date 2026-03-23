import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import pytz
import statistics

st.set_page_config(page_title="Scanner V6 PRO", layout="wide")

st.title("🌍 Scanner Automático V6 PRO (MODO PROFISSIONAL)")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# =============================
# DATA
# =============================
data_input = st.date_input("📅 Selecione a data:", value=datetime.today())

data_alvo = data_input.strftime('%Y-%m-%d')

st.write(f"🔎 Buscando jogos do dia: **{data_alvo}**")

# =============================
# BUSCA DE JOGOS (CORRIGIDO UTC)
# =============================
@st.cache_data(ttl=600)
def get_matches(data_alvo):
    try:
        tz_sp = pytz.timezone("America/Sao_Paulo")

        start_sp = tz_sp.localize(datetime.strptime(data_alvo, "%Y-%m-%d"))
        end_sp = start_sp + timedelta(days=1)

        start_utc = start_sp.astimezone(pytz.utc)
        end_utc = end_sp.astimezone(pytz.utc)

        url = f"https://api.sofascore.com/api/v1/sport/football/events?from={int(start_utc.timestamp()*1000)}&to={int(end_utc.timestamp()*1000)}"

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
# DADOS DOS TIMES
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
# SCORE (REFINADO)
# =============================
def calculate_score(home, away):
    score = 50

    score += (home["win_rate"] - away["win_rate"]) * 40
    score += (home["avg_scored"] - away["avg_scored"]) * 15
    score += (away["avg_conceded"] - home["avg_conceded"]) * 15
    score += (home["consistency"] - away["consistency"]) * 10

    return max(0, min(100, score))

# =============================
# FILTRO V6 (INTELIGENTE)
# =============================
def is_valid_bet(score):
    # elimina apenas jogos MUITO equilibrados
    if 49 <= score <= 51:
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
    return "Sem aposta"

def get_strength(score):
    if score >= 70 or score <= 30:
        return "🔥 Forte"
    elif score >= 60 or score <= 40:
        return "✅ Boa"
    return "⚠️ Arriscada"

# =============================
# PROCESSAMENTO
# =============================
matches = get_matches(data_alvo)

results = []

st.write(f"📊 Total de jogos encontrados: {len(matches)}")

for m in matches:
    home = get_last_matches(m["home_id"])
    away = get_last_matches(m["away_id"])

    score = calculate_score(home, away)

    if not is_valid_bet(score):
        continue

    results.append({
        "Jogo": f"{m['home']} x {m['away']}",
        "Liga": m["tournament"],
        "Score": round(score, 2),
        "Aposta": get_prediction(score),
        "Força": get_strength(score)
    })

# =============================
# OUTPUT
# =============================
st.subheader("📊 Jogos Encontrados")
st.dataframe(pd.DataFrame(results), use_container_width=True)

if results:
    st.subheader("💰 Apostas Sugeridas")
    df = pd.DataFrame(results)

    st.dataframe(
        df[df["Aposta"] != "Sem aposta"],
        use_container_width=True
    )
else:
    st.warning("Nenhuma aposta válida encontrada (filtro V6).")
