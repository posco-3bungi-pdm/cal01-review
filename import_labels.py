"""버전별 라벨(v4, v5, v6)을 DB에 넣기 (검토 화면의 라벨 띠)

실행 (저장소 폴더에서):
    python import_labels.py

- labels 표만 비우고 다시 채움. 팀원 판단, 의견, 기록은 건드리지 않음
- DATABASE_URL이 있으면 Render Postgres에, 없으면 local.db에 넣음
- 1분마다 구역별로 숫자 하나
    0 평소, 1 통계 1(STAT만), 2 확정 1(DOMAIN 1), 3 해제(STAT 1이었지만 DOMAIN 0), 빈칸 제외 구간
  LABEL = DOMAIN_LABEL이 있으면 DOMAIN, 없으면 STAT (모델 노트북과 같은 규칙)
"""

import json
import os

import pandas as pd

import db

# ---------------------------------------------------------------- 경로 설정
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)  # Posco_Project 폴더
PROCESSED_DIR = os.path.join(PROJECT, "pdm-project", "data", "processed")
ENC = "utf-8-sig"

VERSIONS = ["v4", "v5", "v6"]
ZONES = ["CLN", "Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8", "Z9", "COOLING"]


def label_code(stat, domain, excluded):
    if excluded:
        return None
    if domain == 1:
        return 2
    if domain == 0 and stat == 1:
        return 3
    if pd.isna(domain) and stat == 1:
        return 1
    return 0


def main():
    conn = db.connect()
    db.create_tables(conn)
    db.run(conn, "DELETE FROM labels")
    conn.commit()

    for version in VERSIONS:
        path = os.path.join(PROCESSED_DIR, "cal01_base_" + version + ".csv")
        base = pd.read_csv(path, encoding=ENC, low_memory=False)
        base = base.sort_values(["LOT_NO", "MEAS_DT"])
        base["EXCLUDED"] = base["EXCLUDED"].astype(str) == "True"

        ones = 0
        for lot, part in base.groupby("LOT_NO"):
            data = {"time": part["MEAS_DT"].tolist(), "zones": {}}
            for zone in ZONES:
                codes = []
                for stat, domain, excluded in zip(part[zone + "__STAT_LABEL"], part[zone + "__DOMAIN_LABEL"], part["EXCLUDED"]):
                    code = label_code(stat, domain, excluded)
                    codes.append(code)
                    if code == 1 or code == 2:
                        ones = ones + 1
                data["zones"][zone] = codes
            db.run(conn, "INSERT INTO labels VALUES (?, ?, ?)", (str(lot), version, json.dumps(data)))
        conn.commit()
        print(version, "LOT", base["LOT_NO"].nunique(), "/ 구역별 LABEL 1인 분 합계", ones)

    print("완료")
    conn.close()


if __name__ == "__main__":
    main()
