"""모델 후보(M 번호)에 팀원이 붙인 판단을 검토 표에 VERSION v7로 더하기

실행 (저장소 폴더에서):
    python export_candidates.py

- 사이트의 "모델 후보" 중 판단자가 팀원인 것만 가져옴. 판단자가 "AI 제안"인 것은 팀 확인 전이라 넣지 않음
- 1, 0은 v7, 보류는 v7_보류로 넣음
- 검토 표(pdm-project/data/labels/domain_decisions.csv)에 이미 있는 번호는 건너뜀. 아무것도 지우지 않음
- REASON은 사이트의 판단 메모(label_note), 없으면 후보 메모의 첫 줄
"""

import csv
import os

import db

HERE = os.path.dirname(os.path.abspath(__file__))
DECISION_CSV = os.path.join(os.path.dirname(HERE), "pdm-project", "data", "labels", "domain_decisions.csv")
ENC = "utf-8-sig"
SKIP_AUTHORS = ["AI 제안", "모델 후보", ""]


def main():
    conn = db.connect()
    print("DB:", "Render Postgres" if db.DATABASE_URL else "local.db")

    rows = db.run(conn, "SELECT id, lot_no, sensor, start_at, end_at, label, label_by, label_note, memo FROM candidates "
                        "WHERE source = '모델 후보' AND label IN ('1', '0', '보류') ORDER BY id")
    conn.close()

    with open(DECISION_CSV, encoding=ENC, newline="") as f:
        existing = list(csv.DictReader(f))
    existing_ids = []
    for d in existing:
        existing_ids.append(d["DECISION_ID"])

    added = []
    skipped_ai = 0
    skipped_exist = 0
    for r in rows:
        author = (r["label_by"] or "").strip()
        if author in SKIP_AUTHORS:
            skipped_ai = skipped_ai + 1
            continue
        if r["id"] in existing_ids:
            skipped_exist = skipped_exist + 1
            continue

        reason = (r["label_note"] or "").strip()
        if not reason:
            for line in (r["memo"] or "").splitlines():
                if line.strip() and not line.startswith("#") and not line.startswith("_"):
                    reason = line.strip()
                    break

        version = "v7_보류" if r["label"] == "보류" else "v7"
        label = "" if r["label"] == "보류" else r["label"]
        added.append({"DECISION_ID": r["id"], "VERSION": version, "LOT_NO": r["lot_no"], "SENSOR": r["sensor"],
                      "START": r["start_at"], "END": r["end_at"], "DOMAIN_LABEL": label, "REASON": reason,
                      "SOURCE": "팀 판단: " + author})

    if added:
        with open(DECISION_CSV, "a", encoding=ENC, newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["DECISION_ID", "VERSION", "LOT_NO", "SENSOR", "START", "END", "DOMAIN_LABEL", "REASON", "SOURCE"],
                                    lineterminator="\r\n")
            for d in added:
                writer.writerow(d)

    print("사이트 판단:", len(rows), "/ 검토 표에 더함:", len(added), "/ AI 제안이라 뺌:", skipped_ai, "/ 이미 있음:", skipped_exist)
    for d in added:
        print(" ", d["DECISION_ID"], d["VERSION"], d["LOT_NO"], d["SENSOR"], d["DOMAIN_LABEL"], "|", d["SOURCE"])
    print("완료")


if __name__ == "__main__":
    main()
