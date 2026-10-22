"""팀원 접속 코드를 해시로 바꿔서 TEAM_ACCESS_MEMBERS_JSON 한 줄을 만듦

python make_hashes.py
→ 팀원별 코드를 물어보고, 마지막에 Render 환경변수에 붙여 넣을 한 줄을 보여 줌
  (코드 자체는 어디에도 저장하지 않음)
"""

import getpass
import hashlib
import json

MEMBERS = [
    ["team-minho", "박민호"],
    ["team-jungyeol", "김정렬"],
    ["team-sujin", "정수진"],
    ["team-yujin", "황유진"],
    ["team-taegu", "김태구"],
]

result = []
for user_id, name in MEMBERS:
    code = getpass.getpass(name + " 접속 코드: ")
    clean = code.upper().replace(" ", "").replace("-", "")
    result.append({"userId": user_id, "displayName": name,
                   "codeHash": hashlib.sha256(clean.encode("utf-8")).hexdigest()})

print()
print("TEAM_ACCESS_MEMBERS_JSON=" + json.dumps(result, ensure_ascii=False))
