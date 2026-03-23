# Arquivo: app.py (Versão Corrigida)

import streamlit as st
import pandas as pd
import numpy as np

# Tentativa de importar joblib com fallback
try:
    import joblib
except ModuleNotFoundError:
    st.error("⚠️ Biblioteca 'joblib' não instalada. Adicione no requirements.txt: joblib")
    st.stop()

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Previsor de Partidas", page_icon="⚽", layout="wide")

# --- FUNÇÕES ---

@st.cache_data
def carregar_ativos():
    try:
        model = joblib.load('modelo_previsor.pkl')
        model_columns = joblib.load('colunas_previsor.pkl')
        label_encoder = joblib.load('encoder_previsor.pkl')

        df_historico = pd.read_csv('dados_final_com_oitavas.csv', parse_dates=['Date'])

        times_casa = df_historico['HomeTeam'].unique()
        times_fora = df_historico['AwayTeam'].unique()

        lista_times = sorted(list(set(np.concatenate((times_casa, times_fora)))))

        return model, model_columns, label_encoder, df_historico, lista_times

    except FileNotFoundError:
        return None, None, None, None, None


def calcular_stats_recentes(time, data_partida, df_historico):
    df_time = df_historico[
        ((df_historico['HomeTeam'] == time) | (df_historico['AwayTeam'] == time)) &
        (df_historico['Date'] < data_partida)
    ]

    if len(df_time) == 0:
        return 0, 0, 0

    df_time = df_time.tail(10)

    gols_feitos, gols_sofridos, pontos = [], [], []

    for _, row in df_time.iterrows():
        if row['HomeTeam'] == time:
            gols_feitos.append(row['FTHG'])
            gols_sofridos.append(row['FTAG'])
            pontos.append(3 if row['FTR'] == 'H' else (1 if row['FTR'] == 'D' else 0))
        else:
            gols_feitos.append(row['FTAG'])
            gols_sofridos.append(row['FTHG'])
            pontos.append(3 if row['FTR'] == 'A' else (1 if row['FTR'] == 'D' else 0))

    return (
        np.mean(gols_feitos),
        np.mean(gols_sofridos),
        np.mean(pontos)
    )


# --- CARREGAMENTO ---
model, model_columns, le, df_historico, lista_times = carregar_ativos()

if model is None:
    st.error("❌ Arquivos do modelo não encontrados.")
    st.stop()

# --- UI ---
st.title('⚽ Previsor de Partidas')

col1, col2 = st.columns(2)

with col1:
    time_A = st.selectbox('Time A', lista_times)

with col2:
    time_B = st.selectbox('Time B', lista_times)

# --- INPUT ---
def preparar_input(home, away, forma_H, gf_H, gs_H, forma_A, gf_A, gs_A):
    data = {
        'Home_Forma_10_Jogos': forma_H,
        'Home_Media_Gols_Feitos_10J': gf_H,
        'Home_Media_Gols_Sofridos_10J': gs_H,
        'Away_Forma_10_Jogos': forma_A,
        'Away_Media_Gols_Feitos_10J': gf_A,
        'Away_Media_Gols_Sofridos_10J': gs_A
    }

    input_df = pd.DataFrame([data])

    for col in model_columns:
        if col not in input_df.columns:
            input_df[col] = False

    input_df[f'HomeTeam_{home}'] = True
    input_df[f'AwayTeam_{away}'] = True

    return input_df.reindex(columns=model_columns, fill_value=False)


# --- EXECUÇÃO ---
if st.button("Prever"):
    data_hoje = pd.to_datetime('today').normalize()

    gf_A, gs_A, forma_A = calcular_stats_recentes(time_A, data_hoje, df_historico)
    gf_B, gs_B, forma_B = calcular_stats_recentes(time_B, data_hoje, df_historico)

    input1 = preparar_input(time_A, time_B, forma_A, gf_A, gs_A, forma_B, gf_B, gs_B)
    input2 = preparar_input(time_B, time_A, forma_B, gf_B, gs_B, forma_A, gf_A, gs_A)

    prob_1 = model.predict_proba(input1)
    prob_2 = model.predict_proba(input2)

    map_classes = {classe: i for i, classe in enumerate(le.classes_)}

    prob_A = np.mean([prob_1[0][map_classes['H']], prob_2[0][map_classes['A']]])
    prob_B = np.mean([prob_1[0][map_classes['A']], prob_2[0][map_classes['H']]])
    prob_D = np.mean([prob_1[0][map_classes['D']], prob_2[0][map_classes['D']]])

    total = prob_A + prob_B + prob_D

    prob_A /= total
    prob_B /= total
    prob_D /= total

    st.subheader("Resultado")

    if prob_A > prob_B and prob_A > prob_D:
        st.success(f"🏆 Vitória do {time_A}")
    elif prob_B > prob_A and prob_B > prob_D:
        st.success(f"🏆 Vitória do {time_B}")
    else:
        st.warning("⚖️ Empate")

    st.write("### Probabilidades")
    st.metric(f"{time_A}", f"{prob_A:.2%}")
    st.metric("Empate", f"{prob_D:.2%}")
    st.metric(f"{time_B}", f"{prob_B:.2%}")
