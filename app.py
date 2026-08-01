"""고객은 왜 이탈하는가 — 이탈 원인 진단 대시보드 강의용 (st.navigation 멀티페이지)"""
import html
import re

import pandas as pd
import streamlit as st

import common as c

st.set_page_config(page_title="고객은 왜 이탈하는가", layout="wide", page_icon="📊")
c.inject_global_css()

WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)
BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
CONFIDENCE_BADGE_COLOR = {"높음": "green", "중간": "orange", "낮음": "red"}


def clean_text(text: str) -> str:
    """옵시디언 위키링크 [[x]]를 코드 스타일로, 남는 공백을 정리한다."""
    return WIKILINK_RE.sub(r"`\1`", text).strip()


def render_md(text: str):
    """clean_text 처리 후 렌더링한다. **볼드**는 마크다운 자체 파싱에 맡기지 않고
    미리 <strong> 태그로 바꿔서 넣는다 — Streamlit 마크다운 렌더러가 한 문단 안에
    볼드 구간이 여러 개 있을 때(특히 퍼센트·괄호 뒤) 일부를 문자 그대로 노출하는
    버그가 있어, 이를 우회하기 위함이다."""
    text = clean_text(text)
    rendered = BOLD_RE.sub(r"<strong>\1</strong>", text)
    st.markdown(rendered, unsafe_allow_html=True)


def confidence_badge(level: str):
    st.badge(f"confidence: {level}", color=CONFIDENCE_BADGE_COLOR.get(level, "gray"))


def parse_markdown_table(md_text: str) -> pd.DataFrame:
    """마크다운 표 문자열을 DataFrame으로 변환한다. 위키링크는 정리하고 굵게 표시는 제거한다."""
    lines = [l for l in md_text.strip().split("\n") if l.strip().startswith("|")]
    header = [clean_text(cell.strip()).replace("**", "") for cell in lines[0].strip("|").split("|")]
    rows = []
    for line in lines[2:]:
        cells = [clean_text(cell.strip()).replace("**", "") for cell in line.strip("|").split("|")]
        if len(cells) == len(header):
            rows.append(cells)
    return pd.DataFrame(rows, columns=header)


def to_html_inline(text: str) -> str:
    """순수 HTML 컨텍스트(커스텀 표 셀 등)에서 쓸 인라인 텍스트로 변환한다.
    HTML 특수문자를 이스케이프한 뒤 위키링크→<code>, **볼드**→<strong>로 바꾼다."""
    text = html.escape(text)
    text = WIKILINK_RE.sub(r"<code>\1</code>", text)
    text = BOLD_RE.sub(r"<strong>\1</strong>", text)
    return text


def render_html_table(df: pd.DataFrame, center_cols: set):
    """순위/임팩트/난이도처럼 중앙정렬이 필요한 표를 커스텀 HTML 표로 렌더링한다.
    (st.dataframe은 캔버스 기반이라 헤더 굵게·정렬을 CSS로 제어할 수 없어 직접 그린다.)"""
    headers = "".join(f"<th>{to_html_inline(col)}</th>" for col in df.columns)
    rows_html = []
    for _, row in df.iterrows():
        cells = []
        for col in df.columns:
            cls = ' class="center"' if col in center_cols else ""
            cells.append(f"<td{cls}>{to_html_inline(str(row[col]))}</td>")
        rows_html.append(f"<tr>{''.join(cells)}</tr>")
    table_html = (
        f'<table class="report-table"><thead><tr>{headers}</tr></thead>'
        f"<tbody>{''.join(rows_html)}</tbody></table>"
    )
    st.markdown(table_html, unsafe_allow_html=True)


def _render_plan_region_pair(customers):
    """4-2절 전용: 요금제·지역 차트를 나란히(같은 높이) 배치한다."""
    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(c.build_plan_chart(customers), width="stretch", config=c.PLOTLY_CONFIG)
    with col_b:
        st.plotly_chart(c.build_region_chart(customers), width="stretch", config=c.PLOTLY_CONFIG)


