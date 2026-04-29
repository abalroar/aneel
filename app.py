from __future__ import annotations

from datetime import date
from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from aneel_power_watch.aneel_api import (
    OCCURRENCE_RESOURCES,
    add_total_time,
    combine_years,
    interruption_cause_summary,
    occurrence_monthly_trend,
    occurrence_regional_summary,
    occurrence_top_agents,
)
from aneel_power_watch.brazil import REGION_ORDER, STATE_BY_UF, states_records


st.set_page_config(
    page_title="Radar ANEEL de Quedas de Energia",
    page_icon=None,
    layout="wide",
)

PALETTE = ["#287C76", "#D66A47", "#E0A72F", "#6E5B9A", "#4E8AC8", "#7A8B3A"]

SOURCE_LINKS = {
    "Portal de Dados Abertos da ANEEL": "https://dadosabertos.aneel.gov.br/",
    "Ocorrências Emergenciais nas Redes de Distribuição": (
        "https://dadosabertos.aneel.gov.br/dataset/"
        "ocorrencias-emergenciais-nas-redes-de-distribuicao"
    ),
    "Interrupções de Energia Elétrica nas Redes de Distribuição": (
        "https://dadosabertos.aneel.gov.br/dataset/"
        "interrupcoes-de-energia-eletrica-nas-redes-de-distribuicao"
    ),
    "Relatórios e Indicadores de Distribuição da ANEEL": (
        "https://www.gov.br/aneel/pt-br/centrais-de-conteudos/"
        "relatorios-e-indicadores/distribuicao"
    ),
}


@st.cache_data(ttl=60 * 60, show_spinner=False)
def cached_regional_summary(year: int, ufs: tuple[str, ...]) -> pd.DataFrame:
    return occurrence_regional_summary(year, ufs)


@st.cache_data(ttl=60 * 60, show_spinner=False)
def cached_monthly_trend(year: int, ufs: tuple[str, ...]) -> pd.DataFrame:
    return occurrence_monthly_trend(year, ufs)


@st.cache_data(ttl=60 * 60, show_spinner=False)
def cached_top_agents(year: int, ufs: tuple[str, ...]) -> pd.DataFrame:
    return occurrence_top_agents(year, ufs)


@st.cache_data(ttl=60 * 60, show_spinner=False)
def cached_interruption_causes(year: int) -> pd.DataFrame:
    return interruption_cause_summary(year)


def parse_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    result = df.copy()
    for column in columns:
        if column in result.columns:
            result[column] = pd.to_numeric(result[column], errors="coerce")
    return result


def format_number(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value):,.0f}".replace(",", ".")


def format_minutes(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value):,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


