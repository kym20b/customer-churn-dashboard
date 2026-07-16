"""고객별 재문의 횟수 구간(0회/1회/2회 이상)에 따른 이탈율 비교"""
import os

import pandas as pd
import plotly.express as px

# 색상 (dataviz 스킬 팔레트: 중립 회색 + critical 빨강 강조)
COLOR_NEUTRAL = "#898781"
COLOR_CRITICAL = "#d03b3b"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

consultations = pd.read_csv(os.path.join(DATA_DIR, "data_consultations.csv"))
customers = pd.read_csv(os.path.join(DATA_DIR, "data_customers.csv"))

# 고객별 재문의(is_recontact=Y) 횟수
recontact_count = (
    consultations[consultations["is_recontact"] == "Y"]
    .groupby("customer_id")
    .size()
    .rename("recontact_count")
)

merged = customers.merge(recontact_count, on="customer_id", how="left")
merged["recontact_count"] = merged["recontact_count"].fillna(0).astype(int)


def bucket(n):
    if n == 0:
        return "0회"
    if n == 1:
        return "1회"
    return "2회 이상"


merged["recontact_bucket"] = merged["recontact_count"].apply(bucket)

bucket_order = ["0회", "1회", "2회 이상"]

summary = (
    merged.groupby("recontact_bucket")
    .agg(
        total_customers=("customer_id", "count"),
        churned_customers=("churn_yn", lambda s: (s == "Y").sum()),
    )
    .reindex(bucket_order)
    .reset_index()
)
summary["churn_rate"] = summary["churned_customers"] / summary["total_customers"] * 100

overall_rate = (customers["churn_yn"] == "Y").mean() * 100

fig = px.bar(
    summary,
    x="recontact_bucket",
    y="churn_rate",
    color="recontact_bucket",
    color_discrete_map={
        "0회": COLOR_NEUTRAL,
        "1회": COLOR_NEUTRAL,
        "2회 이상": COLOR_CRITICAL,
    },
    text=summary["churn_rate"].map(lambda v: f"{v:.1f}%"),
    custom_data=["total_customers", "churned_customers"],
    title="재문의 횟수 구간별 이탈율",
    labels={"recontact_bucket": "재문의 횟수", "churn_rate": "이탈율 (%)"},
    category_orders={"recontact_bucket": bucket_order},
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

fig.add_hline(
    y=overall_rate,
    line_dash="dash",
    line_color="#52514e",
    annotation_text=f"전체 평균 이탈율 {overall_rate:.1f}%",
    annotation_position="top right",
)

fig.update_layout(
    showlegend=False,
    yaxis=dict(range=[0, max(summary["churn_rate"].max(), overall_rate) * 1.3], gridcolor="#e1e0d9"),
    plot_bgcolor="#fcfcfb",
    paper_bgcolor="#fcfcfb",
    font=dict(family="Malgun Gothic, sans-serif", color="#0b0b0b"),
)

print(summary.to_string(index=False))
print(f"전체 평균 이탈율: {overall_rate:.2f}%")

fig.show()
