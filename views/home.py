from datetime import date, timedelta
from html import escape

import streamlit as st

from modules.activity import add as add_activity
from modules.activity import today as activities_today
from modules.database import get_xp
from modules.gamification import general_streak
from modules.habits import today as habits_today
from modules.planner import (
    add_journal,
    add_priority,
    assessments,
    checkins_for_date,
    complete_review,
    due_reviews,
    priorities_for_date,
    toggle_weekly,
    weekly_for_date,
    weekly_goal_progress,
)
from modules.reading import all_books, remaining_today
from modules.routine import today_records as routine_today
from modules.routine import toggle as toggle_routine
from modules.studies import calculate_level, stats
from modules.tasks import add as add_task
from modules.tasks import today_records as tasks_today
from modules.tasks import toggle as toggle_task
from modules.ui import header, section


MONTHS_PT = [
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
]


def render_quick_capture():
    with st.expander("＋ Captura rápida"):
        capture_type = st.radio(
            "Tipo",
            ["Tarefa", "Amanhã", "Diário"],
            horizontal=True,
            label_visibility="collapsed",
        )

        if capture_type == "Tarefa":
            with st.form("home_quick_task", clear_on_submit=True):
                task = st.text_input(
                    "Tarefa",
                    placeholder="Ex.: terminar exercícios de Física",
                )
                category = st.selectbox(
                    "Categoria",
                    ["Escola", "Estudos", "Pessoal", "Projeto", "Outro"],
                )
                submitted = st.form_submit_button(
                    "Adicionar para hoje",
                    type="primary",
                    use_container_width=True,
                )

            if submitted and task.strip():
                add_task(task.strip(), category, date.today())
                st.rerun()

        elif capture_type == "Amanhã":
            with st.form("home_quick_tomorrow", clear_on_submit=True):
                priority = st.text_input(
                    "Prioridade",
                    placeholder="Uma das 3 coisas mais importantes de amanhã",
                )
                submitted = st.form_submit_button(
                    "Adicionar para amanhã",
                    type="primary",
                    use_container_width=True,
                )

            if submitted and priority.strip():
                if add_priority(
                    date.today() + timedelta(days=1),
                    priority.strip(),
                ):
                    st.rerun()
                else:
                    st.warning("Amanhã já tem 3 prioridades.")

        else:
            with st.form("home_quick_journal", clear_on_submit=True):
                note = st.text_area(
                    "Nota",
                    placeholder="O que aprendeu ou quer lembrar?",
                    height=90,
                )
                submitted = st.form_submit_button(
                    "Salvar",
                    type="primary",
                    use_container_width=True,
                )

            if submitted and note.strip():
                add_journal(note)
                st.rerun()


def render_top_cards(xp, level, streak, study_stats, goal):
    left, middle, right = st.columns([1, 1, 1.28], gap="small")

    cards = [
        (left, "⚡", "XP TOTAL", f"{xp:,}".replace(",", "."), f"nível {level}"),
        (middle, "🔥", "SEQUÊNCIA", str(streak), "dias ativos"),
    ]

    for col, icon, label, value, note in cards:
        with col:
            st.html(
                f"""
                <div class="stat-card">
                    <div class="stat-icon">{icon}</div>
                    <div class="stat-label">{label}</div>
                    <div class="stat-value">{value}</div>
                    <div class="stat-note">{note}</div>
                </div>
                """
            )

    progress_percent = round(goal["progress"] * 100)
    progress_degrees = round(goal["progress"] * 360)

    with right:
        st.html(
            f"""
            <div class="dashboard-card">
                <div class="progress-orb-wrap">
                    <div class="progress-orb" style="--progress:{progress_degrees}deg">
                        <div class="progress-orb-value">{progress_percent}%<small>da meta</small></div>
                    </div>
                    <div>
                        <div class="dashboard-card-label">QUESTÕES DA SEMANA</div>
                        <div class="dashboard-card-title">{goal['done']} de {goal['target']}</div>
                        <div class="dashboard-card-copy">
                            {study_stats['hours']}h estudadas no histórico total. Continue avançando sem quebrar a sequência.
                        </div>
                    </div>
                </div>
            </div>
            """
        )


