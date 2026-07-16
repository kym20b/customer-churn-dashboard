"""고객은 왜 이탈하는가 — 이탈 원인 진단 대시보드"""
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dateutil.relativedelta import relativedelta
from plotly.subplots import make_subplots

st.set_page_config(page_title="고객은 왜 이탈하는가", layout="wide")

# 색상 (dataviz 스킬 팔레트)
COLOR_NEUTRAL = "#898781"
COLOR_CRITICAL = "#d03b3b"
COLOR_ACTIVE = "#0ca30c"
COLOR_BAR = "#2a78d6"
COLOR_LINE = "#e34948"
COLOR_GRID = "#e1e0d9"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

CHART_LAYOUT = dict(
    plot_bgcolor="#fcfcfb",
    paper_bgcolor="#fcfcfb",
    font=dict(family="Malgun Gothic, sans-serif", color="#0b0b0b"),
)


@st.cache_data
def load_data():
    customers = pd.read_csv(os.path.join(DATA_DIR, "data_customers.csv"))
    voc = pd.read_csv(os.path.join(DATA_DIR, "data_voc.csv"))
    consultations = pd.read_csv(os.path.join(DATA_DIR, "data_consultations.csv"))
    satisfaction = pd.read_csv(os.path.join(DATA_DIR, "data_satisfaction.csv"))
    usage = pd.read_csv(os.path.join(DATA_DIR, "data_usage_history.csv"))
    return customers, voc, consultations, satisfaction, usage


customers, voc, consultations, satisfaction, usage = load_data()


# ── ① VOC로 본 이탈 ──────────────────────────────────────────────
def build_voc_chart(customers, voc):
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
            "<b>%{x}</b><br>고객 수: %{customdata[0]:,}명<br>"
            "이탈 고객 수: %{customdata[1]:,}명<br>이탈율: %{customdata[2]:.2f}%<extra></extra>"
        ),
    )
    fig.update_layout(
        showlegend=False,
        yaxis=dict(range=[0, max(df["churn_rate"]) * 1.25], gridcolor=COLOR_GRID),
        **CHART_LAYOUT,
    )
    return fig


# ── ② 채널·만족도로 본 이탈 ──────────────────────────────────────
def build_channel_csat_chart(consultations, satisfaction):
    merged = satisfaction.merge(
        consultations[["consult_id", "channel", "is_recontact"]], on="consult_id", how="inner"
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
            hovertemplate="<b>%{x}</b><br>CSAT 평균: %{y:.2f}<br>재문의율: %{customdata[0]:.1f}%<extra></extra>",
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
            hovertemplate="<b>%{x}</b><br>재문의율: %{y:.1f}%<br>CSAT 평균: %{customdata[0]:.2f}<extra></extra>",
        ),
        secondary_y=True,
    )
    fig.update_layout(
        title="채널별 CSAT 평균 vs 재문의율 (CSAT 낮은 순)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        **CHART_LAYOUT,
    )
    fig.update_yaxes(title_text="CSAT 평균", secondary_y=False, gridcolor=COLOR_GRID)
    fig.update_yaxes(title_text="재문의율 (%)", secondary_y=True, showgrid=False)
    fig.update_xaxes(title_text="")
    return fig


# ── ③ 재문의 반복으로 본 이탈 ────────────────────────────────────
def build_recontact_bucket_chart(consultations, customers):
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
        color_discrete_map={"0회": COLOR_NEUTRAL, "1회": COLOR_NEUTRAL, "2회 이상": COLOR_CRITICAL},
        text=summary["churn_rate"].map(lambda v: f"{v:.1f}%"),
        custom_data=["total_customers", "churned_customers"],
        title="재문의 횟수 구간별 이탈율",
        labels={"recontact_bucket": "재문의 횟수", "churn_rate": "이탈율 (%)"},
        category_orders={"recontact_bucket": bucket_order},
    )
    fig.update_traces(
        textposition="outside",
        hovertemplate=(
            "<b>%{x}</b><br>고객 수: %{customdata[0]:,}명<br>"
            "이탈 고객 수: %{customdata[1]:,}명<br>이탈율: %{y:.2f}%<extra></extra>"
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
        yaxis=dict(range=[0, max(summary["churn_rate"].max(), overall_rate) * 1.3], gridcolor=COLOR_GRID),
        **CHART_LAYOUT,
    )
    return fig


# ── ④ 요금제로 본 이탈 ───────────────────────────────────────────
def build_plan_chart(customers):
    highlight_plan = "베이직"
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

    color_map = {plan: (COLOR_CRITICAL if plan == highlight_plan else COLOR_NEUTRAL) for plan in summary["plan"]}

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
            "<b>%{x}</b><br>고객 수: %{customdata[0]:,}명<br>"
            "이탈 고객 수: %{customdata[1]:,}명<br>이탈율: %{y:.2f}%<extra></extra>"
        ),
    )
    fig.update_layout(
        showlegend=False,
        yaxis=dict(range=[0, summary["churn_rate"].max() * 1.25], gridcolor=COLOR_GRID),
        **CHART_LAYOUT,
    )
    return fig