def load_data(years: list[int], ufs: tuple[str, ...]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    summary_frames = []
    monthly_frames = []
    agent_frames = []
    for year in years:
        with st.spinner(f"Consultando ocorrências emergenciais de {year} na ANEEL..."):
            summary_frames.append(cached_regional_summary(year, ufs))
            monthly_frames.append(cached_monthly_trend(year, ufs))
            agent_frames.append(cached_top_agents(year, ufs))
    summary = add_total_time(combine_years(summary_frames))
    monthly = combine_years(monthly_frames)
    agents = combine_years(agent_frames)
    summary = parse_numeric(
        summary,
        [
            "ocorrencias",
            "distribuidoras",
            "municipios",
            "preparo_medio_min",
            "deslocamento_medio_min",
            "execucao_medio_min",
            "tempo_total_medio_min",
        ],
    )
    monthly = parse_numeric(monthly, ["ocorrencias", "municipios", "distribuidoras"])
    agents = parse_numeric(
        agents,
        [
            "ocorrencias",
            "municipios",
            "preparo_medio_min",
            "deslocamento_medio_min",
            "execucao_medio_min",
            "tempo_total_medio_min",
        ],
    )
    return summary, monthly, agents


def metric_row(summary: pd.DataFrame) -> None:
    total_occurrences = summary["ocorrencias"].sum()
    states = summary["uf"].dropna().nunique()
    distributors = summary.groupby("uf")["distribuidoras"].max().sum()
    cities = summary.groupby("uf")["municipios"].max().sum()
    weighted_time = (
        (summary["tempo_total_medio_min"] * summary["ocorrencias"]).sum() / total_occurrences
        if total_occurrences
        else None
    )
    non_programmed = summary.loc[
        summary["programacao"].astype(str).str.contains("NAO", case=False, na=False)
        & summary["programacao"].astype(str).str.contains("PROGRAM", case=False, na=False),
        "ocorrencias",
    ].sum()
    non_programmed_share = non_programmed / total_occurrences if total_occurrences else 0

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Ocorrências", format_number(total_occurrences))
    col2.metric("UFs", format_number(states))
    col3.metric("Municípios", format_number(cities))
    col4.metric("Distribuidoras", format_number(distributors))
    col5.metric("Não programadas", f"{non_programmed_share:.1%}".replace(".", ","))
    st.caption(f"Tempo médio estimado de atendimento: {format_minutes(weighted_time)} min")


def regional_frame(summary: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        summary.groupby(["ano", "uf_code", "uf", "state", "region", "lat", "lon"], dropna=False)
        .agg(
            ocorrencias=("ocorrencias", "sum"),
            tempo_total_medio_min=("tempo_total_medio_min", "mean"),
            distribuidoras=("distribuidoras", "max"),
            municipios=("municipios", "max"),
        )
        .reset_index()
    )
    return grouped.sort_values("ocorrencias", ascending=False)


def render_map(summary: pd.DataFrame) -> None:
    geo = regional_frame(summary)
    if geo.empty:
        st.info("Sem dados para os filtros selecionados.")
        return
    fig = px.scatter_geo(
        geo,
        lat="lat",
        lon="lon",
        size="ocorrencias",
        color="region",
        hover_name="state",
        hover_data={
            "uf": True,
            "ocorrencias": ":,",
            "municipios": ":,",
            "distribuidoras": ":,",
            "tempo_total_medio_min": ":.1f",
            "lat": False,
            "lon": False,
        },
        color_discrete_sequence=PALETTE,
        projection="natural earth",
        size_max=48,
        height=470,
    )
    fig.update_geos(
        visible=False,
        showcountries=True,
        countrycolor="#B8C4BE",
        lonaxis_range=[-76, -30],
        lataxis_range=[-35, 7],
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        legend_title_text="Região",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, width="stretch")


def render_region_charts(summary: pd.DataFrame) -> None:
    region = (
        summary.groupby("region", dropna=False)["ocorrencias"]
        .sum()
        .reindex(REGION_ORDER)
        .dropna()
        .reset_index()
    )
    causes = (
        summary.groupby("grupo_causa", dropna=False)["ocorrencias"]
        .sum()
        .sort_values(ascending=False)
        .head(12)
        .reset_index()
    )
    col1, col2 = st.columns([0.95, 1.05])
    fig_region = px.bar(
        region,
        x="region",
        y="ocorrencias",
        color="region",
        color_discrete_sequence=PALETTE,
        text_auto=".2s",
    )
    fig_region.update_layout(
        showlegend=False,
        xaxis_title="",
        yaxis_title="Ocorrências",
        margin=dict(l=0, r=10, t=20, b=0),
    )
    col1.plotly_chart(fig_region, width="stretch")

    fig_causes = px.bar(
        causes.sort_values("ocorrencias"),
        x="ocorrencias",
        y="grupo_causa",
        orientation="h",
        color="ocorrencias",
        color_continuous_scale=["#E0A72F", "#D66A47", "#7B2D26"],
        text_auto=".2s",
    )
    fig_causes.update_layout(
        coloraxis_showscale=False,
        xaxis_title="Ocorrências",
        yaxis_title="",
        margin=dict(l=0, r=10, t=20, b=0),
    )
    col2.plotly_chart(fig_causes, width="stretch")


def render_monthly(monthly: pd.DataFrame) -> None:
    if monthly.empty:
        return
    monthly = monthly.sort_values(["ano", "mes"])
    fig = px.line(
        monthly,
        x="mes",
        y="ocorrencias",
        color=monthly["ano"].astype(str),
        markers=True,
        color_discrete_sequence=PALETTE,
    )
    fig.update_layout(
        xaxis_title="Mês",
        yaxis_title="Ocorrências",
        legend_title_text="Ano",
        margin=dict(l=0, r=10, t=20, b=0),
    )
    st.plotly_chart(fig, width="stretch")


def render_agents(agents: pd.DataFrame) -> None:
    if agents.empty:
        return
    agents = agents.sort_values("ocorrencias", ascending=False).head(20)
    fig = px.bar(
        agents.sort_values("ocorrencias"),
        x="ocorrencias",
        y="distribuidora",
        orientation="h",
        color="tempo_total_medio_min",
        color_continuous_scale=["#287C76", "#E0A72F", "#D66A47"],
        hover_data=["cnpj", "municipios", "tempo_total_medio_min"],
        text_auto=".2s",
    )
    fig.update_layout(
        coloraxis_colorbar_title="Min",
        xaxis_title="Ocorrências",
        yaxis_title="",
        margin=dict(l=0, r=10, t=20, b=0),
        height=560,
    )
    st.plotly_chart(fig, width="stretch")


def render_interruption_tab() -> None:
    st.subheader("Causas técnicas nas bases de interrupções")
    year = st.selectbox("Ano da base de interrupções", sorted([2025, 2026], reverse=True))
    with st.spinner(f"Consultando interrupções de {year} na ANEEL..."):
        causes = cached_interruption_causes(year)
    if causes.empty:
        st.info("Sem dados de interrupção para o ano selecionado.")
        return
    causes = parse_numeric(causes, ["interrupcoes", "distribuidoras"])
    fig = px.treemap(
        causes,
        path=["tipo", "causa"],
        values="interrupcoes",
        color="interrupcoes",
        color_continuous_scale=["#F0D98D", "#D66A47", "#7B2D26"],
    )
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=620)
    st.plotly_chart(fig, width="stretch")
    st.dataframe(causes, hide_index=True, width="stretch")


