"""CAL01 소둔로 공동 검토 사이트

내 PC에서 실행:  python app.py  → http://127.0.0.1:5000
Render에서 실행: gunicorn app:app
"""

import base64
import csv
import hashlib
import io
import json
import os
import statistics
import time
from functools import wraps

from flask import Flask, Response, abort, g, jsonify, redirect, render_template, request, session, url_for

import db  # .env도 여기서 읽음

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "local-only-secret")
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 스냅샷 그림은 8MB까지

LABELS = ["1", "0", "보류"]
TRAININGS = ["포함", "제외", "미결정"]
OPERATIONS = ["미정", "운전 중", "정지", "재가동", "그 외"]
FOLDER_COLORS = ["#F59E0B", "#2563EB", "#059669", "#C2261F", "#7C3AED", "#DB2777", "#8A94A6", "#0EA5E9"]


# ---------------------------------------------------------------- DB 연결
def conn():
    if "conn" not in g:
        g.conn = db.connect()
    return g.conn


def sql(text, params=()):
    rows = db.run(conn(), text, params)
    conn().commit()
    return rows


@app.teardown_appcontext
def close_conn(error):
    c = g.pop("conn", None)
    if c is not None:
        c.close()


def setup():
    """처음 실행할 때 표를 만들고, 환경변수의 팀원 목록을 넣음"""
    c = db.connect()
    db.create_tables(c)

    members = json.loads(os.environ.get("TEAM_ACCESS_MEMBERS_JSON", "[]"))
    for m in members:
        db.run(c, """INSERT INTO members (user_id, name, code_hash, last_seen) VALUES (?, ?, ?, NULL)
                     ON CONFLICT (user_id) DO UPDATE SET name = excluded.name, code_hash = excluded.code_hash""",
               (m["userId"], m["displayName"], m["codeHash"].lower()))
    c.commit()
    c.close()


setup()


# ---------------------------------------------------------------- 로그인
def code_hash(code):
    """옛 사이트와 같은 방식: 대문자로 바꾸고 공백, 하이픈을 지운 뒤 SHA-256"""
    clean = code.upper().replace(" ", "").replace("-", "")
    return hashlib.sha256(clean.encode("utf-8")).hexdigest()


ATTEMPTS = {}  # IP별 로그인 시도 횟수 (10분에 20번까지)


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "접속 코드로 들어와 주세요."}), 401
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapper


def me():
    return session["user"]["name"]


@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0]
        count, until = ATTEMPTS.get(ip, (0, 0))
        if time.time() > until:
            count, until = 0, time.time() + 600
        count = count + 1
        ATTEMPTS[ip] = (count, until)

        if count > 20:
            error = "시도가 많아요. 10분 뒤에 다시 해 주세요."
        else:
            found = sql("SELECT user_id, name FROM members WHERE code_hash = ?", (code_hash(request.form.get("code", "")),))
            if found:
                session["user"] = {"id": found[0]["user_id"], "name": found[0]["name"]}
                session.permanent = True
                return redirect(request.args.get("next") or url_for("review"))
            error = "접속 코드를 다시 확인해 주세요."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------- 화면
@app.route("/")
@login_required
def review():
    lots = sql("SELECT lot_no, grade, start_at, end_at FROM lots ORDER BY lot_no")
    lot = request.args.get("lot") or lots[0]["lot_no"]
    view = request.args.get("view", "pinned")

    rows = sql("SELECT id, sensor, start_at, end_at, label, label_by, pinned FROM candidates WHERE lot_no = ? ORDER BY start_at", (lot,))
    pinned = []
    others = []
    for r in rows:
        if view == "todo" and r["label"]:
            continue
        if view == "done" and not r["label"]:
            continue
        if r["pinned"]:
            pinned.append(r)
        else:
            others.append(r)

    return render_template("review.html", lots=lots, lot=lot, view=view, pinned=pinned, others=others,
                           labels=LABELS, trainings=TRAININGS, operations=OPERATIONS)


