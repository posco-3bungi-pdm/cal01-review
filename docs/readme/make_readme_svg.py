"""README용 애니메이션 SVG: 종이 장부와 도장 스타일 (라이트는 크림 종이, 다크는 어두운 크라프트지)

실행 (저장소 루트에서):
    python docs/readme/make_readme_svg.py

- 외부 도구 없이 문자열로 SVG를 씀. 애니메이션은 SVG 표준(SMIL)이라 GitHub에서 그대로 움직임
- pdm-project(양각 카드), cal01-monitor(관제실 HUD), 조직 프로필(외부 위젯)과 다르게 줄 노트, 붙임 쪽지, 테이프, 연필 선, 도장으로 꾸밈
- 만드는 파일: hero, flow (각각 -dark.svg, -light.svg)
"""

import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SERIF = "'Nanum Myeongjo', 'Noto Serif KR', 'Apple SD Gothic Neo', serif"
SANS = "Pretendard, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Noto Sans KR', sans-serif"

THEMES = {
    "light": {"paper": "#f7f2e8", "paper2": "#efe7d8", "rule": "#d8ccb6", "margin": "#d9847a", "ink": "#2b2a33", "pencil": "#8a8378",
              "red": "#c8322b", "blue": "#2b5fb3", "gray": "#8d8a84", "note": "#f7df6a", "note_ink": "#4a3f12", "tape": "#ffffff", "shadow_a": "0.18"},
    "dark": {"paper": "#24211c", "paper2": "#2d2922", "rule": "#3d382f", "margin": "#8d5a52", "ink": "#efe7d6", "pencil": "#a89f8f",
             "red": "#ff6a5e", "blue": "#7aa6ff", "gray": "#a39f97", "note": "#e3c84a", "note_ink": "#2c2608", "tape": "#ffffff", "shadow_a": "0.5"},
}


def defs(t):
    return (
        '<defs>\n'
        '<pattern id="ruled" width="40" height="28" patternUnits="userSpaceOnUse"><line x1="0" y1="27.5" x2="40" y2="27.5" stroke="%s" stroke-width="1"/></pattern>\n'
        '<filter id="shadow" x="-10%%" y="-10%%" width="130%%" height="140%%"><feDropShadow dx="2" dy="5" stdDeviation="5" flood-color="#000" flood-opacity="%s"/></filter>\n'
        '<filter id="rough"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="1.6"/></filter>\n'
        '<filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.7" numOctaves="2" stitchTiles="stitch"/><feColorMatrix values="0 0 0 0 0.5  0 0 0 0 0.45  0 0 0 0 0.35  0 0 0 0.5 0"/></filter>\n'
        '</defs>\n' % (t["rule"], t["shadow_a"]))


def head(W, H, t, margin=True):
    s = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" font-family="%s">\n' % (W, H, W, H, SANS))
    s += defs(t)
    s += '<rect width="%d" height="%d" rx="6" fill="%s"/>\n' % (W, H, t["paper"])
    s += '<rect width="%d" height="%d" rx="6" filter="url(#grain)" opacity="0.07"/>\n' % (W, H)
    s += '<rect width="%d" height="%d" rx="6" fill="url(#ruled)"/>\n' % (W, H)
    if margin:
        s += '<line x1="96" y1="0" x2="96" y2="%d" stroke="%s" stroke-opacity="0.8" stroke-width="1.5"/>\n' % (H, t["margin"])
        for y in range(70, H - 40, 120):
            s += '<circle cx="48" cy="%d" r="9" fill="%s" stroke="%s" stroke-opacity="0.6"/>\n' % (y, t["paper2"], t["rule"])
    return s


def text(x, y, s, size, fill, weight="normal", anchor="start", serif=False, extra=""):
    fam = ' font-family="%s"' % SERIF if serif else ""
    return '<text x="%s" y="%s" font-size="%s" fill="%s" font-weight="%s" text-anchor="%s"%s %s>%s</text>\n' % (
        x, y, size, fill, weight, anchor, fam, extra, s)


