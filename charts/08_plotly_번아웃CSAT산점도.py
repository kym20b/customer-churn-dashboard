"""번아웃(초과근무 시간)과 CSAT 평균의 관계 산점도 (BigQuery agents/consultations/satisfaction 직접 조회)"""
import pandas as pd
import plotly.express as px
from google.cloud import bigquery

# 색상 (dataviz 스킬 팔레트)
COLOR_POINT = "#2a78d6"
COLOR_TREND = "#d03b3b"
COLOR_TEXT_PRIMARY = "#0b0b0b"
COLOR_GRID = "#e1e0d9"

PROJECT = "sql-study-493001"
DATASET = "project1_day1"

client = bigquery.Client(project=PROJECT)

query = f"""
WITH agent_csat AS (
  SELECT
    c.agent_id,
    AVG(s.csat) AS avg_csat
  FROM `{PROJECT}.{DATASET}.consultations` c
  JOIN `{PROJECT}.{DATASET}.satisfaction` s ON c.consult_id = s.consult_id
  WHERE c.agent_id IS NOT NULL
  GROUP BY c.agent_id
)
SELECT
  a.agent_id,
  a.team,
  a.overtime_hours_avg,
  ac.avg_csat
FROM `{PROJECT}.{DATASET}.agents` a
JOIN agent_csat ac ON a.agent_id = ac.agent_id
"""

df = client.query(query).result().to_dataframe()

correlation = df["overtime_hours_avg"].corr(df["avg_csat"])

fig = px.scatter(
    df,
    x="overtime_hours_avg",
    y="avg_csat",
    trendline="ols",
    custom_data=["agent_id", "overtime_hours_avg", "avg_csat"],
    title="번아웃(초과근무 시간) vs CSAT 평균",
    labels={"overtime_hours_avg": "초과근무 시간 (평균, 시간)", "avg_csat": "CSAT 평균"},
)

fig.update_traces(
    selector=dict(mode="markers"),
    marker=dict(size=10, color=COLOR_POINT, opacity=0.85),
    hovertemplate=(
        "<b>%{customdata[0]}</b><br>"
        "초과근무 시간: %{customdata[1]}시간<br>"
        "CSAT 평균: %{customdata[2]:.2f}"
        "<extra></extra>"
    ),
)
fig.update_traces(selector=dict(mode="lines"), line=dict(color=COLOR_TREND, width=2))

fig.add_annotation(
    xref="paper",
    yref="paper",
    x=0.98,
    y=0.98,
    text=f"r = {correlation:.2f}",
    showarrow=False,
    font=dict(size=16, color=COLOR_TEXT_PRIMARY),
    align="right",
)

fig.update_layout(
    plot_bgcolor="#fcfcfb",
    paper_bgcolor="#fcfcfb",
    font=dict(family="Malgun Gothic, sans-serif", color=COLOR_TEXT_PRIMARY),
    xaxis=dict(gridcolor=COLOR_GRID),
    yaxis=dict(gridcolor=COLOR_GRID),
)

print(df.to_string(index=False))
print(f"상관계수 r = {correlation:.4f}")

fig.show()
