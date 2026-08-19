from datetime import date

import streamlit as st

from modules.planner import (
    checkins_for_date,
    toggle_weekly,
    weekly_for_date,
)
from modules.routine import add, records_for_date, remove, toggle
from modules.ui import header, section


def render():
    header("Rotina", "Horários do dia e agenda fixa.")

    selected_date = st.date_input(
        "Dia",
        value=date.today(),
        key="routine_view_date",
    )

    fixed = weekly_for_date(selected_date)
    fixed_checkins = checkins_for_date(selected_date)
    custom = records_for_date(selected_date)

    total = len(fixed) + len(custom)
    done_fixed = sum(
        fixed_checkins.get(str(item["id"]), {}).get("status") == "Concluída"
        for item in fixed
    )
    done_custom = sum(
        item.get("status") == "Concluída"
        for item in custom
    )

    if total:
        st.progress(
            (done_fixed + done_custom) / total,
            text=f"{done_fixed + done_custom} de {total} atividades concluídas",
        )

    section("🧩 Semana fixa")

    if not fixed:
        st.info("Nada fixo para este dia. Cadastre em Planejar.")
    else:
        for item in sorted(fixed, key=lambda row: str(row.get("hora"))):
            checkin = fixed_checkins.get(str(item["id"]), {})
            checked = checkin.get("status") == "Concluída"
            new_value = st.checkbox(
                f"{item.get('hora', '--:--')} — {item.get('atividade', '')} · {item.get('categoria', '')}",
                value=checked,
                key=f"fixed_{selected_date}_{item['id']}",
            )
            if new_value != checked:
                toggle_weekly(item["id"], selected_date, new_value)
                st.rerun()

    section("📌 Compromissos avulsos")

    with st.expander("Adicionar compromisso"):
        with st.form("routine_add_form", clear_on_submit=True):
            activity = st.text_input(
                "Atividade",
                placeholder="Ex.: reunião, médico, estudo extra...",
            )
            hour = st.time_input("Horário")
            submitted = st.form_submit_button(
                "Adicionar",
                type="primary",
                use_container_width=True,
            )

        if submitted and activity.strip():
            add(
                activity.strip(),
                hour.strftime("%H:%M"),
                selected_date,
            )
            st.rerun()

    if not custom:
        st.info("Nenhum compromisso avulso.")
        return

    for item in sorted(custom, key=lambda row: str(row.get("hora"))):
        check_col, delete_col = st.columns([10, 1])
        checked = item.get("status") == "Concluída"

        with check_col:
            new_value = st.checkbox(
                f"{item.get('hora', '--:--')} — {item.get('atividade', '')}",
                value=checked,
                key=f"routine_{item['id']}",
            )

        with delete_col:
            if st.button(
                "🗑️",
                key=f"delete_routine_{item['id']}",
                help="Excluir",
            ):
                remove(item["id"])
                st.rerun()

        if new_value != checked:
            toggle(item["id"], new_value)
            st.rerun()