def pencil_line(t, d, dur=9, t0=0.05, t1=0.25, col=None, width=2.2):
    """연필로 긋는 선: 한 바퀴마다 다시 그려짐"""
    col = col or t["pencil"]
    return ('<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" filter="url(#rough)" pathLength="100" stroke-dasharray="100" stroke-dashoffset="100">'
            '<animate attributeName="stroke-dashoffset" values="100;100;0;0" keyTimes="0;%.3f;%.3f;1" dur="%ss" repeatCount="indefinite"/></path>\n' % (d, col, width, t0, t1, dur))


def slip(t, x, y, w, h, rot=0, fill=None, tape=True):
    """종이 쪽지: 살짝 기울고 그림자, 위에 테이프"""
    fill = fill or t["paper2"]
    s = '<g transform="rotate(%s %d %d)">\n' % (rot, x + w / 2, y + h / 2)
    s += '<rect x="%d" y="%d" width="%d" height="%d" fill="%s" filter="url(#shadow)"/>\n' % (x, y, w, h, fill)
    s += '<rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="%s" stroke-opacity="0.6"/>\n' % (x, y, w, h, t["rule"])
    if tape:
        s += '<rect x="%d" y="%d" width="64" height="18" fill="%s" fill-opacity="0.45" transform="rotate(-4 %d %d)"/>\n' % (x + w / 2 - 32, y - 9, t["tape"], x + w / 2, y)
    s += "</g>" + chr(10)
    return s


def stamp(t, cx, cy, label, col, dur=9, t0=0.3, r=24, rot=-12):
    """도장: 커다랗게 떠 있다가 쾅 찍힘"""
    s = '<g transform="translate(%d %d) rotate(%d)">' % (cx, cy, rot)
    s += '<g opacity="0"><animateTransform attributeName="transform" type="scale" values="2.6;2.6;1;1" keyTimes="0;%.3f;%.3f;1" dur="%ss" repeatCount="indefinite" calcMode="spline" keySplines="0 0 1 1;0.1 0.9 0.2 1;0 0 1 1"/>' % (t0, t0 + 0.04, dur)
    s += '<animate attributeName="opacity" values="0;0;1;1" keyTimes="0;%.3f;%.3f;1" dur="%ss" repeatCount="indefinite"/>' % (t0, t0 + 0.02, dur)
    s += '<circle r="%d" fill="none" stroke="%s" stroke-width="3" filter="url(#rough)"/>' % (r, col)
    s += '<circle r="%d" fill="none" stroke="%s" stroke-width="1" stroke-opacity="0.7"/>' % (r - 5, col)
    s += '<text y="%d" font-size="%d" font-weight="bold" fill="%s" text-anchor="middle" font-family="%s">%s</text>' % (r * 0.36, int(r * 0.95) if len(label) == 1 else int(r * 0.6), col, SERIF, label)
    s += "</g></g>\n"
    return s


def sticky(t, x, y, w, h, lines, rot=-3):
    s = '<g transform="rotate(%s %d %d)">' % (rot, x + w / 2, y + h / 2)
    s += '<rect x="%d" y="%d" width="%d" height="%d" fill="%s" filter="url(#shadow)"/>\n' % (x, y, w, h, t["note"])
    s += '<path d="M %d %d L %d %d L %d %d Z" fill="#000" fill-opacity="0.08"/>\n' % (x + w - 22, y + h, x + w, y + h - 22, x + w, y + h)
    for i, line in enumerate(lines):
        s += text(x + 14, y + 26 + i * 20, line, 13, t["note_ink"], "bold" if i == 0 else "normal")
    s += "</g>\n"
    return s


def write(name, theme, body):
    path = os.path.join(HERE, "%s-%s.svg" % (name, theme))
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    print("wrote", os.path.relpath(path))


