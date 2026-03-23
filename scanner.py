import requests
import pandas as pd
import streamlit as st
from datetime import date

st.set_page_config(page_title="Scanner Base Estável", layout="wide")

st.title("⚽ Scanner de Jogos (Versão Estável)")

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
        response = requests.get(url, headers=HEADERS, timeout=10)
        return response.json()
    except:
        return {"response": []}

# =============================
# BUSCAR JOGOS
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
# ANALISE SIMPLES
# =============================
def simple_score():

    import random

    return random.randint(40, 70)

# =============================
# PREVISÃO
# =============================
def prediction(score):

    if score >= 60:
        return "Casa"
    elif score <= 40:
        return "Visitante"
    else:
        return "Sem aposta"

# =============================
# EXECUÇÃO
# =============================
matches = get_matches()

if not matches:
    st.warning("Nenhum jogo encontrado na API.")
    st.stop()

results = []

for m in matches:

    score = simple_score()

    results.append({
        "Jogo": f"{m['home']} x {m['away']}",
        "Score": score,
        "Pick": prediction(score)
    })

# =============================
# OUTPUT
# =============================
df = pd.DataFrame(results)

st.subheader("📊 Jogos do Dia")

st.dataframe(df, use_container_width=True)