@app.route("/records")
@login_required
def records():
    sort = request.args.get("sort", "new")
    author = request.args.get("author", "")
    folder = request.args.get("folder", "")

    order = {"new": "created_at DESC", "old": "created_at ASC", "title": "title ASC", "author": "author ASC, created_at DESC"}
    where = []
    params = []
    if author:
        where.append("author = ?")
        params.append(author)
    if folder == "none":
        where.append("folder_id IS NULL")
    elif folder:
        where.append("folder_id = ?")
        params.append(folder)

    text = "SELECT id, author, title, note, lot_no, sensor, start_at, end_at, folder_id, created_at FROM snapshots"
    if where:
        text = text + " WHERE " + " AND ".join(where)
    text = text + " ORDER BY " + order.get(sort, order["new"])

    snaps = sql(text, tuple(params))
    folders = sql("SELECT id, name, color FROM folders ORDER BY position")
    authors = sql("SELECT author, COUNT(*) AS n FROM snapshots GROUP BY author ORDER BY author")
    total = sql("SELECT COUNT(*) AS n FROM snapshots")[0]["n"]

    folder_by_id = {}
    for f in folders:
        folder_by_id[f["id"]] = f
    for s in snaps:
        s["folder"] = folder_by_id.get(s["folder_id"])

    return render_template("records.html", snaps=snaps, folders=folders, authors=authors, total=total,
                           sort=sort, author=author, folder=folder, colors=FOLDER_COLORS)


@app.route("/compare")
@login_required
def compare():
    lots = sql("SELECT lot_no, grade, start_at FROM lots ORDER BY lot_no")
    return render_template("compare.html", lots=lots)


# ---------------------------------------------------------------- 그래프 데이터
@app.route("/api/series")
@login_required
def api_series():
    found = sql("SELECT lot_no, grade, start_at, end_at, series FROM lots WHERE lot_no = ?", (request.args.get("lot", ""),))
    if not found:
        abort(404)
    lot = found[0]
    series = json.loads(lot["series"])

    # 제외 구간을 뺀 값으로 평균과 표준편차 (Z-score 기준선)
    stats = {}
    for sensor, values in series["sensors"].items():
        usable = []
        for v, excluded in zip(values, series["excluded"]):
            if v is not None and not excluded:
                usable.append(v)
        if len(usable) > 1:
            stats[sensor] = {"mean": statistics.fmean(usable), "std": statistics.pstdev(usable),
                             "median": statistics.median(usable)}
    return jsonify({"lot": lot["lot_no"], "grade": lot["grade"], "start": lot["start_at"], "end": lot["end_at"],
                    "time": series["time"], "excluded": series["excluded"], "sensors": series["sensors"], "stats": stats})


@app.route("/api/work-records")
@login_required
def api_work_records():
    start = request.args.get("start", "")
    end = request.args.get("end", "")
    rows = sql("SELECT kind, start_at, end_at, title, detail FROM work_records WHERE end_at >= ? AND start_at <= ? ORDER BY start_at",
               (start, end))
    return jsonify(rows)


# ---------------------------------------------------------------- 후보와 판단
@app.route("/api/candidates/<cid>")
@login_required
def api_candidate(cid):
    found = sql("SELECT * FROM candidates WHERE id = ?", (cid,))
    if not found:
        abort(404)
    item = found[0]
    item.pop("old_review", None)
    item["history"] = sql("SELECT author, created_at, action, label, training FROM history WHERE candidate_id = ? ORDER BY created_at DESC", (cid,))
    item["comments"] = sql("SELECT author, created_at, text FROM comments WHERE candidate_id = ? ORDER BY created_at", (cid,))
    return jsonify(item)