# ---------------------------------------------------------------- 1. 머리: 검토 노트
def hero(theme):
    t = THEMES[theme]
    W, H = 1200, 420
    s = head(W, H, t)
    s += text(124, 52, "CAL01 공동 검토 노트", 13, t["pencil"], extra='letter-spacing="3"')
    s += text(124, 112, "같은 구간을 보고,", 42, t["ink"], "bold", serif=True)
    s += text(124, 164, "판단을 함께 남김", 42, t["red"], "bold", serif=True)
    s += pencil_line(t, "M 124 176 C 200 170, 300 182, 470 174", t0=0.04, t1=0.16, col=t["red"], width=3)
    s += text(124, 200, "3σ 후보와 모델 후보를 LOT 그래프 위에 띄우고, 팀원이 1 · 0 · 보류와 메모를 남김", 14, t["pencil"])
    s += text(124, 222, "그 판단이 검토 표(domain_decisions.csv)가 되어 pdm-project의 다음 정답으로 돌아감", 14, t["pencil"])

    # 오른쪽: 검토 쪽지
    x, y, w, h = 780, 54, 360, 230
    s += slip(t, x, y, w, h, rot=2)
    s += '<g transform="rotate(2 %d %d)">\n' % (x + w / 2, y + h / 2)
    s += text(x + 22, y + 36, "검토 #T01", 16, t["ink"], "bold", serif=True)
    s += text(x + w - 22, y + 36, "LOT 069 · CP-Z4", 13, t["pencil"], anchor="end")
    s += text(x + 22, y + 64, "7/8 02:28 ~ 02:42 · 14분 · CP 0.45 → 0.88", 13, t["ink"])
    s += text(x + 22, y + 90, "메모: 2시간 뒤 전기 BM 절연 저하, O링 교체", 12.5, t["pencil"])
    s += '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-opacity="0.8"/>\n' % (x + 22, y + 106, x + w - 22, y + 106, t["rule"])
    s += text(x + 22, y + 134, "판단", 13, t["pencil"])
    for i, (label, col) in enumerate([("1", t["red"]), ("0", t["blue"]), ("보류", t["gray"])]):
        cx = x + 110 + i * 92
        s += '<circle cx="%d" cy="%d" r="24" fill="none" stroke="%s" stroke-opacity="0.5" stroke-dasharray="3 3"/>\n' % (cx, y + 150, t["rule"])
        s += text(cx, y + 190, label, 12, t["pencil"], anchor="middle")
    s += stamp(t, x + 110, y + 150, "1", t["red"], t0=0.32)
    s += text(x + 22, y + h - 18, "판단자: 박민호 · 2026-10-20", 11.5, t["pencil"])
    s += "</g>\n"
    s += sticky(t, 640, 250, 150, 70, ["노란 구간", "= 후보 시각"], rot=-5)

    # 아래: 검토 칸 60개가 차례로 체크됨
    bx, by, cell, gap = 124, 300, 30, 6
    s += text(bx, by - 12, "모델 후보 60건 · 팀이 하나씩 확인", 12, t["pencil"])
    marks = ["1", "0", "0", "보", "0", "1", "0", "0", "0", "보"]
    for i in range(30):
        x0 = bx + i * (cell + gap)
        s += '<rect x="%d" y="%d" width="%d" height="%d" fill="%s" stroke="%s" stroke-opacity="0.8"/>\n' % (x0, by, cell, cell, t["paper2"], t["rule"])
        m = marks[i % len(marks)]
        col = t["red"] if m == "1" else (t["blue"] if m == "0" else t["gray"])
        t0 = 0.45 + i * 0.016
        s += ('<text x="%d" y="%d" font-size="%d" font-weight="bold" fill="%s" text-anchor="middle" font-family="%s" opacity="0">'
              '<animate attributeName="opacity" values="0;0;1;1" keyTimes="0;%.3f;%.3f;1" dur="9s" repeatCount="indefinite"/>%s</text>\n'
              % (x0 + cell / 2, by + 21, 15 if m != "보" else 12, col, SERIF, t0, t0 + 0.01, m))
    s += text(bx + 30 * (cell + gap) + 8, by + 21, "… 60", 13, t["pencil"])
    s += pencil_line(t, "M %d %d L %d %d" % (bx, by + cell + 14, bx + 30 * (cell + gap) - 6, by + cell + 14), t0=0.9, t1=0.98, width=1.6)
    s += text(bx, by + cell + 36, "검토 표 → 정답 v7 · 판단자가 \"AI 제안\"인 것은 팀이 확인해 이름을 바꾼 것만 넣음", 12, t["pencil"])
    s += "</svg>\n"
    write("hero", theme, s)


