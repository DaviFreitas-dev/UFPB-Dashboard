import streamlit as st

from modules.activity import add, today
from modules.ui import header, section


def render():
    header(
        "Atividade",
        "Registre treino e outras atividades físicas do dia.",
    )

    with st.container(border=True):
        activity_type = st.selectbox(
            "Atividade realizada",
            ["Treino", "Caminhada", "Corrida", "Alongamento", "Outro"],
        )

        if st.button(
            "✅ Registrar atividade",
            type="primary",
            use_container_width=True,
        ):
            add(activity_type)
            st.success("Atividade registrada!")
            st.rerun()

    section("📅 Registro de hoje")
    items = today()

    if not items:
        st.info("Nenhuma atividade registrada hoje.")
        return

    for item in items:
        st.success(f"✅ {item['tipo']}")
