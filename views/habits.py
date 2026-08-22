import streamlit as st

from modules.habits import active_configs, add, archive, streaks, today, toggle
from modules.ui import header, section


def render():
    header(
        "Hábitos",
        "Hábitos e sequências diárias.",
    )

    with st.container(border=True):
        name = st.text_input(
            "Novo hábito",
            placeholder="Ex.: Ler, estudar, programar...",
        )

        if st.button(
            "Adicionar hábito",
            type="primary",
            use_container_width=True,
        ):
            if not name.strip():
                st.warning("Digite o nome do hábito.")
            elif add(name.strip()):
                st.success("Hábito criado.")
                st.rerun()
            else:
                st.info("Esse hábito já está ativo.")

    section("Hoje")
    habits = today()

    if not habits:
        st.info("Nenhum hábito cadastrado.")
    else:
        done = sum(habit["feito"] == "Sim" for habit in habits)
        st.progress(
            done / len(habits),
            text=f"{done} de {len(habits)} hábitos concluídos hoje",
        )

        streak_map = streaks([habit["habito"] for habit in habits])

        for habit in habits:
            checked = habit["feito"] == "Sim"
            habit_streak = streak_map.get(habit["habito"], 0)
            new_value = st.checkbox(
                f"{habit['habito']} · 🔥 sequência de {habit_streak} dias",
                value=checked,
                key=f"habit_{habit['id']}",
            )

            if new_value != checked:
                toggle(habit["id"], new_value)
                st.rerun()

    st.write("")
    section("Gerenciar hábitos")
    configs = active_configs()

    if configs:
        with st.expander("Arquivar um hábito"):
            selected = st.selectbox(
                "Hábito",
                configs,
                format_func=lambda item: item["nome"],
            )
            if st.button("Arquivar hábito", use_container_width=True):
                archive(selected["id"])
                st.success("Hábito arquivado; o histórico foi mantido.")
                st.rerun()
