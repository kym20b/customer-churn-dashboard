"""번아웃(초과근무 시간) vs CSAT 평균: 이상치(AG02·AG03) 포함/제외 비교"""
import numpy as np
import plotly.graph_objects as go
from google.cloud import bigquery
from plotly.subplots import make_subplots

# 색상 (dataviz 스킬 팔레트)
COLOR_POINT = "#2a78d6"
COLOR_TREND = "#d03b3b"
COLOR_OUTLIER = "#eda100"
COLOR_TEXT_PRIMARY = "#0b0b0b"
COLOR_GRID = "#e1e0d9"

PROJECT = "sql-study-493001"
DATASET = "project1_day1"

OUTLIER_AGENT_IDS = ["AG02", "AG03"]

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
  a.overtime_hours_avg,
  ac.avg_csat
FROM `{PROJECT}.{DATASET}.agents` a
JOIN agent_csat ac ON a.agent_id = ac.agent_id
"""

df = client.query(query).result().to_dataframe()
df_excl = df[~df["agent_id"].isin(OUTLIER_AGENT_IDS)]


def fit_ols(data):
    x = data["overtime_hours_avg"].to_numpy(dtype=float)
    y = data["avg_csat"].to_numpy(dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    r = data["overtime_hours_avg"].corr(data["avg_csat"])
    return slope, intercept, r


slope_all, intercept_all, r_all = fit_ols(df)
slope_excl, intercept_excl, r_excl = fit_ols(df_excl)

y_range = [df["avg_csat"].min() - 0.1, df["avg_csat"].max() + 0.1]
x_range = [df["overtime_hours_avg"].min() - 1, df["overtime_hours_avg"].max() + 1]

fig = make_subplots(
    rows=1,
    cols=2,
    subplot_titles=(
        f"AG02·AG03 포함 (n={len(df)})<br>r = {r_all:.2f}, 기울기 = {slope_all:.3f}",
        f"AG02·AG03 제외 (n={len(df_excl)})<br>r = {r_excl:.2f}, 기울기 = {slope_excl:.3f}",
    ),
    shared_yaxes=True,
)

# 왼쪽: 전체 포함
is_outlier = df["agent_id"].isin(OUTLIER_AGENT_IDS)
fig.add_trace(
    go.Scatter(
        x=df.loc[~is_outlier, "overtime_hours_avg"],
        y=df.loc[~is_outlier, "avg_csat"],
        mode="markers",
        marker=dict(size=10, color=COLOR_POINT, opacity=0.85),
        customdata=df.loc[~is_outlier, ["agent_id", "overtime_hours_avg", "avg_csat"]],
        hovertemplate="<b>%{customdata[0]}</b><br>초과근무: %{customdata[1]}시간<br>CSAT 평균: %{customdata[2]:.2f}<extra></extra>",
        name="상담원",
        showlegend=False,
    ),
    row=1,
    col=1,
)
fig.add_trace(
    go.Scatter(
        x=df.loc[is_outlier, "overtime_hours_avg"],
        y=df.loc[is_outlier, "avg_csat"],
        mode="markers",
        marker=dict(size=12, color=COLOR_OUTLIER, symbol="diamond", line=dict(width=2, color="white")),
        customdata=df.loc[is_outlier, ["agent_id", "overtime_hours_avg", "avg_csat"]],
        hovertemplate="<b>%{customdata[0]}</b> (이상치)<br>초과근무: %{customdata[1]}시간<br>CSAT 평균: %{customdata[2]:.2f}<extra></extra>",
        name="이상치 (AG02·AG03)",
        showlegend=True,
    ),
    row=1,
    col=1,
)
trend_x_all = np.array(x_range)
fig.add_trace(
    go.Scatter(
        x=trend_x_all,
        y=slope_all * trend_x_all + intercept_all,
        mode="lines",
        line=dict(color=COLOR_TREND, width=2),
        name="추세선(OLS)",
        showlegend=True,
    ),
    row=1,
    col=1,
)

# 오른쪽: 이상치 제외
fig.add_trace(
    go.Scatter(
        x=df_excl["overtime_hours_avg"],
        y=df_excl["avg_csat"],
        mode="markers",
        marker=dict(size=10, color=COLOR_POINT, opacity=0.85),
        customdata=df_excl[["agent_id", "overtime_hours_avg", "avg_csat"]],
        hovertemplate="<b>%{customdata[0]}</b><br>초과근무: %{customdata[1]}시간<br>CSAT 평균: %{customdata[2]:.2f}<extra></extra>",
        showlegend=False,
    ),
    row=1,
    col=2,
)
trend_x_excl = np.array(
    [df_excl["overtime_hours_avg"].min() - 1, df_excl["overtime_hours_avg"].max() + 1]
)
fig.add_trace(
    go.Scatter(
        x=trend_x_excl,
        y=slope_excl * trend_x_excl + intercept_excl,
        mode="lines",
        line=dict(color=COLOR_TREND, width=2),
        showlegend=False,
    ),
    row=1,
    col=2,
)

fig.update_xaxes(title_text="초과근무 시간 (평균, 시간)", gridcolor=COLOR_GRID, range=x_range, row=1, col=1)
fig.update_xaxes(title_text="초과근무 시간 (평균, 시간)", gridcolor=COLOR_GRID, range=x_range, row=1, col=2)
fig.update_yaxes(title_text="CSAT 평균", gridcolor=COLOR_GRID, range=y_range, row=1, col=1)
fig.update_yaxes(gridcolor=COLOR_GRID, range=y_range, row=1, col=2)

fig.update_layout(
    title="번아웃(초과근무) vs CSAT: 이상치(AG02·AG03) 포함/제외 비교",
    plot_bgcolor="#fcfcfb",
    paper_bgcolor="#fcfcfb",
    font=dict(family="Malgun Gothic, sans-serif", color=COLOR_TEXT_PRIMARY),
    legend=dict(orientation="h", yanchor="bottom", y=1.12, xanchor="center", x=0.5),
)

print(f"[포함] n={len(df)}, r={r_all:.4f}, 기울기={slope_all:.4f}")
print(f"[제외] n={len(df_excl)}, r={r_excl:.4f}, 기울기={slope_excl:.4f}")
print(f"기울기 변화: {slope_all:.4f} -> {slope_excl:.4f} (변화량 {slope_excl - slope_all:+.4f})")
print(f"상관계수 변화: {r_all:.4f} -> {r_excl:.4f} (변화량 {r_excl - r_all:+.4f})")

fig.show()
