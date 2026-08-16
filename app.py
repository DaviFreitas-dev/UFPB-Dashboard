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


st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="st-"] {
        font-family: "Inter", sans-serif;
    }

    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at 85% 0%, rgba(56,189,248,.08), transparent 28%),
            radial-gradient(circle at 0% 20%, rgba(96,165,250,.07), transparent 25%),
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
            linear-gradient(135deg, rgba(19,42,70,.98), rgba(8,24,42,.98));
        border: 1px solid rgba(110,168,255,.14);
        border-radius: 24px;
        padding: 28px 30px;
        margin-bottom: 18px;
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
        margin-top: 9px;
        font-size: .98rem;
    }

    .level-badge {
        background: rgba(56,189,248,.08);
        border: 1px solid rgba(56,189,248,.22);
        border-radius: 18px;
        padding: 18px 20px;
        text-align: right;
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
        font-size: 2rem;
        font-weight: 800;
        margin: 2px 0;
    }

    .level-xp {
        color: #38bdf8;
        font-size: .85rem;
        font-weight: 700;
    }

    .stat-card {
        background: linear-gradient(
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
        font-size: 1.2rem;
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

    .mission {
        background:
            linear-gradient(
                135deg,
                rgba(14,38,62,.98),
                rgba(9,25,43,.98)
            );
        border: 1px solid rgba(56,189,248,.16);
        border-radius: 20px;
        padding: 18px;
        margin-bottom: 12px;
    }

    .mission-title {
        color: #f4f7fb;
        font-size: 1.04rem;
        font-weight: 800;
    }

    .mission-meta {
        color: #91a4bc;
        font-size: .84rem;
        margin-top: 4px;
    }

    .mission-xp {
        color: #34d399;
        font-weight: 800;
        text-align: right;
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
    }

    .empty-state {
        background: rgba(10,24,41,.7);
        border: 1px dashed rgba(110,168,255,.2);
        border-radius: 18px;
        padding: 24px;
        text-align: center;
        color: #91a4bc;
    }

    .section-title {
        color: #f4f7fb;
        font-size: 1.05rem;
        font-weight: 800;
        margin: 8px 0 10px;
    }

    .footer {
        color: #66809c;
        text-align: center;
        font-size: .75rem;
        padding: 18px 0 4px;
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
            padding: 20px;
            border-radius: 20px;
        }

        .level-badge {
            text-align: left;
            margin-top: 12px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def conectar_planilha():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    creds_dict = dict(st.secrets["gsheets"])

    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=scopes,
    )

    cliente = gspread.authorize(creds)

    return cliente.open("Banco_UFPB").sheet1


planilha = conectar_planilha()


def salvar_dados(dados):
    texto_json = json.dumps(
        dados,
        ensure_ascii=False,
    )

    planilha.update_acell(
        "A1",
        texto_json,
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
    if not isinstance(dados, dict):
        return criar_padrao()

    dados.setdefault("xp", 0)
    dados.setdefault("historico_dias", {})
    dados.setdefault("config_base", CICLO_PADRAO)

    dados.setdefault(
        "ciclo_atual",
        {
            mat: info["horas"]
            for mat, info in dados["config_base"].items()
        },
    )

    config = {}

    for mat, info in dados["config_base"].items():
        try:
            horas = max(
                0,
                int(info.get("horas", 0)),
            )
        except (TypeError, ValueError):
            horas = 0

        ambiente = info.get(
            "ambiente",
            "Ambos",
        )

        if ambiente not in AMBIENTES:
            ambiente = "Ambos"

        config[str(mat)] = {
            "horas": horas,
            "ambiente": ambiente,
        }

    dados["config_base"] = config

    ciclo = {}

    for mat, info in config.items():
        try:
            restante = int(
                dados["ciclo_atual"].get(
                    mat,
                    info["horas"],
                )
            )
        except (TypeError, ValueError):
            restante = info["horas"]

        ciclo[mat] = max(
            0,
            min(restante, info["horas"]),
        )

    dados["ciclo_atual"] = ciclo

    try:
        dados["xp"] = max(
            0,
            int(dados["xp"]),
        )
    except (TypeError, ValueError):
        dados["xp"] = 0

    historico = {}

    for dia, horas in dados.get(
        "historico_dias",
        {},
    ).items():

        try:
            historico[str(dia)] = max(
                0,
                int(horas),
            )
        except (TypeError, ValueError):
            continue

    dados["historico_dias"] = historico

    return dados


def inicializar_dados():
    try:
        valor = planilha.acell("A1").value

        if valor:
            return normalizar_dados(
                json.loads(valor)
            )

    except Exception:
        pass

    padrao = criar_padrao()

    salvar_dados(padrao)

    return padrao


def calcular_nivel(xp):
    nivel = (
        xp // XP_POR_NIVEL
    ) + 1

    xp_no_nivel = (
        xp % XP_POR_NIVEL
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
        faltam,
    )


def calcular_estatisticas(dados):
    historico = dados.get(
        "historico_dias",
        {},
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
            TypeError,
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


def gerar_missoes(
    dados,
    horas_solicitadas,
    filtro,
):
    limite = horas_solicitadas
    rotina = {}

    while limite > 0:

        urna = []

        for (
            mat,
            restante,
        ) in dados[
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

        if not urna:
            break

        sorteada = random.choice(
            urna
        )

        max_h = min(
            limite,
            dados[
                "ciclo_atual"
            ][sorteada],
        )

        horas = random.randint(
            1,
            max_h,
        )

        rotina[sorteada] = (
            rotina.get(
                sorteada,
                0,
            )
            + horas
        )

        dados[
            "ciclo_atual"
        ][sorteada] -= horas

        limite -= horas

    return rotina


def registrar_estudo(
    dados,
    rotina,
):
    horas_totais = sum(
        rotina.values()
    )

    if horas_totais <= 0:
        return 0

    dados["xp"] += (
        horas_totais
        * XP_POR_HORA
    )

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
            0,
        )
        + horas_totais
    )

    salvar_dados(
        dados
    )

    return horas_totais


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
    0,
)

progresso_ciclo = (
    concluido_ciclo
    / total_ciclo
    if total_ciclo
    else 0
)


col1, col2 = st.columns(
    [2.5, 1],
    vertical_alignment="center",
)

with col1:
    st.markdown(
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
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
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
        """.replace(",", "."),
        unsafe_allow_html=True,
    )


st.progress(
    progresso,
    text=(
        f"{xp_no_nivel}/{XP_POR_NIVEL} XP • "
        f"{xp_faltante} XP para o próximo nível"
    ),
)


stats_cols = st.columns(4)


with stats_cols[0]:
    st.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-icon">⚡</div>
            <div class="stat-label">XP total</div>
            <div class="stat-value">
                {dados['xp']:,}
            </div>
            <div class="stat-note">
                +{XP_POR_HORA} XP por hora
            </div>
        </div>
        """.replace(",", "."),
        unsafe_allow_html=True,
    )


with stats_cols[1]:
    st.markdown(
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
        """,
        unsafe_allow_html=True,
    )


with stats_cols[2]:
    st.markdown(
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
        """,
        unsafe_allow_html=True,
    )


with stats_cols[3]:
    st.markdown(
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
        """,
        unsafe_allow_html=True,
    )


st.write("")


tab_dashboard, tab_historico, tab_edital = st.tabs(
    [
        "🎯 Missões",
        "📈 Histórico",
        "⚙️ Edital",
    ]
)


with tab_dashboard:

    left, right = st.columns(
        [1.15, 1],
        gap="large",
    )

    with left:

        st.markdown(
            '<div class="section-title">🎯 Gerar próxima missão</div>',
            unsafe_allow_html=True,
        )

        with st.container(border=True):

            modo = st.radio(
                "Ambiente",
                [
                    "🔄 Qualquer ambiente",
                    "🚌 Transporte",
                    "🖥️ Mesa",
                ],
                horizontal=True,
                label_visibility="collapsed",
            )

            horas = st.slider(
                "Horas para esta rodada",
                min_value=1,
                max_value=6,
                value=3,
            )

            gerar = st.button(
                "🚀 SORTEAR MISSÕES",
                type="primary",
                use_container_width=True,
            )

        if gerar:

            filtro = "Ambos"

            if "Transporte" in modo:
                filtro = "Transporte"

            elif "Mesa" in modo:
                filtro = "Mesa"

            rotina = gerar_missoes(
                dados,
                horas,
                filtro,
            )

            if not rotina:

                st.warning(
                    "Não encontrei horas pendentes "
                    "para esse ambiente."
                )

            else:

                horas_totais = registrar_estudo(
                    dados,
                    rotina,
                )

                st.session_state[
                    "ultima_rotina"
                ] = rotina

                st.session_state[
                    "ultimo_xp"
                ] = (
                    horas_totais
                    * XP_POR_HORA
                )

                st.rerun()

        if st.session_state.get(
            "ultima_rotina"
        ):

            st.markdown(
                '<div class="section-title">🔥 Suas missões</div>',
                unsafe_allow_html=True,
            )

            rotina = st.session_state[
                "ultima_rotina"
            ]

            for (
                mat,
                horas_missao,
            ) in rotina.items():

                ambiente = dados[
                    "config_base"
                ][mat]["ambiente"]

                xp = (
                    horas_missao
                    * XP_POR_HORA
                )

                st.markdown(
                    f"""
                    <div class="mission">
                        <div style="
                            display:flex;
                            justify-content:space-between;
                            gap:12px;
                        ">
                            <div>
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
                            </div>

                            <div class="mission-xp">
                                +{xp} XP
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            if st.button(
                "🧹 Limpar missões",
            ):
                st.session_state.pop(
                    "ultima_rotina",
                    None,
                )

                st.session_state.pop(
                    "ultimo_xp",
                    None,
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
                    90,
                ],
                value=50,
            )

            iniciar = st.button(
                "▶️ Iniciar foco",
                use_container_width=True,
            )

            if iniciar:

                cronometro = st.empty()

                for segundos in range(
                    minutos * 60,
                    0,
                    -1,
                ):

                    mm, ss = divmod(
                        segundos,
                        60,
                    )

                    cronometro.metric(
                        "Tempo restante",
                        f"{mm:02d}:{ss:02d}",
                    )

                    time.sleep(1)

                cronometro.success(
                    "Sessão concluída. "
                    "Faça uma pausa."
                )

                st.balloons()


    with right:

        st.markdown(
            '<div class="section-title">📊 Progresso do ciclo</div>',
            unsafe_allow_html=True,
        )

        with st.container(border=True):

            st.markdown(
                f"""
                <div class="cycle-big">
                    {progresso_ciclo:.0%}
                </div>

                <div class="cycle-copy">
                    {concluido_ciclo}h concluídas de
                    {total_ciclo}h •
                    {restante_ciclo}h restantes
                </div>
                """,
                unsafe_allow_html=True,
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
                    ),
                }
            )

            st.dataframe(
                df_ciclo,
                hide_index=True,
                use_container_width=True,
            )

            if restante_ciclo == 0:

                st.success(
                    "🏆 Ciclo 100% concluído!"
                )

                if st.button(
                    "🔄 Começar novo ciclo",
                    use_container_width=True,
                ):

                    dados[
                        "ciclo_atual"
                    ] = {
                        mat: info[
                            "horas"
                        ]

                        for (
                            mat,
                            info,
                        ) in dados[
                            "config_base"
                        ].items()
                    }

                    salvar_dados(
                        dados
                    )

                    st.rerun()


