"""고객은 왜 이탈하는가 — 이탈 원인 진단 대시보드 강의용"""
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dateutil.relativedelta import relativedelta
from google.cloud import bigquery
from google.oauth2 import service_account
from plotly.subplots import make_subplots

st.set_page_config(page_title="고객은 왜 이탈하는가", layout="wide")

# 색상 (dataviz 스킬 팔레트)
COLOR_NEUTRAL = "#898781"
COLOR_CRITICAL = "#d03b3b"
COLOR_ACTIVE = "#0ca30c"
COLOR_GOOD = "#0ca30c"
COLOR_BAR = "#2a78d6"
COLOR_LINE = "#e34948"
COLOR_GRID = "#e1e0d9"
COLOR_HIGHLIGHT = "#2a78d6"
COLOR_NEGATIVE_ZONE = "#f6d9d6"
COLOR_POSITIVE_ZONE = "#e1e0d9"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

BQ_PROJECT = "sql-study-493001"
BQ_DATASET = "project1_day1"

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


def get_bigquery_client():
    """Streamlit Cloud에서는 st.secrets의 서비스 계정으로, 로컬에서는 ADC로 인증한다."""
    try:
        has_secret = "gcp_service_account" in st.secrets
    except Exception:
        has_secret = False  # secrets.toml 자체가 없는 로컬 환경

    if has_secret:
        credentials = service_account.Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"])
        )
        return bigquery.Client(project=BQ_PROJECT, credentials=credentials)
    return bigquery.Client(project=BQ_PROJECT)


@st.cache_data
def load_bigquery_agent_data():
    """BigQuery agents/consultations/satisfaction을 조인해 상담원 단위·상담 단위 데이터를 가져온다."""
    client = get_bigquery_client()

    agent_query = f"""
    WITH agent_csat AS (
      SELECT c.agent_id, AVG(s.csat) AS avg_csat
      FROM `{BQ_PROJECT}.{BQ_DATASET}.consultations` c
      JOIN `{BQ_PROJECT}.{BQ_DATASET}.satisfaction` s ON c.consult_id = s.consult_id
      WHERE c.agent_id IS NOT NULL
      GROUP BY c.agent_id
    )
    SELECT
      a.agent_id,
      a.team,
      a.overtime_hours_avg,
      a.agent_satisfaction,
      ac.avg_csat
    FROM `{BQ_PROJECT}.{BQ_DATASET}.agents` a
    JOIN agent_csat ac ON a.agent_id = ac.agent_id
    """

    consult_query = f"""
    SELECT
      c.agent_id,
      a.team,
      a.training_completed_yn,
      c.is_recontact,
      s.csat
    FROM `{BQ_PROJECT}.{BQ_DATASET}.consultations` c
    JOIN `{BQ_PROJECT}.{BQ_DATASET}.satisfaction` s ON c.consult_id = s.consult_id
    JOIN `{BQ_PROJECT}.{BQ_DATASET}.agents` a ON c.agent_id = a.agent_id
    """

    agent_df = client.query(agent_query).result().to_dataframe()
    consult_df = client.query(consult_query).result().to_dataframe()
    return agent_df, consult_df


def compute_enps(satisfaction_scores):
    promoters = (satisfaction_scores >= 9).sum()
    detractors = (satisfaction_scores <= 6).sum()
    return (promoters - detractors) * 100.0 / len(satisfaction_scores)


def build_enps_gauge(agent_df, title):
    enps = compute_enps(agent_df["agent_satisfaction"])
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=enps,
            title={"text": title, "font": {"size": 18}},
            number={"font": {"size": 36, "color": COLOR_CRITICAL if enps < 0 else COLOR_GOOD}},
            gauge={
                "axis": {"range": [-100, 100]},
                "bar": {"color": COLOR_CRITICAL if enps < 0 else COLOR_GOOD},
                "steps": [
                    {"range": [-100, 0], "color": COLOR_NEGATIVE_ZONE},
                    {"range": [0, 100], "color": COLOR_POSITIVE_ZONE},
                ],
                "threshold": {"line": {"color": "#52514e", "width": 2}, "thickness": 0.8, "value": 0},
            },
        )
    )
    fig.update_layout(height=280, margin=dict(l=30, r=30, t=50, b=10), **CHART_LAYOUT)
    return fig


