import streamlit as st

from modules.achievements import check
from modules.ui import header


def render():
    header(
        "Conquistas",
        "Marcos do seu progresso.",
    )

    items = check()
    cols = st.columns(2)

    for index, (code, title, description, unlocked) in enumerate(items):
        with cols[index % 2]:
            class_name = (
                "achievement"
                if unlocked
                else "achievement achievement-locked"
            )
            status = "Concluída" if unlocked else "Bloqueada"

            st.html(
                f"""
                <div class="{class_name}">
                    <div class="achievement-status">{status}</div>
                    <div class="achievement-title">
                        {title}
                    </div>
                    <div class="achievement-desc">
                        {description}
                    </div>
                </div>
                """
            )
