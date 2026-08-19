import pandas as pd
import streamlit as st

from modules.database import get_history, get_xp
from modules.studies import calculate_level, stats
from modules.ui import header


def render():
    xp = get_xp()
    level, xp_in_level, progress, missing = calculate_level(xp)
    s = stats()

    header(
        "Progresso",
        "Veja sua evolução ao longo dos dias.",
    )

    cols = st.columns(4)

    values = [
        ("Horas totais", f"{s['hours']}h"),
        ("Média diária", f"{s['average']:.1f}h"),
        ("Melhor dia", f"{s['best']}h"),
        ("Sequência", f"{s['streak']} dias"),
    ]

    for col, (label, value) in zip(cols, values):
        with col:
            st.metric(label, value)

    st.progress(
        progress,
        text=f"Nível {level} • {xp_in_level}/1000 XP • faltam {missing} XP",
    )

    history = get_history()

    if history:
        df = pd.DataFrame(history)
        df["data"] = pd.to_datetime(df["data"])
        df["horas"] = pd.to_numeric(df["horas"])
        df = df.sort_values("data").set_index("data")
        st.bar_chart(df, y="horas")
    else:
        st.info("Ainda não há histórico.")
