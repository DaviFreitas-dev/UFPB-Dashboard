import streamlit as st

from modules.activity import add as add_activity
from modules.activity import today as activities_today
from modules.database import get_xp
from modules.habits import today as habits_today
from modules.reading import all_books
from modules.routine import today_records as routine_today
from modules.studies import calculate_level, stats
from modules.tasks import today_records as tasks_today
from modules.tasks import toggle as toggle_task
from modules.ui import header, section


def render():
    xp = get_xp()
    level, _, _, _ = calculate_level(xp)
    study_stats = stats()
    books = all_books()
    habits = habits_today()
    activities = activities_today()
    tasks = tasks_today()
    routine = routine_today()

    habit_done = sum(habit["feito"] == "Sim" for habit in habits)

    header(
        "Hoje",
        "Seu painel do dia: estudos, tarefas, leitura, hábitos e atividade.",
    )

    cols = st.columns(4)
    cards = [
        ("📚", "Estudos", f"{study_stats['hours']}h", "total acumulado"),
        ("📖", "Leitura", str(len(books)), "livros cadastrados"),
        ("🔥", "Hábitos", f"{habit_done}/{len(habits)}", "concluídos hoje"),
        ("⚡", "XP", f"{xp:,}".replace(",", "."), f"Nível {level}"),
    ]

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
    left, right = st.columns([1.1, 1], gap="large")

    with left:
        section("🎯 Prioridades de hoje")
        if not tasks:
            st.info("Nenhuma tarefa para hoje.")
        else:
            for task in tasks:
                checked = task["status"] == "Concluída"
                new_value = st.checkbox(
                    task["tarefa"],
                    value=checked,
                    key=f"home_task_{task['id']}",
                )
                if new_value != checked:
                    toggle_task(task["id"], new_value)
                    st.rerun()

        section("📅 Próximos horários")
        if not routine:
            st.info("Sua rotina de hoje está vazia.")
        else:
            for item in sorted(routine, key=lambda x: x["hora"]):
                status = "✅" if item["status"] == "Concluída" else "•"
                st.write(f"{status} **{item['hora']}** — {item['atividade']}")

    with right:
        section("📖 Leitura atual")
        current = [book for book in books if book["status"] == "Lendo"]

        if current:
            book = current[0]
            current_page = int(book["pagina_atual"])
            total_pages = int(book["total_paginas"])
            book_progress = current_page / total_pages if total_pages else 0

            st.html(
                f"""
                <div class="panel">
                    <div style="color:#f4f7fb;font-weight:800;">{book['titulo']}</div>
                    <div style="color:#91a4bc;font-size:.8rem;margin-top:4px;">{book['autor']}</div>
                    <div style="margin-top:14px;color:#f4f7fb;">Página {current_page} de {total_pages}</div>
                </div>
                """
            )
            st.progress(book_progress)
        else:
            st.info("Você ainda não definiu uma leitura atual.")

        section("🏋️ Atividade de hoje")
        if activities:
            for item in activities:
                st.success(f"✅ {item['tipo']}")
        elif st.button("✅ Marcar treino", use_container_width=True):
            add_activity("Treino")
            st.rerun()
