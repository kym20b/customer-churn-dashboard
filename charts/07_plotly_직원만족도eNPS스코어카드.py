"""직원만족도(eNPS) 스코어카드: 전체 게이지 + 팀별 숫자 카드 (BigQuery agents 테이블 직접 조회)"""
import plotly.graph_objects as go
from google.cloud import bigquery

# 색상 (dataviz 스킬 팔레트: 상태 색상)
COLOR_CRITICAL = "#d03b3b"
COLOR_GOOD = "#0ca30c"
COLOR_NEGATIVE_ZONE = "#f6d9d6"
COLOR_POSITIVE_ZONE = "#e1e0d9"
COLOR_TEXT_PRIMARY = "#0b0b0b"
COLOR_TEXT_SECONDARY = "#52514e"

PROJECT = "sql-study-493001"
DATASET = "project1_day1"
TABLE = "agents"

client = bigquery.Client(project=PROJECT)

query = f"""
WITH scored AS (
  SELECT
    team,
    CASE
      WHEN agent_satisfaction >= 9 THEN 'promoter'
      WHEN agent_satisfaction >= 7 THEN 'passive'
      ELSE 'detractor'
    END AS category
  FROM `{PROJECT}.{DATASET}.{TABLE}`
)
SELECT
  team,
  COUNT(*) AS n,
  ROUND((COUNTIF(category = 'promoter') - COUNTIF(category = 'detractor')) * 100.0 / COUNT(*), 1) AS enps
FROM scored
GROUP BY team
"""

rows = list(client.query(query).result())
team_enps = {row.team: row.enps for row in rows}

overall_query = f"""
SELECT
  ROUND(
    (COUNTIF(agent_satisfaction >= 9) - COUNTIF(agent_satisfaction <= 6)) * 100.0 / COUNT(*), 1
  ) AS enps
FROM `{PROJECT}.{DATASET}.{TABLE}`
"""
overall_enps = list(client.query(overall_query).result())[0].enps

teams_ordered = sorted(team_enps.keys())

fig = go.Figure()

# 큰 게이지: 전체 eNPS (-100 ~ 100, 마이너스 구간 빨간 배경)
fig.add_trace(
    go.Indicator(
        mode="gauge+number",
        value=overall_enps,
        title={"text": "전체 eNPS", "font": {"size": 20, "color": COLOR_TEXT_PRIMARY}},
        number={"font": {"size": 40, "color": COLOR_CRITICAL if overall_enps < 0 else COLOR_GOOD}},
        gauge={
            "axis": {"range": [-100, 100], "tickcolor": COLOR_TEXT_SECONDARY},
            "bar": {"color": COLOR_CRITICAL if overall_enps < 0 else COLOR_GOOD},
            "bgcolor": "white",
            "steps": [
                {"range": [-100, 0], "color": COLOR_NEGATIVE_ZONE},
                {"range": [0, 100], "color": COLOR_POSITIVE_ZONE},
            ],
            "threshold": {
                "line": {"color": COLOR_TEXT_SECONDARY, "width": 2},
                "thickness": 0.8,
                "value": 0,
            },
        },
        domain={"x": [0, 0.55], "y": [0, 1]},
    )
)

# 작은 숫자 카드 3개: 팀별 eNPS, 0.6~1.0 구간에 균등하게 나란히 배치
card_width = (1.0 - 0.60) / 3
card_x_ranges = [
    [0.60 + i * card_width, 0.60 + (i + 1) * card_width - 0.01] for i in range(3)
]

for i, team in enumerate(teams_ordered):
    value = team_enps[team]
    fig.add_trace(
        go.Indicator(
            mode="number",
            value=value,
            title={"text": team, "font": {"size": 16, "color": COLOR_TEXT_SECONDARY}},
            number={
                "suffix": "",
                "font": {"size": 28, "color": COLOR_CRITICAL if value < 0 else COLOR_GOOD},
            },
            domain={"x": card_x_ranges[i], "y": [0.35, 0.65]},
        )
    )

fig.update_layout(
    title="직원만족도(eNPS) 스코어카드",
    plot_bgcolor="#fcfcfb",
    paper_bgcolor="#fcfcfb",
    font=dict(family="Malgun Gothic, sans-serif", color=COLOR_TEXT_PRIMARY),
    height=420,
    margin=dict(l=40, r=40, t=80, b=40),
)

print(f"전체 eNPS: {overall_enps}")
for team in teams_ordered:
    print(f"{team} eNPS: {team_enps[team]}")

fig.show()
