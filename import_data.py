"""옛 사이트 백업과 분석 데이터를 새 DB에 넣기

실행 (저장소 폴더에서):
    python import_data.py

- DATABASE_URL이 있으면 Render Postgres에, 없으면 local.db에 넣음
- 넣기 전에 표를 모두 비우고 처음부터 다시 넣음 (여러 번 실행해도 결과가 같음)
- 경로는 아래 '경로 설정'에서 바꿈
"""

import base64
import json
import os

import pandas as pd

import db

# ---------------------------------------------------------------- 경로 설정
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)  # Posco_Project 폴더
ENC = "utf-8-sig"

BACKUP_JSON = os.path.join(PROJECT, "_backup", "cal01-review-20261022", "cal01-review-backup-20261022.json")
# 백업 뒤에 옛 사이트에 올라온 팀원 기록 (10-22 17시 정수진 6개)
EXTRA_JSON = os.path.join(PROJECT, "_backup", "cal01-review-20261022", "cal01-review-extra-after-backup.json")
DATA_DIR = os.path.join(PROJECT, "pdm-project", "data")
MINUTE_CSV = os.path.join(DATA_DIR, "processed", "cal01_base_v5.csv")
DECISION_CSV = os.path.join(DATA_DIR, "labels", "domain_decisions.csv")

SENSORS = [
    "CLN-IN", "TC-Z1", "OP-Z1", "TC-Z2", "OP-Z2", "TC-Z3", "OP-Z3",
    "TC-Z4", "OP-Z4", "CP-Z4", "TC-Z5", "OP-Z5", "TC-Z6", "OP-Z6",
    "TC-Z7", "OP-Z7", "TC-Z8", "OP-Z8", "TC-Z9", "TC-OUT1", "TC-OUT2",
]


def clean_time(text):
    """'2024-01-02T04:29:22' 같은 글자를 '2024-01-02 04:29:22'로 맞춤

    끝에 Z가 붙은 시각(옛 사이트의 저장 시각, 세계 표준시)은 한국 시각으로 바꿈
    """
    if not text:
        return None
    text = str(text)
    if text.endswith("Z"):
        utc = pd.Timestamp(text).tz_convert("Asia/Seoul")
        return utc.strftime("%Y-%m-%d %H:%M:%S")
    text = text.replace("T", " ")
    if len(text) == 16:
        text = text + ":00"
    return text[:19]


def memo_from_old(review):
    """옛 판단 칸을 마크다운 메모 하나로 묶음"""
    parts = []
    if review.get("teamJudgment", "").strip(" ."):
        parts.append("## 판단\n" + review["teamJudgment"].strip())
    if review.get("facts", "").strip():
        parts.append("## 관찰\n" + review["facts"].strip())
    if review.get("references", "").strip():
        parts.append("## 근거\n" + review["references"].strip())
    study = []
    if review.get("trainingPurpose", "").strip():
        study.append(review["trainingPurpose"].strip())
    if review.get("exclusionReason", "").strip(" ㅇ"):
        study.append("제외 이유: " + review["exclusionReason"].strip())
    if study:
        parts.append("## 학습\n" + "\n".join(study))
    return "\n\n".join(parts)