def split_sections(body: str) -> dict:
    """'## N. 제목' 최상위 헤더 기준으로 본문을 {번호: (제목, 내용)}로 분할한다."""
    pattern = re.compile(r"^## (\d+)\.\s+(.+)$", re.MULTILINE)
    matches = list(pattern.finditer(body))
    sections = {}
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        sections[m.group(1)] = (m.group(2).strip(), body[start:end].strip())
    return sections


# ──────────────────────────────────────────────────────────────────
# 대시보드 페이지
# ──────────────────────────────────────────────────────────────────
def dashboard_page():
    customers, voc, consultations, satisfaction, usage = c.load_data()

    c.render_hero(
        "고객은 왜 이탈하는가",
        "이탈 원인 진단 대시보드 · VOC·채널·요금제·지역·상담원 데이터를 한 곳에서 살펴봅니다",
    )

    total_customers = len(customers)
    churned_customers = int((customers["churn_yn"] == "Y").sum())
    churn_rate = churned_customers / total_customers * 100

    col1, col2, col3 = st.columns(3)
    with col1:
        c.render_stat_tile("전체 고객 수", f"{total_customers:,}")
    with col2:
        c.render_stat_tile("이탈 고객 수", f"{churned_customers:,}", status="critical")
    with col3:
        c.render_stat_tile("전체 이탈률", f"{churn_rate:.1f}%", status="critical")

    st.write("")
    st.subheader("① VOC로 본 이탈률")
    st.plotly_chart(c.build_voc_chart(customers, voc), width="stretch", config=c.PLOTLY_CONFIG)

    st.subheader("② 채널·만족도로 본 이탈률")
    st.plotly_chart(
        c.build_channel_csat_chart(consultations, satisfaction), width="stretch", config=c.PLOTLY_CONFIG
    )

    st.subheader("③ 재문의 반복으로 본 이탈률")
    st.plotly_chart(
        c.build_recontact_bucket_chart(consultations, customers), width="stretch", config=c.PLOTLY_CONFIG
    )

    st.subheader("④ 요금제로 본 이탈률")
    st.plotly_chart(c.build_plan_chart(customers), width="stretch", config=c.PLOTLY_CONFIG)

    st.subheader("⑤ 지역으로 본 이탈률")
    st.plotly_chart(c.build_region_chart(customers), width="stretch", config=c.PLOTLY_CONFIG)

    st.subheader("⑥ 가입기간·이용량으로 본 이탈분포")
    st.plotly_chart(c.build_tenure_usage_chart(customers, usage), width="stretch", config=c.PLOTLY_CONFIG)

    # ── 상담원 관점: 직원만족도와 고객 경험 ────────────────────────
    st.divider()
    st.subheader("상담원 관점: 직원만족도와 고객 경험")

    agent_df, consult_df, is_live = c.load_agent_data_with_fallback()

    if is_live:
        st.caption("🟢 BigQuery 라이브 데이터")
    else:
        st.caption(
            f"🟡 로컬 스냅샷 데이터 ({c.SNAPSHOT_DATE} 기준) — 배포 환경에 BigQuery 인증 정보가 없어 "
            "그 시점에 미리 내려받아 둔 데이터로 대체 표시 중입니다. 최신 값이 아닐 수 있습니다."
        )

    team_options = ["전체"] + sorted(agent_df["team"].unique())
    selected_team = st.selectbox("팀 선택", team_options)

    # selectbox 값이 바뀌면 이 함수가 위에서부터 다시 실행되고,
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
        st.plotly_chart(
            c.build_enps_gauge(filtered_agents, f"eNPS ({selected_team})"),
            width="stretch",
            config=c.PLOTLY_CONFIG,
        )
    with scatter_col:
        st.plotly_chart(
            c.build_burnout_csat_chart(filtered_agents, f"번아웃 vs CSAT ({selected_team})"),
            width="stretch",
            config=c.PLOTLY_CONFIG,
        )

    st.plotly_chart(
        c.build_training_compare_chart(filtered_consults, f"교육 이수 비교 ({selected_team})"),
        width="stretch",
        config=c.PLOTLY_CONFIG,
    )


