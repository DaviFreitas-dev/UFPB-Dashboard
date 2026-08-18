import streamlit as st

from modules.habits import add, today, toggle
from modules.ui import header, section


def render():
    header(
        "Hábitos",
        "Pequenas ações repetidas todos os dias formam sua rotina.",
    )

    with st.container(border=True):
        name = st.text_input(
            "Novo hábito",
            placeholder="Ex.: Ler, estudar, programar...",
        )

        if st.button(
            "🔥 Adicionar hábito",
            type="primary",
            use_container_width=True,
        ):
            if name.strip():
                add(name.strip())
                st.success("Hábito criado!")
                st.rerun()

    section("🔥 Hoje")
    habits = today()

    if not habits:
        st.info("Você ainda não cadastrou hábitos.")
        return

    for habit in habits:
        checked = habit["feito"] == "Sim"
        new_value = st.checkbox(
            habit["habito"],
            value=checked,
            key=f"habit_{habit['id']}",
        )

        if new_value != checked:
            toggle(habit["id"], new_value)
            st.rerun()
