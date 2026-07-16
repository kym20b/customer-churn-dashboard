"""지역(region)별 고객 수와 이탈율 비교 (부산·대구 강조)"""
import os

import pandas as pd
import plotly.express as px

# 색상 (dataviz 스킬 팔레트: 중립 회색 + critical 빨강 강조)
COLOR_NEUTRAL = "#898781"
COLOR_CRITICAL = "#d03b3b"
HIGHLIGHT_REGIONS = ["부산", "대구"]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

customers = pd.read_csv(os.path.join(DATA_DIR, "data_customers.csv"))

summary = (
    customers.groupby("region")
    .agg(
        total_customers=("customer_id", "count"),
        churned_customers=("churn_yn", lambda s: (s == "Y").sum()),
    )
    .reset_index()
)
summary["churn_rate"] = summary["churned_customers"] / summary["total_customers"] * 100
summary = summary.sort_values("churn_rate", ascending=False)

color_map = {
    region: (COLOR_CRITICAL if region in HIGHLIGHT_REGIONS else COLOR_NEUTRAL)
    for region in summary["region"]
}

fig = px.bar(
    summary,
    x="region",
    y="churn_rate",
    color="region",
    color_discrete_map=color_map,
    text=summary["churn_rate"].map(lambda v: f"{v:.1f}%"),
    custom_data=["total_customers", "churned_customers"],
    title="지역(region)별 이탈율",
    labels={"region": "지역", "churn_rate": "이탈율 (%)"},
    category_orders={"region": list(summary["region"])},
)

fig.update_traces(
    textposition="outside",
    hovertemplate=(
        "<b>%{x}</b><br>"
        "고객 수: %{customdata[0]:,}명<br>"
        "이탈 고객 수: %{customdata[1]:,}명<br>"
        "이탈율: %{y:.2f}%"
        "<extra></extra>"
    ),
)

# 인천은 표본이 작아(53건, 이탈 1건) 이탈율이 낮게 나온 것으로 보이므로 캡션으로 명시
incheon = summary.loc[summary["region"] == "인천"].iloc[0]
caption = (
    f"※ 인천은 표본이 {int(incheon['total_customers'])}건이지만 "
    f"이탈은 {int(incheon['churned_customers'])}건뿐이라 이탈율 해석에 주의가 필요합니다."
)

fig.update_layout(
    showlegend=False,
    yaxis=dict(range=[0, summary["churn_rate"].max() * 1.3], gridcolor="#e1e0d9"),
    plot_bgcolor="#fcfcfb",
    paper_bgcolor="#fcfcfb",
    font=dict(family="Malgun Gothic, sans-serif", color="#0b0b0b"),
    margin=dict(b=100),
)

fig.add_annotation(
    text=caption,
    xref="paper",
    yref="paper",
    x=0,
    y=-0.28,
    showarrow=False,
    align="left",
    font=dict(size=12, color="#52514e"),
)

print(summary.to_string(index=False))

fig.show()
