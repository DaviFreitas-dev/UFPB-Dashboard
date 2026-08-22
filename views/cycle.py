import pandas as pd
import streamlit as st

from modules.database import get_cycle, reset_cycle
from modules.studies import cycle_summary
from modules.ui import header, section, without_emoji


def render():
    header(
        "Ciclo de estudos",
        "Distribuição de horas por matéria.",
    )

    total, remaining, done, progress = cycle_summary()

    st.html(
        f"""
        <div class="performance-card" style="min-height:180px">
            <div class="performance-label">PROGRESSO DO CICLO</div>
            <div class="performance-value">{progress:.0%}</div>
            <div class="performance-copy">
                {done}h concluídas • {remaining}h restantes • {total}h no ciclo
            </div>
        </div>
        """
    )

    st.progress(progress)

    section("Matérias")
    cycle = pd.DataFrame(get_cycle())
    if not cycle.empty and "disciplina" in cycle:
        cycle["disciplina"] = cycle["disciplina"].map(without_emoji)

    st.dataframe(
        cycle,
        hide_index=True,
        use_container_width=True,
    )

    if st.button("Reiniciar ciclo", use_container_width=True):
        reset_cycle()
        st.success("Ciclo reiniciado.")
        st.rerun()
