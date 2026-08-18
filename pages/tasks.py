import streamlit as st

from modules.tasks import add, today_records, toggle
from modules.ui import header, section


def render():
    header(
        "Tarefas",
        "Tudo o que precisa ser feito, sem depender necessariamente de um horário.",
    )

    with st.container(border=True):
        task = st.text_input(
            "Nova tarefa",
            placeholder="Ex.: Fazer trabalho de História",
        )
        category = st.selectbox(
            "Categoria",
            ["Escola", "Estudos", "Pessoal", "Projeto", "Outro"],
        )

        if st.button(
            "➕ Adicionar tarefa",
            type="primary",
            use_container_width=True,
        ):
            if task.strip():
                add(task.strip(), category)
                st.success("Tarefa adicionada!")
                st.rerun()

    section("✅ Tarefas de hoje")
    tasks = today_records()

    if not tasks:
        st.info("Nenhuma tarefa cadastrada para hoje.")
        return

    for item in tasks:
        checked = item["status"] == "Concluída"
        new_value = st.checkbox(
            f"{item['tarefa']} • {item['categoria']}",
            value=checked,
            key=f"task_{item['id']}",
        )

        if new_value != checked:
            toggle(item["id"], new_value)
            st.rerun()