@app.route("/api/candidates/<cid>/judgment", methods=["POST"])
@login_required
def api_judgment(cid):
    data = request.get_json(force=True)
    label = data.get("label") or None
    training = data.get("training", "미결정")
    operation = data.get("operation", "미정")
    memo = data.get("memo", "")

    if label is not None and label not in LABELS:
        abort(400)
    if training not in TRAININGS or operation not in OPERATIONS:
        abort(400)

    now = db.now_text()
    label_by = me() if label else None
    sql("""UPDATE candidates SET label = ?, label_by = ?, label_note = ?, training = ?, operation = ?, memo = ?,
           updated_by = ?, updated_at = ? WHERE id = ?""",
        (label, label_by, None, training, operation, memo, me(), now, cid))
    sql("INSERT INTO history VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (db.new_id(), cid, me(), now, "판단 저장", label, training, memo))
    return jsonify({"ok": True, "label_by": label_by, "updated_at": now})


@app.route("/api/candidates/<cid>/pin", methods=["POST"])
@login_required
def api_pin(cid):
    found = sql("SELECT pinned FROM candidates WHERE id = ?", (cid,))
    if not found:
        abort(404)
    pinned = 0 if found[0]["pinned"] else 1
    sql("UPDATE candidates SET pinned = ? WHERE id = ?", (pinned, cid))
    return jsonify({"pinned": pinned})


@app.route("/api/candidates/<cid>/comments", methods=["POST"])
@login_required
def api_comment(cid):
    text = (request.get_json(force=True).get("text") or "").strip()
    if not text:
        abort(400)
    sql("INSERT INTO comments VALUES (?, ?, ?, ?, ?)", (db.new_id(), cid, me(), db.now_text(), text))
    return jsonify({"ok": True})


# ---------------------------------------------------------------- 팀원 기록 (스냅샷)
@app.route("/api/snapshots", methods=["POST"])
@login_required
def api_snapshot_create():
    data = request.get_json(force=True)
    image = None
    image_type = None
    if data.get("image", "").startswith("data:image/png;base64,"):
        image = base64.b64decode(data["image"].split(",", 1)[1])
        image_type = "image/png"

    now = db.now_text()
    context = {"lot": data.get("lot"), "channels": data.get("channels", []), "start": data.get("start"), "end": data.get("end")}
    sql("INSERT INTO snapshots VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (db.new_id(), me(), data.get("title", "").strip() or "제목 없음", data.get("note", ""), data.get("lot"),
         data.get("sensor"), data.get("start"), data.get("end"), json.dumps(context, ensure_ascii=False),
         data.get("folder") or None, 0, image_type, image, now, now))
    return jsonify({"ok": True})


@app.route("/api/snapshots/<sid>", methods=["POST"])
@login_required
def api_snapshot_update(sid):
    data = request.get_json(force=True)
    if "folder" in data:
        sql("UPDATE snapshots SET folder_id = ? WHERE id = ?", (data["folder"] or None, sid))
    if "title" in data or "note" in data:
        sql("UPDATE snapshots SET title = ?, note = ?, updated_at = ? WHERE id = ?",
            (data.get("title", ""), data.get("note", ""), db.now_text(), sid))
    return jsonify({"ok": True})


@app.route("/snapshots/<sid>/image")
@login_required
def snapshot_image(sid):
    found = sql("SELECT image, image_type FROM snapshots WHERE id = ?", (sid,))
    if not found or found[0]["image"] is None:
        abort(404)
    return Response(bytes(found[0]["image"]), mimetype=found[0]["image_type"] or "image/png",
                    headers={"Cache-Control": "private, max-age=86400"})


@app.route("/api/folders", methods=["POST"])
@login_required
def api_folder_create():
    name = (request.get_json(force=True).get("name") or "").strip()[:60]
    if not name:
        abort(400)
    count = sql("SELECT COUNT(*) AS n FROM folders")[0]["n"]
    sql("INSERT INTO folders VALUES (?, ?, ?, ?)", (db.new_id(), name, "#8A94A6", count))
    return jsonify({"ok": True})


