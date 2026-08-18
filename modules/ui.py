from pathlib import Path

import streamlit as st

from modules.config import XP_POR_NIVEL
from modules.database import get_xp


def apply_css():
    css_path = Path(__file__).resolve().parent.parent / "assets" / "style.css"
    css = css_path.read_text(encoding="utf-8")
    st.html(f"<style>{css}</style>")


def render_sidebar():
    xp = get_xp()
    nivel = xp // XP_POR_NIVEL + 1

    with st.sidebar:
        st.html(
            """
            <div class="app-logo">🚀 UFPB ACADEMY</div>
            <div class="app-logo-sub">PERSONAL COMMAND CENTER</div>
            """
        )

        st.html(
            f"""
            <div class="side-level">
                <div class="side-level-label">Nível atual</div>
                <div class="side-level-number">{nivel}</div>
                <div style="color:#38bdf8;font-size:.75rem;">{xp:,} XP</div>
            </div>
            """.replace(",", ".")
        )

        return st.radio(
            "NAVEGAÇÃO",
            [
                "🏠 Hoje",
                "📅 Rotina",
                "🎯 Ciclo",
                "📚 Missões",
                "📖 Leitura",
                "✅ Tarefas",
                "🔥 Hábitos",
                "🏋️ Atividade",
                "📈 Progresso",
                "🏆 Conquistas",
                "⚙️ Configurações",
            ],
            label_visibility="collapsed",
        )


def header(title, subtitle):
    st.html(
        f"""
        <div class="hero">
            <div class="hero-kicker">UFPB ACADEMY</div>
            <div class="hero-title">{title}</div>
            <div class="hero-subtitle">{subtitle}</div>
        </div>
        """
    )


def section(title):
    st.html(f'<div class="section-title">{title}</div>')
