"""channel별 CSAT 평균(막대, 왼쪽 축) vs 재문의율(꺾은선, 오른쪽 축) 결합차트"""
import os

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 색상 (dataviz 스킬 팔레트: 카테고리컬 1번 blue = 막대, 8번 red = 꺾은선)
COLOR_BAR = "#2a78d6"
COLOR_LINE = "#e34948"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

satisfaction = pd.read_csv(os.path.join(DATA_DIR, "data_satisfaction.csv"))
consultations = pd.read_csv(os.path.join(DATA_DIR, "data_consultations.csv"))

merged = satisfaction.merge(
    consultations[["consult_id", "channel", "is_recontact"]],
    on="consult_id",
    how="inner",
)

summary = (
    merged.groupby("channel")
    .agg(
        csat_mean=("csat", "mean"),
        recontact_rate=("is_recontact", lambda s: (s == "Y").mean() * 100),
        count=("consult_id", "count"),
    )
    .reset_index()
    .sort_values("csat_mean", ascending=True)
)

fig = make_subplots(specs=[[{"secondary_y": True}]])

fig.add_trace(
    go.Bar(
        x=summary["channel"],
        y=summary["csat_mean"],
        name="CSAT 평균",
        marker_color=COLOR_BAR,
        customdata=summary[["recontact_rate", "count"]],
        hovertemplate=(
            "<b>%{x}</b><br>"
            "CSAT 평균: %{y:.2f}<br>"
            "재문의율: %{customdata[0]:.1f}%"
            "<extra></extra>"
        ),
    ),
    secondary_y=False,
)

fig.add_trace(
    go.Scatter(
        x=summary["channel"],
        y=summary["recontact_rate"],
        name="재문의율",
        mode="lines+markers",
        line=dict(color=COLOR_LINE, width=2),
        marker=dict(size=8, color=COLOR_LINE),
        customdata=summary[["csat_mean", "count"]],
        hovertemplate=(
            "<b>%{x}</b><br>"
            "재문의율: %{y:.1f}%<br>"
            "CSAT 평균: %{customdata[0]:.2f}"
            "<extra></extra>"
        ),
    ),
    secondary_y=True,
)

fig.update_layout(
    title="채널별 CSAT 평균 vs 재문의율 (CSAT 낮은 순)",
    plot_bgcolor="#fcfcfb",
    paper_bgcolor="#fcfcfb",
    font=dict(family="Malgun Gothic, sans-serif", color="#0b0b0b"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hovermode="x unified",
)
fig.update_yaxes(title_text="CSAT 평균", secondary_y=False, gridcolor="#e1e0d9")
fig.update_yaxes(title_text="재문의율 (%)", secondary_y=True, showgrid=False)
fig.update_xaxes(title_text="")

print(summary.to_string(index=False))

fig.show()
