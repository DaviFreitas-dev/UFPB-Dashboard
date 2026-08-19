import pandas as pd
import streamlit as st

from modules.database import get_cycle, reset_cycle
from modules.studies import cycle_summary
from modules.ui import header, section


def render():
    header(
        "Ciclo de estudos",
        "Seu planejamento de matérias separado da organização diária.",
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
    st.dataframe(
        pd.DataFrame(get_cycle()),
        hide_index=True,
        use_container_width=True,
    )

    if st.button("Reiniciar ciclo", use_container_width=True):
        reset_cycle()
        st.success("Ciclo reiniciado!")
        st.rerun()
