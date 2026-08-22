import streamlit as st
import streamlit.components.v1 as components

from modules.config import XP_POR_HORA
from modules.database import get_config, new_id
from modules.studies import draw_mission
from modules.study_sessions import (
    MissionConsistencyError,
    complete_study_session,
)
from modules.ui import header, section, without_emoji


def render_pomodoro(minutes):
    seconds = int(minutes) * 60
    components.html(
        f"""
        <div class="timer-shell">
            <div class="timer-topline">
                <span class="timer-dot"></span>
                SESSÃO DE FOCO
            </div>
            <div id="timer">{minutes:02d}:00</div>
            <div id="status">Pronto para começar</div>
            <div class="timer-actions">
                <button class="primary" onclick="startTimer()">Iniciar</button>
                <button onclick="pauseTimer()">Pausar</button>
                <button onclick="resetTimer()">Reiniciar</button>
            </div>
        </div>

        <style>
            * {{ box-sizing: border-box; }}
            body {{ margin: 0; font-family: Inter, "Segoe UI", Arial, sans-serif; background: transparent; }}
            .timer-shell {{
                position: relative;
                overflow: hidden;
                background: #15181d;
                border: 1px solid #2a2f37;
                border-radius: 12px;
                padding: 28px;
                text-align: center;
                color: #f2f4f7;
            }}
            .timer-topline {{
                display: inline-flex;
                align-items: center;
                gap: 7px;
                color: #8f96a3;
                font-size: 10px;
                font-weight: 850;
                letter-spacing: .16em;
            }}
            .timer-dot {{
                width: 6px;
                height: 6px;
                border-radius: 50%;
                background: #7692ff;
            }}
            #timer {{
                font-size: 62px;
                line-height: 1;
                font-weight: 850;
                letter-spacing: -.05em;
                margin: 18px 0 9px;
                font-variant-numeric: tabular-nums;
            }}
            #status {{ color: #9198a5; font-size: 13px; margin-bottom: 22px; }}
            .timer-actions {{ display: flex; gap: 9px; justify-content: center; flex-wrap: wrap; }}
            button {{
                min-width: 96px;
                border: 1px solid #303640;
                background: #1c2026;
                color: #e5e8ed;
                border-radius: 9px;
                padding: 10px 15px;
                font-weight: 750;
                cursor: pointer;
                transition: all .15s ease;
            }}
            button:hover {{ background: #242931; border-color: #465062; }}
            button.primary {{ background: #6f8cff; border-color: #6f8cff; color: #0d1015; }}
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
                        document.getElementById('status').textContent = 'Sessão concluída';
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

    st.html(
        f"""
        <div class="question-review">
            <div class="question-review-label">FECHAR MISSÃO</div>
            <div class="question-review-title">Registre o que foi feito</div>
            <div class="question-review-meta">{total_hours}h planejadas</div>
        </div>
        """
    )

    subjects = list(mission.keys())

    with st.form("mission_review_form"):
        primary_subject = st.selectbox(
            "Disciplina principal",
            subjects,
            format_func=without_emoji,
        )
        topic = st.text_input(
            "Assunto estudado",
            placeholder="Ex.: Cinemática ou funções",
        )

        col_total, col_correct, col_wrong = st.columns(3)
        with col_total:
            total = st.number_input("Questões feitas", min_value=0, step=1, value=0)
        with col_correct:
            correct = st.number_input("Acertos", min_value=0, step=1, value=0)
        with col_wrong:
            wrong = st.number_input("Erros", min_value=0, step=1, value=0)

        note = st.text_area(
            "Observações",
            placeholder="Opcional. Anote o que precisa revisar.",
            height=90,
        )

        submitted = st.form_submit_button(
            "Salvar e concluir",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if correct + wrong != total:
            st.error("Acertos + erros precisam ser iguais ao total.")
            return

        session_id = st.session_state.get("pending_mission_id") or new_id()
        st.session_state["pending_mission_id"] = session_id
        try:
            session = complete_study_session(
                session_id,
                mission,
                primary_subject,
                topic,
                total,
                correct,
                wrong,
                note,
            )
        except (ValueError, MissionConsistencyError) as error:
            st.error(str(error))
            return

        st.session_state["pending_mission"] = None
        st.session_state["pending_mission_id"] = None
        st.session_state["mission_review"] = None
        st.session_state["completion"] = {
            "hours": session["hours"],
            "base_xp": session["base_xp"],
            "bonus_xp": session["question_xp"],
            "questions": session["questions"],
            "correct": session["correct"],
        }
        st.rerun()

    if st.button("Voltar", use_container_width=True):
        st.session_state["mission_review"] = None
        st.rerun()


def render():
    header("Missões", "Defina a sessão e registre o resultado.")

    if "pending_mission" not in st.session_state:
        st.session_state["pending_mission"] = None
    if "mission_review" not in st.session_state:
        st.session_state["mission_review"] = None
    if "pending_mission_id" not in st.session_state:
        st.session_state["pending_mission_id"] = (
            new_id() if st.session_state["pending_mission"] else None
        )

    if st.session_state["mission_review"]:
        render_review(st.session_state["mission_review"])

    elif st.session_state["pending_mission"]:
        mission = st.session_state["pending_mission"]
        total_hours = sum(mission.values())

        st.html(
            f"""
            <div class="mission mission-active">
                <div class="mission-kicker">MISSÃO ATIVA</div>
                <div class="mission-title">Sessão em andamento</div>
                <div class="mission-hours">{total_hours}h</div>
                <div class="mission-meta">Ao terminar, registre as horas e as questões.</div>
            </div>
            """
        )

        config = {
            row.get("disciplina"): row.get("ambiente")
            for row in get_config()
        }

        for subject, hours in mission.items():
            subject_label = without_emoji(subject)
            st.html(
                f"""
                <div class="mission">
                    <div class="mission-title">{subject_label}</div>
                    <div class="mission-meta">
                        <span class="badge">{config.get(subject, 'Ambos')}</span>
                        • {hours}h • +{hours * XP_POR_HORA} XP
                    </div>
                </div>
                """
            )

        complete_col, cancel_col = st.columns([3, 1])
        with complete_col:
            if st.button("Finalizar missão", type="primary", use_container_width=True):
                st.session_state["mission_review"] = mission
                st.rerun()
        with cancel_col:
            if st.button("Cancelar", use_container_width=True):
                st.session_state["pending_mission"] = None
                st.session_state["pending_mission_id"] = None
                st.session_state["mission_review"] = None
                st.rerun()

    else:
        with st.container(border=True):
            mode = st.radio(
                "Ambiente",
                ["Qualquer ambiente", "Transporte", "Mesa"],
                horizontal=True,
            )
            hours = st.slider("Horas", 1, 6, 3)

            if st.button("Sortear missão", type="primary", use_container_width=True):
                environment = "Ambos"
                if "Transporte" in mode:
                    environment = "Transporte"
                elif "Mesa" in mode:
                    environment = "Mesa"

                mission = draw_mission(hours, environment)
                if mission:
                    st.session_state["pending_mission"] = mission
                    st.session_state["pending_mission_id"] = new_id()
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
        total_xp = completion["base_xp"] + completion["bonus_xp"]

        st.success(
            f"Missão concluída: {completion['hours']}h, {total_xp} XP e "
            f"{accuracy:.0f}% de acerto em {total} questões. "
            "Revisões marcadas para 1, 7 e 30 dias."
        )

    st.write("")
    section("Pomodoro")
    minutes = st.select_slider(
        "Duração",
        options=[25, 40, 50, 60, 90],
        value=50,
    )
    render_pomodoro(minutes)