# ---------------------------------------------------------------- 2. 흐름: 쪽지 네 장
def flow(theme):
    t = THEMES[theme]
    W, H = 1200, 360
    s = head(W, H, t, margin=False)
    s += text(56, 44, "후보가 들어와 정답으로 돌아가는 길", 20, t["ink"], "bold", serif=True)
    slips = [("후보 들어옴", ["3σ 통계 후보 (06 노트북)", "모델 후보 60건 (12 노트북)", "import_candidates.py"], -2, t["blue"]),
             ("검토 화면", ["LOT 그래프 위 노란 구간", "채널, 시간창, 라벨 띠", "정비 기록 줄, 1초 원본"], 1.5, t["pencil"]),
             ("팀 판단", ["1 · 0 · 보류와 메모", "팀원 의견, 수정 이력", "팀 알림"], -1, t["red"]),
             ("검토 표", ["export_candidates.py", "domain_decisions.csv", "VERSION v6, v7"], 2, t["blue"])]
    sw, sh, y0 = 236, 168, 76
    xs = [56, 356, 656, 956]
    for (title, lines, rot, col), x in zip(slips, xs):
        s += slip(t, x, y0, sw, sh, rot=rot)
        s += '<g transform="rotate(%s %d %d)">\n' % (rot, x + sw / 2, y0 + sh / 2)
        s += text(x + 18, y0 + 40, title, 19, t["ink"], "bold", serif=True)
        s += '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="2" stroke-opacity="0.7"/>\n' % (x + 18, y0 + 50, x + 18 + len(title) * 19, y0 + 50, col)
        for i, line in enumerate(lines):
            s += text(x + 18, y0 + 82 + i * 26, line, 13, t["ink"])
        s += "</g>\n"
    # 쪽지 사이 연필 화살표
    for i in range(3):
        xa, xb = xs[i] + sw + 8, xs[i + 1] - 8
        ym = y0 + sh / 2
        d = "M %d %d C %d %d, %d %d, %d %d" % (xa, ym, xa + 20, ym - 18, xb - 20, ym + 14, xb, ym)
        s += pencil_line(t, d, t0=0.1 + i * 0.12, t1=0.2 + i * 0.12, width=2.4)
        s += ('<polyline points="%d,%d %d,%d %d,%d" fill="none" stroke="%s" stroke-width="2.4" stroke-linecap="round" opacity="0">'
              '<animate attributeName="opacity" values="0;0;1;1" keyTimes="0;%.3f;%.3f;1" dur="9s" repeatCount="indefinite"/></polyline>\n'
              % (xb - 12, ym - 9, xb, ym, xb - 12, ym + 9, t["pencil"], 0.2 + i * 0.12, 0.21 + i * 0.12))
    # 도장: 다음 정답
    s += stamp(t, 1120, y0 + 24, "v7", t["red"], t0=0.56, r=30, rot=14)
    # 되돌아가는 점선: 두 번째 바퀴
    d = "M %d %d C %d %d, %d %d, %d %d" % (xs[3] + sw / 2, y0 + sh + 14, xs[3] + sw / 2, y0 + sh + 90, xs[0] + sw / 2, y0 + sh + 90, xs[0] + sw / 2, y0 + sh + 14)
    s += '<path d="%s" fill="none" stroke="%s" stroke-width="2" stroke-dasharray="2 7" stroke-linecap="round"/>\n' % (d, t["pencil"])
    s += pencil_line(t, d, t0=0.62, t1=0.9, col=t["blue"], width=2.4)
    s += text(600, y0 + sh + 92, "검토 표 → 정답 v6, v7 → 다음 후보 (두 번째 바퀴)", 13, t["blue"], "bold", anchor="middle", serif=True)
    s += "</svg>\n"
    write("flow", theme, s)


if __name__ == "__main__":
    for theme in THEMES:
        hero(theme)
        flow(theme)
