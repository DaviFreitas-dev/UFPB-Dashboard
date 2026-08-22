import pandas as pd
import streamlit as st

from modules.config import AMBIENTES
from modules.database import get_config, reset_cycle, reset_progress, update_user_config
from modules.ui import header, section, without_emoji


def render():
    header(
        "Configurações",
        "Ciclo de estudos e dados do aplicativo.",
    )

    section("Edital")
    df = pd.DataFrame(get_config())
    if not df.empty and "disciplina" in df:
        df["disciplina"] = df["disciplina"].map(without_emoji)

    edited = st.data_editor(
        df,
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "disciplina": st.column_config.TextColumn("Disciplina", required=True),
            "horas": st.column_config.NumberColumn(
                "Horas",
                min_value=0,
                max_value=100,
                step=1,
            ),
            "ambiente": st.column_config.SelectboxColumn(
                "Ambiente",
                options=AMBIENTES,
                required=True,
            ),
        },
    )

    if st.button("Salvar edital", type="primary", use_container_width=True):
        rows = []
        invalid_row = False

        for _, row in edited.iterrows():
            discipline = str(row.get("disciplina", "")).strip()
            if not discipline or discipline.lower() == "nan":
                continue

            try:
                hours = int(row.get("horas", 0))
            except (TypeError, ValueError):
                invalid_row = True
                break

            environment = row.get("ambiente", "Ambos")
            if environment not in AMBIENTES:
                environment = "Ambos"

            rows.append([discipline, hours, environment])

        if invalid_row:
            st.error("Revise as horas: há um valor inválido na tabela.")
        elif not rows:
            st.error("Adicione pelo menos uma disciplina.")
        else:
            update_user_config(rows)
            st.success("Edital salvo e ciclo reiniciado.")
            st.rerun()

    st.write("")
    section("Ciclo")

    if st.button("Reiniciar ciclo", use_container_width=True):
        reset_cycle()
        st.success("Ciclo reiniciado.")
        st.rerun()

    st.write("")
    section("Apagar dados")

    with st.container(border=True):
        st.warning(
            "Apaga XP, histórico de estudo e eventos de XP. "
            "O edital não muda."
        )
        confirm = st.checkbox("Confirmo que quero apagar meu progresso.")

        if st.button("Apagar progresso", use_container_width=True):
            if confirm:
                reset_progress()
                st.success("Progresso apagado.")
                st.rerun()
            else:
                st.error("Confirme a operação primeiro.")
