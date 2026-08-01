"""배포 전 로컬 스냅샷을 한 번에 새로 만드는 스크립트.

BigQuery 라이브 조회에 필요한 인증 정보(ADC 또는 서비스 계정)가 로컬에
있어야 실행할 수 있다. 배포 환경(Streamlit Cloud)에는 이 스크립트가
배포되지 않고, 여기서 만든 CSV 결과물만 커밋되어 함께 올라간다.

사용법:
    python refresh_snapshots.py

DEPLOY.md 3번 항목 참고. 이 단계는 건너뛰어도 배포 자체에는 지장 없다
(스냅샷이 오래된 것일 뿐, 없어서 깨지지는 않는다 — 이미 커밋된
data/*_snapshot.csv가 계속 쓰인다).
"""
import os

import pandas as pd
from google.cloud import bigquery

PROJECT = "sql-study-493001"   # 본인 프로젝트 ID로 변경
DATASET = "project1_day1"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

client = bigquery.Client(project=PROJECT)


def refresh_agent_snapshots():
    agent_query = f"""
    WITH agent_csat AS (
      SELECT c.agent_id, AVG(s.csat) AS avg_csat
      FROM `{PROJECT}.{DATASET}.consultations` c
      JOIN `{PROJECT}.{DATASET}.satisfaction` s ON c.consult_id = s.consult_id
      WHERE c.agent_id IS NOT NULL
      GROUP BY c.agent_id
    )
    SELECT a.agent_id, a.team, a.overtime_hours_avg, a.agent_satisfaction, ac.avg_csat
    FROM `{PROJECT}.{DATASET}.agents` a
    JOIN agent_csat ac ON a.agent_id = ac.agent_id
    """
    consult_query = f"""
    SELECT c.agent_id, a.team, a.training_completed_yn, c.is_recontact, s.csat
    FROM `{PROJECT}.{DATASET}.consultations` c
    JOIN `{PROJECT}.{DATASET}.satisfaction` s ON c.consult_id = s.consult_id
    JOIN `{PROJECT}.{DATASET}.agents` a ON c.agent_id = a.agent_id
    """
    client.query(agent_query).result().to_dataframe().to_csv(
        os.path.join(DATA_DIR, "agents_snapshot.csv"), index=False, encoding="utf-8-sig"
    )
    client.query(consult_query).result().to_dataframe().to_csv(
        os.path.join(DATA_DIR, "agent_consultations_snapshot.csv"), index=False, encoding="utf-8-sig"
    )
    print("agents_snapshot.csv / agent_consultations_snapshot.csv 갱신 완료")


def refresh_marketing_spend_snapshot():
    """채널 효율 페이지용 — marketing_spend는 읽기(SELECT)만 하고, 그
    결과를 스냅샷으로 저장한다. BigQuery에는 아무것도 쓰지 않는다
    (Day4_추가교안.md 참고 — 샌드박스 프로젝트는 DML이 막혀 있음)."""
    spend_query = f"""
    SELECT month, channel, spend, impressions, clicks, signups
    FROM `{PROJECT}.{DATASET}.marketing_spend`
    ORDER BY month, channel
    """
    client.query(spend_query).result().to_dataframe().to_csv(
        os.path.join(DATA_DIR, "marketing_spend_snapshot.csv"), index=False, encoding="utf-8-sig"
    )
    print("marketing_spend_snapshot.csv 갱신 완료")


def refresh_channel_efficiency_snapshot():
    """채널 효율(common.py의 load_channel_efficiency)이 읽는 스냅샷을
    marketing_spend·marketing_campaigns 두 테이블에서 매번 다시 계산해
    만든다. 둘 다 SELECT만 하고, BigQuery에는 쓰지 않는다.

    - spend_recent/signups_recent : marketing_campaigns의 완료
      캠페인(is_completed=TRUE)만, 3개월(2024-05~07) 전체 합
    - spend_cumulative/signups_cumulative : marketing_spend
      누적(~2024-06) + marketing_campaigns 2024-07월분(완료 여부
      무관, 전체) — marketing_spend의 월 집계 방식과 맞추기 위해
      07월만은 완료 여부를 따지지 않는다.
    """
    cumulative_base = client.query(f"""
        SELECT channel, SUM(spend) AS spend, SUM(signups) AS signups
        FROM `{PROJECT}.{DATASET}.marketing_spend`
        GROUP BY channel
    """).result().to_dataframe()

    recent = client.query(f"""
        SELECT `채널` AS channel, SUM(`실집행`) AS spend_recent, SUM(`유입건수`) AS signups_recent
        FROM `{PROJECT}.{DATASET}.marketing_campaigns`
        WHERE is_completed
        GROUP BY `채널`
    """).result().to_dataframe()

    july_all = client.query(f"""
        SELECT `채널` AS channel, SUM(`실집행`) AS spend_jul, SUM(`유입건수`) AS signups_jul
        FROM `{PROJECT}.{DATASET}.marketing_campaigns`
        WHERE `월` = '2024-07'
        GROUP BY `채널`
    """).result().to_dataframe()

    df = cumulative_base.merge(july_all, on="channel", how="left").fillna(0)
    df["spend_cumulative"] = df["spend"] + df["spend_jul"]
    df["signups_cumulative"] = df["signups"] + df["signups_jul"]
    df = df.merge(recent, on="channel", how="left").fillna(0)
    df = df[["channel", "spend_recent", "signups_recent", "spend_cumulative", "signups_cumulative"]]
    for col in df.columns[1:]:
        df[col] = df[col].astype(int)

    df.to_csv(os.path.join(DATA_DIR, "channel_efficiency_snapshot.csv"), index=False, encoding="utf-8-sig")
    print("channel_efficiency_snapshot.csv 갱신 완료")
    print(df.to_string(index=False))


if __name__ == "__main__":
    refresh_agent_snapshots()
    refresh_marketing_spend_snapshot()
    refresh_channel_efficiency_snapshot()
    print()
    print("SNAPSHOT_DATE도 common.py에서 오늘 날짜로 함께 바꿔주세요.")
