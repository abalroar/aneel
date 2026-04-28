from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd
import requests

from .brazil import states_records


CKAN_BASE_URL = "https://dadosabertos.aneel.gov.br/api/3/action"

OCCURRENCE_RESOURCES: dict[int, str] = {
    2017: "845b550c-e454-4cac-a8e7-ab7f1732fa6d",
    2018: "5a7f1a13-2ec1-406c-b542-3bcba96c8a9e",
    2019: "770611ff-cec4-4b18-82e0-b06375a462f0",
    2020: "f41804fe-b3c3-4f39-b777-c48c602affb1",
    2021: "ca188f2f-2384-4690-af3a-048f44575c74",
    2022: "4ecf2f60-65de-4874-b293-330927720ccf",
    2023: "4796181d-5156-4ce5-8729-43f4e71e2d45",
    2024: "d6024771-f068-414a-8476-656e5fb83aea",
    2025: "04e2d968-76a5-4433-91c2-c1d5d43147c0",
    2026: "040c840a-b9fa-4c63-bd3c-f1a99640366b",
}

INTERRUPTION_RESOURCES: dict[int, str] = {
    2025: "1aa6ad85-05b8-4471-9ca4-316566214ba9",
    2026: "33a21bd6-4893-42fc-bc05-888154f7511e",
}


@dataclass(frozen=True)
class CkanError(RuntimeError):
    message: str
    sql: str | None = None

    def __str__(self) -> str:
        if self.sql:
            return f"{self.message}\nSQL: {self.sql}"
        return self.message


