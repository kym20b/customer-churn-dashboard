"""교육 이수 여부(Y/N)에 따른 CSAT 평균 vs 재문의율 평균 비교 (BigQuery agents/consultations/satisfaction 직접 조회)"""
import plotly.graph_objects as go
from google.cloud import bigquery
from plotly.subplots import make_subplots

# 색상 (dataviz 스킬 팔레트: 강조 blue + 중립 회색)
COLOR_HIGHLIGHT = "#2a78d6"
COLOR_NEUTRAL = "#898781"
COLOR_TEXT_PRIMARY = "#0b0b0b"
COLOR_GRID = "#e1e0d9"

PROJECT = "sql-study-493001"
DATASET = "project1_day1"

client = bigquery.Client(project=PROJECT)

query = f"""
WITH consult_info AS (
  SELECT
    c.is_recontact,
    s.csat,
    a.training_completed_yn
  FROM `{PROJECT}.{DATASET}.consultations` c
  JOIN `{PROJECT}.{DATASET}.satisfaction` s ON c.consult_id = s.consult_id
  JOIN `{PROJECT}.{DATASET}.agents` a ON c.agent_id = a.agent_id
)
SELECT
  training_completed_yn,
  COUNT(*) AS n,
  AVG(csat) AS avg_csat,
  AVG(CAST(is_recontact AS INT64)) * 100 AS recontact_rate
FROM consult_info
GROUP BY training_completed_yn
"""

df = client.query(query).result().to_dataframe()
df["label"] = df["training_completed_yn"].map({True: "Y (이수)", False: "N (미이수)"})
df = df.sort_values("training_completed_yn", ascending=False)  # Y가 왼쪽

color_map = {"Y (이수)": COLOR_HIGHLIGHT, "N (미이수)": COLOR_NEUTRAL}
bar_colors = df["label"].map(color_map)

fig = make_subplots(rows=1, cols=2, subplot_titles=("CSAT 평균", "재문의율 평균 (%)"))

fig.add_trace(
    go.Bar(
        x=df["label"],
        y=df["avg_csat"],
        marker_color=bar_colors,
        text=df["avg_csat"].map(lambda v: f"{v:.2f}"),
        textposition="outside",
        customdata=df[["n"]],
        hovertemplate="<b>%{x}</b><br>CSAT 평균: %{y:.2f}<br>상담 건수: %{customdata[0]:,}건<extra></extra>",
        showlegend=False,
    ),
    row=1,
    col=1,
)

fig.add_trace(
    go.Bar(
        x=df["label"],
        y=df["recontact_rate"],
        marker_color=bar_colors,
        text=df["recontact_rate"].map(lambda v: f"{v:.1f}%"),
        textposition="outside",
        customdata=df[["n"]],
        hovertemplate="<b>%{x}</b><br>재문의율: %{y:.1f}%<br>상담 건수: %{customdata[0]:,}건<extra></extra>",
        showlegend=False,
    ),
    row=1,
    col=2,
)

fig.update_yaxes(title_text="CSAT 평균", range=[0, df["avg_csat"].max() * 1.25], gridcolor=COLOR_GRID, row=1, col=1)
fig.update_yaxes(title_text="재문의율 (%)", range=[0, df["recontact_rate"].max() * 1.25], gridcolor=COLOR_GRID, row=1, col=2)

fig.update_layout(
    title="교육 이수 여부에 따른 CSAT 평균 · 재문의율 평균 비교",
    plot_bgcolor="#fcfcfb",
    paper_bgcolor="#fcfcfb",
    font=dict(family="Malgun Gothic, sans-serif", color=COLOR_TEXT_PRIMARY),
)

print(df[["label", "n", "avg_csat", "recontact_rate"]].to_string(index=False))

fig.show()