with tab_historico:

    st.markdown(
        '<div class="section-title">📈 Seu histórico de batalha</div>',
        unsafe_allow_html=True,
    )

    h1, h2, h3, h4 = st.columns(4)

    with h1:
        st.metric(
            "Horas totais",
            f"{stats['total_horas']}h",
        )

    with h2:
        st.metric(
            "Média diária",
            f"{stats['media']:.1f}h",
        )

    with h3:
        st.metric(
            "Melhor dia",
            f"{stats['melhor_dia']}h",
        )

    with h4:
        st.metric(
            "Dias estudados",
            stats["dias_estudados"],
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
                "Horas",
            ],
        )

        df_hist[
            "Data"
        ] = pd.to_datetime(
            df_hist["Data"]
        )

        df_hist = (
            df_hist
            .sort_values("Data")
            .set_index("Data")
        )

        st.bar_chart(
            df_hist,
            y="Horas",
        )

        with st.expander(
            "Ver registros"
        ):

            st.dataframe(
                df_hist.sort_index(
                    ascending=False
                ),
                use_container_width=True,
            )

    else:

        st.markdown(
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
                    Gere sua primeira missão para
                    começar a registrar progresso.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


with tab_edital:

    st.markdown(
        '<div class="section-title">⚙️ Configurar ciclo base</div>',
        unsafe_allow_html=True,
    )

    df_config = (
        pd.DataFrame.from_dict(
            dados[
                "config_base"
            ],
            orient="index",
        )
        .reset_index()
    )

    df_config.rename(
        columns={
            "index": "Disciplina"
        },
        inplace=True,
    )

    df_editado = st.data_editor(
        df_config,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "Disciplina": st.column_config.TextColumn(
                "Disciplina",
                required=True,
            ),
            "horas": st.column_config.NumberColumn(
                "Horas",
                min_value=0,
                max_value=100,
                step=1,
            ),
            "ambiente": st.column_config.SelectboxColumn(
                "Ambiente",
                options=AMBIENTES,
                required=True,
            ),
        },
    )

    if st.button(
        "💾 Salvar nova estratégia",
        type="primary",
        use_container_width=True,
    ):

        nova_config = {}

        for (
            _,
            row,
        ) in df_editado.iterrows():

            disciplina = str(
                row.get(
                    "Disciplina",
                    "",
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
                            0,
                        )
                    ),
                )

            except (
                TypeError,
                ValueError,
            ):
                horas_config = 0

            ambiente = str(
                row.get(
                    "ambiente",
                    "Ambos",
                )
            )

            if ambiente not in AMBIENTES:
                ambiente = "Ambos"

            nova_config[
                disciplina
            ] = {
                "horas": horas_config,
                "ambiente": ambiente,
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
                    info,
                ) in nova_config.items()
            }

            salvar_dados(
                dados
            )

            st.success(
                "Edital atualizado!"
            )

            st.rerun()

    st.write("")

    st.markdown(
        '<div class="section-title">🔄 Reiniciar apenas o ciclo</div>',
        unsafe_allow_html=True,
    )

    with st.container(
        border=True
    ):

        st.write(
            "Seu XP e histórico serão preservados."
        )

        if st.button(
            "🔄 Reiniciar ciclo atual",
            use_container_width=True,
        ):

            dados[
                "ciclo_atual"
            ] = {
                mat: info[
                    "horas"
                ]

                for (
                    mat,
                    info,
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

    st.markdown(
        '<div class="section-title">🗑️ Zona de perigo</div>',
        unsafe_allow_html=True,
    )

    with st.container(
        border=True
    ):

        st.warning(
            "Isso apaga XP, histórico e configurações."
        )

        if st.button(
            "🚨 Apagar tudo e voltar ao padrão",
            use_container_width=True,
        ):

            padrao = criar_padrao()

            salvar_dados(
                padrao
            )

            st.session_state.pop(
                "ultima_rotina",
                None,
            )

            st.session_state.pop(
                "ultimo_xp",
                None,
            )

            st.success(
                "Banco de dados reiniciado."
            )

            time.sleep(1)

            st.rerun()


st.markdown(
    """
    <div class="footer">
        UFPB Academy • seu ciclo, suas missões, seu progresso.
    </div>
    """,
    unsafe_allow_html=True,
)
