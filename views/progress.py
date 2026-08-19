import pandas as pd
import streamlit as st

from modules.database import get_history, get_xp, records
from modules.gamification import general_streak
from modules.planner import weekly_summary
from modules.questions import (
    subject_totals,
    totals as question_totals,
    weekly_accuracy_series,
)
from modules.studies import calculate_level, stats
from modules.ui import header, section


def render_question_chart(question_stats):
    chart_data = pd.DataFrame(
        [
            {"resultado": "Acertos", "quantidade": question_stats["correct"]},
            {"resultado": "Erros", "quantidade": question_stats["wrong"]},
        ]
    )

    spec = {
        "mark": {
            "type": "arc",
            "outerRadius": 118,
            "innerRadius": 70,
            "stroke": "#081126",
            "strokeWidth": 3,
            "cornerRadius": 5,
        },
        "encoding": {
            "theta": {
                "field": "quantidade",
                "type": "quantitative",
            },
            "color": {
                "field": "resultado",
                "type": "nominal",
                "scale": {
                    "domain": ["Acertos", "Erros"],
                    "range": ["#3ed9a4", "#ff668f"],
                },
                "legend": {
                    "title": None,
                    "orient": "bottom",
                    "labelColor": "#8392b3",
                },
            },
            "tooltip": [
                {"field": "resultado", "type": "nominal", "title": "Resultado"},
                {"field": "quantidade", "type": "quantitative", "title": "Questões"},
            ],
        },
        "view": {"stroke": None},
        "background": None,
    }

    st.vega_lite_chart(chart_data, spec, use_container_width=True)


def render_summary_cards(study, questions, streak):
    values = [
        ("◷", "HORAS", f"{study['hours']}h", "tempo acumulado"),
        ("◎", "QUESTÕES", questions["total"], "resolvidas"),
        ("↗", "APROVEITAMENTO", f"{questions['accuracy']:.1%}", "média geral"),
        ("⚡", "SEQUÊNCIA", streak, "dias ativos"),
    ]
    cols = st.columns(4)

    for col, (icon, label, value, note) in zip(cols, values):
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


def render():
    xp = get_xp()
    level, xp_in_level, level_progress, missing = calculate_level(xp)
    study = stats()
    questions = question_totals()
    streak = general_streak()
    week = weekly_summary()

    header("Progresso", "Seu desempenho em uma visão única.")
    render_summary_cards(study, questions, streak)

    st.write("")
    st.progress(
        level_progress,
        text=f"Nível {level} • {xp_in_level}/1000 XP • faltam {missing} XP",
    )

    section("Esta semana")
    week_cols = st.columns(5)
    week_values = [
        ("Horas", f"{week['hours']}h"),
        ("Questões", week["questions"]),
        ("Acerto", f"{week['accuracy']:.0%}"),
        ("Tarefas", week["tasks"]),
        ("Revisões", week["reviews"]),
    ]

    for col, (label, value) in zip(week_cols, week_values):
        with col:
            st.metric(label, value)

    section("Horas estudadas")
    history = get_history()

    if history:
        df = pd.DataFrame(history)
        df["data"] = pd.to_datetime(df["data"], errors="coerce")
        df["horas"] = pd.to_numeric(df["horas"], errors="coerce").fillna(0)
        df = df.dropna(subset=["data"]).sort_values("data").set_index("data")
        st.bar_chart(df, y="horas")
    else:
        st.info("Ainda não há histórico de estudo.")

    section("Questões")
    if questions["total"] > 0:
        left, right = st.columns([1.05, 1], gap="large")

        with left:
            st.html(
                f"""
                <div class="performance-card">
                    <div class="performance-label">DESEMPENHO GERAL</div>
                    <div class="performance-value">{questions['accuracy']:.1%}</div>
                    <div class="performance-copy">
                        {questions['correct']} acertos • {questions['wrong']} erros • {questions['total']} questões
                    </div>
                </div>
                """
            )

        with right:
            st.html(
                """
                <div class="dashboard-card-label" style="margin:6px 0 0 4px">DISTRIBUIÇÃO</div>
                """
            )
            render_question_chart(questions)
    else:
        st.info("Registre questões ao concluir uma missão para liberar esta análise.")

    section("Evolução semanal")
    trend = pd.DataFrame(weekly_accuracy_series(8))

    if trend["questoes"].sum() > 0:
        chart = trend.set_index("semana")
        st.line_chart(chart, y="acuracia")
        st.caption("Percentual de acerto nas últimas 8 semanas.")
    else:
        st.info("Ainda não há questões suficientes para mostrar a evolução.")

    section("Desempenho por matéria")
    subjects = subject_totals()

    if subjects:
        rows = []
        for subject, values in subjects.items():
            rows.append(
                {
                    "Matéria": subject,
                    "Questões": values["total"],
                    "Acertos": values["correct"],
                    "Erros": values["wrong"],
                    "Aproveitamento": values["accuracy"] * 100,
                }
            )

        subject_df = pd.DataFrame(rows).sort_values(
            ["Aproveitamento", "Questões"],
            ascending=[False, False],
        )

        st.dataframe(
            subject_df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Aproveitamento": st.column_config.ProgressColumn(
                    "Aproveitamento",
                    min_value=0,
                    max_value=100,
                    format="%.1f%%",
                )
            },
        )
    else:
        st.info("O desempenho por matéria começa a aparecer nas novas sessões registradas.")

    section("Pontos para revisar")
    open_errors = [
        row for row in records("Erros")
        if row.get("status") != "Resolvido"
    ]

    if not open_errors:
        st.success("Nenhum erro aberto no caderno.")
    else:
        error_df = pd.DataFrame(open_errors)
        if not error_df.empty:
            grouped = (
                error_df.assign(
                    quantidade=pd.to_numeric(
                        error_df["quantidade"],
                        errors="coerce",
                    ).fillna(0)
                )
                .groupby(["disciplina", "assunto"], as_index=False)["quantidade"]
                .sum()
                .sort_values("quantidade", ascending=False)
            )
            st.dataframe(
                grouped.rename(
                    columns={
                        "disciplina": "Matéria",
                        "assunto": "Assunto",
                        "quantidade": "Erros",
                    }
                ),
                hide_index=True,
                use_container_width=True,
            )
