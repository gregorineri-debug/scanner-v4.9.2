# Arquivo: app.py (Versão Final de Produção)

import streamlit as st
import pandas as pd
import joblib
import numpy as np

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Previsor de Partidas", page_icon="⚽", layout="wide")

# --- FUNÇÕES DE LÓGICA DO MODELO ---

@st.cache_data
def carregar_ativos():
    """ Carrega todos os ativos necessários para a aplicação. """
    try:
        model = joblib.load('modelo_previsor.pkl')
        model_columns = joblib.load('colunas_previsor.pkl')
        label_encoder = joblib.load('encoder_previsor.pkl')
        # Carrega o dataset final e mais atualizado
        df_historico = pd.read_csv('dados_final_com_oitavas.csv', parse_dates=['Date'])
        
        times_casa = df_historico['HomeTeam'].unique()
        times_fora = df_historico['AwayTeam'].unique()
        lista_times = sorted(list(set(np.concatenate((times_casa, times_fora)))))
        return model, model_columns, label_encoder, df_historico, lista_times
    except FileNotFoundError:
        return None, None, None, None, None

def calcular_stats_recentes(time, data_partida, df_historico):
    """ Calcula as stats de forma recente (10 jogos) para um único time. """
    df_time = df_historico[((df_historico['HomeTeam'] == time) | (df_historico['AwayTeam'] == time)) & (df_historico['Date'] < data_partida)]
    if len(df_time) == 0: return 0, 0, 0
    df_time = df_time.tail(10) 

    gols_feitos, gols_sofridos, pontos = [], [], []
    for _, row in df_time.iterrows():
        if row['HomeTeam'] == time:
            gols_feitos.append(row['FTHG']); gols_sofridos.append(row['FTAG'])
            pontos.append(3 if row['FTR'] == 'H' else (1 if row['FTR'] == 'D' else 0))
        else:
            gols_feitos.append(row['FTAG']); gols_sofridos.append(row['FTHG'])
            pontos.append(3 if row['FTR'] == 'A' else (1 if row['FTR'] == 'D' else 0))
    
    media_gf = np.mean(gols_feitos) if gols_feitos else 0
    media_gs = np.mean(gols_sofridos) if gols_sofridos else 0
    media_pontos = np.mean(pontos) if pontos else 0
    return media_gf, media_gs, media_pontos

# --- CARREGAMENTO INICIAL E INTERFACE ---
model, model_columns, le, df_historico, lista_times = carregar_ativos()

if model is None:
    st.error("ERRO CRÍTICO: Arquivos de modelo (.pkl) ou de dados (.csv) não encontrados. Execute o script 'treinar_modelo_final.py' primeiro.")
    st.stop()

st.title('🥇 Previsor de Partidas - Copa do Mundo de Clubes de Futebol')
st.markdown("### Previsões para o  Copa do Mundo de Clubes 2025 - Atualizado em 02/07/2025")

col1, col2 = st.columns(2)
with col1:
    time_A = st.selectbox('Selecione o Time A', lista_times, index=lista_times.index('Real Madrid') if 'Real Madrid' in lista_times else 0)
with col2:
    time_B = st.selectbox('Selecione o Time B', lista_times, index=lista_times.index('Manchester City') if 'Manchester City' in lista_times else 1)

if st.button('Fazer Previsão', type="primary", use_container_width=True):
    if time_A == time_B:
        st.error("Os times A e B devem ser diferentes.")
    else:
        with st.spinner('Calculando estatísticas e fazendo a previsão...'):
            data_hoje = pd.to_datetime('today').normalize()
            gf_A, gs_A, forma_A = calcular_stats_recentes(time_A, data_hoje, df_historico)
            gf_B, gs_B, forma_B = calcular_stats_recentes(time_B, data_hoje, df_historico)
            
            st.markdown("---")
            st.subheader("Estatísticas Recentes (Últimos 10 Jogos)")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**{time_A}**")
                st.metric(label="Média de Pontos", value=f"{forma_A:.2f}")
                st.metric(label="Média de Gols Feitos", value=f"{gf_A:.2f}")
                st.metric(label="Média de Gols Sofridos", value=f"{gs_A:.2f}")
            with c2:
                st.markdown(f"**{time_B}**")
                st.metric(label="Média de Pontos", value=f"{forma_B:.2f}")
                st.metric(label="Média de Gols Feitos", value=f"{gf_B:.2f}")
                st.metric(label="Média de Gols Sofridos", value=f"{gs_B:.2f}")

            def preparar_input(home, away, forma_H, gf_H, gs_H, forma_A, gf_A, gs_A):
                data = {'Home_Forma_10_Jogos': forma_H, 'Home_Media_Gols_Feitos_10J': gf_H, 'Home_Media_Gols_Sofridos_10J': gs_H, 'Away_Forma_10_Jogos': forma_A, 'Away_Media_Gols_Feitos_10J': gf_A, 'Away_Media_Gols_Sofridos_10J': gs_A}
                input_df = pd.DataFrame([data])
                for col in model_columns:
                    if col not in input_df.columns: input_df[col] = False
                
                home_col = 'HomeTeam_' + home
                away_col = 'AwayTeam_' + away
                if home_col in input_df.columns: input_df[home_col] = True
                if away_col in input_df.columns: input_df[away_col] = True
                
                return input_df.reindex(columns=model_columns, fill_value=False)

            input1 = preparar_input(time_A, time_B, forma_A, gf_A, gs_A, forma_B, gf_B, gs_B)
            prob_1 = model.predict_proba(input1)
            input2 = preparar_input(time_B, time_A, forma_B, gf_B, gs_B, forma_A, gf_A, gs_A)
            prob_2 = model.predict_proba(input2)

            map_classes = {classe: i for i, classe in enumerate(le.classes_)}
            prob_A_vence = np.mean([prob_1[0][map_classes['H']], prob_2[0][map_classes['A']]])
            prob_B_vence = np.mean([prob_1[0][map_classes['A']], prob_2[0][map_classes['H']]])
            prob_empate = np.mean([prob_1[0][map_classes['D']], prob_2[0][map_classes['D']]])
            
            soma_probs = prob_A_vence + prob_B_vence + prob_empate
            prob_A_vence /= soma_probs
            prob_B_vence /= soma_probs
            prob_empate /= soma_probs
            
            st.markdown("---")
            st.subheader(f'Previsão para: {time_A} vs {time_B}')
            
            if prob_A_vence > prob_B_vence and prob_A_vence > prob_empate:
                st.success(f"🏆 Resultado Mais Provável: Vitória do {time_A}!")
            elif prob_B_vence > prob_A_vence and prob_B_vence > prob_empate:
                st.success(f"🏆 Resultado Mais Provável: Vitória do {time_B}!")
            else:
                st.warning(f"⚖️ Resultado Mais Provável: Empate!")

            st.write("---")
            st.subheader('Probabilidades da Partida')
            c1, c2, c3 = st.columns(3)
            c1.metric(label=f"Vitória {time_A}", value=f"{prob_A_vence:.2%}")
            c2.metric(label="Empate", value=f"{prob_empate:.2%}")
            c3.metric(label=f"Vitória {time_B}", value=f"{prob_B_vence:.2%}")
