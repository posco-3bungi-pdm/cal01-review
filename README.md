# cal01-review

소둔로(CAL01) 이상 후보를 팀이 함께 보고 판단을 남기는 검토 사이트

| 화면 | 하는 일 |
|---|---|
| 검토 | 왼쪽 1 : 오른쪽 9. 후보를 고르면 그래프에 노란색 표시, 판단 메모가 왼쪽에서 나옴 |
| 팀원 기록 | 팀원이 공유한 구간. 최신순, 오래된순, 제목순, 작성자순. 격자형, 패널형. 폴더 색 |
| LOT 나란히 비교 | 고른 LOT 수만큼 열이 생김. 세로 눈금 같음 |
| 검토 표 내보내기 | `/export/domain_decisions.csv` 판단 1, 0만 분석 노트북 형식으로 받음 |

## 만든 방식

| 부분 | 쓴 것 |
|---|---|
| 서버 | Python Flask (`app.py` 한 파일) |
| DB | 내 PC는 `local.db` (SQLite), Render는 Postgres |
| 화면 | Jinja 템플릿 + 기본 JavaScript + Chart.js |
| 배포 | Render 무료 (15분 안 쓰면 잠들고, 다시 열 때 약 1분) |

## 내 PC에서 실행

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
.venv\Scripts\python import_data.py
.venv\Scripts\python app.py
```

- `http://127.0.0.1:5000` 으로 열기
- `.env`의 `TEAM_ACCESS_MEMBERS_JSON`은 `python make_hashes.py`로 만듦 (코드는 해시로만 저장)

## Render에 올리기 (처음 한 번)

1. Render에 GitHub로 가입, `posco-3bungi-pdm/cal01-review` 저장소 접근 허용
2. New → Blueprint → 이 저장소 선택 → `render.yaml`대로 웹 서비스와 Postgres가 만들어짐
3. `TEAM_ACCESS_MEMBERS_JSON` 값을 물어보면 `make_hashes.py` 결과를 붙여 넣음
4. Postgres 화면의 External Database URL을 복사해서 내 PC `.env`의 `DATABASE_URL=`에 넣고 `python import_data.py` 실행
5. 넣은 뒤 `.env`의 `DATABASE_URL=`은 다시 비움
6. (선택) Render → `cal01-review` → Environment에 `CONTACT_EMAIL`을 넣으면 푸터에 이메일 아이콘이 생김

## 주의

| 항목 | 내용 |
|---|---|
| `import_data.py` | 표를 비우고 다시 채움. Render DB에 실행하면 팀원이 사이트에 남긴 판단도 지워짐 (실행 전에 yes를 물어봄) |
| 무료 Postgres | 만든 날부터 30일 뒤 만료 (14일 유예). 그 전에 `검토 표 내보내기`로 받아 두기 |
| 올리지 않는 것 | `.env`, `local.db`, `.venv` (`.gitignore`에 있음) |
