from datetime import date, timedelta
from html import escape

import streamlit as st

from modules.planner import (
    WEEKDAYS,
    add_assessment,
    add_journal,
    add_priority,
    add_weekly,
    archive_weekly,
    assessments,
    complete_assessment,
    complete_review,
    current_week_goal,
    due_reviews,
    journal_entries,
    open_errors,
    priorities_for_date,
    remove_assessment,
    resolve_error,
    set_weekly_question_goal,
    toggle_priority,
    weekly_goal_progress,
    weekly_items,
    weekly_summary,
)
from modules.ui import header, section, without_emoji


def render_calendar(items):
    day_blocks = []

    for day_name in WEEKDAYS:
        day_items = [
            item for item in items
            if item.get("dia_semana") == day_name
        ]
        entries = []

        for item in sorted(day_items, key=lambda row: str(row.get("hora", ""))):
            entries.append(
                f"""
                <div class="calendar-item">
                    <div class="calendar-item-time">{escape(str(item.get('hora', '--:--')))}</div>
                    <div class="calendar-item-title">{escape(str(item.get('atividade', '')))}</div>
                    <div class="calendar-item-category">{escape(str(item.get('categoria', '')))}</div>
                </div>
                """
            )

        if not entries:
            entries.append(
                '<div class="calendar-item-category" style="padding:6px 2px">livre</div>'
            )

        day_blocks.append(
            f"""
            <div class="calendar-day">
                <div class="calendar-day-name">{day_name}</div>
                {''.join(entries)}
            </div>
            """
        )

    st.html(
        f"""
        <div class="calendar-board">
            <div class="calendar-grid">{''.join(day_blocks)}</div>
        </div>
        """
    )


def render_week():
    section("Calendário semanal")
    items = weekly_items()
    render_calendar(items)

    with st.expander("Adicionar ou gerenciar horários"):
        with st.form("weekly_schedule_form", clear_on_submit=True):
            cols = st.columns([1.1, 1, 2.4, 1.3])
            with cols[0]:
                day_name = st.selectbox("Dia", WEEKDAYS)
            with cols[1]:
                hour = st.time_input("Horário")
            with cols[2]:
                activity = st.text_input(
                    "Atividade",
                    placeholder="Ex.: Escola, academia, revisão...",
                )
            with cols[3]:
                category = st.selectbox(
                    "Categoria",
                    ["Escola", "Estudo", "Saúde", "Pessoal", "Outro"],
                )

            submitted = st.form_submit_button(
                "Adicionar à semana",
                type="primary",
                use_container_width=True,
            )

        if submitted and activity.strip():
            add_weekly(
                day_name,
                hour.strftime("%H:%M"),
                activity.strip(),
                category,
            )
            st.rerun()

        if not items:
            st.caption("Sem horários fixos.")
        else:
            for day_name in WEEKDAYS:
                day_items = [
                    item for item in items
                    if item.get("dia_semana") == day_name
                ]
                if not day_items:
                    continue

                st.markdown(f"**{day_name}**")
                for item in sorted(day_items, key=lambda row: str(row.get("hora", ""))):
                    text_col, action_col = st.columns([8, 2])
                    with text_col:
                        st.write(
                            f"{item.get('hora', '--:--')} — "
                            f"**{item.get('atividade', '')}** · {item.get('categoria', '')}"
                        )
                    with action_col:
                        if st.button(
                            "Arquivar",
                            key=f"archive_weekly_{item['id']}",
                            help="Arquivar",
                        ):
                            archive_weekly(item["id"])
                            st.rerun()