# ──────────────────────────────────────────────────────────────────
# 개선 제안 리포트 페이지
# ──────────────────────────────────────────────────────────────────
def report_page():
    with st.container(key="report-page"):
        customers, voc, consultations, satisfaction, usage = c.load_data()
        raw = c.load_report_markdown()

        frontmatter_match = FRONTMATTER_RE.match(raw)
        body = raw[frontmatter_match.end():] if frontmatter_match else raw

        title_match = re.search(r"^# (.+)$", body, re.MULTILINE)
        title = title_match.group(1) if title_match else "리포트"
        body = body[title_match.end():] if title_match else body

        sections = split_sections(body)

        # ── 헤더 ──
        c.render_hero(title, "근거 → 해석 → 시사점 순서로 축적된 6개 인사이트(i-001~i-006)를 통합한 처방적 리포트")
        badge_col1, badge_col2, badge_col3, badge_col4, pdf_col = st.columns([1, 1, 1, 1, 1.4])
        with badge_col1:
            st.badge("2026-07-24 작성", icon="📅", color="gray")
        with badge_col2:
            st.badge("높음 4건", color="green")
        with badge_col3:
            st.badge("중간 1건", color="orange")
        with badge_col4:
            st.badge("낮음 1건", color="red")
        with pdf_col:
            st.download_button(
                "📄 PDF로 다운로드",
                data=c.get_report_pdf_bytes(raw),
                file_name="고객서비스_만족도개선_리포트.pdf",
                mime="application/pdf",
                width="stretch",
            )
        st.divider()

        # ── 1. Executive Summary ──
        st.header(f"1. {sections['1'][0]}")
        items = re.split(r"^\d+\.\s+", sections["1"][1], flags=re.MULTILINE)
        items = [it.strip() for it in items if it.strip()]
        summary_cols = st.columns(len(items))
        for idx, (col, item) in enumerate(zip(summary_cols, items)):
            conf_match = re.search(r"\*\*confidence\s+(\S+?)\*\*", item)
            level = conf_match.group(1) if conf_match else "중간"
            text_only = re.sub(r"\(\*\*confidence\s+\S+?\*\*\)", "", item).strip()
            with col:
                with st.container(border=True, height=220, key=f"summary-card-{idx}"):
                    confidence_badge(level)
                    render_md(text_only)

        st.divider()

        # ── 2. 배경·목적 ──
        st.header(f"2. {sections['2'][0]}")
        render_md(sections["2"][1])

        st.write("")

        # ── 3. 데이터·방법론 ──
        st.header(f"3. {sections['3'][0]}")
        text3 = sections["3"][1]
        tables3 = re.findall(r"(\|.+\|(?:\n\|.+\|)+)", text3)
        prose3 = re.sub(r"(\|.+\|(?:\n\|.+\|)+)", "\n[[TABLE]]\n", text3, count=1)
        prose3_parts = prose3.split("[[TABLE]]")
        render_md(prose3_parts[0])
        if tables3:
            st.dataframe(parse_markdown_table(tables3[0]), width="stretch", hide_index=True)
        if len(prose3_parts) > 1:
            render_md(prose3_parts[1])
        if len(tables3) > 1:
            st.dataframe(parse_markdown_table(tables3[1]), width="stretch", hide_index=True)

        st.divider()

        # ── 4. 현황 (소절마다 관련 차트 임베드) ──
        st.header(f"4. {sections['4'][0]}")
        section4 = sections["4"][1]
        sub_pattern = re.compile(r"^### (4-\d)\.\s+(.+?)\s*\(confidence:\s*(.+?)\)\s*$", re.MULTILINE)
        sub_matches = list(sub_pattern.finditer(section4))
        chart_by_subsection = {
            "4-1": lambda: st.plotly_chart(
                c.build_voc_chart(customers, voc), width="stretch", config=c.PLOTLY_CONFIG
            ),
            "4-2": lambda: _render_plan_region_pair(customers),
            "4-3": lambda: st.plotly_chart(
                c.build_channel_csat_chart(consultations, satisfaction), width="stretch", config=c.PLOTLY_CONFIG
            ),
            "4-4": lambda: st.plotly_chart(
                c.build_recontact_bucket_chart(consultations, customers), width="stretch", config=c.PLOTLY_CONFIG
            ),
            "4-5": lambda: st.plotly_chart(
                c.build_agents_reproducibility_chart(), width="stretch", config=c.PLOTLY_CONFIG
            ),
        }
        for i, m in enumerate(sub_matches):
            sub_id, sub_title, sub_conf = m.group(1), m.group(2), m.group(3)
            start = m.end()
            end = sub_matches[i + 1].start() if i + 1 < len(sub_matches) else len(section4)
            sub_body = section4[start:end].strip()

            st.subheader(f"{sub_id}. {sub_title}")
            confidence_badge(sub_conf)
            render_md(sub_body)
            renderer = chart_by_subsection.get(sub_id)
            if renderer:
                renderer()
            if i < len(sub_matches) - 1:
                st.write("")

        st.divider()

        # ── 5. 원인 분석 (카드형) ──
        st.header(f"5. {sections['5'][0]}")
        section5 = sections["5"][1]
        paragraphs = [p.strip() for p in section5.split("\n\n") if p.strip()]
        intro = [p for p in paragraphs if not p.startswith("**")]
        cards = [p for p in paragraphs if p.startswith("**")]
        for p in intro[:1]:
            render_md(p)
        # 2x2 그리드, 모든 카드 가로·세로 크기 동일
        card_cols = st.columns(2) + st.columns(2)
        icons = ["🔗", "⚙️", "💳", "🚫"]
        for i, card_text in enumerate(cards):
            lead_match = re.match(r"\*\*(.+?)\*\*\s*(.*)", card_text, re.DOTALL)
            lead = lead_match.group(1) if lead_match else ""
            rest = lead_match.group(2) if lead_match else card_text
            with card_cols[i]:
                with st.container(border=True, height=300, key=f"cause-card-{i}"):
                    st.markdown(f"### {icons[i % len(icons)]} {lead}")
                    render_md(rest)
        for p in intro[1:]:
            render_md(p)

        st.divider()

        # ── 6. 개선 제안 우선순위 (스타일 테이블) ──
        st.header(f"6. {sections['6'][0]}")
        section6 = sections["6"][1]
        tables6 = re.findall(r"(\|.+\|(?:\n\|.+\|)+)", section6)
        prose6 = re.sub(r"(\|.+\|(?:\n\|.+\|)+)", "\n[[TABLE]]\n", section6, count=2)
        prose_parts = prose6.split("[[TABLE]]")

        if prose_parts:
            render_md(prose_parts[0])
        if tables6:
            priority_df = parse_markdown_table(tables6[0])
            # 상/중/하는 순서형 3단계라 억지로 진행률 바(수치 정밀도)로 바꾸지 않고,
            # 짧은 배지 컬럼(레벨)과 근거 설명(전문)을 분리해 스캔하기 쉽게만 정리한다.
            priority_df["임팩트"] = priority_df["이탈 감소 임팩트"].str.extract(r"(상|중|하)")[0]
            priority_df["난이도"] = priority_df["실행 난이도"].str.extract(r"(상|중|하)")[0]
            priority_df = priority_df.rename(
                columns={"이탈 감소 임팩트": "임팩트 근거", "실행 난이도": "난이도 근거"}
            )
            priority_df = priority_df[["순위", "후보", "임팩트", "임팩트 근거", "난이도", "난이도 근거"]]
            render_html_table(priority_df, center_cols={"순위", "임팩트", "난이도"})
            st.caption(
                "※ 비고 요약: 1번은 임팩트·난이도 조합이 가장 좋은 퀵윈이다. 2번은 표 안에서 유일하게 "
                "채널 문제가 아니면서도 실측 이탈률에 근거한다. 3번은 근본 해결이 아니라 우회책이라 효과가 "
                "제한적일 수 있고, 4번(이메일 채널 개선)과 병행할 수 있다. 5번은 confidence가 중간 수준이라 "
                "파일럿으로 먼저 효과를 확인하는 것을 권장한다. 6·7번은 임팩트가 가장 크지만 각각 엔지니어링 "
                "부담과 외부(통신사 간 프로세스) 의존성 때문에 난이도가 높아 우선순위가 뒤로 밀렸다."
            )
        if len(prose_parts) > 1:
            render_md(prose_parts[1])
        if len(tables6) > 1:
            render_html_table(parse_markdown_table(tables6[1]), center_cols={"#"})
        if len(prose_parts) > 2:
            render_md(prose_parts[2])

        st.divider()

        # ── 7. 한계 / 8. 부록 (접이식) ──
        with st.expander(f"7. {sections['7'][0]}"):
            render_md(sections["7"][1])

        with st.expander(f"8. {sections['8'][0]}"):
            text8 = sections["8"][1]
            tables8 = re.findall(r"(\|.+\|(?:\n\|.+\|)+)", text8)
            prose8 = re.sub(r"(\|.+\|(?:\n\|.+\|)+)", "", text8)
            render_md(prose8)
            for tbl in tables8:
                st.dataframe(parse_markdown_table(tbl), width="stretch", hide_index=True)


