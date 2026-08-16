import streamlit as st
import random
import json
import os
import pandas as pd
import time
from datetime import date

st.set_page_config(page_title="UFPB Academy Dashboard", page_icon="🚀", layout="wide")

ARQUIVO_DADOS = "banco_de_dados_ufpb.json"

CICLO_PADRAO = {
    "📐 Matemática (Assaad)": {"horas": 5, "ambiente": "Mesa"},
    "📚 Linguagens (Fernanda Pessoa)": {"horas": 5, "ambiente": "Transporte"},
    "🖋️ Redação (Fernanda Pessoa)": {"horas": 4, "ambiente": "Ambos"},
    "⚡ Física (Guisoli)": {"horas": 3, "ambiente": "Mesa"},
    "🧪 Química (Michel Arthaud)": {"horas": 3, "ambiente": "Mesa"},
    "🧬 Biologia (Samuel Cunha)": {"horas": 3, "ambiente": "Transporte"},
    "🏛️ História (Débora Aladim)": {"horas": 2, "ambiente": "Transporte"},
    "🌐 Geografia (Thais Formagio)": {"horas": 2, "ambiente": "Transporte"},
    "🧠 Filosofia (Ferretto)": {"horas": 1, "ambiente": "Transporte"},
    "📊 Sociologia (Ferretto)": {"horas": 1, "ambiente": "Transporte"}
}

def inicializar_dados():
    if os.path.exists(ARQUIVO_DADOS):
        with open(ARQUIVO_DADOS, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "xp": 0,
        "historico_dias": {},
        "config_base": CICLO_PADRAO,
        "ciclo_atual": {mat: info["horas"] for mat, info in CICLO_PADRAO.items()}
    }