# ── ⑤ 지역으로 본 이탈 ───────────────────────────────────────────
def build_region_chart(customers):
    highlight_regions = ["부산", "대구"]
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
        region: (COLOR_CRITICAL if region in highlight_regions else COLOR_NEUTRAL)
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
            "<b>%{x}</b><br>고객 수: %{customdata[0]:,}명<br>"
            "이탈 고객 수: %{customdata[1]:,}명<br>이탈율: %{y:.2f}%<extra></extra>"
        ),
    )

    incheon = summary.loc[summary["region"] == "인천"].iloc[0]
    caption = (
        f"※ 인천은 표본이 {int(incheon['total_customers'])}건이지만 "
        f"이탈은 {int(incheon['churned_customers'])}건뿐이라 이탈율 해석에 주의가 필요합니다."
    )

    fig.update_layout(
        showlegend=False,
        yaxis=dict(range=[0, summary["churn_rate"].max() * 1.3], gridcolor=COLOR_GRID),
        margin=dict(b=100),
        **CHART_LAYOUT,
    )
    fig.add_annotation(
        text=caption, xref="paper", yref="paper", x=0, y=-0.28,
        showarrow=False, align="left", font=dict(size=12, color="#52514e"),
    )
    return fig


# ── ⑥ 가입기간·이용량으로 본 이탈 ────────────────────────────────
def build_tenure_usage_chart(customers, usage):
    reference_date = pd.Timestamp("2024-12-31")
    customers = customers.copy()
    customers["join_date"] = pd.to_datetime(customers["join_date"])
    customers["tenure_months"] = customers["join_date"].apply(
        lambda d: relativedelta(reference_date, d).years * 12 + relativedelta(reference_date, d).months
    )
    avg_usage = usage.groupby("customer_id")["data_gb"].mean().rename("avg_data_gb")
    merged = customers.merge(avg_usage, on="customer_id", how="inner")

    fig = px.scatter(
        merged,
        x="tenure_months",
        y="avg_data_gb",
        color="churn_yn",
        color_discrete_map={"N": COLOR_ACTIVE, "Y": COLOR_CRITICAL},
        category_orders={"churn_yn": ["N", "Y"]},
        custom_data=["customer_id", "tenure_months", "avg_data_gb", "churn_yn"],
        title="가입기간 vs 평균 데이터 사용량 (이탈 여부)",
        labels={"tenure_months": "가입기간 (개월)", "avg_data_gb": "평균 데이터 사용량 (GB)", "churn_yn": "이탈 여부"},
    )
    fig.update_traces(
        marker=dict(size=8, opacity=0.8),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>가입기간: %{customdata[1]}개월<br>"
            "평균 데이터 사용량: %{customdata[2]:.2f}GB<br>이탈 여부: %{customdata[3]}<extra></extra>"
        ),
    )
    fig.update_layout(
        xaxis=dict(gridcolor=COLOR_GRID),
        yaxis=dict(gridcolor=COLOR_GRID),
        legend_title_text="이탈 여부",
        **CHART_LAYOUT,
    )
    return fig


# ── 대시보드 레이아웃 ─────────────────────────────────────────────
st.title("고객은 왜 이탈하는가 — 이탈 원인 진단 대시보드")

total_customers = len(customers)
churned_customers = int((customers["churn_yn"] == "Y").sum())
churn_rate = churned_customers / total_customers * 100

col1, col2, col3 = st.columns(3)
col1.metric("전체 고객 수", f"{total_customers:,}")
col2.metric("이탈 고객 수", f"{churned_customers:,}")
col3.metric("전체 이탈율", f"{churn_rate:.1f}%")

st.subheader("① VOC로 본 이탈")
st.plotly_chart(build_voc_chart(customers, voc), width="stretch")

st.subheader("② 채널·만족도로 본 이탈")
st.plotly_chart(build_channel_csat_chart(consultations, satisfaction), width="stretch")

st.subheader("③ 재문의 반복으로 본 이탈")
st.plotly_chart(build_recontact_bucket_chart(consultations, customers), width="stretch")

st.subheader("④ 요금제로 본 이탈")
st.plotly_chart(build_plan_chart(customers), width="stretch")

st.subheader("⑤ 지역으로 본 이탈")
st.plotly_chart(build_region_chart(customers), width="stretch")

st.subheader("⑥ 가입기간·이용량으로 본 이탈")
st.plotly_chart(build_tenure_usage_chart(customers, usage), width="stretch")