def execute_sql(sql: str, timeout: int = 90) -> list[dict]:
    response = requests.get(
        f"{CKAN_BASE_URL}/datastore_search_sql",
        params={"sql": sql},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success"):
        raise CkanError(str(payload.get("error") or "Consulta CKAN sem sucesso"), sql)
    return payload["result"].get("records", [])


def _resource_for_year(resources: dict[int, str], year: int) -> str:
    try:
        return resources[year]
    except KeyError as exc:
        years = ", ".join(str(value) for value in sorted(resources))
        raise ValueError(f"Ano indisponivel: {year}. Anos suportados: {years}") from exc


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _uf_filter(ufs: Iterable[str] | None) -> str:
    selected = [uf.strip().upper() for uf in (ufs or []) if uf.strip()]
    if not selected:
        return ""
    states = pd.DataFrame(states_records())
    prefixes = states.loc[states["uf"].isin(selected), "uf_code"].tolist()
    if not prefixes:
        return ""
    values = ", ".join(_sql_literal(prefix) for prefix in prefixes)
    return f' AND substring("CodIBGE" from 1 for 2) IN ({values})'


def occurrence_regional_summary(year: int, ufs: Iterable[str] | None = None) -> pd.DataFrame:
    resource_id = _resource_for_year(OCCURRENCE_RESOURCES, year)
    sql = f"""
        SELECT
            {year} AS ano,
            substring("CodIBGE" from 1 for 2) AS uf_code,
            split_part(REPLACE("DscOcorrenciaAberta", ',', ';'), ';', 1) AS origem,
            split_part(REPLACE("DscOcorrenciaAberta", ',', ';'), ';', 2) AS programacao,
            split_part(REPLACE("DscOcorrenciaAberta", ',', ';'), ';', 3) AS grupo_causa,
            COUNT(*)::int AS ocorrencias,
            COUNT(DISTINCT "NomAgente")::int AS distribuidoras,
            COUNT(DISTINCT "CodIBGE")::int AS municipios,
            AVG(CASE WHEN "MdaPreparo" <> ''
                THEN REPLACE("MdaPreparo", ',', '.')::numeric END) AS preparo_medio_min,
            AVG(CASE WHEN "MdaDeslocamento" <> ''
                THEN REPLACE("MdaDeslocamento", ',', '.')::numeric END) AS deslocamento_medio_min,
            AVG(CASE WHEN "MdaExecucao" <> ''
                THEN REPLACE("MdaExecucao", ',', '.')::numeric END) AS execucao_medio_min
        FROM "{resource_id}"
        WHERE "CodIBGE" IS NOT NULL
          AND "CodIBGE" <> ''
          {_uf_filter(ufs)}
        GROUP BY 1, 2, 3, 4, 5
        ORDER BY ocorrencias DESC
    """
    records = execute_sql(sql, timeout=120)
    return enrich_states(pd.DataFrame(records))


def occurrence_monthly_trend(year: int, ufs: Iterable[str] | None = None) -> pd.DataFrame:
    resource_id = _resource_for_year(OCCURRENCE_RESOURCES, year)
    sql = f"""
        SELECT
            {year} AS ano,
            substring("DthInicioOcorrenciaAberta" from 1 for 7) AS mes,
            COUNT(*)::int AS ocorrencias,
            COUNT(DISTINCT "CodIBGE")::int AS municipios,
            COUNT(DISTINCT "NomAgente")::int AS distribuidoras
        FROM "{resource_id}"
        WHERE "DthInicioOcorrenciaAberta" IS NOT NULL
          AND "DthInicioOcorrenciaAberta" <> ''
          AND "CodIBGE" IS NOT NULL
          AND "CodIBGE" <> ''
          {_uf_filter(ufs)}
        GROUP BY 1, 2
        ORDER BY mes
    """
    return pd.DataFrame(execute_sql(sql, timeout=90))


def occurrence_top_agents(year: int, ufs: Iterable[str] | None = None, limit: int = 20) -> pd.DataFrame:
    resource_id = _resource_for_year(OCCURRENCE_RESOURCES, year)
    sql = f"""
        SELECT
            {year} AS ano,
            "NomAgente" AS distribuidora,
            "NumCPFCNPJ" AS cnpj,
            COUNT(*)::int AS ocorrencias,
            COUNT(DISTINCT "CodIBGE")::int AS municipios,
            AVG(CASE WHEN "MdaPreparo" <> ''
                THEN REPLACE("MdaPreparo", ',', '.')::numeric END) AS preparo_medio_min,
            AVG(CASE WHEN "MdaDeslocamento" <> ''
                THEN REPLACE("MdaDeslocamento", ',', '.')::numeric END) AS deslocamento_medio_min,
            AVG(CASE WHEN "MdaExecucao" <> ''
                THEN REPLACE("MdaExecucao", ',', '.')::numeric END) AS execucao_medio_min
        FROM "{resource_id}"
        WHERE "NomAgente" IS NOT NULL
          AND "NomAgente" <> ''
          AND "CodIBGE" IS NOT NULL
          AND "CodIBGE" <> ''
          {_uf_filter(ufs)}
        GROUP BY 1, 2, 3
        ORDER BY ocorrencias DESC
        LIMIT {int(limit)}
    """
    df = pd.DataFrame(execute_sql(sql, timeout=90))
    return add_total_time(df)


def interruption_cause_summary(year: int, limit: int = 30) -> pd.DataFrame:
    resource_id = _resource_for_year(INTERRUPTION_RESOURCES, year)
    sql = f"""
        SELECT
            {year} AS ano,
            "DscFatoGeradorInterrupcao" AS causa,
            "DscTipoInterrupcao" AS tipo,
            COUNT(*)::int AS interrupcoes,
            COUNT(DISTINCT "SigAgente")::int AS distribuidoras
        FROM "{resource_id}"
        WHERE "DscFatoGeradorInterrupcao" IS NOT NULL
          AND "DscFatoGeradorInterrupcao" <> ''
        GROUP BY 1, 2, 3
        ORDER BY interrupcoes DESC
        LIMIT {int(limit)}
    """
    return pd.DataFrame(execute_sql(sql, timeout=90))


def enrich_states(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    states = pd.DataFrame(states_records())
    result = df.copy()
    result["uf_code"] = result["uf_code"].astype(str).str.zfill(2)
    return result.merge(states, how="left", on="uf_code")


def add_total_time(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    result = df.copy()
    for column in ("preparo_medio_min", "deslocamento_medio_min", "execucao_medio_min"):
        result[column] = pd.to_numeric(result[column], errors="coerce")
    result["tempo_total_medio_min"] = result[
        ["preparo_medio_min", "deslocamento_medio_min", "execucao_medio_min"]
    ].sum(axis=1, min_count=1)
    return result


def combine_years(frames: Iterable[pd.DataFrame]) -> pd.DataFrame:
    non_empty = [frame for frame in frames if not frame.empty]
    if not non_empty:
        return pd.DataFrame()
    return pd.concat(non_empty, ignore_index=True)