def render_insights(summary: pd.DataFrame, agents: pd.DataFrame) -> None:
    if summary.empty:
        return
    total = summary["ocorrencias"].sum()
    by_region = summary.groupby("region")["ocorrencias"].sum().sort_values(ascending=False)
    by_state = regional_frame(summary).groupby("uf")["ocorrencias"].sum().sort_values(ascending=False)
    by_cause = summary.groupby("grupo_causa")["ocorrencias"].sum().sort_values(ascending=False)
    lead_region = by_region.index[0]
    lead_region_share = by_region.iloc[0] / total if total else 0
    lead_state = by_state.index[0]
    lead_state_share = by_state.iloc[0] / total if total else 0
    lead_cause = by_cause.index[0]
    top_agent = agents.sort_values("ocorrencias", ascending=False).iloc[0] if not agents.empty else None

    bullets = [
        f"{lead_region} concentra {lead_region_share:.1%} das ocorrências no recorte selecionado.",
        f"{lead_state} é a UF com maior volume, com {lead_state_share:.1%} do total.",
        f"O principal grupo de causa declarado é {lead_cause}.",
    ]
    if top_agent is not None:
        bullets.append(
            f"Distribuidora no topo do recorte: {top_agent['distribuidora']} "
            f"({format_number(top_agent['ocorrencias'])} ocorrências)."
        )
    st.subheader("Leitura rápida")
    for bullet in bullets:
        st.markdown(f"- {bullet}")


def render_about_tab() -> None:
    st.subheader("O que este dashboard mostra")
    st.markdown(
        """
        Este MVP acompanha problemas de fornecimento de energia nas redes de distribuição
        usando dados públicos da ANEEL. A leitura principal é regional: onde há mais
        ocorrências, quais UFs aparecem no topo, quais causas foram declaradas e quais
        distribuidoras concentram mais registros no recorte escolhido.

        O painel não mede diretamente percepção de consumidores nem substitui uma
        apuração jornalística local. Ele organiza bases regulatórias declaradas e
        publicadas pela ANEEL, úteis para achar padrões, comparar regiões e levantar
        perguntas melhores.
        """
    )

    st.subheader("O que está disponível no painel")
    st.markdown(
        """
        - **Filtros laterais:** ano, região e UF. A base de ocorrências cobre 2017 a 2026.
        - **KPIs do topo:** total de ocorrências, UFs, municípios, distribuidoras,
          percentual de registros não programados e tempo médio estimado de atendimento.
        - **Mapa regional:** bolhas por UF, coloridas por região, com volume de ocorrências.
        - **Leitura rápida:** destaques automáticos do recorte selecionado.
        - **Ranking por região:** compara o volume de ocorrências entre Norte, Nordeste,
          Centro-Oeste, Sudeste e Sul.
        - **Ranking de causas:** mostra os principais grupos de causa declarados.
        - **Tendência mensal:** evolução das ocorrências ao longo dos meses do ano.
        - **Distribuidoras:** ranking das empresas com mais ocorrências e seus tempos
          médios de preparo, deslocamento e execução.
        - **Causas técnicas:** treemap da base de interrupções por tipo e causa.
        - **Dados:** tabelas agregadas para exportar, copiar ou auditar os números.
        """
    )

    st.subheader("Como os dados são tratados")
    st.markdown(
        """
        A base principal é **Ocorrências Emergenciais nas Redes de Distribuição**. Ela
        tem município via `CodIBGE`, então o app converte o prefixo do código IBGE em
        UF e região. O campo `DscOcorrenciaAberta` é separado em origem, programação
        e grupo de causa. Os tempos médios são calculados com `MdaPreparo`,
        `MdaDeslocamento` e `MdaExecucao`, quando esses campos estão preenchidos.

        A base **Interrupções de Energia Elétrica nas Redes de Distribuição** é usada
        como complemento para causas técnicas. Ela é boa para entender tipo e fato
        gerador da interrupção, mas a versão usada no MVP não é a base principal do
        mapa regional porque não traz UF diretamente.
        """
    )

    st.subheader("Fontes oficiais")
    for label, url in SOURCE_LINKS.items():
        st.markdown(f"- [{label}]({url})")

    st.subheader("Limitações importantes")
    st.markdown(
        """
        - Os dados são declarados pelas distribuidoras e publicados pela ANEEL.
        - Alguns anos têm arquivos muito grandes; a primeira consulta pode demorar.
        - O app usa cache de uma hora para não consultar a API em toda interação.
        - A leitura por UF/região é derivada do código IBGE do município.
        - Volumes de ocorrências não devem ser lidos isoladamente como qualidade
          absoluta do serviço; população atendida, extensão da rede, clima e densidade
          regional também importam.
        """
    )


