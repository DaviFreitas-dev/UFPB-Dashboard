from datetime import date

import streamlit as st

from modules.tasks import add, records_for_date, remove, toggle
from modules.ui import header, section


def render():
    header(
        "Tarefas",
        "Planeje o que precisa ser feito hoje ou em uma data específica.",
    )

    with st.container(border=True):
        task = st.text_input(
            "Nova tarefa",
            placeholder="Ex.: Fazer trabalho de História",
        )
        col1, col2 = st.columns(2)

        with col1:
            category = st.selectbox(
                "Categoria",
                ["Escola", "Estudos", "Pessoal", "Projeto", "Outro"],
            )

        with col2:
            target_date = st.date_input("Data", value=date.today())

        if st.button(
            "➕ Adicionar tarefa",
            type="primary",
            use_container_width=True,
        ):
            if task.strip():
                add(task.strip(), category, target_date)
                st.success("Tarefa adicionada!")
                st.rerun()
            else:
                st.warning("Digite uma tarefa antes de adicionar.")

    section("✅ Agenda de tarefas")
    selected_date = st.date_input(
        "Ver tarefas de",
        value=date.today(),
        key="tasks_view_date",
    )
    tasks = records_for_date(selected_date)

    if not tasks:
        st.info("Nenhuma tarefa cadastrada para essa data.")
        return

    done_count = sum(item["status"] == "Concluída" for item in tasks)
    st.progress(
        done_count / len(tasks),
        text=f"{done_count} de {len(tasks)} tarefas concluídas",
    )

    for item in tasks:
        check_col, delete_col = st.columns([10, 1])
        checked = item["status"] == "Concluída"

        with check_col:
            new_value = st.checkbox(
                f"{item['tarefa']} • {item['categoria']}",
                value=checked,
                key=f"task_{item['id']}",
            )

        with delete_col:
            if st.button(
                "🗑️",
                key=f"delete_task_{item['id']}",
                help="Excluir tarefa",
            ):
                remove(item["id"])
                st.rerun()

        if new_value != checked:
            toggle(item["id"], new_value)
            st.rerun()
