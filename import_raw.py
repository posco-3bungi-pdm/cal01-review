"""1초 원본 값을 DB에 넣기 (구간 확대에서 시간창이 2시간 이하일 때 씀)

실행 (저장소 폴더에서):
    python import_raw.py

- raw_chunks 표만 비우고 다시 채움. 팀원 판단, 의견, 기록은 건드리지 않음
- DATABASE_URL이 있으면 Render Postgres에, 없으면 local.db에 넣음
- LOT마다 한 시간씩 묶어서 저장하고, LOT 전체 평균, 표준편차(제외 구간 빼고)도 함께 저장
"""

import json
import os

import pandas as pd

import db

# ---------------------------------------------------------------- 경로 설정
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)  # Posco_Project 폴더
RAW_CSV = os.path.join(PROJECT, "pdm-project", "data", "processed", "cal01_base_v1.csv")
ENC = "utf-8-sig"

SENSORS = [
    "CLN-IN", "TC-Z1", "OP-Z1", "TC-Z2", "OP-Z2", "TC-Z3", "OP-Z3",
    "TC-Z4", "OP-Z4", "CP-Z4", "TC-Z5", "OP-Z5", "TC-Z6", "OP-Z6",
    "TC-Z7", "OP-Z7", "TC-Z8", "OP-Z8", "TC-Z9", "TC-OUT1", "TC-OUT2",
]


def main():
    conn = db.connect()
    db.create_tables(conn)
    db.run(conn, "DELETE FROM raw_chunks")
    conn.commit()

    raw = pd.read_csv(RAW_CSV, encoding=ENC, usecols=["LOT_NO", "MEAS_DT", "EXCLUDED"] + SENSORS, low_memory=False)
    raw = raw.sort_values(["LOT_NO", "MEAS_DT"])
    raw["EXCLUDED"] = raw["EXCLUDED"].astype(str) == "True"
    raw["HOUR"] = raw["MEAS_DT"].str.slice(0, 13) + ":00:00"
    print("원본 행", len(raw))

    chunk_count = 0
    for lot, part in raw.groupby("LOT_NO"):
        # 기준선용 값: 제외 구간을 뺀 평균, 표준편차(ddof=0), 중앙값 (STAT_LABEL과 같은 방식)
        usable = part[~part["EXCLUDED"]]
        stats = {}
        for sensor in SENSORS:
            values = usable[sensor].dropna()
            if len(values) > 1:
                stats[sensor] = {"mean": float(values.mean()), "std": float(values.std(ddof=0)),
                                 "median": float(values.median())}
        db.run(conn, "INSERT INTO raw_chunks VALUES (?, ?, ?)", (str(lot), "stats", json.dumps(stats)))

        for hour, chunk in part.groupby("HOUR"):
            data = {"time": chunk["MEAS_DT"].tolist(), "excluded": chunk["EXCLUDED"].tolist(), "sensors": {}}
            for sensor in SENSORS:
                values = []
                for v in chunk[sensor]:
                    values.append(None if pd.isna(v) else round(float(v), 4))
                data["sensors"][sensor] = values
            db.run(conn, "INSERT INTO raw_chunks VALUES (?, ?, ?)", (str(lot), hour, json.dumps(data)))
            chunk_count = chunk_count + 1

        conn.commit()
        print("LOT", lot, "행", len(part))

    print("한 시간 묶음", chunk_count)
    print("완료")
    conn.close()


if __name__ == "__main__":
    main()
