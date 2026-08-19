import streamlit as st

from modules.database import initialize_database
from modules.ui import apply_css, render_sidebar
from views import (
    home,
    routine,
    cycle,
    missions,
    reading,
    tasks,
    habits,
    activity,
    progress,
    achievements,
    settings,
)

st.set_page_config(
    page_title="UFPB Academy",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_css()
initialize_database()

page = render_sidebar()

pages = {
    "🏠 Hoje": home.render,
    "📅 Rotina": routine.render,
    "🎯 Ciclo": cycle.render,
    "📚 Missões": missions.render,
    "📖 Leitura": reading.render,
    "✅ Tarefas": tasks.render,
    "🔥 Hábitos": habits.render,
    "🏋️ Atividade": activity.render,
    "📈 Progresso": progress.render,
    "🏆 Conquistas": achievements.render,
    "⚙️ Configurações": settings.render,
}

pages[page]()
