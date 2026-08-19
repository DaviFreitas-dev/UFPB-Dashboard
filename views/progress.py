import pandas as pd
import streamlit as st

from modules.database import get_history, get_xp
from modules.questions import totals as question_totals
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
            "outerRadius": 122,
            "innerRadius": 42,
            "stroke": "#0b1019",
            "strokeWidth": 2,
        },
        "encoding": {
            "theta": {
                "field": "quantidade",
                "type": "quantitative",
                "stack": True,
            },
            "color": {
                "field": "resultado",
                "type": "nominal",
                "scale": {
                    "domain": ["Acertos", "Erros"],
                    "range": ["#34d399", "#fb7185"],
                },
                "legend": {
                    "title": None,
                    "orient": "bottom",
                    "labelColor": "#cbd5e1",
                },
            },
            "tooltip": [
                {"field": "resultado", "type": "nominal", "title": "Resultado"},
                {"field": "quantidade", "type": "quantitative", "title": "Questões"},
            ],
        },
        "view": {"stroke": None},
    }

    st.vega_lite_chart(
        chart_data,
        spec,
        use_container_width=True,
    )


def render():
    xp = get_xp()
    level, xp_in_level, progress, missing = calculate_level(xp)
    study_stats = stats()
    question_stats = question_totals()

    header(
        "Progresso",
        "Seu histórico acumulado de estudo e desempenho.",
    )

    cols = st.columns(4)
    values = [
        ("Horas totais", f"{study_stats['hours']}h"),
        ("Média diária", f"{study_stats['average']:.1f}h"),
        ("Melhor dia", f"{study_stats['best']}h"),
        ("Sequência", f"{study_stats['streak']} dias"),
    ]

    for col, (label, value) in zip(cols, values):
        with col:
            st.metric(label, value)

    st.progress(
        progress,
        text=f"Nível {level} • {xp_in_level}/1000 XP • faltam {missing} XP",
    )

    history = get_history()

    section("📊 Horas estudadas")
    if history:
        df = pd.DataFrame(history)
        df["data"] = pd.to_datetime(df["data"])
        df["horas"] = pd.to_numeric(df["horas"])
        df = df.sort_values("data").set_index("data")
        st.bar_chart(df, y="horas")
    else:
        st.info("Ainda não há histórico de estudo.")

    section("🎯 Questões")

    question_cols = st.columns(4)
    question_values = [
        ("Questões feitas", question_stats["total"]),
        ("Acertos", question_stats["correct"]),
        ("Erros", question_stats["wrong"]),
        ("Aproveitamento", f"{question_stats['accuracy']:.1%}"),
    ]

    for col, (label, value) in zip(question_cols, question_values):
        with col:
            st.metric(label, value)

    if question_stats["total"] > 0:
        left, right = st.columns([1.15, 1], gap="large")

        with left:
            st.html(
                f"""
                <div class="performance-card">
                    <div class="performance-label">DESEMPENHO GERAL</div>
                    <div class="performance-value">{question_stats['accuracy']:.1%}</div>
                    <div class="performance-copy">
                        {question_stats['correct']} acertos em {question_stats['total']} questões registradas.
                    </div>
                </div>
                """
            )

        with right:
            render_question_chart(question_stats)
    else:
        st.info(
            "Quando você concluir uma missão e registrar suas questões, "
            "o gráfico de acertos e erros aparecerá aqui."
        )
