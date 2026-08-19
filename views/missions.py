import streamlit as st
import streamlit.components.v1 as components

from modules.config import XP_POR_HORA
from modules.database import get_config
from modules.questions import record_session
from modules.studies import complete_mission, draw_mission
from modules.ui import header, section


def render_pomodoro(minutes):
    seconds = int(minutes) * 60
    components.html(
        f"""
        <div class="timer-shell">
            <div class="timer-label">FOCO</div>
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
                background: linear-gradient(145deg, #101725, #0b101a);
                border: 1px solid rgba(125,211,252,.18);
                border-radius: 18px;
                padding: 28px;
                text-align: center;
                color: #f8fafc;
                box-shadow: 0 18px 50px rgba(0,0,0,.20);
            }}
            .timer-label {{
                color: #7dd3fc;
                font-size: 11px;
                font-weight: 800;
                letter-spacing: .18em;
            }}
            #timer {{
                font-size: 64px;
                line-height: 1;
                font-weight: 800;
                margin: 18px 0 10px;
                font-variant-numeric: tabular-nums;
            }}
            #status {{ color: #94a3b8; font-size: 14px; margin-bottom: 22px; }}
            .timer-actions {{ display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; }}
            button {{
                border: 1px solid rgba(125,211,252,.20);
                background: #151e2e;
                color: #f8fafc;
                border-radius: 10px;
                padding: 10px 16px;
                font-weight: 700;
                cursor: pointer;
            }}
            button:hover {{ background: #1b2940; border-color: rgba(125,211,252,.42); }}
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
                        document.getElementById('status').textContent = '✅ Sessão concluída';
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


def render_review(mission):
    total_hours = sum(mission.values())
    subjects = " • ".join(mission.keys())

    st.html(
        f"""
        <div class="question-review">
            <div class="question-review-label">FECHAMENTO DA MISSÃO</div>
            <div class="question-review-title">Como foi sua prática?</div>
            <div class="question-review-meta">{total_hours}h • {subjects}</div>
        </div>
        """
    )

    with st.form("mission_review_form"):
        col_total, col_correct, col_wrong = st.columns(3)

        with col_total:
            total = st.number_input(
                "Questões feitas",
                min_value=0,
                step=1,
                value=0,
            )

        with col_correct:
            correct = st.number_input(
                "Acertos",
                min_value=0,
                step=1,
                value=0,
            )

        with col_wrong:
            wrong = st.number_input(
                "Erros",
                min_value=0,
                step=1,
                value=0,
            )

        submitted = st.form_submit_button(
            "✅ SALVAR E CONCLUIR",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if correct + wrong != total:
            st.error("Acertos + erros precisam ser iguais ao total de questões feitas.")
            return

        hours, xp = complete_mission(mission)
        record_session(mission, total, correct, wrong)

        st.session_state["pending_mission"] = None
        st.session_state["mission_review"] = None
        st.session_state["completion"] = {
            "hours": hours,
            "xp": xp,
            "questions": total,
            "correct": correct,
            "wrong": wrong,
        }
        st.rerun()

    if st.button("← Voltar para a missão", use_container_width=True):
        st.session_state["mission_review"] = None
        st.rerun()


def render():
    header(
        "Missões",
        "Sorteie uma sessão, estude e registre o resultado no final.",
    )

    if "pending_mission" not in st.session_state:
        st.session_state["pending_mission"] = None

    if "mission_review" not in st.session_state:
        st.session_state["mission_review"] = None

    if st.session_state["mission_review"]:
        render_review(st.session_state["mission_review"])

    elif st.session_state["pending_mission"]:
        mission = st.session_state["pending_mission"]
        total_hours = sum(mission.values())

        st.html(
            f"""
            <div class="mission mission-active">
                <div class="mission-kicker">MISSÃO ATIVA</div>
                <div class="mission-title">Sessão pronta</div>
                <div class="mission-hours">{total_hours}h</div>
                <div class="mission-meta">Conclua quando terminar o estudo.</div>
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
                        <span class="mission-separator">•</span>
                        {hours}h
                        <span class="mission-separator">•</span>
                        +{hours * XP_POR_HORA} XP
                    </div>
                </div>
                """
            )

        complete_col, cancel_col = st.columns([3, 1])

        with complete_col:
            if st.button(
                "✅ FINALIZAR MISSÃO",
                type="primary",
                use_container_width=True,
            ):
                st.session_state["mission_review"] = mission
                st.rerun()

        with cancel_col:
            if st.button("✖️ Cancelar", use_container_width=True):
                st.session_state["pending_mission"] = None
                st.session_state["mission_review"] = None
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
                "◆ SORTEAR MISSÃO",
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
                    st.session_state["mission_review"] = None
                    st.session_state.pop("completion", None)
                    st.rerun()
                else:
                    st.warning("Não há horas disponíveis para esse ambiente.")

    if st.session_state.get("completion"):
        completion = st.session_state["completion"]
        total = completion["questions"]
        correct = completion["correct"]
        accuracy = (correct / total * 100) if total else 0

        st.success(
            f"Missão concluída: {completion['hours']}h • +{completion['xp']} XP • "
            f"{total} questões • {accuracy:.0f}% de acerto"
        )

    st.write("")
    section("⏱️ Pomodoro")
    minutes = st.select_slider(
        "Duração da sessão",
        options=[25, 40, 50, 60, 90],
        value=50,
    )
    render_pomodoro(minutes)
