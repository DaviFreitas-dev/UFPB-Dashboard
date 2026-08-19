import time

import streamlit as st

from modules.config import XP_POR_HORA
from modules.studies import complete_mission, draw_mission
from modules.database import get_config
from modules.ui import header, section


def render():
    header(
        "Missões",
        "Transforme seu ciclo em sessões de estudo concretas.",
    )

    if "pending_mission" not in st.session_state:
        st.session_state["pending_mission"] = None

    if st.session_state["pending_mission"]:
        mission = st.session_state["pending_mission"]
        total_hours = sum(mission.values())

        st.html(
            f"""
            <div class="mission">
                <div class="mission-kicker">MISSÃO ATIVA</div>
                <div class="mission-title">Sua missão está pronta.</div>
                <div class="mission-hours">{total_hours}h</div>
                <div class="mission-meta">
                    Estude primeiro. Só depois conclua para receber XP.
                </div>
            </div>
            """
        )

        config = {row["disciplina"]: row["ambiente"] for row in get_config()}

        for subject, hours in mission.items():
            st.html(
                f"""
                <div class="mission">
                    <div class="mission-title">{subject}</div>
                    <div class="mission-meta">
                        <span class="badge">{config.get(subject, 'Ambos')}</span>
                        • {hours}h • +{hours * XP_POR_HORA} XP
                    </div>
                </div>
                """
            )

        if st.button("✅ CONCLUIR MISSÃO", type="primary", use_container_width=True):
            hours, xp = complete_mission(mission)
            st.session_state["pending_mission"] = None
            st.session_state["completion"] = {"hours": hours, "xp": xp}
            st.rerun()

        if st.button("✖️ Cancelar missão", use_container_width=True):
            st.session_state["pending_mission"] = None
            st.rerun()

    else:
        with st.container(border=True):
            mode = st.radio(
                "Ambiente",
                ["🔄 Qualquer ambiente", "🚌 Transporte", "🖥️ Mesa"],
                horizontal=True,
            )
            hours = st.slider("Horas", 1, 6, 3)

            if st.button("🚀 SORTEAR MISSÃO", type="primary", use_container_width=True):
                environment = "Ambos"
                if "Transporte" in mode:
                    environment = "Transporte"
                elif "Mesa" in mode:
                    environment = "Mesa"

                mission = draw_mission(hours, environment)

                if mission:
                    st.session_state["pending_mission"] = mission
                    st.rerun()
                else:
                    st.warning("Não há horas disponíveis para esse ambiente.")

    if st.session_state.get("completion"):
        completion = st.session_state["completion"]
        st.success(
            f"✅ Missão concluída: {completion['hours']}h e +{completion['xp']} XP!"
        )

    st.write("")
    section("⏱️ Pomodoro")

    with st.container(border=True):
        minutes = st.select_slider(
            "Duração",
            options=[25, 40, 50, 60, 90],
            value=50,
        )

        if st.button("▶️ Iniciar foco", use_container_width=True):
            timer = st.empty()

            for seconds in range(minutes * 60, 0, -1):
                mm, ss = divmod(seconds, 60)
                timer.metric("Tempo restante", f"{mm:02d}:{ss:02d}")
                time.sleep(1)

            timer.success("✅ Sessão concluída!")
