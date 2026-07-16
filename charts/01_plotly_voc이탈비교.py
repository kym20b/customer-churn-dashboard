"""전체 고객 이탈율 vs 해지관련 부정 VOC 이력 고객 이탈율 비교 (plotly.express)"""
import os

import pandas as pd
import plotly.express as px

# 색상 (dataviz 스킬 팔레트: 중립 회색 + critical 빨강)
COLOR_NEUTRAL = "#898781"
COLOR_CRITICAL = "#d03b3b"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

voc = pd.read_csv(os.path.join(DATA_DIR, "data_voc.csv"))
customers = pd.read_csv(os.path.join(DATA_DIR, "data_customers.csv"))

# 해지관련 + 부정 VOC를 남긴 고객(중복 제거)
target_ids = voc.loc[
    (voc["category"] == "해지관련") & (voc["sentiment"] == "부정"), "customer_id"
].unique()

target_customers = customers[customers["customer_id"].isin(target_ids)]
target_total = len(target_customers)
target_churned = int((target_customers["churn_yn"] == "Y").sum())
target_rate = target_churned / target_total * 100

overall_total = len(customers)
overall_churned = int((customers["churn_yn"] == "Y").sum())
overall_rate = overall_churned / overall_total * 100

df = pd.DataFrame(
    {
        "category": ["전체 고객", "해지관련 부정 VOC 이력 있음"],
        "churn_rate": [overall_rate, target_rate],
        "total_customers": [overall_total, target_total],
        "churned_customers": [overall_churned, target_churned],
    }
)

fig = px.bar(
    df,
    x="category",
    y="churn_rate",
    color="category",
    color_discrete_map={
        "전체 고객": COLOR_NEUTRAL,
        "해지관련 부정 VOC 이력 있음": COLOR_CRITICAL,
    },
    text=df["churn_rate"].map(lambda v: f"{v:.1f}%"),
    custom_data=["total_customers", "churned_customers", "churn_rate"],
    title="전체 고객 vs 해지관련 부정 VOC 이력 고객 이탈율 비교",
    labels={"category": "", "churn_rate": "이탈율 (%)"},
)

fig.update_traces(
    textposition="outside",
    hovertemplate=(
        "<b>%{x}</b><br>"
        "고객 수: %{customdata[0]:,}명<br>"
        "이탈 고객 수: %{customdata[1]:,}명<br>"
        "이탈율: %{customdata[2]:.2f}%"
        "<extra></extra>"
    ),
)

fig.update_layout(
    showlegend=False,
    yaxis=dict(range=[0, max(df["churn_rate"]) * 1.25], gridcolor="#e1e0d9"),
    plot_bgcolor="#fcfcfb",
    paper_bgcolor="#fcfcfb",
    font=dict(family="Malgun Gothic, sans-serif", color="#0b0b0b"),
    title_font=dict(size=18),
)

print(f"전체 고객 이탈율: {overall_rate:.2f}% ({overall_churned}/{overall_total})")
print(f"해지관련 부정 VOC 이력 고객 이탈율: {target_rate:.2f}% ({target_churned}/{target_total})")

fig.show()