def render_deadlines():
    section("Provas, trabalhos e prazos")

    with st.form("assessment_form", clear_on_submit=True):
        title = st.text_input("Título", placeholder="Ex.: Prova de Física")
        cols = st.columns(4)
        with cols[0]:
            kind = st.selectbox("Tipo", ["Prova", "Trabalho", "Entrega", "Outro"])
        with cols[1]:
            subject = st.text_input("Disciplina", placeholder="Física")
        with cols[2]:
            target_date = st.date_input("Data", value=date.today() + timedelta(days=7))
        with cols[3]:
            goal = st.number_input(
                "Meta de questões",
                min_value=0,
                max_value=5000,
                value=0,
                step=10,
            )

        submitted = st.form_submit_button(
            "Adicionar prazo",
            type="primary",
            use_container_width=True,
        )

    if submitted and title.strip():
        add_assessment(
            title.strip(),
            kind,
            subject.strip(),
            target_date,
            int(goal),
        )
        st.rerun()

    items = assessments()

    if not items:
        st.info("Nenhum prazo futuro.")
        return

    today = date.today()

    for item in items:
        try:
            target = date.fromisoformat(str(item.get("data")))
            days = (target - today).days
        except ValueError:
            days = 0

        boss = item.get("tipo") == "Prova"
        label = "BOSS" if boss else str(item.get("tipo", "Prazo")).upper()
        countdown = (
            "hoje"
            if days == 0
            else f"em {days} {'dia' if days == 1 else 'dias'}"
            if days > 0
            else f"{abs(days)} {'dia' if abs(days) == 1 else 'dias'} em atraso"
        )
        title_text = escape(str(item.get("titulo", "")))
        subject_text = escape(without_emoji(item.get("disciplina", "")))
        date_text = escape(str(item.get("data", "")))
        question_goal = int(item.get("meta_questoes", 0) or 0)
        meta_text = f" • meta {question_goal} questões" if question_goal else ""

        st.html(
            f"""
            <div class="mission {'mission-active' if boss else ''}">
                <div class="mission-kicker">{label}</div>
                <div class="mission-title">{title_text}</div>
                <div class="mission-meta">
                    {subject_text} • {date_text} • {countdown}{meta_text}
                </div>
            </div>
            """
        )

        done_col, delete_col = st.columns([4, 1])
        with done_col:
            if st.button(
                "Concluir",
                key=f"complete_assessment_{item['id']}",
                use_container_width=True,
            ):
                complete_assessment(item["id"])
                st.rerun()

        with delete_col:
            if st.button(
                "Excluir",
                key=f"delete_assessment_{item['id']}",
                use_container_width=True,
            ):
                remove_assessment(item["id"])
                st.rerun()


def render_reviews_errors():
    left, right = st.columns(2, gap="large")

    with left:
        section("Revisões pendentes")
        reviews = due_reviews()

        if not reviews:
            st.success("Nenhuma revisão vencida.")
        else:
            for review in reviews:
                discipline = escape(without_emoji(review.get("disciplina", "")))
                topic = escape(str(review.get("assunto", "")))
                when = escape(str(review.get("data", "")))
                st.html(
                    f"""
                    <div class="dashboard-card">
                        <div class="dashboard-card-label">REVISÃO</div>
                        <div class="dashboard-card-title">{discipline}</div>
                        <div class="dashboard-card-copy">{topic} • {when}</div>
                    </div>
                    """
                )
                if st.button(
                    "Revisão feita",
                    key=f"review_{review['id']}",
                    use_container_width=True,
                ):
                    complete_review(review["id"])
                    st.rerun()

    with right:
        section("Caderno de erros")
        errors = open_errors()

        if not errors:
            st.success("Nenhum erro pendente.")
        else:
            for error in errors:
                discipline = escape(without_emoji(error.get("disciplina", "")))
                topic = escape(str(error.get("assunto", "")))
                note = escape(str(error.get("nota", ""))) if error.get("nota") else ""
                note_text = f" • {note}" if note else ""
                quantity = int(error.get("quantidade", 0) or 0)
                error_label = "erro" if quantity == 1 else "erros"
                st.html(
                    f"""
                    <div class="dashboard-card">
                        <div class="dashboard-card-label">PONTO FRACO</div>
                        <div class="dashboard-card-title">{discipline} · {topic}</div>
                        <div class="dashboard-card-copy">
                            {quantity} {error_label}{note_text}
                        </div>
                    </div>
                    """
                )
                if st.button(
                    "Marcar como resolvido",
                    key=f"error_{error['id']}",
                    use_container_width=True,
                ):
                    resolve_error(error["id"])
                    st.rerun()


