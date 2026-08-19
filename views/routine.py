from datetime import date

import streamlit as st

from modules.routine import add, records_for_date, remove, toggle
from modules.ui import header, section


def render():
    header(
        "Rotina",
        "Organize horários e compromissos do dia sem misturar com suas tarefas.",
    )

    with st.container(border=True):
        activity = st.text_input(
            "Atividade",
            placeholder="Ex.: estudar, academia, projeto pessoal...",
        )
        col1, col2 = st.columns(2)

        with col1:
            hour = st.time_input("Horário")

        with col2:
            target_date = st.date_input("Data", value=date.today())

        if st.button(
            "➕ Adicionar à rotina",
            type="primary",
            use_container_width=True,
        ):
            if activity.strip():
                add(
                    activity.strip(),
                    hour.strftime("%H:%M"),
                    target_date,
                )
                st.success("Atividade adicionada!")
                st.rerun()
            else:
                st.warning("Digite uma atividade antes de adicionar.")

    section("📅 Agenda")
    selected_date = st.date_input(
        "Ver rotina de",
        value=date.today(),
        key="routine_view_date",
    )
    items = records_for_date(selected_date)

    if not items:
        st.info("Sua rotina está vazia nessa data.")
        return

    done_count = sum(item["status"] == "Concluída" for item in items)
    st.progress(
        done_count / len(items),
        text=f"{done_count} de {len(items)} atividades concluídas",
    )

    for item in sorted(items, key=lambda row: row["hora"]):
        check_col, delete_col = st.columns([10, 1])
        checked = item["status"] == "Concluída"

        with check_col:
            new_value = st.checkbox(
                f"{item['hora']} — {item['atividade']}",
                value=checked,
                key=f"routine_{item['id']}",
            )

        with delete_col:
            if st.button(
                "🗑️",
                key=f"delete_routine_{item['id']}",
                help="Excluir atividade",
            ):
                remove(item["id"])
                st.rerun()

        if new_value != checked:
            toggle(item["id"], new_value)
            st.rerun()
