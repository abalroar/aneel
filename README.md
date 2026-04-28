# Radar ANEEL de Quedas de Energia

MVP em Streamlit para monitorar quedas de energia e ocorrências emergenciais nas redes de distribuição a partir dos dados abertos da ANEEL.

O foco inicial é reproduzir uma experiência parecida com painéis de distribuição da ANEEL: leitura por região, UF, causa declarada, mês e distribuidora. A base principal é **Ocorrências Emergenciais nas Redes de Distribuição**, porque ela traz `CodIBGE` e permite agregação por UF/região. A aba de causas técnicas usa a base **Interrupções de Energia Elétrica nas Redes de Distribuição**.

## Fontes

- Portal de dados abertos da ANEEL: <https://dadosabertos.aneel.gov.br/>
- Ocorrências emergenciais: <https://dadosabertos.aneel.gov.br/dataset/ocorrencias-emergenciais-nas-redes-de-distribuicao>
- Interrupções: <https://dadosabertos.aneel.gov.br/dataset/interrupcoes-de-energia-eletrica-nas-redes-de-distribuicao>
- Indicadores de distribuição da ANEEL: <https://www.gov.br/aneel/pt-br/centrais-de-conteudos/relatorios-e-indicadores/distribuicao>

## Rodando localmente

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Escopo do MVP

- Mapa de bolhas por UF, com cor por região.
- KPIs de ocorrências, UFs, municípios, distribuidoras e ocorrências não programadas.
- Ranking de regiões, causas declaradas e distribuidoras.
- Tendência mensal por ano selecionado.
- Aba técnica com treemap de causas de interrupções.
- Cache de uma hora no Streamlit para não martelar a API.

## Observações de engenharia

Os arquivos históricos são grandes. Algumas consultas agregadas, principalmente 2025 e anos anteriores de ocorrências, podem demorar na primeira carga. O app evita baixar arquivos completos e usa `datastore_search_sql` para trazer apenas agregados.

Para uma versão de produção, o próximo passo é criar uma camada de ingestão diária que salve os agregados em DuckDB ou Parquet, deixando o Streamlit ler de um cache local/versionado.
