"""모델이 고른 후보를 검토 사이트에 올리기 (아무것도 지우지 않음)

실행 (저장소 폴더에서):
    python import_candidates.py

- 12번 노트북이 만든 if_candidates.csv (CANDIDATE_CSV)를 읽음
- 사이트에는 출처(SOURCE)를 넣지 않음. 팀이 모델을 모르는 채로 판단하도록
- 이미 들어간 번호는 건너뛰므로 여러 번 실행해도 됨
"""

import csv
import os

import db

HERE = os.path.dirname(os.path.abspath(__file__))
CANDIDATE_CSV = os.path.join(os.path.dirname(HERE), "pdm-project", "data", "processed", "if_candidates.csv")
ENC = "utf-8-sig"

# 센서가 비어 있는 후보(구간 전체를 보는 후보)는 가운데 구역 온도로 그림을 열게 함
DEFAULT_SENSOR = "TC-Z4"


def main():
    conn = db.connect()
    print("DB:", "Render Postgres" if db.DATABASE_URL else "local.db")

    with open(CANDIDATE_CSV, encoding=ENC, newline="") as f:
        candidates = list(csv.DictReader(f))
    print("후보 파일:", len(candidates), "개")

    added = 0
    skipped = 0
    for c in candidates:
        if db.run(conn, "SELECT id FROM candidates WHERE id = ?", (c["CANDIDATE_ID"],)):
            skipped = skipped + 1
            continue

        sensor = c["SENSOR"] if c["SENSOR"] else DEFAULT_SENSOR
        minutes = str(int(float(c["MINUTES"])))

        # 가까운 정비 기록 (없으면 빈칸)
        maint = []
        if c["NEXT_MAINT"]:
            maint.append(c["NEXT_MAINT"])
        if c["PREV_MAINT"]:
            maint.append(c["PREV_MAINT"])
        maint_text = ", ".join(maint) if maint else "가까운 기록 없음"

        reason = "모델 후보, " + minutes + "분"
        memo = ("## 후보\n모델이 고른 구간 (" + minutes + "분)\n\n"
                "- 가까운 CAL01 정비: " + maint_text + "\n\n"
                "1, 0, 보류 중 하나를 눌러 주세요")

        db.run(conn, """INSERT INTO candidates
            (id, lot_no, sensor, start_at, end_at, reason, source, label, label_by, label_note,
             training, operation, memo, pinned, updated_by, updated_at, old_review)
            VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, '미결정', '미정', ?, 0, ?, ?, NULL)""",
               (c["CANDIDATE_ID"], c["LOT_NO"], sensor, c["START"], c["END"], reason, "모델 후보",
                memo, "모델 후보", db.now_text()))
        added = added + 1

    conn.commit()
    conn.close()
    print("새로 넣음", added, "/ 이미 있음", skipped)
    print("완료")


if __name__ == "__main__":
    main()
