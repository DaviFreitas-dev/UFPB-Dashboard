import streamlit as st

from modules.routine import add, today_records, toggle
from modules.ui import header, section


def render():
    header(
        "Rotina",
        "Organize o que acontece no seu dia e dê horários às suas atividades.",
    )

    with st.container(border=True):
        activity = st.text_input(
            "Atividade",
            placeholder="Ex.: estudar, academia, projeto pessoal...",
        )
        hour = st.time_input("Horário")

        if st.button(
            "➕ Adicionar à rotina",
            type="primary",
            use_container_width=True,
        ):
            if activity.strip():
                add(activity.strip(), hour.strftime("%H:%M"))
                st.success("Atividade adicionada!")
                st.rerun()

    section("📅 Hoje")
    items = today_records()

    if not items:
        st.info("Sua rotina de hoje está vazia.")
        return

    for item in sorted(items, key=lambda x: x["hora"]):
        checked = item["status"] == "Concluída"
        new_value = st.checkbox(
            f"{item['hora']} — {item['atividade']}",
            value=checked,
            key=f"routine_{item['id']}",
        )

        if new_value != checked:
            toggle(item["id"], new_value)
            st.rerun()
