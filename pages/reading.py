import streamlit as st

from modules.reading import add, all_books, update
from modules.ui import header, section


def render():
    header(
        "Leitura",
        "Acompanhe livros, páginas e metas sem misturar isso com o ciclo.",
    )

    with st.container(border=True):
        section("➕ Adicionar livro")

        title = st.text_input("Título")
        author = st.text_input("Autor")

        col1, col2 = st.columns(2)

        with col1:
            total = st.number_input("Total de páginas", min_value=1, value=100)

        with col2:
            goal = st.number_input("Meta diária", min_value=1, value=20)

        if st.button("📚 Adicionar livro", type="primary", use_container_width=True):
            if title.strip():
                add(title.strip(), author.strip(), int(total), int(goal))
                st.success("Livro adicionado!")
                st.rerun()

    section("📚 Minha biblioteca")
    books = all_books()

    if not books:
        st.info("Sua biblioteca está vazia.")
        return

    for book in books:
        current = int(book["pagina_atual"])
        total = int(book["total_paginas"])
        progress = current / total if total else 0

        with st.container(border=True):
            st.subheader(f"📖 {book['titulo']}")
            st.caption(book["autor"])
            st.progress(progress, text=f"{current}/{total} páginas")

            page = st.number_input(
                "Página atual",
                min_value=0,
                max_value=total,
                value=current,
                key=f"page_{book['id']}",
            )

            if st.button(
                "💾 Atualizar leitura",
                key=f"book_{book['id']}",
                use_container_width=True,
            ):
                update(
                    book["id"],
                    page,
                    "Concluído" if page >= total else None,
                )
                st.success("Leitura atualizada!")
                st.rerun()