def render_goals_tomorrow():
    left, right = st.columns(2, gap="large")

    with left:
        section("Meta semanal de questões")
        goal = current_week_goal()
        target = int(goal.get("alvo", 200) or 200)

        with st.form("weekly_goal_form"):
            new_target = st.number_input(
                "Questões nesta semana",
                min_value=1,
                max_value=10000,
                value=target,
                step=25,
            )
            submitted = st.form_submit_button(
                "Salvar meta",
                use_container_width=True,
            )

        if submitted:
            set_weekly_question_goal(int(new_target))
            st.rerun()

        progress = weekly_goal_progress()
        progress_percent = round(progress["progress"] * 100)
        progress_degrees = round(progress["progress"] * 360)
        remaining = max(progress["target"] - progress["done"], 0)
        goal_copy = (
            "Meta concluída."
            if remaining == 0
            else f"Faltam {remaining} questões."
        )
        st.html(
            f"""
            <div class="dashboard-card">
                <div class="progress-orb-wrap">
                    <div class="progress-orb" style="--target-progress:{progress_degrees}deg">
                        <div class="progress-orb-value">{progress_percent}%<small>semana</small></div>
                    </div>
                    <div>
                        <div class="dashboard-card-label">META ATUAL</div>
                        <div class="dashboard-card-title">{progress['done']} / {progress['target']} questões</div>
                        <div class="dashboard-card-copy">{goal_copy}</div>
                    </div>
                </div>
            </div>
            """
        )

        if progress["reached"]:
            st.success("Meta concluída. 100 XP adicionados.")

    with right:
        section("Prioridades de amanhã")
        tomorrow = date.today() + timedelta(days=1)
        priorities = priorities_for_date(tomorrow)

        with st.form("tomorrow_priority_form", clear_on_submit=True):
            priority = st.text_input(
                "Nova prioridade",
                placeholder="Ex.: terminar lista de Física",
            )
            submitted = st.form_submit_button(
                "Adicionar",
                use_container_width=True,
            )

        if submitted and priority.strip():
            if add_priority(tomorrow, priority.strip()):
                st.rerun()
            else:
                st.warning("Amanhã já tem três prioridades.")

        for item in priorities:
            checked = item.get("status") == "Concluída"
            new_value = st.checkbox(
                item.get("prioridade", ""),
                value=checked,
                key=f"tomorrow_{item['id']}",
            )
            if new_value != checked:
                toggle_priority(item["id"], new_value)
                st.rerun()


def render_journal():
    section("Diário rápido")

    with st.form("journal_form", clear_on_submit=True):
        text = st.text_area(
            "O que aprendeu, percebeu ou quer lembrar?",
            height=120,
        )
        submitted = st.form_submit_button(
            "Salvar nota",
            type="primary",
            use_container_width=True,
        )

    if submitted and text.strip():
        add_journal(text)
        st.rerun()

    entries = journal_entries()

    if not entries:
        st.info("Nenhuma nota no diário.")
        return

    for entry in entries:
        with st.expander(f"{entry.get('data', '')}"):
            st.write(entry.get("texto", ""))


def render_weekly_review():
    summary = weekly_summary()
    section("Visão da semana")

    cols = st.columns(5)
    values = [
        ("Horas", f"{summary['hours']}h"),
        ("Questões", summary["questions"]),
        ("Acerto", f"{summary['accuracy']:.0%}"),
        ("Tarefas", summary["tasks"]),
        ("Revisões", summary["reviews"]),
    ]

    for col, (label, value) in zip(cols, values):
        with col:
            st.metric(label, value)


def render():
    header("Planejar", "Semana, prazos, revisões e metas.")
    render_weekly_review()

    tabs = st.tabs(
        [
            "Calendário",
            "Prazos",
            "Revisões & erros",
            "Metas & amanhã",
            "Diário",
        ]
    )

    with tabs[0]:
        render_week()

    with tabs[1]:
        render_deadlines()

    with tabs[2]:
        render_reviews_errors()

    with tabs[3]:
        render_goals_tomorrow()

    with tabs[4]:
        render_journal()
