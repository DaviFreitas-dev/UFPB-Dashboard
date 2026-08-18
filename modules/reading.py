from modules.database import new_id, records, replace_records


def all_books():
    return records("Leitura")


def add(title, author, total_pages, daily_goal):
    rows = records("Leitura")
    rows.append({
        "id": new_id(),
        "titulo": title,
        "autor": author,
        "pagina_atual": 0,
        "total_paginas": total_pages,
        "meta_diaria": daily_goal,
        "status": "Lendo",
    })
    replace_records(
        "Leitura",
        [
            [
                r["id"],
                r["titulo"],
                r["autor"],
                r["pagina_atual"],
                r["total_paginas"],
                r["meta_diaria"],
                r["status"],
            ]
            for r in rows
        ],
    )


def update(book_id, page, status=None):
    rows = records("Leitura")

    for row in rows:
        if row["id"] == book_id:
            row["pagina_atual"] = int(page)
            if status:
                row["status"] = status

    replace_records(
        "Leitura",
        [
            [
                r["id"],
                r["titulo"],
                r["autor"],
                r["pagina_atual"],
                r["total_paginas"],
                r["meta_diaria"],
                r["status"],
            ]
            for r in rows
        ],
    )