def render():
    today = date.today()
    tomorrow = today + timedelta(days=1)
    xp = get_xp()
    level, _, _, _ = calculate_level(xp)
    study_stats = stats()
    streak = general_streak()
    goal = weekly_goal_progress()

    books = all_books()
    habits = habits_today()
    activities = activities_today()
    tasks = tasks_today()
    routine = routine_today()
    fixed = weekly_for_date(today)
    fixed_checkins = checkins_for_date(today)
    reviews = due_reviews(today)
    deadlines = assessments()
    tomorrow_priorities = priorities_for_date(tomorrow)

    date_text = f"{today.day} de {MONTHS_PT[today.month - 1]} de {today.year}"

    header("Hoje", date_text)
    render_top_cards(xp, level, streak, study_stats, goal)
    render_quick_capture()

    if deadlines:
        nearest = deadlines[0]
        try:
            target = date.fromisoformat(str(nearest.get("data")))
            days = (target - today).days
        except ValueError:
            days = 0

        label = "BOSS" if nearest.get("tipo") == "Prova" else "PRÓXIMO PRAZO"
        countdown = (
            "hoje"
            if days == 0
            else f"faltam {days} dia(s)"
            if days > 0
            else f"atrasado {abs(days)} dia(s)"
        )
        title = escape(str(nearest.get("titulo", "")))
        subject = escape(str(nearest.get("disciplina", "")))
        target_text = escape(str(nearest.get("data", "")))

        st.html(
            f"""
            <div class="mission mission-active">
                <div class="mission-kicker">{label}</div>
                <div class="mission-title">{title}</div>
                <div class="mission-meta">{subject} • {target_text} • {countdown}</div>
            </div>
            """
        )

    left, right = st.columns([1.18, 1], gap="large")

    with left:
        section("Revisões")
        if not reviews:
            st.success("Nenhuma revisão pendente.")
        else:
            for review in reviews[:4]:
                row_col, action_col = st.columns([5, 2])
                with row_col:
                    st.write(
                        f"**{review.get('disciplina', '')}** — "
                        f"{review.get('assunto', '')}"
                    )
                    st.caption(f"Prevista para {review.get('data', '')}")
                with action_col:
                    if st.button(
                        "Feita",
                        key=f"home_review_{review['id']}",
                        use_container_width=True,
                    ):
                        complete_review(review["id"])
                        st.rerun()

        section("Prioridades de hoje")
        if not tasks:
            st.info("Nenhuma tarefa para hoje.")
        else:
            for task in tasks:
                checked = task.get("status") == "Concluída"
                new_value = st.checkbox(
                    task.get("tarefa", ""),
                    value=checked,
                    key=f"home_task_{task['id']}",
                )
                if new_value != checked:
                    toggle_task(task["id"], new_value)
                    st.rerun()

        section("Agenda de hoje")
        combined = []
        for item in fixed:
            combined.append((str(item.get("hora", "")), "fixa", item))
        for item in routine:
            combined.append((str(item.get("hora", "")), "avulsa", item))

        if not combined:
            st.info("Nada marcado para hoje.")
        else:
            for _, kind, item in sorted(combined, key=lambda row: row[0]):
                if kind == "fixa":
                    checkin = fixed_checkins.get(str(item["id"]), {})
                    checked = checkin.get("status") == "Concluída"
                    new_value = st.checkbox(
                        f"{item.get('hora', '--:--')} — {item.get('atividade', '')}",
                        value=checked,
                        key=f"home_fixed_{item['id']}",
                    )
                    if new_value != checked:
                        toggle_weekly(item["id"], today, new_value)
                        st.rerun()
                else:
                    checked = item.get("status") == "Concluída"
                    new_value = st.checkbox(
                        f"{item.get('hora', '--:--')} — {item.get('atividade', '')}",
                        value=checked,
                        key=f"home_routine_{item['id']}",
                    )
                    if new_value != checked:
                        toggle_routine(item["id"], new_value)
                        st.rerun()

    with right:
        section("Amanhã")
        if not tomorrow_priorities:
            st.info("Nenhuma prioridade definida.")
        else:
            rows_html = "".join(
                f"""
                <div class="data-row">
                    <div class="data-row-main">
                        <div class="data-row-title">{escape(str(item.get('prioridade', '')))}</div>
                        <div class="data-row-subtitle">prioridade planejada</div>
                    </div>
                    <span class="data-chip">amanhã</span>
                </div>
                """
                for item in tomorrow_priorities
            )
            st.html(f'<div class="dashboard-card">{rows_html}</div>')

        section("Leitura")
        current = [book for book in books if book.get("status") == "Lendo"]

        if current:
            book = current[0]
            current_page = int(book.get("pagina_atual", 0) or 0)
            total_pages = max(1, int(book.get("total_paginas", 1) or 1))
            progress = min(current_page / total_pages, 1.0)
            daily_target = remaining_today(book)
            title = escape(str(book.get("titulo", "")))
            author = escape(str(book.get("autor", "")))

            st.html(
                f"""
                <div class="dashboard-card">
                    <div class="dashboard-card-label">LENDO AGORA</div>
                    <div class="dashboard-card-title">{title}</div>
                    <div class="dashboard-card-copy">{author}</div>
                    <div class="data-row">
                        <div class="data-row-title">Página {current_page} de {total_pages}</div>
                        <span class="data-chip">+{daily_target} hoje</span>
                    </div>
                </div>
                """
            )
            st.progress(progress)
        else:
            st.info("Nenhuma leitura atual.")

        section("Hábitos")
        if not habits:
            st.info("Nenhum hábito ativo.")
        else:
            done = sum(habit.get("feito") == "Sim" for habit in habits)
            st.progress(done / len(habits), text=f"{done}/{len(habits)} concluídos")
            for habit in habits:
                icon = "✓" if habit.get("feito") == "Sim" else "○"
                st.write(f"{icon} {habit.get('habito', '')}")

        section("Atividade")
        if activities:
            for item in activities:
                st.success(f"✓ {item.get('tipo', '')}")
        elif st.button("Marcar treino", use_container_width=True):
            add_activity("Treino")
            st.rerun()
