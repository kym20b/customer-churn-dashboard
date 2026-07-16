"""요금제(plan)별 고객 수와 이탈율 비교 (베이직 강조)"""
import os

import pandas as pd
import plotly.express as px

# 색상 (dataviz 스킬 팔레트: 중립 회색 + critical 빨강 강조)
COLOR_NEUTRAL = "#898781"
COLOR_CRITICAL = "#d03b3b"
HIGHLIGHT_PLAN = "베이직"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

customers = pd.read_csv(os.path.join(DATA_DIR, "data_customers.csv"))

summary = (
    customers.groupby("plan")
    .agg(
        total_customers=("customer_id", "count"),
        churned_customers=("churn_yn", lambda s: (s == "Y").sum()),
    )
    .reset_index()
)
summary["churn_rate"] = summary["churned_customers"] / summary["total_customers"] * 100
summary = summary.sort_values("churn_rate", ascending=False)

color_map = {plan: (COLOR_CRITICAL if plan == HIGHLIGHT_PLAN else COLOR_NEUTRAL) for plan in summary["plan"]}

fig = px.bar(
    summary,
    x="plan",
    y="churn_rate",
    color="plan",
    color_discrete_map=color_map,
    text=summary["churn_rate"].map(lambda v: f"{v:.1f}%"),
    custom_data=["total_customers", "churned_customers"],
    title="요금제(plan)별 이탈율",
    labels={"plan": "요금제", "churn_rate": "이탈율 (%)"},
    category_orders={"plan": list(summary["plan"])},
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

fig.update_layout(
    showlegend=False,
    yaxis=dict(range=[0, summary["churn_rate"].max() * 1.25], gridcolor="#e1e0d9"),
    plot_bgcolor="#fcfcfb",
    paper_bgcolor="#fcfcfb",
    font=dict(family="Malgun Gothic, sans-serif", color="#0b0b0b"),
)

print(summary.to_string(index=False))

fig.show()