def main() -> None:
    st.title("Radar ANEEL de Quedas de Energia")
    st.caption(
        "Ocorrências emergenciais e interrupções nas redes de distribuição. "
        f"Atualizado sob demanda pela API de dados abertos da ANEEL em {date.today():%d/%m/%Y}."
    )

    all_states = pd.DataFrame(states_records())
    default_years = [max(OCCURRENCE_RESOURCES)]
    with st.sidebar:
        st.header("Filtros")
        years = st.multiselect(
            "Anos",
            options=sorted(OCCURRENCE_RESOURCES.keys(), reverse=True),
            default=default_years,
        )
        regions = st.multiselect("Regiões", options=list(REGION_ORDER), default=[])
        allowed_ufs = all_states
        if regions:
            allowed_ufs = allowed_ufs[allowed_ufs["region"].isin(regions)]
        ufs = st.multiselect("UFs", options=allowed_ufs["uf"].tolist(), default=[])
        st.divider()
        st.caption(
            "Anos completos com arquivos grandes podem levar mais tempo na primeira consulta. "
            "Depois disso, o Streamlit usa cache por uma hora."
        )

    if not years:
        st.warning("Selecione pelo menos um ano.")
        return

    selected_ufs = tuple(ufs)
    if regions and not selected_ufs:
        selected_ufs = tuple(
            state.uf for state in STATE_BY_UF.values() if state.region in set(regions)
        )

    try:
        summary, monthly, agents = load_data(years, selected_ufs)
    except Exception as exc:
        st.error("A consulta à ANEEL falhou.")
        st.exception(exc)
        return

    if summary.empty:
        st.info("A ANEEL não retornou registros para os filtros selecionados.")
        return

    metric_row(summary)

    tab_overview, tab_agents, tab_interruptions, tab_data, tab_about = st.tabs(
        ["Mapa regional", "Distribuidoras", "Causas técnicas", "Dados", "Sobre e fontes"]
    )
    with tab_overview:
        left, right = st.columns([1.25, 0.75])
        with left:
            render_map(summary)
        with right:
            render_insights(summary, agents)
        render_region_charts(summary)
        render_monthly(monthly)

    with tab_agents:
        render_agents(agents)
        st.dataframe(
            agents.sort_values("ocorrencias", ascending=False),
            hide_index=True,
            width="stretch",
        )

    with tab_interruptions:
        render_interruption_tab()

    with tab_data:
        st.subheader("Agregado regional")
        st.dataframe(
            regional_frame(summary),
            hide_index=True,
            width="stretch",
        )
        st.subheader("Agregado por causa")
        st.dataframe(
            summary.sort_values("ocorrencias", ascending=False),
            hide_index=True,
            width="stretch",
        )

    with tab_about:
        render_about_tab()


if __name__ == "__main__":
    main()
