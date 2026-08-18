from datetime import date

from modules.database import new_id, records, replace_records


def today_records():
    return [
        row for row in records("Tarefas")
        if row["data"] == str(date.today())
    ]


def add(task, category):
    rows = records("Tarefas")
    rows.append({
        "id": new_id(),
        "data": str(date.today()),
        "tarefa": task,
        "categoria": category,
        "status": "Pendente",
    })
    replace_records(
        "Tarefas",
        [[r["id"], r["data"], r["tarefa"], r["categoria"], r["status"]] for r in rows],
    )


def toggle(item_id, done):
    rows = records("Tarefas")
    for row in rows:
        if row["id"] == item_id:
            row["status"] = "Concluída" if done else "Pendente"
    replace_records(
        "Tarefas",
        [[r["id"], r["data"], r["tarefa"], r["categoria"], r["status"]] for r in rows],
    )
