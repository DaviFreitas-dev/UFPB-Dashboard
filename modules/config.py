XP_POR_HORA = 100
XP_POR_NIVEL = 1000

AMBIENTES = ["Mesa", "Transporte", "Ambos"]

CICLO_PADRAO = {
    "📐 Matemática (Assaad)": {"horas": 5, "ambiente": "Mesa"},
    "📚 Linguagens (Fernanda Pessoa)": {"horas": 5, "ambiente": "Transporte"},
    "🖋️ Redação (Fernanda Pessoa)": {"horas": 4, "ambiente": "Ambos"},
    "⚡ Física (Guisoli)": {"horas": 3, "ambiente": "Mesa"},
    "🧪 Química (Michel Arthaud)": {"horas": 3, "ambiente": "Mesa"},
    "🧬 Biologia (Samuel Cunha)": {"horas": 3, "ambiente": "Transporte"},
    "🏛️ História (Débora Aladim)": {"horas": 2, "ambiente": "Transporte"},
    "🌐 Geografia (Thais Formagio)": {"horas": 2, "ambiente": "Transporte"},
    "🧠 Filosofia (Ferretto)": {"horas": 1, "ambiente": "Transporte"},
    "📊 Sociologia (Ferretto)": {"horas": 1, "ambiente": "Transporte"},
}

SHEETS = {
    "Usuario": ["chave", "valor"],
    "Config": ["disciplina", "horas", "ambiente"],
    "Ciclo": ["disciplina", "restantes"],
    "Historico": ["data", "horas", "xp"],
    "Rotina": ["id", "data", "hora", "atividade", "status"],
    "Tarefas": ["id", "data", "tarefa", "categoria", "status"],
    "Leitura": [
        "id",
        "titulo",
        "autor",
        "pagina_atual",
        "total_paginas",
        "meta_diaria",
        "status",
    ],
    "HabitosConfig": ["id", "nome", "ativo"],
    "Habitos": ["id", "data", "habito", "feito"],
    "Atividade": ["id", "data", "tipo", "feito"],
    "Conquistas": ["id", "nome", "descricao", "desbloqueada", "data"],
}
