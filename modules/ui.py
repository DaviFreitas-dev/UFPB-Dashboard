import re
from pathlib import Path

import streamlit as st

from modules.config import XP_POR_NIVEL
from modules.database import get_xp


_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F1E6-\U0001F1FF"
    "\U0001F300-\U0001FAFF"
    "\u2600-\u27BF"
    "\u200D\uFE0E\uFE0F"
    "]+",
)


def without_emoji(value):
    text = _EMOJI_PATTERN.sub("", str(value))
    return re.sub(r"\s+", " ", text).strip()


def apply_css():
    css_path = Path(__file__).resolve().parent.parent / "assets" / "style.css"
    css = css_path.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_sidebar():
    xp = get_xp()
    level = xp // XP_POR_NIVEL + 1
    xp_in_level = xp % XP_POR_NIVEL
    progress = int((xp_in_level / XP_POR_NIVEL) * 100)

    with st.sidebar:
        st.html(
            """
            <div class="brand">
                <div class="brand-mark"><span>N</span></div>
                <div class="brand-name">NEXO</div>
            </div>
            """
        )

        st.html(
            f"""
            <div class="side-level">
                <div class="side-level-row">
                    <div class="side-level-number">Nível {level}</div>
                    <div class="side-level-xp">{xp:,} XP</div>
                </div>
                <div class="xp-track">
                    <div class="xp-fill" style="width:{progress}%"></div>
                </div>
                <div class="side-level-hint">{xp_in_level}/{XP_POR_NIVEL}</div>
            </div>
            """.replace(",", ".")
        )

        return st.radio(
            "NAVEGAÇÃO",
            [
                "Hoje",
                "Planejar",
                "Rotina",
                "Ciclo",
                "Missões",
                "Leitura",
                "Tarefas",
                "Hábitos",
                "Atividade",
                "Progresso",
                "Conquistas",
                "Configurações",
            ],
            label_visibility="collapsed",
        )


def header(title, subtitle=None):
    subtitle_html = (
        f'<div class="page-subtitle">{subtitle}</div>'
        if subtitle
        else ""
    )

    st.html(
        f"""
        <div class="page-head">
            <div class="page-title">{title}</div>
            {subtitle_html}
        </div>
        """
    )


def section(title):
    st.html(f'<div class="section-title"><span>{title}</span></div>')
