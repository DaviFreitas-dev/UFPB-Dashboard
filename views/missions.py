import streamlit as st
import streamlit.components.v1 as components

from modules.config import XP_POR_HORA
from modules.database import get_config
from modules.studies import complete_mission, draw_mission
from modules.ui import header, section


def render_pomodoro(minutes):
    seconds = int(minutes) * 60
    components.html(
        f"""
        <div class="timer-shell">
            <div class="timer-label">SESSÃO DE FOCO</div>
            <div id="timer">{minutes:02d}:00</div>
            <div id="status">Pronto para começar</div>
            <div class="timer-actions">
                <button onclick="startTimer()">▶ Iniciar</button>
                <button onclick="pauseTimer()">⏸ Pausar</button>
                <button onclick="resetTimer()">↻ Reiniciar</button>
            </div>
        </div>

        <style>
            body {{ margin: 0; font-family: Inter, Arial, sans-serif; background: transparent; }}
            .timer-shell {{
                background: linear-gradient(135deg, #0e263e, #09192b);
                border: 1px solid rgba(56,189,248,.22);
                border-radius: 20px;
                padding: 28px;
                text-align: center;
                color: #f4f7fb;
            }}
            .timer-label {{
                color: #38bdf8;
                font-size: 11px;
                font-weight: 800;
                letter-spacing: .16em;
            }}
            #timer {{
                font-size: 64px;
                line-height: 1;
                font-weight: 800;
                margin: 18px 0 10px;
                font-variant-numeric: tabular-nums;
            }}
            #status {{ color: #91a4bc; font-size: 14px; margin-bottom: 22px; }}
            .timer-actions {{ display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; }}
            button {{
                border: 1px solid rgba(56,189,248,.25);
                background: #102c47;
                color: #f4f7fb;
                border-radius: 10px;
                padding: 10px 16px;
                font-weight: 700;
                cursor: pointer;
            }}
            button:hover {{ background: #163958; }}
        </style>

        <script>
            const initialSeconds = {seconds};
            let remaining = initialSeconds;
            let interval = null;

            function draw() {{
                const minutes = Math.floor(remaining / 60);
                const seconds = remaining % 60;
                document.getElementById('timer').textContent =
                    String(minutes).padStart(2, '0') + ':' + String(seconds).padStart(2, '0');
            }}

            function startTimer() {{
                if (interval || remaining <= 0) return;
                document.getElementById('status').textContent = 'Foco em andamento';
                interval = setInterval(() => {{
                    remaining -= 1;
                    draw();
                    if (remaining <= 0) {{
                        clearInterval(interval);
                        interval = null;
                        remaining = 0;
                        draw();
                        document.getElementById('status').textContent = '✅ Sessão concluída!';
                    }}
                }}, 1000);
            }}

            function pauseTimer() {{
                if (interval) {{
                    clearInterval(interval);
                    interval = null;
                    document.getElementById('status').textContent = 'Sessão pausada';
                }}
            }}

            function resetTimer() {{
                if (interval) clearInterval(interval);
                interval = null;
                remaining = initialSeconds;
                draw();
                document.getElementById('status').textContent = 'Pronto para começar';
            }}
        </script>
        """,
        height=285,
    )


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

        config = {
            row["disciplina"]: row["ambiente"]
            for row in get_config()
        }

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

        complete_col, cancel_col = st.columns([3, 1])
        with complete_col:
            if st.button(
                "✅ CONCLUIR MISSÃO",
                type="primary",
                use_container_width=True,
            ):
                hours, xp = complete_mission(mission)
                st.session_state["pending_mission"] = None
                st.session_state["completion"] = {
                    "hours": hours,
                    "xp": xp,
                }
                st.rerun()

        with cancel_col:
            if st.button("✖️ Cancelar", use_container_width=True):
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

            if st.button(
                "🚀 SORTEAR MISSÃO",
                type="primary",
                use_container_width=True,
            ):
                environment = "Ambos"
                if "Transporte" in mode:
                    environment = "Transporte"
                elif "Mesa" in mode:
                    environment = "Mesa"

                mission = draw_mission(hours, environment)
                if mission:
                    st.session_state["pending_mission"] = mission
                    st.session_state.pop("completion", None)
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
    minutes = st.select_slider(
        "Duração da sessão",
        options=[25, 40, 50, 60, 90],
        value=50,
    )
    render_pomodoro(minutes)
    st.caption(
        "O cronômetro roda no navegador, então não bloqueia mais o Streamlit."
    )
