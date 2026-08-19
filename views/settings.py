import pandas as pd
import streamlit as st

from modules.config import AMBIENTES
from modules.database import get_config, reset_cycle, reset_progress, update_user_config
from modules.ui import header, section


def render():
    header(
        "Configurações",
        "Ajuste o ciclo e mantenha o sistema do seu jeito.",
    )

    section("🎯 Edital")
    df = pd.DataFrame(get_config())

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

    if st.button("💾 Salvar edital", type="primary", use_container_width=True):
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
            st.success("Edital atualizado e ciclo reiniciado!")
            st.rerun()

    st.write("")
    section("🔄 Ciclo")

    if st.button("🔄 Reiniciar ciclo", use_container_width=True):
        reset_cycle()
        st.success("Ciclo reiniciado!")
        st.rerun()

    st.write("")
    section("🗑️ Zona de perigo")

    with st.container(border=True):
        st.warning("Isso apaga XP e histórico. O edital continua salvo.")
        confirm = st.checkbox("Eu realmente quero apagar meu progresso.")

        if st.button("🚨 Apagar progresso", use_container_width=True):
            if confirm:
                reset_progress()
                st.success("Progresso apagado.")
                st.rerun()
            else:
                st.error("Confirme a operação primeiro.")
