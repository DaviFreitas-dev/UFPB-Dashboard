import streamlit as st

from modules.reading import add, all_books, remaining_today, remove, update
from modules.ui import header, section


def render():
    header(
        "Leitura",
        "Acompanhe livros, páginas e metas diárias sem misturar com o ciclo de estudos.",
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

        if st.button(
            "📚 Adicionar livro",
            type="primary",
            use_container_width=True,
        ):
            if title.strip():
                add(title.strip(), author.strip(), int(total), int(goal))
                st.success("Livro adicionado!")
                st.rerun()
            else:
                st.warning("Digite o título do livro.")

    section("📚 Minha biblioteca")
    books = all_books()

    if not books:
        st.info("Sua biblioteca está vazia.")
        return

    for book in books:
        current = int(book["pagina_atual"])
        total = max(1, int(book["total_paginas"]))
        progress = min(current / total, 1.0)
        daily_remaining = remaining_today(book)
        status = book.get("status", "Lendo")

        with st.container(border=True):
            title_col, status_col = st.columns([4, 1])
            with title_col:
                st.subheader(f"📖 {book['titulo']}")
                st.caption(book["autor"] or "Autor não informado")
            with status_col:
                st.caption(status)

            st.progress(progress, text=f"{current}/{total} páginas")

            if status == "Lendo":
                st.info(
                    f"Meta de hoje: até {daily_remaining} página(s) restantes "
                    f"da sua meta diária de {book['meta_diaria']}."
                )

            page = st.number_input(
                "Página atual",
                min_value=0,
                max_value=total,
                value=min(current, total),
                key=f"page_{book['id']}",
            )

            save_col, status_button_col, delete_col = st.columns([5, 3, 1])

            with save_col:
                if st.button(
                    "💾 Atualizar leitura",
                    key=f"book_{book['id']}",
                    use_container_width=True,
                ):
                    new_status = "Concluído" if page >= total else status
                    update(book["id"], page, new_status)
                    st.success("Leitura atualizada!")
                    st.rerun()

            with status_button_col:
                if status == "Concluído":
                    if st.button(
                        "↩️ Voltar a ler",
                        key=f"reopen_{book['id']}",
                        use_container_width=True,
                    ):
                        update(book["id"], page, "Lendo")
                        st.rerun()
                elif st.button(
                    "✅ Concluir",
                    key=f"finish_{book['id']}",
                    use_container_width=True,
                ):
                    update(book["id"], total, "Concluído")
                    st.rerun()

            with delete_col:
                if st.button(
                    "🗑️",
                    key=f"delete_book_{book['id']}",
                    help="Excluir livro",
                ):
                    remove(book["id"])
                    st.rerun()
