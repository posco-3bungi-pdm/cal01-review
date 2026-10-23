"""이미 쓰고 있는 DB에 새 기록만 더하기 (아무것도 지우지 않음)

실행 (저장소 폴더에서):
    python import_extra.py

- 백업 뒤에 옛 사이트에 올라온 팀원 기록 (EXTRA_JSON)
- 검토 표의 공통 움직임 해제(v2, v3)와 팀 판단(v6, v6_보류) (USE_VERSIONS)
- 이미 들어간 것은 건너뛰므로 여러 번 실행해도 됨
- 사이트에서 이미 다른 판단이 붙은 후보는 덮어쓰지 않고 목록으로 알려 줌
"""

import base64
import json
import os

import pandas as pd

import db
from import_data import DECISION_CSV, ENC, EXTRA_JSON, clean_time

# 사이트에 넣을 검토 표 VERSION (v6_제안은 넣지 않음)
USE_VERSIONS = ["v2", "v3", "v6", "v6_보류"]


def main():
    conn = db.connect()
    print("DB:", "Render Postgres" if db.DATABASE_URL else "local.db")

    # ------------------------------------------------------------ 1. 팀원 기록 (그림 포함)
    extra = json.load(open(EXTRA_JSON, encoding="utf-8"))

    folder_of = {}
    for p in extra["placements"]:
        folder_of[p["snapshotId"]] = p["folderId"]

    added = 0
    for s in extra["snapshots"]:
        if db.run(conn, "SELECT id FROM snapshots WHERE id = ?", (s["id"],)):
            continue
        ctx = s["context"]
        image = extra["images"][s["id"]]
        position = db.run(conn, "SELECT COUNT(*) AS n FROM snapshots")[0]["n"]
        db.run(conn, "INSERT INTO snapshots VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
               (s["id"], s["author"]["displayName"], s["title"], s["note"], ctx.get("lot"), ctx.get("selectedChannel"),
                clean_time(ctx.get("start")), clean_time(ctx.get("end")), json.dumps(ctx, ensure_ascii=False),
                folder_of.get(s["id"]), position, image["type"], base64.b64decode(image["base64"]),
                clean_time(s["createdAt"]), clean_time(s["updatedAt"])))
        added = added + 1
    print("팀원 기록: 새로", added, "/ 이미 있음", len(extra["snapshots"]) - added)

    # ------------------------------------------------------------ 2. 검토 표의 판단 (import_data.py와 같은 방식)
    decisions = pd.read_csv(DECISION_CSV, encoding=ENC)
    decisions = decisions[decisions["VERSION"].isin(USE_VERSIONS)]

    counts = {}
    conflicts = []
    for _, d in decisions.iterrows():
        version = d["VERSION"]
        if version not in counts:
            counts[version] = {"새 구간": 0, "기존 후보에 붙임": 0, "이미 있음": 0, "부딪힘": 0}

        label = str(int(d["DOMAIN_LABEL"]))
        if version == "v6_보류":
            label = "보류"
        # 판단한 사람 그대로 (공통 움직임 검토는 사람 대신 검토 이름)
        names = d["SOURCE"].replace("팀 판단: ", "")
        start = clean_time(d["START"])
        end = clean_time(d["END"])
        memo = "## 판단\n" + d["REASON"] + "\n\n_" + d["SOURCE"] + "_"

        if db.run(conn, "SELECT id FROM candidates WHERE id = ?", (d["DECISION_ID"],)):
            counts[version]["이미 있음"] = counts[version]["이미 있음"] + 1
            continue

        same = db.run(conn, "SELECT id, memo, label, label_by FROM candidates WHERE lot_no = ? AND sensor = ? AND start_at = ?",
                      (str(d["LOT_NO"]), d["SENSOR"], start))
        if same:
            old_memo = same[0]["memo"] or ""
            if memo in old_memo:
                counts[version]["이미 있음"] = counts[version]["이미 있음"] + 1
                continue

            # 사이트에서 이미 다른 판단이 붙은 후보는 덮어쓰지 않음
            if same[0]["label"] and same[0]["label"] != label:
                conflicts.append([d["DECISION_ID"], same[0]["id"], same[0]["label"], same[0]["label_by"], label])
                counts[version]["부딪힘"] = counts[version]["부딪힘"] + 1
                continue

            db.run(conn, "UPDATE candidates SET label = ?, label_by = ?, label_note = ?, memo = ? WHERE id = ?",
                   (label, names, "가져온 판단", (old_memo + "\n\n" + memo).strip(), same[0]["id"]))
            counts[version]["기존 후보에 붙임"] = counts[version]["기존 후보에 붙임"] + 1
        else:
            db.run(conn, """INSERT INTO candidates
                (id, lot_no, sensor, start_at, end_at, reason, source, label, label_by, label_note,
                 training, operation, memo, pinned, updated_by, updated_at, old_review)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '미결정', '미정', ?, 0, ?, ?, NULL)""",
                   (d["DECISION_ID"], str(d["LOT_NO"]), d["SENSOR"], start, end, d["REASON"],
                    "검토 표 (" + version + ")", label, names, "가져온 판단", memo, "검토 표", db.now_text()))
            counts[version]["새 구간"] = counts[version]["새 구간"] + 1

    for version in counts:
        print("검토 표", version, counts[version])
    for c in conflicts:
        print("부딪힘 (그대로 둠):", c[0], "→ 후보", c[1], "사이트 판단", c[2], c[3], "/ 검토 표 판단", c[4])

    conn.commit()
    conn.close()
    print("완료")


if __name__ == "__main__":
    main()
