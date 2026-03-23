import requests
import pandas as pd
import streamlit as st
from datetime import datetime, date
import pytz
import statistics

st.set_page_config(page_title="Scanner V5 PRO+", layout="wide")

st.title("🌍 Scanner V5 PRO+ (Modelo Completo)")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# =============================
# DATA
# =============================
data_input = st.date_input("📅 Selecione a data:", value=date.today())
data_alvo = data_input.strftime('%Y-%m-%d')

# =============================
# CACHE
# =============================
@st.cache_data(ttl=600)
def safe_get(url):
    try:
        return requests.get(url, headers=HEADERS, timeout=10).json()
    except:
        return {}

# =============================
# JOGOS
# =============================
@st.cache_data(ttl=600)
def get_matches(data_alvo):

    tz = pytz.timezone("America/Sao_Paulo")
    start = tz.localize(datetime.strptime(data_alvo, "%Y-%m-%d"))

    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{data_alvo}"
    data = safe_get(url)

    matches = []

    for e in data.get("events", []):
        try:
            matches.append({
                "home_id": e["homeTeam"]["id"],
                "away_id": e["awayTeam"]["id"],
                "home": e["homeTeam"]["name"],
                "away": e["awayTeam"]["name"],
                "league": e["tournament"]["name"],
                "league_level": e["tournament"].get("category", {}).get("name", "unknown")
            })
        except:
            continue

    return matches

# =============================
# POSIÇÃO NA TABELA (simulado)
# =============================
def get_position(team_id):
    try:
        url = f"https://api.sofascore.com/api/v1/team/{team_id}/rankings"
        data = safe_get(url)

        # fallback (pois nem sempre disponível)
        return 5
    except:
        return 10

# =============================
# ELO
# =============================
def get_elo(position):
    if position <= 3:
        return 1.2
    elif position <= 6:
        return 1.1
    elif position <= 12:
        return 1.0
    return 0.9

# =============================
# FORMA
# =============================
@st.cache_data(ttl=600)
def get_last_matches(team_id):
    url = f"https://api.sofascore.com/api/v1/team/{team_id}/events/last/10"
    data = safe_get(url)

    events = data.get("events", [])

    wins = 0
    goals = []

    for e in events:
        try:
            is_home = e["homeTeam"]["id"] == team_id
            hs = e["homeScore"]["current"] or 0
            as_ = e["awayScore"]["current"] or 0

            if is_home:
                goals.append(hs)
                if hs > as_:
                    wins += 1
            else:
                goals.append(as_)
                if as_ > hs:
                    wins += 1
        except:
            continue

    if not goals:
        goals = [1]

    return {
        "win_rate": wins / max(1, len(goals)),
        "avg_goals": sum(goals) / len(goals)
    }

# =============================
# H2H
# =============================
def get_h2h(home_id, away_id):
    try:
        url = f"https://api.sofascore.com/api/v1/team/{home_id}/h2h/{away_id}/events"
        data = safe_get(url)

        events = data.get("events", [])[:5]

        home_wins = 0

        for e in events:
            try:
                hs = e["homeScore"]["current"]
                as_ = e["awayScore"]["current"]

                if hs > as_:
                    home_wins += 1
            except:
                continue

        return home_wins / max(1, len(events))

    except:
        return 0.5

# =============================
# DESFALQUES (estimado)
# =============================
def get_injuries(team_id):
    # Sofascore não expõe facilmente, usamos proxy
    return 0.1

# =============================
# SCORE COMPLETO
# =============================
def calculate_score(home, away, h2h):

    score = (
        (home["win_rate"] - away["win_rate"]) * 25 +
        (home["avg_goals"] - away["avg_goals"]) * 15 +
        (home["elo"] - away["elo"]) * 15 +
        (h2h - 0.5) * 10 +
        (away["injuries"] - home["injuries"]) * 10
    )

    return max(0, min(100, 50 + score))

# =============================
# FILTRO
# =============================
def is_valid(score):
    if 45 <= score <= 55:
        return False
    return True

# =============================
# PREDIÇÃO
# =============================
def get_prediction(score):
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

    home = get_last_matches(m["home_id"])
    away = get_last_matches(m["away_id"])

    home["elo"] = get_elo(home_pos)
    away["elo"] = get_elo(away_pos)

    home["injuries"] = get_injuries(m["home_id"])
    away["injuries"] = get_injuries(m["away_id"])

    h2h = get_h2h(m["home_id"], m["away_id"])

    score = calculate_score(home, away, h2h)

    if not is_valid(score):
        continue

    results.append({
        "Jogo": f"{m['home']} x {m['away']}",
        "Liga": m["league"],
        "Score": round(score, 1),
        "Pick": get_prediction(score)
    })

# =============================
# OUTPUT
# =============================
if results:
    df = pd.DataFrame(results)

    st.subheader("📊 Resultados")

    st.dataframe(df, use_container_width=True)

    st.subheader("💰 Melhores Picks")

    st.dataframe(
        df[df["Pick"] != "Sem aposta"],
        use_container_width=True
    )

else:
    st.warning("Nenhum jogo encontrado com critérios válidos.")
