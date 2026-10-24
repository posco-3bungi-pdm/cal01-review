"""README용 애니메이션 SVG (다크, 라이트 두 벌). pdm-project figures/readme/make_readme_svg.py와 같은 스타일

실행 (저장소 루트에서):
    python docs/readme/make_readme_svg.py
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "Pretendard, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Noto Sans KR', sans-serif"

THEMES = {
    "dark": {"bg": "#0d110e", "bg2": "#161d17", "plate": "#1a231c", "plate2": "#212c23", "deep": "#080b09",
             "ink": "#eef4ec", "sub": "#9fb39d", "accent": "#a8ff3e", "warm": "#ffb347", "hot": "#ff5a5f", "cool": "#5ec8ff",
             "hi": "#ffffff", "lo": "#000000", "hi_a": "0.10", "lo_a": "0.55", "shadow_a": "0.45", "grain_a": "0.05"},
    "light": {"bg": "#eef1ea", "bg2": "#e4e9df", "plate": "#f7f9f4", "plate2": "#eef2ea", "deep": "#d9dfd4",
              "ink": "#17221b", "sub": "#5b6b5d", "accent": "#3f8f1a", "warm": "#d9741a", "hot": "#d8323a", "cool": "#1f7fb8",
              "hi": "#ffffff", "lo": "#1a2a1e", "hi_a": "0.9", "lo_a": "0.18", "shadow_a": "0.18", "grain_a": "0.06"},
}


def defs(t):
    return (
        '<defs>\n'
        '<filter id="shadow" x="-10%%" y="-10%%" width="120%%" height="140%%"><feDropShadow dx="0" dy="8" stdDeviation="8" flood-color="#000" flood-opacity="%s"/></filter>\n'
        '<filter id="shadow-sm" x="-10%%" y="-10%%" width="120%%" height="140%%"><feDropShadow dx="0" dy="3" stdDeviation="3" flood-color="#000" flood-opacity="%s"/></filter>\n'
        '<filter id="inset" x="-10%%" y="-10%%" width="120%%" height="130%%">'
        '<feOffset dx="0" dy="3"/><feGaussianBlur stdDeviation="3" result="ob"/>'
        '<feComposite operator="out" in="SourceGraphic" in2="ob" result="inv"/>'
        '<feFlood flood-color="#000" flood-opacity="0.55" result="col"/>'
        '<feComposite operator="in" in="col" in2="inv" result="sh"/>'
        '<feComposite operator="over" in="sh" in2="SourceGraphic"/></filter>\n'
        '<filter id="glow" x="-50%%" y="-50%%" width="200%%" height="200%%"><feGaussianBlur stdDeviation="6" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>\n'
        '<filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="2" stitchTiles="stitch"/><feColorMatrix values="0 0 0 0 0.5  0 0 0 0 0.5  0 0 0 0 0.5  0 0 0 0.6 0"/></filter>\n'
        '<linearGradient id="plate" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>\n'
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>\n'
        '<radialGradient id="coin" cx="0.35" cy="0.3" r="0.8"><stop offset="0" stop-color="%s" stop-opacity="0.9"/><stop offset="0.55" stop-color="%s" stop-opacity="0"/><stop offset="1" stop-color="%s" stop-opacity="0.35"/></radialGradient>\n'
        '</defs>\n' % (t["shadow_a"], t["shadow_a"], t["plate"], t["plate2"], t["bg"], t["bg2"], t["hi"], t["hi"], t["lo"]))


def head(width, height, t):
    s = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" font-family="%s">\n'
         % (width, height, width, height, FONT))
    s += defs(t)
    s += '<rect width="%d" height="%d" rx="22" fill="url(#bg)"/>\n' % (width, height)
    s += '<rect width="%d" height="%d" rx="22" filter="url(#grain)" opacity="%s"/>\n' % (width, height, t["grain_a"])
    return s


def text(x, y, s, size, fill, weight="normal", anchor="start", extra=""):
    return '<text x="%s" y="%s" font-size="%s" fill="%s" font-weight="%s" text-anchor="%s" %s>%s</text>\n' % (
        x, y, size, fill, weight, anchor, extra, s)


def emboss_text(t, x, y, s, size, fill, weight="bold", anchor="start"):
    out = text(x + 1, y + 2, s, size, t["lo"], weight, anchor, 'opacity="%s"' % t["lo_a"])
    out += text(x - 1, y - 1, s, size, t["hi"], weight, anchor, 'opacity="%s"' % t["hi_a"])
    out += text(x, y, s, size, fill, weight, anchor)
    return out


def raised(t, x, y, w, h, r=16, fill="url(#plate)", back=True, edge=None):
    s = ""
    if back:
        s += '<rect x="%d" y="%d" width="%d" height="%d" rx="%d" fill="%s" opacity="0.55"/>\n' % (x + 10, y + 12, w, h, r, t["deep"])
    s += '<rect x="%d" y="%d" width="%d" height="%d" rx="%d" fill="%s" filter="url(#shadow)"/>\n' % (x, y, w, h, r, fill)
    if edge:
        s += '<rect x="%d" y="%d" width="%d" height="%d" rx="%d" fill="none" stroke="%s" stroke-opacity="0.55" stroke-width="1.5"/>\n' % (x, y, w, h, r, edge)
    s += '<path d="M %d %d L %d %d Q %d %d %d %d L %d %d" fill="none" stroke="%s" stroke-opacity="%s" stroke-width="1.5"/>\n' % (
        x + 1, y + h - r, x + 1, y + r, x + 1, y + 1, x + r, y + 1, x + w - r, y + 1, t["hi"], t["hi_a"])
    s += '<path d="M %d %d L %d %d Q %d %d %d %d L %d %d" fill="none" stroke="%s" stroke-opacity="%s" stroke-width="1.5"/>\n' % (
        x + r, y + h - 1, x + w - r, y + h - 1, x + w - 1, y + h - 1, x + w - 1, y + h - r, x + w - 1, y + r, t["lo"], t["lo_a"])
    return s


def inset(t, x, y, w, h, r=12, fill=None):
    fill = fill or t["deep"]
    s = '<rect x="%d" y="%d" width="%d" height="%d" rx="%d" fill="%s" filter="url(#inset)"/>\n' % (x, y, w, h, r, fill)
    s += '<path d="M %d %d L %d %d" stroke="%s" stroke-opacity="%s" stroke-width="1.5"/>\n' % (x + r, y + h + 1, x + w - r, y + h + 1, t["hi"], t["hi_a"])
    return s


def groove(t, x1, y1, x2, y2, dash=""):
    d = ' stroke-dasharray="%s"' % dash if dash else ""
    s = '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-opacity="%s" stroke-width="3"%s/>\n' % (x1, y1, x2, y2, t["lo"], t["lo_a"], d)
    s += '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-opacity="%s" stroke-width="1.5"%s/>\n' % (x1, y1 + 2, x2, y2 + 2, t["hi"], t["hi_a"], d)
    return s


def coin(t, cx, cy, r, fill, extra=""):
    s = '<circle cx="%d" cy="%d" r="%d" fill="%s" filter="url(#shadow-sm)"%s/>\n' % (cx, cy, r, fill, extra)
    s += '<circle cx="%d" cy="%d" r="%d" fill="url(#coin)"/>\n' % (cx, cy, r)
    return s


def pipe(t, x1, x2, y, col, label="", dur=1.6):
    """연결 관: 파인 홈 속을 빛 덩이가 지나가고 끝에 화살촉. label은 무엇이 흐르는지"""
    s = inset(t, x1, y - 8, x2 - x1 - 10, 16, 8)
    s += '<polygon points="%d,%d %d,%d %d,%d" fill="%s" filter="url(#shadow-sm)"/>\n' % (x2 - 14, y - 11, x2, y, x2 - 14, y + 11, col)
    for begin in [0, dur / 2]:
        s += ('<rect x="%d" y="%d" width="22" height="8" rx="4" fill="%s" filter="url(#glow)" opacity="0">'
              '<animate attributeName="x" from="%d" to="%d" dur="%ss" begin="%ss" repeatCount="indefinite"/>'
              '<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.15;0.85;1" dur="%ss" begin="%ss" repeatCount="indefinite"/></rect>\n'
              % (x1 + 2, y - 4, col, x1 + 2, x2 - 36, dur, begin, dur, begin))
    if label:
        s += text((x1 + x2) / 2 - 5, y - 16, label, 11, t["sub"], anchor="middle")
    return s


def curve_pipe(t, d, col, label="", lx=0, ly=0, dur=2.4):
    """굽은 관: 홈 선 위로 캡슐이 경로(d)를 따라 감. 화살촉은 호출 쪽에서 붙임"""
    s = '<path d="%s" fill="none" stroke="%s" stroke-opacity="%s" stroke-width="10" stroke-linecap="round"/>\n' % (d, t["lo"], t["lo_a"])
    s += '<path d="%s" fill="none" stroke="%s" stroke-opacity="%s" stroke-width="3" stroke-linecap="round"/>\n' % (d, t["hi"], t["hi_a"])
    s += '<path d="%s" fill="none" stroke="%s" stroke-opacity="0.35" stroke-width="2"/>\n' % (d, col)
    s += ('<rect x="-14" y="-4" width="28" height="8" rx="4" fill="%s" filter="url(#glow)">'
          '<animateMotion dur="%ss" repeatCount="indefinite" rotate="auto" path="%s"/></rect>\n' % (col, dur, d))
    if label:
        s += text(lx, ly, label, 11.5, col, "bold", "middle")
    return s


def up_arrow(t, x, y, col):
    return '<polygon points="%d,%d %d,%d %d,%d" fill="%s" filter="url(#shadow-sm)"/>\n' % (x - 9, y + 10, x + 9, y + 10, x, y - 4, col)


def pill(t, x, y, label, col, size=14):
    w = 26 + len(label) * size * 0.68
    s = raised(t, x, y, w, 36, 18, back=False, edge=col)
    s += coin(t, x + 18, y + 18, 7, col)
    s += text(x + 34, y + 23, label, size, t["ink"])
    return s, w


def layered_decor(t, x, y, r, col):
    s = ""
    for i, op in enumerate(["0.05", "0.08", "0.12"]):
        s += '<circle cx="%d" cy="%d" r="%d" fill="%s" opacity="%s"/>\n' % (x - i * 26, y + i * 18, r - i * 28, col, op)
    return s


def write(name, theme, body):
    path = os.path.join(HERE, "%s-%s.svg" % (name, theme))
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    print("wrote", os.path.relpath(path))


def hero(theme):
    t = THEMES[theme]
    W, H = 1200, 360
    s = head(W, H, t)
    s += layered_decor(t, 1060, 90, 190, t["warm"])
    s += layered_decor(t, 210, 350, 150, t["cool"])
    s += text(56, 78, "CAL01 · TEAM REVIEW · 소둔로 공동 검토", 15, t["sub"], extra='letter-spacing="3"')
    s += emboss_text(t, 56, 134, "같은 구간을 보고,", 40, t["ink"])
    s += emboss_text(t, 56, 186, "판단을 함께 남김", 40, t["warm"])
    s += text(56, 226, "채널 변화, 작업 기록, 팀원 판단을 한 화면에. 판단은 검토 표가 되어 다음 정답으로 돌아감", 16, t["sub"])
    x = 56
    for label, col in [("후보: 3σ 통계 + 모델 (출처 숨김)", t["cool"]), ("판단: 1 · 0 · 보류, 메모 · 고정 · 스냅샷 · 댓글", t["warm"]),
                       ("검토 표 CSV → 정답 v6, v7", t["accent"])]:
        piece, w = pill(t, x, 250, label, col)
        s += piece
        x += w + 14
    # 아래: 60분 띠 위에 판단이 찍히는 모습 (예시)
    s += inset(t, 40, 300, 1120, 44, 16)
    cell, gap, x0 = 14, 4, 56
    states = "000SS000S00000SSSS000S000000SS00S0000000SSS00000S00000000TTT"
    colors = {"0": t["plate2"], "S": t["hot"], "T": t["accent"]}
    for i, st in enumerate(states):
        cx = x0 + i * (cell + gap)
        s += '<rect x="%d" y="312" width="%d" height="20" rx="4" fill="%s" fill-opacity="%s" filter="url(#shadow-sm)">' % (cx, cell, colors[st], "0.6" if st == "0" else "0.95")
        if st in "ST":
            s += '<animate attributeName="fill-opacity" values="0.95;0.35;0.95" dur="3s" begin="%.2fs" repeatCount="indefinite"/>' % (i * 0.05)
        s += '</rect>\n'
    s += "</svg>\n"
    write("hero", theme, s)


def flow(theme):
    t = THEMES[theme]
    W, H = 1200, 400
    s = head(W, H, t)
    s += layered_decor(t, 1120, 40, 150, t["accent"])
    s += emboss_text(t, 56, 48, "후보가 들어와 판단이 되어 정답으로 돌아가는 길", 20, t["ink"])
    cards = [("1 후보가 들어옴", ["3σ 통계 후보 (v1 ~ v3, import_data)", "모델 후보 60개 (import_candidates)", "1초 원본 (import_raw)"], t["cool"]),
             ("2 검토 화면", ["LOT 고르기, 채널 고르기", "그래프에 후보 구간 노란 표시", "라벨 띠 v4 · v5 · v6, 정비 기록 줄"], t["accent"]),
             ("3 팀 판단", ["1 · 0 · 보류와 판단 메모", "고정, 댓글, 구간 스냅샷", "팀원 기록, LOT 나란히 비교"], t["warm"]),
             ("4 검토 표로", ["/export/domain_decisions.csv", "export_candidates.py (M → v7)", "pdm-project 정답 v6, v7"], t["hot"])]
    cw, ch, y0 = 238, 170, 78
    xs = [56, 339, 622, 905]
    for (title, lines, col), x in zip(cards, xs):
        s += raised(t, x, y0, cw, ch, 18)
        s += '<rect x="%d" y="%d" width="10" height="%d" rx="5" fill="%s" filter="url(#shadow-sm)"/>\n' % (x + 16, y0 + 18, ch - 36, col)
        s += '<rect x="%d" y="%d" width="3" height="%d" rx="1.5" fill="%s" opacity="0.5"/>\n' % (x + 18, y0 + 22, ch - 44, t["hi"])
        s += emboss_text(t, x + 40, y0 + 44, title, 19, t["ink"])
        s += inset(t, x + 36, y0 + 62, cw - 52, 92, 10)
        for i, line in enumerate(lines):
            s += coin(t, x + 52, y0 + 84 + i * 26, 4, col)
            s += text(x + 64, y0 + 89 + i * 26, line, 11.5, t["ink"])
    # 카드 사이 관: 무엇이 흐르는지 적음
    for x, label, col in [(294, "후보 목록", t["cool"]), (577, "노란 구간", t["accent"]), (860, "1 · 0 · 보류", t["warm"])]:
        s += pipe(t, x, x + 45, y0 + 90, col, label)
    # 되돌아오는 관: 검토 표가 정답이 되고, 새 정답으로 뽑은 다음 후보가 1번으로 들어옴
    yb = y0 + ch + 2
    d = "M 1024 %d C 1024 %d, 175 %d, 175 %d" % (yb, yb + 58, yb + 58, yb + 2)
    s += curve_pipe(t, d, t["accent"], "검토 표 CSV → 정답 v6, v7 → 다음 후보 (두 번째 바퀴)", 600, yb + 80, dur=3.0)
    s += up_arrow(t, 175, yb - 4, t["accent"])
    s += text(W / 2, 384, "판단자 이름이 그대로 남음. \"AI 제안\"은 팀이 확인해 이름을 바꾼 것만 정답에 들어감", 12, t["sub"], anchor="middle")
    s += "</svg>\n"
    write("flow", theme, s)


if __name__ == "__main__":
    for theme in THEMES:
        hero(theme)
        flow(theme)