@app.route("/api/folders/<fid>", methods=["POST"])
@login_required
def api_folder_update(fid):
    data = request.get_json(force=True)
    if data.get("color") in FOLDER_COLORS:
        sql("UPDATE folders SET color = ? WHERE id = ?", (data["color"], fid))
    if (data.get("name") or "").strip():
        sql("UPDATE folders SET name = ? WHERE id = ?", (data["name"].strip()[:60], fid))
    return jsonify({"ok": True})


# ---------------------------------------------------------------- 알림 (다른 팀원의 새 판단, 새 기록, 의견)
@app.route("/api/notifications")
@login_required
def api_notifications():
    seen = sql("SELECT last_seen FROM members WHERE user_id = ?", (session["user"]["id"],))
    last_seen = (seen[0]["last_seen"] if seen else None) or "2000-01-01 00:00:00"

    items = []
    for r in sql("SELECT h.author, h.created_at, c.lot_no, c.sensor, h.candidate_id FROM history h JOIN candidates c ON c.id = h.candidate_id "
                 "WHERE h.action = '판단 저장' AND h.author <> ? ORDER BY h.created_at DESC LIMIT 20", (me(),)):
        items.append({"time": r["created_at"], "text": r["author"] + "님이 판단을 남겼어요",
                      "sub": r["lot_no"] + " · " + r["sensor"], "link": "/?lot=" + r["lot_no"] + "#" + r["candidate_id"]})
    for r in sql("SELECT author, created_at, title FROM snapshots WHERE author <> ? ORDER BY created_at DESC LIMIT 20", (me(),)):
        items.append({"time": r["created_at"], "text": r["author"] + "님이 구간을 공유했어요", "sub": r["title"], "link": "/records"})
    for r in sql("SELECT m.author, m.created_at, c.lot_no, c.sensor FROM comments m JOIN candidates c ON c.id = m.candidate_id "
                 "WHERE m.author <> ? ORDER BY m.created_at DESC LIMIT 20", (me(),)):
        items.append({"time": r["created_at"], "text": r["author"] + "님이 의견을 남겼어요", "sub": r["lot_no"] + " · " + r["sensor"], "link": "/?lot=" + r["lot_no"]})

    items.sort(key=lambda x: x["time"], reverse=True)
    items = items[:20]
    unread = 0
    for item in items:
        item["new"] = item["time"] > last_seen
        if item["new"]:
            unread = unread + 1
    return jsonify({"unread": unread, "items": items})


@app.route("/api/notifications/read", methods=["POST"])
@login_required
def api_notifications_read():
    sql("UPDATE members SET last_seen = ? WHERE user_id = ?", (db.now_text(), session["user"]["id"]))
    return jsonify({"ok": True})


# ---------------------------------------------------------------- 검토 표 내보내기 (분석 노트북의 domain_decisions.csv 형식)
@app.route("/export/domain_decisions.csv")
@login_required
def export_decisions():
    rows = sql("SELECT id, lot_no, sensor, start_at, end_at, label, label_by, memo FROM candidates "
               "WHERE label IN ('1', '0') ORDER BY lot_no, start_at")
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["DECISION_ID", "VERSION", "LOT_NO", "SENSOR", "START", "END", "DOMAIN_LABEL", "REASON", "SOURCE"])
    for r in rows:
        first_line = ""
        for line in (r["memo"] or "").splitlines():
            if line.strip() and not line.startswith("#"):
                first_line = line.strip()
                break
        writer.writerow([r["id"], "v6", r["lot_no"], r["sensor"], r["start_at"], r["end_at"], r["label"],
                         first_line, "사이트 판단: " + (r["label_by"] or "")])
    return Response("﻿" + out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=domain_decisions_site.csv"})


@app.route("/health")
def health():
    return {"ok": True}


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