def salvar_dados(dados):
    with open(ARQUIVO_DADOS, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

dados = inicializar_dados()

XP_POR_HORA = 100
level_atual = (dados["xp"] // 1000) + 1
xp_para_proximo = 1000 - (dados["xp"] % 1000)
progresso_level = (dados["xp"] % 1000) / 1000

col_logo, col_level = st.columns([2, 1])
with col_logo:
    st.markdown("## 🚀 UFPB ACADEMY | CENTRAL DE ESTUDOS")
with col_level:
    st.markdown(f"### 🛡️ Nível {level_atual}")
    st.progress(progresso_level, text=f"XP Atual: {dados['xp']} (Faltam {xp_para_proximo} para subir de nível)")
    
st.markdown("---")

tab_dashboard, tab_estatisticas, tab_config = st.tabs([
    "🎯 Dashboard Principal", 
    "📈 Histórico & Gráficos", 
    "⚙️ Ajustar Edital"
])

with tab_dashboard:
    col_acao, col_visao = st.columns([1.5, 1], gap="large")

    with col_acao:
        st.subheader("🎯 Controle de Missões")
        
        with st.container(border=True):
            modo = st.radio("Onde você está agora?", 
                            ["🔄 Qualquer Ambiente", "🚌 Transporte (Foco em Teoria)", "🖥️ Mesa (Foco em Cálculo/Prática)"], 
                            horizontal=True)
            
            horas_hoje = st.slider("Quantas horas vamos alocar agora?", min_value=1, max_value=6, value=3)
            gerar = st.button("GERAR MISSÕES", type="primary", use_container_width=True)

        if gerar:
            limite = horas_hoje
            rotina_hoje = {}
            
            filtro = "Ambos"
            if "Transporte" in modo: filtro = "Transporte"
            elif "Mesa" in modo: filtro = "Mesa"

            while limite > 0 and sum(dados["ciclo_atual"].values()) > 0:
                urna = []
                for mat, h in dados["ciclo_atual"].items():
                    ambiente_mat = dados["config_base"][mat]["ambiente"]
                    if h > 0 and (filtro == "Ambos" or ambiente_mat == "Ambos" or ambiente_mat == filtro):
                        urna.extend([mat] * h)
                
                if not urna:
                    st.warning("⚠️ Nenhuma matéria desse ambiente possui horas pendentes neste ciclo!")
                    break
                
                sorteada = random.choice(urna)
                max_h = min(limite, dados["ciclo_atual"][sorteada])
                h_sorteadas = random.randint(1, max_h)
                
                rotina_hoje[sorteada] = rotina_hoje.get(sorteada, 0) + h_sorteadas
                limite -= h_sorteadas
                dados["ciclo_atual"][sorteada] -= h_sorteadas

            if rotina_hoje:
                horas_totais = sum(rotina_hoje.values())
                dados["xp"] += horas_totais * XP_POR_HORA
                
                hoje_str = str(date.today())
                dados["historico_dias"][hoje_str] = dados["historico_dias"].get(hoje_str, 0) + horas_totais
                
                salvar_dados(dados)
                st.success(f"Missões geradas! Você ganhou +{horas_totais * XP_POR_HORA} XP! 🔼")
                
                for mat, h in rotina_hoje.items():
                    with st.container(border=True):
                        st.info(f"⏱️ **{h} hora(s)** -> {mat}")

        st.write("")
        with st.expander("⏱️ Abrir Timer Pomodoro"):
            st.write("Inicie o timer para focar. O aplicativo ficará travado até o tempo acabar para evitar distrações.")
            minutos = st.number_input("Minutos de foco:", min_value=1, max_value=120, value=50)
            if st.button("▶️ Iniciar Foco"):
                cronometro = st.empty()
                for segundos in range(minutos * 60, 0, -1):
                    mm, ss = divmod(segundos, 60)
                    cronometro.metric("Tempo Restante:", f"{mm:02d}:{ss:02d}")
                    time.sleep(1)
                cronometro.success("Sessão finalizada! Faça uma pausa.")
                st.balloons()

    with col_visao:
        st.subheader("📊 Horas Pendentes do Ciclo")
        df_ciclo = pd.DataFrame({
            "Disciplina": list(dados["ciclo_atual"].keys()),
            "Pendentes": list(dados["ciclo_atual"].values())
        })
        st.dataframe(df_ciclo, hide_index=True, use_container_width=True)
        
        if sum(dados["ciclo_atual"].values()) == 0:
            st.success("🔄 Ciclo 100% Finalizado! Pressione o botão abaixo para recomeçar.")
            if st.button("Reiniciar Ciclo Completo"):
                dados["ciclo_atual"] = {mat: info["horas"] for mat, info in dados["config_base"].items()}
                salvar_dados(dados)
                st.rerun()

with tab_estatisticas:
    st.subheader("📈 Seu Histórico de Batalha")
    if dados["historico_dias"]:
        df_hist = pd.DataFrame(list(dados["historico_dias"].items()), columns=["Data", "Horas Estudadas"])
        df_hist["Data"] = pd.to_datetime(df_hist["Data"])
        df_hist.set_index("Data", inplace=True)
        
        st.bar_chart(df_hist, color="#00ff00")
    else:
        st.info("Nenhuma hora registrada ainda. Gere suas primeiras missões para começar a gerar gráficos!")

with tab_config:
    st.subheader("⚙️ Editor do Edital (Ciclo Base)")
    st.write("Edite os pesos e ambientes diretamente na tabela abaixo. **Nota:** Só altere isso se você decidir mudar sua estratégia.")
    
    df_config = pd.DataFrame.from_dict(dados["config_base"], orient="index")
    df_config.reset_index(inplace=True)
    df_config.rename(columns={"index": "Disciplina"}, inplace=True)
    
    df_editado = st.data_editor(
        df_config,
        use_container_width=True,
        num_rows="dynamic"
    )
    
    if st.button("💾 Salvar Nova Estratégia", type="primary"):
        nova_config = {}
        for _, row in df_editado.iterrows():
            if row["Disciplina"]:
                nova_config[row["Disciplina"]] = {
                    "horas": int(row["horas"]),
                    "ambiente": row["ambiente"]
                }
        dados["config_base"] = nova_config
        dados["ciclo_atual"] = {mat: info["horas"] for mat, info in nova_config.items()}
        salvar_dados(dados)
        st.success("Edital atualizado! Seu ciclo foi resetado com os novos pesos.")
        st.rerun()

    st.markdown("---")
    st.subheader("🗑️ Zona de Perigo")
    st.write("Isso vai apagar todo o seu histórico de gráficos, zerar seu Nível/XP e reiniciar o ciclo. **Ação irreversível.**")
    
    if st.button("🚨 Apagar Todos os Dados e Reiniciar", use_container_width=True):
        if os.path.exists(ARQUIVO_DADOS):
            os.remove(ARQUIVO_DADOS)
        
        st.success("Dados deletados! Recarregando o sistema...")
        time.sleep(1.5)
        st.rerun()