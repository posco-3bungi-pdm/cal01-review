-- CAL01 검토 사이트 테이블
-- 시각은 모두 'YYYY-MM-DD HH:MM:SS' 글자로 저장함 (SQLite, Postgres 둘 다 같은 방식)

-- 팀원 (접속 코드는 해시로만 저장)
CREATE TABLE IF NOT EXISTS members (
    user_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    code_hash TEXT NOT NULL,
    last_seen TEXT
);

-- LOT별 1분 평균 센서값 (series는 JSON 글자)
CREATE TABLE IF NOT EXISTS lots (
    lot_no TEXT PRIMARY KEY,
    grade TEXT,
    start_at TEXT,
    end_at TEXT,
    series TEXT
);

-- 정비, 조업 기록 (그래프 아래 막대)
CREATE TABLE IF NOT EXISTS work_records (
    id TEXT PRIMARY KEY,
    kind TEXT,
    start_at TEXT,
    end_at TEXT,
    title TEXT,
    detail TEXT
);

-- 이상 후보 구간과 팀 판단
CREATE TABLE IF NOT EXISTS candidates (
    id TEXT PRIMARY KEY,
    lot_no TEXT,
    sensor TEXT,
    start_at TEXT,
    end_at TEXT,
    reason TEXT,
    source TEXT,
    label TEXT,
    label_by TEXT,
    label_note TEXT,
    training TEXT,
    operation TEXT,
    memo TEXT,
    pinned INTEGER,
    updated_by TEXT,
    updated_at TEXT,
    old_review TEXT
);

-- 판단 수정 이력
CREATE TABLE IF NOT EXISTS history (
    id TEXT PRIMARY KEY,
    candidate_id TEXT,
    author TEXT,
    created_at TEXT,
    action TEXT,
    label TEXT,
    training TEXT,
    memo TEXT
);

-- 후보에 남긴 의견
CREATE TABLE IF NOT EXISTS comments (
    id TEXT PRIMARY KEY,
    candidate_id TEXT,
    author TEXT,
    created_at TEXT,
    text TEXT
);

-- 팀원 기록 폴더
CREATE TABLE IF NOT EXISTS folders (
    id TEXT PRIMARY KEY,
    name TEXT,
    color TEXT,
    position INTEGER
);

-- 팀원이 남긴 구간 (스냅샷)
CREATE TABLE IF NOT EXISTS snapshots (
    id TEXT PRIMARY KEY,
    author TEXT,
    title TEXT,
    note TEXT,
    lot_no TEXT,
    sensor TEXT,
    start_at TEXT,
    end_at TEXT,
    context TEXT,
    folder_id TEXT,
    position INTEGER,
    image_type TEXT,
    image {BLOB},
    created_at TEXT,
    updated_at TEXT
)
;

-- 1초 원본 값 (구간 확대용). LOT별 한 시간씩 JSON 글자로 저장, hour_start='stats'는 LOT 전체 평균, 표준편차
CREATE TABLE IF NOT EXISTS raw_chunks (
    lot_no TEXT,
    hour_start TEXT,
    data TEXT,
    PRIMARY KEY (lot_no, hour_start)
)