def build_burnout_csat_chart(agent_df, title):
    fig = px.scatter(
        agent_df,
        x="overtime_hours_avg",
        y="avg_csat",
        trendline="ols" if agent_df["overtime_hours_avg"].nunique() >= 2 else None,
        custom_data=["agent_id", "overtime_hours_avg", "avg_csat"],
        title=title,
        labels={"overtime_hours_avg": "초과근무 시간 (평균, 시간)", "avg_csat": "CSAT 평균"},
    )
    fig.update_traces(
        selector=dict(mode="markers"),
        marker=dict(size=10, color=COLOR_HIGHLIGHT, opacity=0.85),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>초과근무: %{customdata[1]}시간<br>CSAT 평균: %{customdata[2]:.2f}<extra></extra>"
        ),
    )
    fig.update_traces(selector=dict(mode="lines"), line=dict(color=COLOR_CRITICAL, width=2))
    if agent_df["overtime_hours_avg"].nunique() >= 2 and agent_df["overtime_hours_avg"].std() > 0:
        r = agent_df["overtime_hours_avg"].corr(agent_df["avg_csat"])
        fig.add_annotation(
            xref="paper", yref="paper", x=0.98, y=0.98,
            text=f"r = {r:.2f}", showarrow=False, font=dict(size=14),
        )
    fig.update_layout(xaxis=dict(gridcolor=COLOR_GRID), yaxis=dict(gridcolor=COLOR_GRID), **CHART_LAYOUT)
    return fig


def build_training_compare_chart(consult_df, title):
    summary = (
        consult_df.groupby("training_completed_yn")
        .agg(n=("csat", "count"), avg_csat=("csat", "mean"), recontact_rate=("is_recontact", "mean"))
        .reset_index()
    )
    summary["recontact_rate"] *= 100
    summary["label"] = summary["training_completed_yn"].map({True: "Y (이수)", False: "N (미이수)"})
    summary = summary.sort_values("training_completed_yn", ascending=False)
    bar_colors = summary["label"].map({"Y (이수)": COLOR_HIGHLIGHT, "N (미이수)": COLOR_NEUTRAL})

    fig = make_subplots(rows=1, cols=2, subplot_titles=("CSAT 평균", "재문의율 평균 (%)"))
    fig.add_trace(
        go.Bar(
            x=summary["label"], y=summary["avg_csat"], marker_color=bar_colors,
            text=summary["avg_csat"].map(lambda v: f"{v:.2f}"), textposition="outside", showlegend=False,
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Bar(
            x=summary["label"], y=summary["recontact_rate"], marker_color=bar_colors,
            text=summary["recontact_rate"].map(lambda v: f"{v:.1f}%"), textposition="outside", showlegend=False,
        ),
        row=1, col=2,
    )
    fig.update_yaxes(range=[0, summary["avg_csat"].max() * 1.3], gridcolor=COLOR_GRID, row=1, col=1)
    fig.update_yaxes(range=[0, summary["recontact_rate"].max() * 1.3], gridcolor=COLOR_GRID, row=1, col=2)
    fig.update_layout(title=title, **CHART_LAYOUT)
    return fig


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


# ── 상담원 관점: 직원만족도와 고객 경험 ────────────────────────────
st.divider()
st.subheader("상담원 관점: 직원만족도와 고객 경험")

try:
    agent_df, consult_df = load_bigquery_agent_data()
except Exception:
    agent_df, consult_df = None, None

if agent_df is None:
    st.info(
        "이 섹션은 BigQuery 인증 정보가 있는 환경에서만 표시됩니다. "
        "현재 배포 환경에는 서비스 계정 키가 등록되어 있지 않아(조직 정책으로 발급이 제한됨) "
        "이 섹션을 건너뜁니다 — 로컬에서 실행하면 정상적으로 표시됩니다."
    )
else:
    team_options = ["전체"] + sorted(agent_df["team"].unique())
    selected_team = st.selectbox("팀 선택", team_options)

    # selectbox 값이 바뀌면 app.py 전체가 위에서부터 다시 실행되고,
    # 아래 필터링 → 차트 생성이 선택된 팀 기준으로 다시 수행된다.
    if selected_team == "전체":
        filtered_agents = agent_df
        filtered_consults = consult_df
    else:
        filtered_agents = agent_df[agent_df["team"] == selected_team]
        filtered_consults = consult_df[consult_df["team"] == selected_team]

    st.caption(f"선택: {selected_team}  ·  상담원 {len(filtered_agents)}명  ·  상담 {len(filtered_consults):,}건")

    gauge_col, scatter_col = st.columns([1, 2])
    with gauge_col:
        st.plotly_chart(build_enps_gauge(filtered_agents, f"eNPS ({selected_team})"), width="stretch")
    with scatter_col:
        st.plotly_chart(
            build_burnout_csat_chart(filtered_agents, f"번아웃 vs CSAT ({selected_team})"), width="stretch"
        )

    st.plotly_chart(
        build_training_compare_chart(filtered_consults, f"교육 이수 비교 ({selected_team})"), width="stretch"
    )