# ──────────────────────────────────────────────────────────────────
# 채널 효율 페이지
# ──────────────────────────────────────────────────────────────────
def channel_efficiency_page():
    df = c.load_channel_efficiency()

    c.render_hero("채널 효율", "채널별 유입 1건당 비용 — 다음 분기 예산 배분의 근거")

    total_spend = df["spend_recent"].sum()
    total_signups = df["signups_recent"].sum()
    avg_cost = total_spend / total_signups

    col1, col2, col3 = st.columns(3)
    with col1:
        c.render_stat_tile("총 집행액", f"{total_spend:,.0f}원")
    with col2:
        c.render_stat_tile("총 유입", f"{total_signups:,.0f}건")
    with col3:
        c.render_stat_tile("평균 유입단가", f"{avg_cost:,.0f}원")

    st.write("")
    st.subheader("① 채널별 유입 1건당 비용")
    st.plotly_chart(c.build_channel_cost_chart(df), width="stretch", config=c.PLOTLY_CONFIG)

    st.subheader("② 최근 3개월 vs 누적 단가 비교")
    st.plotly_chart(c.build_channel_cost_compare_chart(df), width="stretch", config=c.PLOTLY_CONFIG)

    st.subheader("③ 채널별 연도별 단가 트렌드")
    monthly_df = c.load_monthly_channel_cost()
    channel_options = sorted(monthly_df["channel"].unique())
    selected_channel = st.selectbox("채널 선택", channel_options, key="trend_channel")
    st.plotly_chart(
        c.build_channel_trend_chart(monthly_df, selected_channel), width="stretch", config=c.PLOTLY_CONFIG
    )


pg = st.navigation(
    [
        st.Page(dashboard_page, title="대시보드", icon="📊", default=True),
        st.Page(report_page, title="개선 제안 리포트", icon="📄"),
        st.Page(channel_efficiency_page, title="채널 효율", icon="💰"),
    ]
)
pg.run()
