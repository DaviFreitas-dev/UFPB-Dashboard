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
            max_chars=80,
            placeholder="Ex.: Ler, estudar, programar...",
        )

        if st.button(
            "Adicionar hábito",
            type="primary",
            use_container_width=True,
        ):
            if not name.strip():
                st.warning("Digite o nome do hábito.")
            else:
                _, created, reactivated = add(name.strip())
                if created:
                    st.success("Hábito criado.")
                    st.rerun()
                elif reactivated:
                    st.success("Hábito reativado.")
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

        for index, habit in enumerate(habits):
            checked = habit["feito"] == "Sim"
            habit_streak = streak_map.get(habit["habito"], 0)
            new_value = st.checkbox(
                f"{habit['habito']} · 🔥 sequência de {habit_streak} dias",
                value=checked,
                key=f"habit_{habit['config_id'] or f'legacy_{index}'}",
                disabled=not bool(habit.get("config_id")),
            )

            if new_value != checked:
                toggle(habit["config_id"], new_value)
                st.rerun()

    st.write("")
    section("Gerenciar hábitos")
    configs = active_configs()

    if configs:
        with st.expander("Arquivar um hábito"):
            selected = st.selectbox(
                "Hábito",
                configs,
                format_func=lambda item: item.get("nome") or "Hábito sem nome",
            )
            if st.button("Arquivar hábito", use_container_width=True):
                config_id = str(selected.get("id") or "").strip()
                if not config_id:
                    st.warning("Disponível após a atualização dos dados.")
                else:
                    archive(config_id)
                    st.success("Hábito arquivado; o histórico foi mantido.")
                    st.rerun()