def main():
    # Render DB에는 팀원이 새로 남긴 판단이 쌓이므로, 지우기 전에 한 번 더 물어봄
    if db.DATABASE_URL:
        answer = input("Render DB의 검토 기록을 모두 지우고 백업으로 다시 채웁니다. 계속하려면 yes: ")
        if answer.strip() != "yes":
            print("그만둡니다.")
            return

    conn = db.connect()
    db.create_tables(conn)

    for table in ["lots", "work_records", "candidates", "history", "comments", "folders", "snapshots"]:
        db.run(conn, "DELETE FROM " + table)
    conn.commit()

    backup = json.load(open(BACKUP_JSON, encoding="utf-8"))

    # 백업 뒤에 올라온 기록이 있으면 같이 넣음
    if os.path.isfile(EXTRA_JSON):
        extra = json.load(open(EXTRA_JSON, encoding="utf-8"))
        backup["snapshots"] = backup["snapshots"] + extra["snapshots"]
        backup["images"].update(extra["images"])
        backup["snapshotOrganization"]["organization"]["placements"] += extra["placements"]

    # ------------------------------------------------------------ 1. LOT별 1분 평균값
    minute = pd.read_csv(MINUTE_CSV, encoding=ENC, usecols=["LOT_NO", "MEAS_DT", "GRADE", "EXCLUDED"] + SENSORS)
    minute = minute.sort_values(["LOT_NO", "MEAS_DT"])

    for lot, part in minute.groupby("LOT_NO"):
        series = {"time": part["MEAS_DT"].tolist(), "excluded": part["EXCLUDED"].astype(bool).tolist(), "sensors": {}}
        for sensor in SENSORS:
            values = []
            for v in part[sensor].tolist():
                values.append(None if pd.isna(v) else round(float(v), 4))
            series["sensors"][sensor] = values

        db.run(conn, "INSERT INTO lots (lot_no, grade, start_at, end_at, series) VALUES (?, ?, ?, ?, ?)",
               (str(lot), part["GRADE"].iloc[0], part["MEAS_DT"].min(), part["MEAS_DT"].max(), json.dumps(series)))
    print("LOT", minute["LOT_NO"].nunique())

    # ------------------------------------------------------------ 2. 정비, 조업 기록
    maint = pd.read_csv(os.path.join(DATA_DIR, "G-02_정비이력.csv"), encoding=ENC)
    parts = pd.read_csv(os.path.join(DATA_DIR, "G-02_부품교체이력.csv"), encoding=ENC)
    part_names = pd.read_csv(os.path.join(DATA_DIR, "G-01_부품마스터.csv"), encoding=ENC)
    parts = parts.merge(part_names[["PART_CD", "PART_NM"]], on="PART_CD", how="left")
    events = pd.read_csv(os.path.join(DATA_DIR, "G-02_조업이벤트.csv"), encoding=ENC)
    repairs = pd.read_csv(os.path.join(DATA_DIR, "G-01_정기수리캘린더.csv"), encoding=ENC)

    count = 0
    cal = maint[maint["EQP_TAG"].str.contains("CAL01")]
    for _, w in cal.iterrows():
        used = parts[parts["WO_NO"] == w["WO_NO"]]
        part_text = ""
        for _, p in used.iterrows():
            part_text = part_text + " " + str(p["PART_NM"]) + " " + str(p["QTY"]) + "개(" + str(p["CHG_RSN"]) + ")"
        detail = w["WO_NO"] + " · 고장 유형 " + str(w["FAIL_MODE"]) + " · 정지 " + str(w["DOWN_MIN"]) + "분"
        if part_text:
            detail = detail + " · 부품:" + part_text
        title = str(w["MNT_TYPE"]) + " · " + str(w["REMARK"]).strip()

        db.run(conn, "INSERT INTO work_records VALUES (?, ?, ?, ?, ?, ?)",
               (w["WO_NO"] + "-감지", "정비 감지", clean_time(w["DETC_DT"]), clean_time(w["DETC_DT"]), title, detail))
        db.run(conn, "INSERT INTO work_records VALUES (?, ?, ?, ?, ?, ?)",
               (w["WO_NO"] + "-작업", "정비 작업", clean_time(w["STRT_DT"]), clean_time(w["END_DT"]), title, detail))
        count = count + 2

    for _, e in events[events["PLANT_CD"] == "CR1"].iterrows():
        title = e["EVT_TYPE"] + " · " + str(e["BEF_VAL"]) + " → " + str(e["AFT_VAL"])
        db.run(conn, "INSERT INTO work_records VALUES (?, ?, ?, ?, ?, ?)",
               (e["EVT_ID"], "조업", clean_time(e["EVT_DT"]), clean_time(e["EVT_DT"]), title, ""))
        count = count + 1

    for _, r in repairs[repairs["PLANT_CD"] == "CR1"].iterrows():
        db.run(conn, "INSERT INTO work_records VALUES (?, ?, ?, ?, ?, ?)",
               (r["PLAN_ID"], "정기수리", r["STRT_DT"] + " 00:00:00", r["END_DT"] + " 23:59:59", r["SCOPE"], ""))
        count = count + 1
    print("작업 기록", count)

    # ------------------------------------------------------------ 3. 후보와 옛 판단
    for c in backup["candidates"]:
        review = c["review"]
        memo = memo_from_old(review)
        db.run(conn, """INSERT INTO candidates
            (id, lot_no, sensor, start_at, end_at, reason, source, label, label_by, label_note,
             training, operation, memo, pinned, updated_by, updated_at, old_review)
            VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?, ?, 0, ?, ?, ?)""",
               (c["id"], c["lot"], c["sensor"], clean_time(c["start"]), clean_time(c["end"]),
                c["reason"], c["method"], review.get("trainingDecision", "미결정"), review.get("operationState", "미정"),
                memo, c["updatedBy"]["displayName"], clean_time(c["updatedAt"]), json.dumps(review, ensure_ascii=False)))

    history_count = 0
    for cid, value in backup["history"].items():
        for h in (value or {}).get("history", []):
            db.run(conn, "INSERT INTO history VALUES (?, ?, ?, ?, ?, NULL, ?, ?)",
                   (h["id"], cid, h["author"]["displayName"], clean_time(h["createdAt"]), h["action"],
                    h["review"].get("trainingDecision", ""), memo_from_old(h["review"])))
            history_count = history_count + 1

    comment_count = 0
    for cid, value in backup["comments"].items():
        for m in (value or {}).get("comments", []):
            db.run(conn, "INSERT INTO comments VALUES (?, ?, ?, ?, ?)",
                   (m["id"], cid, m["author"]["displayName"], clean_time(m["createdAt"]), m["text"]))
            comment_count = comment_count + 1
    print("후보", len(backup["candidates"]), "/ 이력", history_count, "/ 의견", comment_count)

    # ------------------------------------------------------------ 4. 오늘 정리한 팀 판단 (검토 표의 v6, v6_보류)
    decisions = pd.read_csv(DECISION_CSV, encoding=ENC)
    decisions = decisions[decisions["VERSION"].isin(["v6", "v6_보류"])]

    attached = 0
    created = 0
    for _, d in decisions.iterrows():
        label = str(int(d["DOMAIN_LABEL"])) if d["VERSION"] == "v6" else "보류"
        names = d["SOURCE"].replace("팀 판단: ", "")
        start = clean_time(d["START"])
        end = clean_time(d["END"])
        memo = "## 판단\n" + d["REASON"] + "\n\n_" + d["SOURCE"] + "_"

        # 같은 LOT, 센서, 시작 시각의 후보가 이미 있으면 거기에 붙이고, 없으면 새 구간을 만듦
        same = db.run(conn, "SELECT id, memo FROM candidates WHERE lot_no = ? AND sensor = ? AND start_at = ?",
                      (str(d["LOT_NO"]), d["SENSOR"], start))
        if same:
            old_memo = same[0]["memo"] or ""
            new_memo = (old_memo + "\n\n" + memo).strip()
            db.run(conn, "UPDATE candidates SET label = ?, label_by = ?, label_note = ?, memo = ? WHERE id = ?",
                   (label, names, "가져온 판단", new_memo, same[0]["id"]))
            attached = attached + 1
        else:
            db.run(conn, """INSERT INTO candidates
                (id, lot_no, sensor, start_at, end_at, reason, source, label, label_by, label_note,
                 training, operation, memo, pinned, updated_by, updated_at, old_review)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '미결정', '미정', ?, 0, ?, ?, NULL)""",
                   (d["DECISION_ID"], str(d["LOT_NO"]), d["SENSOR"], start, end, d["REASON"],
                    "팀 판단 정리 (10-22)", label, names, "가져온 판단", memo, "검토 표", db.now_text()))
            created = created + 1
    print("팀 판단: 기존 후보에 붙임", attached, "/ 새 구간", created)

    # ------------------------------------------------------------ 5. 폴더와 팀원 기록
    organization = backup["snapshotOrganization"]["organization"]
    position = 0
    for f in organization["folders"]:
        db.run(conn, "INSERT INTO folders VALUES (?, ?, ?, ?)", (f["id"], f["name"].replace("  ", " "), "#8A94A6", position))
        position = position + 1

    placement = {}
    order = 0
    for p in organization["placements"]:
        placement[p["snapshotId"]] = (p["folderId"], order)
        order = order + 1

    for s in backup["snapshots"]:
        ctx = s["context"]
        folder_id, pos = placement.get(s["id"], (None, 9999))
        image = backup["images"].get(s["id"], {})
        image_bytes = base64.b64decode(image["base64"]) if image.get("base64") else None
        db.run(conn, "INSERT INTO snapshots VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
               (s["id"], s["author"]["displayName"], s["title"], s["note"], ctx.get("lot"), ctx.get("selectedChannel"),
                clean_time(ctx.get("start")), clean_time(ctx.get("end")), json.dumps(ctx, ensure_ascii=False),
                folder_id, pos, image.get("type"), image_bytes, clean_time(s["createdAt"]), clean_time(s["updatedAt"])))
    print("폴더", len(organization["folders"]), "/ 팀원 기록", len(backup["snapshots"]))

    conn.commit()
    conn.close()
    print("완료")


if __name__ == "__main__":
    main()
