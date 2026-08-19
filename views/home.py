from datetime import date, timedelta

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
    render_quick_capture()

    cards = [
        ("⚡", "XP", f"{xp:,}".replace(",", "."), f"Nível {level}"),
        ("🔥", "Sequência", str(streak), "dias ativos"),
        ("🎯", "Questões", f"{goal['done']}/{goal['target']}", "meta da semana"),
        ("📚", "Estudo", f"{study_stats['hours']}h", "total acumulado"),
    ]

    cols = st.columns(4)

    for col, (icon, label, value, note) in zip(cols, cards):
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

    st.write("")
    st.progress(
        goal["progress"],
        text=f"Meta semanal de questões: {goal['done']} / {goal['target']}",
    )

    if deadlines:
        nearest = deadlines[0]
        try:
            target = date.fromisoformat(str(nearest.get("data")))
            days = (target - today).days
        except ValueError:
            days = 0

        label = "⚔️ BOSS" if nearest.get("tipo") == "Prova" else "📌 PRÓXIMO PRAZO"
        countdown = (
            "hoje"
            if days == 0
            else f"faltam {days} dia(s)"
            if days > 0
            else f"atrasado {abs(days)} dia(s)"
        )

        st.html(
            f"""
            <div class="mission mission-active">
                <div class="mission-kicker">{label}</div>
                <div class="mission-title">{nearest.get('titulo', '')}</div>
                <div class="mission-meta">
                    {nearest.get('disciplina', '')} • {nearest.get('data', '')} • {countdown}
                </div>
            </div>
            """
        )

    left, right = st.columns([1.15, 1], gap="large")

    with left:
        section("🧠 Revisões")
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

        section("✅ Prioridades")
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

        section("🕒 Agenda de hoje")
        combined = []

        for item in fixed:
            combined.append(
                (
                    str(item.get("hora", "")),
                    "fixa",
                    item,
                )
            )

        for item in routine:
            combined.append(
                (
                    str(item.get("hora", "")),
                    "avulsa",
                    item,
                )
            )

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
        section("🌙 Amanhã")
        if not tomorrow_priorities:
            st.info("Nenhuma prioridade definida.")
        else:
            for item in tomorrow_priorities:
                icon = "✓" if item.get("status") == "Concluída" else "•"
                st.write(f"{icon} {item.get('prioridade', '')}")

        section("📖 Leitura")
        current = [
            book
            for book in books
            if book.get("status") == "Lendo"
        ]

        if current:
            book = current[0]
            current_page = int(book.get("pagina_atual", 0) or 0)
            total_pages = max(1, int(book.get("total_paginas", 1) or 1))
            progress = min(current_page / total_pages, 1.0)
            daily_target = remaining_today(book)

            st.html(
                f"""
                <div class="panel">
                    <strong>{book.get('titulo', '')}</strong><br>
                    <span style="color:#94a3b8">{book.get('autor', '')}</span><br>
                    <span>Página {current_page} de {total_pages}</span><br>
                    <span style="color:#7dd3fc">Meta sugerida: {daily_target} página(s)</span>
                </div>
                """
            )
            st.progress(progress)
        else:
            st.info("Nenhuma leitura atual.")

        section("🔥 Hábitos")
        if not habits:
            st.info("Nenhum hábito ativo.")
        else:
            done = sum(habit.get("feito") == "Sim" for habit in habits)
            st.progress(
                done / len(habits),
                text=f"{done}/{len(habits)} concluídos",
            )

            for habit in habits:
                icon = "✅" if habit.get("feito") == "Sim" else "○"
                st.write(f"{icon} {habit.get('habito', '')}")

        section("🏋️ Atividade")
        if activities:
            for item in activities:
                st.success(f"✅ {item.get('tipo', '')}")
        elif st.button("Marcar treino", use_container_width=True):
            add_activity("Treino")
            st.rerun()
