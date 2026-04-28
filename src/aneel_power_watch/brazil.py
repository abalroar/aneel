from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StateInfo:
    ibge_prefix: str
    uf: str
    name: str
    region: str
    lat: float
    lon: float


STATES: tuple[StateInfo, ...] = (
    StateInfo("11", "RO", "Rondonia", "Norte", -10.83, -63.34),
    StateInfo("12", "AC", "Acre", "Norte", -8.77, -70.55),
    StateInfo("13", "AM", "Amazonas", "Norte", -3.47, -65.10),
    StateInfo("14", "RR", "Roraima", "Norte", 1.99, -61.33),
    StateInfo("15", "PA", "Para", "Norte", -3.79, -52.48),
    StateInfo("16", "AP", "Amapa", "Norte", 1.41, -51.77),
    StateInfo("17", "TO", "Tocantins", "Norte", -9.46, -48.26),
    StateInfo("21", "MA", "Maranhao", "Nordeste", -5.42, -45.44),
    StateInfo("22", "PI", "Piaui", "Nordeste", -6.60, -42.28),
    StateInfo("23", "CE", "Ceara", "Nordeste", -5.20, -39.53),
    StateInfo("24", "RN", "Rio Grande do Norte", "Nordeste", -5.81, -36.59),
    StateInfo("25", "PB", "Paraiba", "Nordeste", -7.28, -36.72),
    StateInfo("26", "PE", "Pernambuco", "Nordeste", -8.38, -37.86),
    StateInfo("27", "AL", "Alagoas", "Nordeste", -9.62, -36.82),
    StateInfo("28", "SE", "Sergipe", "Nordeste", -10.57, -37.45),
    StateInfo("29", "BA", "Bahia", "Nordeste", -12.96, -41.70),
    StateInfo("31", "MG", "Minas Gerais", "Sudeste", -18.10, -44.38),
    StateInfo("32", "ES", "Espirito Santo", "Sudeste", -19.19, -40.34),
    StateInfo("33", "RJ", "Rio de Janeiro", "Sudeste", -22.25, -42.66),
    StateInfo("35", "SP", "Sao Paulo", "Sudeste", -22.19, -48.79),
    StateInfo("41", "PR", "Parana", "Sul", -24.89, -51.55),
    StateInfo("42", "SC", "Santa Catarina", "Sul", -27.45, -50.95),
    StateInfo("43", "RS", "Rio Grande do Sul", "Sul", -30.17, -53.50),
    StateInfo("50", "MS", "Mato Grosso do Sul", "Centro-Oeste", -20.51, -54.54),
    StateInfo("51", "MT", "Mato Grosso", "Centro-Oeste", -12.64, -55.42),
    StateInfo("52", "GO", "Goias", "Centro-Oeste", -15.98, -49.86),
    StateInfo("53", "DF", "Distrito Federal", "Centro-Oeste", -15.83, -47.86),
)

STATE_BY_PREFIX = {state.ibge_prefix: state for state in STATES}
STATE_BY_UF = {state.uf: state for state in STATES}

REGION_ORDER = ("Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul")


def ibge_prefix_to_uf(prefix: str | int | None) -> str | None:
    if prefix is None:
        return None
    info = STATE_BY_PREFIX.get(str(prefix).zfill(2))
    return info.uf if info else None


def ibge_prefix_to_region(prefix: str | int | None) -> str | None:
    if prefix is None:
        return None
    info = STATE_BY_PREFIX.get(str(prefix).zfill(2))
    return info.region if info else None


def states_records() -> list[dict[str, str | float]]:
    return [
        {
            "uf_code": state.ibge_prefix,
            "uf": state.uf,
            "state": state.name,
            "region": state.region,
            "lat": state.lat,
            "lon": state.lon,
        }
        for state in STATES
    ]
