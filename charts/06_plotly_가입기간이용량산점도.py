"""가입기간(tenure_months) vs 평균 데이터 사용량(data_gb) 산점도, 이탈 여부로 색 구분"""
import os

import pandas as pd
import plotly.express as px
from dateutil.relativedelta import relativedelta

# 색상 (dataviz 스킬 팔레트: 상태 색상 - 잔존 good / 이탈 critical)
COLOR_ACTIVE = "#0ca30c"
COLOR_CHURNED = "#d03b3b"

REFERENCE_DATE = pd.Timestamp("2024-12-31")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

customers = pd.read_csv(os.path.join(DATA_DIR, "data_customers.csv"))
usage = pd.read_csv(os.path.join(DATA_DIR, "data_usage_history.csv"))

customers["join_date"] = pd.to_datetime(customers["join_date"])
customers["tenure_months"] = customers["join_date"].apply(
    lambda d: relativedelta(REFERENCE_DATE, d).years * 12 + relativedelta(REFERENCE_DATE, d).months
)

avg_usage = usage.groupby("customer_id")["data_gb"].mean().rename("avg_data_gb")

merged = customers.merge(avg_usage, on="customer_id", how="inner")

fig = px.scatter(
    merged,
    x="tenure_months",
    y="avg_data_gb",
    color="churn_yn",
    color_discrete_map={"N": COLOR_ACTIVE, "Y": COLOR_CHURNED},
    category_orders={"churn_yn": ["N", "Y"]},
    custom_data=["customer_id", "tenure_months", "avg_data_gb", "churn_yn"],
    title="가입기간 vs 평균 데이터 사용량 (이탈 여부)",
    labels={"tenure_months": "가입기간 (개월)", "avg_data_gb": "평균 데이터 사용량 (GB)", "churn_yn": "이탈 여부"},
)

fig.update_traces(
    marker=dict(size=8, opacity=0.8),
    hovertemplate=(
        "<b>%{customdata[0]}</b><br>"
        "가입기간: %{customdata[1]}개월<br>"
        "평균 데이터 사용량: %{customdata[2]:.2f}GB<br>"
        "이탈 여부: %{customdata[3]}"
        "<extra></extra>"
    ),
)

fig.update_layout(
    plot_bgcolor="#fcfcfb",
    paper_bgcolor="#fcfcfb",
    font=dict(family="Malgun Gothic, sans-serif", color="#0b0b0b"),
    xaxis=dict(gridcolor="#e1e0d9"),
    yaxis=dict(gridcolor="#e1e0d9"),
    legend_title_text="이탈 여부",
)

print(merged[["customer_id", "tenure_months", "avg_data_gb", "churn_yn"]].head())
print(f"총 {len(merged)}명 연결 완료")

fig.show()
