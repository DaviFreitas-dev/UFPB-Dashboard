import json
import random
import time
from datetime import date, timedelta

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials


st.set_page_config(
    page_title="UFPB Academy",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)


XP_POR_HORA = 100
XP_POR_NIVEL = 1000

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

AMBIENTES = ["Mesa", "Transporte", "Ambos"]


st.html(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="st-"] {
        font-family: "Inter", sans-serif;
    }

    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(
                circle at 85% 0%,
                rgba(56,189,248,.08),
                transparent 28%
            ),
            radial-gradient(
                circle at 0% 20%,
                rgba(96,165,250,.07),
                transparent 25%
            ),
            #07111f;
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    .block-container {
        max-width: 1400px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    .hero {
        background:
            linear-gradient(
                135deg,
                rgba(19,42,70,.98),
                rgba(8,24,42,.98)
            );
        border: 1px solid rgba(110,168,255,.14);
        border-radius: 24px;
        padding: 28px 30px;
        box-shadow: 0 18px 50px rgba(0,0,0,.22);
    }

    .hero-kicker {
        color: #38bdf8;
        font-size: .76rem;
        font-weight: 800;
        letter-spacing: .14em;
        text-transform: uppercase;
        margin-bottom: 8px;
    }

    .hero-title {
        color: #f4f7fb;
        font-size: clamp(1.8rem, 4vw, 3rem);
        font-weight: 800;
        line-height: 1.05;
        margin: 0;
    }

    .hero-subtitle {
        color: #91a4bc;
        margin-top: 10px;
        font-size: .98rem;
        line-height: 1.5;
    }

    .level-badge {
        background: rgba(56,189,248,.08);
        border: 1px solid rgba(56,189,248,.22);
        border-radius: 18px;
        padding: 20px;
        text-align: center;
    }

    .level-label {
        color: #91a4bc;
        font-size: .75rem;
        text-transform: uppercase;
        letter-spacing: .12em;
        font-weight: 700;
    }

    .level-number {
        color: #f4f7fb;
        font-size: 2.8rem;
        font-weight: 800;
        line-height: 1;
        margin: 7px 0;
    }

    .level-xp {
        color: #38bdf8;
        font-size: .85rem;
        font-weight: 700;
    }

    .stat-card {
        background:
            linear-gradient(
                180deg,
                rgba(14,30,49,.97),
                rgba(10,24,41,.97)
            );
        border: 1px solid rgba(110,168,255,.14);
        border-radius: 20px;
        padding: 18px;
        min-height: 125px;
        box-shadow: 0 10px 30px rgba(0,0,0,.12);
    }

    .stat-icon {
        font-size: 1.25rem;
        margin-bottom: 8px;
    }

    .stat-label {
        color: #91a4bc;
        font-size: .76rem;
        font-weight: 700;
        letter-spacing: .05em;
        text-transform: uppercase;
    }

    .stat-value {
        color: #f4f7fb;
        font-size: 1.75rem;
        font-weight: 800;
        margin-top: 3px;
    }

    .stat-note {
        color: #b7c6d9;
        font-size: .76rem;
        margin-top: 3px;
    }

    .section-title {
        color: #f4f7fb;
        font-size: 1.05rem;
        font-weight: 800;
        margin: 8px 0 10px;
    }

    .mission {
        background:
            linear-gradient(
                135deg,
                rgba(14,38,62,.98),
                rgba(9,25,43,.98)
            );
        border: 1px solid rgba(56,189,248,.18);
        border-radius: 20px;
        padding: 22px;
        margin-bottom: 14px;
    }

    .mission-kicker {
        color: #38bdf8;
        font-size: .73rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: .12em;
        margin-bottom: 7px;
    }

    .mission-title {
        color: #f4f7fb;
        font-size: 1.25rem;
        font-weight: 800;
    }

    .mission-hours {
        color: #f4f7fb;
        font-size: 2.2rem;
        font-weight: 800;
        margin-top: 8px;
    }

    .mission-meta {
        color: #91a4bc;
        font-size: .84rem;
        margin-top: 5px;
    }

    .mission-xp {
        color: #34d399;
        font-weight: 800;
    }

    .badge {
        display: inline-block;
        border-radius: 999px;
        padding: 5px 9px;
        font-size: .72rem;
        font-weight: 800;
        background: rgba(56,189,248,.1);
        border: 1px solid rgba(56,189,248,.18);
        color: #9dddff;
    }

    .cycle-big {
        color: #f4f7fb;
        font-size: 2.3rem;
        font-weight: 800;
        line-height: 1;
        margin-bottom: 7px;
    }

    .cycle-copy {
        color: #91a4bc;
        font-size: .85rem;
        line-height: 1.5;
    }

    .empty-state {
        background: rgba(10,24,41,.7);
        border: 1px dashed rgba(110,168,255,.2);
        border-radius: 18px;
        padding: 24px;
        text-align: center;
        color: #91a4bc;
    }

    .success-card {
        background:
            linear-gradient(
                135deg,
                rgba(6,78,59,.5),
                rgba(5,46,35,.7)
            );
        border: 1px solid rgba(52,211,153,.22);
        border-radius: 20px;
        padding: 22px;
        margin: 15px 0;
    }

    .success-title {
        color: #6ee7b7;
        font-size: 1.2rem;
        font-weight: 800;
    }

    .success-xp {
        color: #f4f7fb;
        font-size: 2rem;
        font-weight: 800;
        margin-top: 5px;
    }

    .footer {
        color: #66809c;
        text-align: center;
        font-size: .75rem;
        padding: 25px 0 4px;
    }

    .stButton > button {
        border-radius: 12px;
        font-weight: 700;
    }

    @media (max-width: 900px) {
        .block-container {
            padding-top: 1rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }

        .hero {
            padding: 21px;
            border-radius: 20px;
        }

        .level-badge {
            margin-top: 12px;
        }
    }
    </style>
    """
)


@st.cache_resource
def conectar_planilha():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    creds_dict = dict(
        st.secrets["gsheets"]
    )

    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=scopes,
    )

    cliente = gspread.authorize(
        creds
    )

    return cliente.open(
        "Banco_UFPB"
    ).sheet1


planilha = conectar_planilha()


def salvar_dados(dados):
    texto_json = json.dumps(
        dados,
        ensure_ascii=False
    )

    planilha.update_acell(
        "A1",
        texto_json
    )


def criar_padrao():
    return {
        "xp": 0,
        "historico_dias": {},
        "config_base": CICLO_PADRAO,
        "ciclo_atual": {
            mat: info["horas"]
            for mat, info in CICLO_PADRAO.items()
        },
    }


def normalizar_dados(dados):
    if not isinstance(
        dados,
        dict
    ):
        return criar_padrao()

    dados.setdefault(
        "xp",
        0
    )

    dados.setdefault(
        "historico_dias",
        {}
    )

    dados.setdefault(
        "config_base",
        CICLO_PADRAO
    )

    dados.setdefault(
        "ciclo_atual",
        {
            mat: info["horas"]
            for mat, info in dados[
                "config_base"
            ].items()
        }
    )

    config = {}

    for mat, info in dados[
        "config_base"
    ].items():

        try:
            horas = max(
                0,
                int(
                    info.get(
                        "horas",
                        0
                    )
                )
            )

        except (
            TypeError,
            ValueError
        ):
            horas = 0

        ambiente = info.get(
            "ambiente",
            "Ambos"
        )

        if ambiente not in AMBIENTES:
            ambiente = "Ambos"

        config[
            str(mat)
        ] = {
            "horas": horas,
            "ambiente": ambiente,
        }

    dados[
        "config_base"
    ] = config

    ciclo = {}

    for mat, info in config.items():

        try:
            restante = int(
                dados[
                    "ciclo_atual"
                ].get(
                    mat,
                    info["horas"]
                )
            )

        except (
            TypeError,
            ValueError
        ):
            restante = info["horas"]

        ciclo[
            mat
        ] = max(
            0,
            min(
                restante,
                info["horas"]
            )
        )

    dados[
        "ciclo_atual"
    ] = ciclo

    try:
        dados[
            "xp"
        ] = max(
            0,
            int(
                dados["xp"]
            )
        )

    except (
        TypeError,
        ValueError
    ):
        dados[
            "xp"
        ] = 0

    historico = {}

    for dia, horas in dados.get(
        "historico_dias",
        {}
    ).items():

        try:
            historico[
                str(dia)
            ] = max(
                0,
                int(horas)
            )

        except (
            TypeError,
            ValueError
        ):
            continue

    dados[
        "historico_dias"
    ] = historico

    return dados


def inicializar_dados():
    try:
        valor = planilha.acell(
            "A1"
        ).value

        if valor:
            return normalizar_dados(
                json.loads(valor)
            )

    except Exception:
        pass

    padrao = criar_padrao()

    salvar_dados(
        padrao
    )

    return padrao


def calcular_nivel(xp):
    nivel = (
        xp
        // XP_POR_NIVEL
    ) + 1

    xp_no_nivel = (
        xp
        % XP_POR_NIVEL
    )

    progresso = (
        xp_no_nivel
        / XP_POR_NIVEL
    )

    faltam = (
        XP_POR_NIVEL
        - xp_no_nivel
    )

    return (
        nivel,
        xp_no_nivel,
        progresso,
        faltam
    )


def calcular_estatisticas(dados):
    historico = dados.get(
        "historico_dias",
        {}
    )

    if not historico:
        return {
            "total_horas": 0,
            "media": 0,
            "melhor_dia": 0,
            "sequencia": 0,
            "dias_estudados": 0,
        }

    horas_por_dia = {}

    for dia, horas in historico.items():

        try:
            horas_por_dia[
                date.fromisoformat(dia)
            ] = int(horas)

        except (
            ValueError,
            TypeError
        ):
            continue

    if not horas_por_dia:
        return {
            "total_horas": 0,
            "media": 0,
            "melhor_dia": 0,
            "sequencia": 0,
            "dias_estudados": 0,
        }

    total = sum(
        horas_por_dia.values()
    )

    media = (
        total
        / len(horas_por_dia)
    )

    melhor = max(
        horas_por_dia.values()
    )

    hoje = date.today()

    sequencia = 0

    cursor = hoje

    if cursor not in horas_por_dia:
        cursor -= timedelta(
            days=1
        )

    while (
        cursor in horas_por_dia
        and horas_por_dia[cursor] > 0
    ):
        sequencia += 1

        cursor -= timedelta(
            days=1
        )

    return {
        "total_horas": total,
        "media": media,
        "melhor_dia": melhor,
        "sequencia": sequencia,
        "dias_estudados": len(
            horas_por_dia
        ),
    }


def sortear_missoes(
    dados,
    horas_solicitadas,
    filtro
):
    limite = horas_solicitadas
    rotina = {}

    urna = []

    for mat, restante in dados[
        "ciclo_atual"
    ].items():

        if restante <= 0:
            continue

        ambiente = dados[
            "config_base"
        ][mat]["ambiente"]

        if (
            filtro == "Ambos"
            or ambiente == "Ambos"
            or ambiente == filtro
        ):
            urna.extend(
                [mat] * restante
            )

    while (
        limite > 0
        and urna
    ):
        sorteada = random.choice(
            urna
        )

        restante = dados[
            "ciclo_atual"
        ][sorteada]

        max_h = min(
            limite,
            restante
        )

        horas = random.randint(
            1,
            max_h
        )

        rotina[
            sorteada
        ] = (
            rotina.get(
                sorteada,
                0
            )
            + horas
        )

        limite -= horas

        urna = []

        for mat, restante in dados[
            "ciclo_atual"
        ].items():

            if restante <= 0:
                continue

            ambiente = dados[
                "config_base"
            ][mat]["ambiente"]

            ja_sorteada = (
                rotina.get(
                    mat,
                    0
                )
            )

            disponivel = (
                restante
                - ja_sorteada
            )

            if disponivel <= 0:
                continue

            if (
                filtro == "Ambos"
                or ambiente == "Ambos"
                or ambiente == filtro
            ):
                urna.extend(
                    [mat] * disponivel
                )

    return rotina


def concluir_missao(
    dados,
    rotina
):
    horas_totais = sum(
        rotina.values()
    )

    for mat, horas in rotina.items():
        dados[
            "ciclo_atual"
        ][mat] = max(
            0,
            dados[
                "ciclo_atual"
            ][mat]
            - horas
        )

    ganho_xp = (
        horas_totais
        * XP_POR_HORA
    )

    dados[
        "xp"
    ] += ganho_xp

    hoje = str(
        date.today()
    )

    dados[
        "historico_dias"
    ][hoje] = (
        dados[
            "historico_dias"
        ].get(
            hoje,
            0
        )
        + horas_totais
    )

    salvar_dados(
        dados
    )

    return (
        horas_totais,
        ganho_xp
    )


dados = inicializar_dados()

nivel, xp_no_nivel, progresso, xp_faltante = calcular_nivel(
    dados["xp"]
)

stats = calcular_estatisticas(
    dados
)

total_ciclo = sum(
    info["horas"]
    for info in dados[
        "config_base"
    ].values()
)

restante_ciclo = sum(
    dados[
        "ciclo_atual"
    ].values()
)

concluido_ciclo = max(
    total_ciclo
    - restante_ciclo,
    0
)

progresso_ciclo = (
    concluido_ciclo
    / total_ciclo
    if total_ciclo
    else 0
)


col1, col2 = st.columns(
    [2.5, 1],
    vertical_alignment="center"
)

with col1:
    st.html(
        """
        <div class="hero">
            <div class="hero-kicker">
                UFPB ACADEMY • STUDY COMMAND CENTER
            </div>

            <div class="hero-title">
                Transforme horas de estudo em progresso.
            </div>

            <div class="hero-subtitle">
                Sorteie suas missões, acompanhe seu ciclo
                e mantenha sua sequência.
            </div>
        </div>
        """
    )

with col2:
    st.html(
        f"""
        <div class="level-badge">
            <div class="level-label">
                Nível atual
            </div>

            <div class="level-number">
                {nivel}
            </div>

            <div class="level-xp">
                {dados['xp']:,} XP
            </div>
        </div>
        """.replace(",", ".")
    )


st.progress(
    progresso,
    text=(
        f"{xp_no_nivel}/{XP_POR_NIVEL} XP • "
        f"{xp_faltante} XP para o próximo nível"
    )
)


stats_cols = st.columns(4)


with stats_cols[0]:
    st.html(
        f"""
        <div class="stat-card">
            <div class="stat-icon">⚡</div>
            <div class="stat-label">
                XP total
            </div>
            <div class="stat-value">
                {dados['xp']:,}
            </div>
            <div class="stat-note">
                +{XP_POR_HORA} XP por hora
            </div>
        </div>
        """.replace(",", ".")
    )


with stats_cols[1]:
    st.html(
        f"""
        <div class="stat-card">
            <div class="stat-icon">📚</div>
            <div class="stat-label">
                Horas estudadas
            </div>
            <div class="stat-value">
                {stats['total_horas']}h
            </div>
            <div class="stat-note">
                Média de {stats['media']:.1f}h/dia
            </div>
        </div>
        """
    )


with stats_cols[2]:
    st.html(
        f"""
        <div class="stat-card">
            <div class="stat-icon">🔥</div>
            <div class="stat-label">
                Sequência
            </div>
            <div class="stat-value">
                {stats['sequencia']} dias
            </div>
            <div class="stat-note">
                {stats['dias_estudados']} dias registrados
            </div>
        </div>
        """
    )


with stats_cols[3]:
    st.html(
        f"""
        <div class="stat-card">
            <div class="stat-icon">🎯</div>
            <div class="stat-label">
                Ciclo atual
            </div>
            <div class="stat-value">
                {progresso_ciclo:.0%}
            </div>
            <div class="stat-note">
                {restante_ciclo}h restantes
            </div>
        </div>
        """
    )


st.write("")


tab_dashboard, tab_historico, tab_edital = st.tabs(
    [
        "🎯 Missões",
        "📈 Histórico",
        "⚙️ Edital"
    ]
)


with tab_dashboard:

    if "missao_pendente" not in st.session_state:
        st.session_state["missao_pendente"] = None

    left, right = st.columns(
        [1.15, 1],
        gap="large"
    )

    with left:

        st.html(
            """
            <div class="section-title">
                🎯 Gerar próxima missão
            </div>
            """
        )

        if st.session_state[
            "missao_pendente"
        ]:

            rotina = st.session_state[
                "missao_pendente"
            ]

            total_horas_missao = sum(
                rotina.values()
            )

            st.html(
                f"""
                <div class="mission">
                    <div class="mission-kicker">
                        MISSÃO ATIVA
                    </div>

                    <div class="mission-title">
                        Sua sessão de estudo está pronta.
                    </div>

                    <div class="mission-hours">
                        {total_horas_missao}h
                    </div>

                    <div class="mission-meta">
                        Conclua a missão para registrar
                        as horas e receber XP.
                    </div>
                </div>
                """
            )

            for mat, horas_missao in rotina.items():

                ambiente = dados[
                    "config_base"
                ][mat]["ambiente"]

                xp_missao = (
                    horas_missao
                    * XP_POR_HORA
                )

                st.html(
                    f"""
                    <div class="mission">
                        <div class="mission-title">
                            {mat}
                        </div>

                        <div class="mission-meta">
                            <span class="badge">
                                {ambiente}
                            </span>
                            &nbsp; • &nbsp;
                            {horas_missao}h de foco
                        </div>

                        <div style="
                            margin-top:12px;
                            color:#34d399;
                            font-weight:800;
                        ">
                            +{xp_missao} XP ao concluir
                        </div>
                    </div>
                    """
                )

            concluir = st.button(
                "✅ CONCLUIR MISSÃO",
                type="primary",
                use_container_width=True
            )

            cancelar = st.button(
                "✖️ Cancelar missão",
                use_container_width=True
            )

            if concluir:

                horas_concluidas, ganho_xp = concluir_missao(
                    dados,
                    rotina
                )

                st.session_state[
                    "missao_pendente"
                ] = None

                st.session_state[
                    "ultima_conclusao"
                ] = {
                    "horas": horas_concluidas,
                    "xp": ganho_xp
                }

                st.rerun()

            if cancelar:
                st.session_state[
                    "missao_pendente"
                ] = None

                st.rerun()

        else:

            with st.container(
                border=True
            ):

                modo = st.radio(
                    "Ambiente",
                    [
                        "🔄 Qualquer ambiente",
                        "🚌 Transporte",
                        "🖥️ Mesa"
                    ],
                    horizontal=True
                )

                horas = st.slider(
                    "Horas para esta missão",
                    min_value=1,
                    max_value=6,
                    value=3
                )

                gerar = st.button(
                    "🚀 SORTEAR MISSÃO",
                    type="primary",
                    use_container_width=True
                )

            if gerar:

                filtro = "Ambos"

                if "Transporte" in modo:
                    filtro = "Transporte"

                elif "Mesa" in modo:
                    filtro = "Mesa"

                rotina = sortear_missoes(
                    dados,
                    horas,
                    filtro
                )

                if not rotina:

                    st.warning(
                        "Não encontrei horas pendentes "
                        "para esse ambiente."
                    )

                else:

                    st.session_state[
                        "missao_pendente"
                    ] = rotina

                    st.rerun()

        if st.session_state.get(
            "ultima_conclusao"
        ):

            conclusao = st.session_state[
                "ultima_conclusao"
            ]

            st.html(
                f"""
                <div class="success-card">
                    <div class="success-title">
                        ✅ MISSÃO CONCLUÍDA!
                    </div>

                    <div class="success-xp">
                        +{conclusao['xp']} XP
                    </div>

                    <div style="
                        margin-top:6px;
                        color:#a7f3d0;
                    ">
                        {conclusao['horas']}h registradas
                        no seu histórico.
                    </div>
                </div>
                """
            )

            if st.button(
                "Fechar aviso"
            ):
                st.session_state.pop(
                    "ultima_conclusao",
                    None
                )

                st.rerun()

        with st.expander(
            "⏱️ Pomodoro"
        ):

            minutos = st.select_slider(
                "Duração",
                options=[
                    25,
                    40,
                    50,
                    60,
                    90
                ],
                value=50
            )

            iniciar = st.button(
                "▶️ Iniciar foco",
                use_container_width=True
            )

            if iniciar:

                cronometro = st.empty()

                for segundos in range(
                    minutos * 60,
                    0,
                    -1
                ):

                    mm, ss = divmod(
                        segundos,
                        60
                    )

                    cronometro.metric(
                        "Tempo restante",
                        f"{mm:02d}:{ss:02d}"
                    )

                    time.sleep(1)

                cronometro.success(
                    "Sessão concluída!"
                )

                st.balloons()

    with right:

        st.html(
            """
            <div class="section-title">
                📊 Progresso do ciclo
            </div>
            """
        )

        with st.container(
            border=True
        ):

            st.html(
                f"""
                <div class="cycle-big">
                    {progresso_ciclo:.0%}
                </div>

                <div class="cycle-copy">
                    {concluido_ciclo}h concluídas
                    de {total_ciclo}h
                    • {restante_ciclo}h restantes
                </div>
                """
            )

            st.progress(
                progresso_ciclo
            )

            df_ciclo = pd.DataFrame(
                {
                    "Disciplina": list(
                        dados[
                            "ciclo_atual"
                        ].keys()
                    ),
                    "Pendentes": list(
                        dados[
                            "ciclo_atual"
                        ].values()
                    )
                }
            )

            st.dataframe(
                df_ciclo,
                hide_index=True,
                use_container_width=True
            )

            if restante_ciclo == 0:

                st.success(
                    "🏆 Ciclo 100% concluído!"
                )

                if st.button(
                    "🔄 Começar novo ciclo",
                    use_container_width=True
                ):

                    dados[
                        "ciclo_atual"
                    ] = {
                        mat: info[
                            "horas"
                        ]

                        for (
                            mat,
                            info
                        ) in dados[
                            "config_base"
                        ].items()
                    }

                    salvar_dados(
                        dados
                    )

                    st.rerun()


with tab_historico:

    st.html(
        """
        <div class="section-title">
            📈 Seu histórico de batalha
        </div>
        """
    )

    h1, h2, h3, h4 = st.columns(4)

    with h1:
        st.metric(
            "Horas totais",
            f"{stats['total_horas']}h"
        )

    with h2:
        st.metric(
            "Média diária",
            f"{stats['media']:.1f}h"
        )

    with h3:
        st.metric(
            "Melhor dia",
            f"{stats['melhor_dia']}h"
        )

    with h4:
        st.metric(
            "Dias estudados",
            stats["dias_estudados"]
        )

    if dados[
        "historico_dias"
    ]:

        df_hist = pd.DataFrame(
            list(
                dados[
                    "historico_dias"
                ].items()
            ),
            columns=[
                "Data",
                "Horas"
            ]
        )

        df_hist[
            "Data"
        ] = pd.to_datetime(
            df_hist["Data"]
        )

        df_hist = (
            df_hist
            .sort_values(
                "Data"
            )
            .set_index(
                "Data"
            )
        )

        st.bar_chart(
            df_hist,
            y="Horas"
        )

        with st.expander(
            "Ver registros"
        ):

            st.dataframe(
                df_hist.sort_index(
                    ascending=False
                ),
                use_container_width=True
            )

    else:

        st.html(
            """
            <div class="empty-state">
                <div style="font-size:2rem;">
                    📚
                </div>

                <div style="
                    margin-top:8px;
                    font-weight:800;
                    color:#dbe7f5;
                ">
                    Seu histórico ainda está vazio.
                </div>

                <div style="margin-top:5px;">
                    Conclua sua primeira missão
                    para começar.
                </div>
            </div>
            """
        )


with tab_edital:

    st.html(
        """
        <div class="section-title">
            ⚙️ Configurar ciclo base
        </div>
        """
    )

    df_config = (
        pd.DataFrame.from_dict(
            dados[
                "config_base"
            ],
            orient="index"
        )
        .reset_index()
    )

    df_config.rename(
        columns={
            "index": "Disciplina"
        },
        inplace=True
    )

    df_editado = st.data_editor(
        df_config,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "Disciplina": st.column_config.TextColumn(
                "Disciplina",
                required=True
            ),
            "horas": st.column_config.NumberColumn(
                "Horas",
                min_value=0,
                max_value=100,
                step=1
            ),
            "ambiente": st.column_config.SelectboxColumn(
                "Ambiente",
                options=AMBIENTES,
                required=True
            )
        }
    )

    if st.button(
        "💾 Salvar nova estratégia",
        type="primary",
        use_container_width=True
    ):

        nova_config = {}

        for _, row in df_editado.iterrows():

            disciplina = str(
                row.get(
                    "Disciplina",
                    ""
                )
            ).strip()

            if (
                not disciplina
                or disciplina == "nan"
            ):
                continue

            try:
                horas_config = max(
                    0,
                    int(
                        row.get(
                            "horas",
                            0
                        )
                    )
                )

            except (
                TypeError,
                ValueError
            ):
                horas_config = 0

            ambiente = str(
                row.get(
                    "ambiente",
                    "Ambos"
                )
            )

            if ambiente not in AMBIENTES:
                ambiente = "Ambos"

            nova_config[
                disciplina
            ] = {
                "horas": horas_config,
                "ambiente": ambiente
            }

        if not nova_config:

            st.error(
                "Adicione pelo menos uma disciplina."
            )

        else:

            dados[
                "config_base"
            ] = nova_config

            dados[
                "ciclo_atual"
            ] = {
                mat: info[
                    "horas"
                ]

                for (
                    mat,
                    info
                ) in nova_config.items()
            }

            salvar_dados(
                dados
            )

            st.success(
                "Edital atualizado e ciclo reiniciado!"
            )

            st.rerun()

    st.write("")

    st.html(
        """
        <div class="section-title">
            🔄 Reiniciar apenas o ciclo
        </div>
        """
    )

    with st.container(
        border=True
    ):

        st.write(
            "Seu XP e histórico serão preservados."
        )

        if st.button(
            "🔄 Reiniciar ciclo atual",
            use_container_width=True
        ):

            dados[
                "ciclo_atual"
            ] = {
                mat: info[
                    "horas"
                ]

                for (
                    mat,
                    info
                ) in dados[
                    "config_base"
                ].items()
            }

            salvar_dados(
                dados
            )

            st.success(
                "Ciclo reiniciado."
            )

            st.rerun()

    st.write("")

    st.html(
        """
        <div class="section-title">
            🗑️ Zona de perigo
        </div>
        """
    )

    with st.container(
        border=True
    ):

        st.warning(
            "Isso apaga XP, histórico e configurações."
        )

        if st.button(
            "🚨 Apagar tudo e voltar ao padrão",
            use_container_width=True
        ):

            padrao = criar_padrao()

            salvar_dados(
                padrao
            )

            st.session_state.pop(
                "missao_pendente",
                None
            )

            st.session_state.pop(
                "ultima_conclusao",
                None
            )

            st.success(
                "Banco de dados reiniciado."
            )

            time.sleep(1)

            st.rerun()


st.html(
    """
    <div class="footer">
        UFPB Academy • seu ciclo, suas missões, seu progresso.
    </div>
    """
)
