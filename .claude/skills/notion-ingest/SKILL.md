---
name: notion-ingest
description: >-
  Notion 'Sources' 보드(data source)를 읽어 mang2wiki의 wiki/ 마크다운 스텁으로
  가져온다. 사용자가 "노션에서 가져와줘 / 보드 동기화 / 새 논문 import / notion ingest"
  등을 요청하거나, 새 위키 항목을 Notion 씨앗에서 시작하려 할 때 사용. 이미 분석을 채운
  페이지의 본문은 보존하고 메타데이터(status/category/tags)만 갱신한다.
---

# notion-ingest

Notion 보드를 mang2wiki 위키의 씨앗으로 끌어오는 스킬. 진실의 원천은 `wiki/**.md`이고
Notion은 단방향 import 소스다(되쓰지 않음).

구현 본체는 레포 안에 있다 — 이 스킬은 그 실행을 오케스트레이션한다:
- 라이브러리: `mang2wiki/notion.py` (타입 리졸버 + data_sources API)
- 스크립트: `scripts/notion_ingest.py`

## 사전 조건 (한 번만)

1. 의존성: `pip install -e .` (notion-client, pyyaml, networkx, rich, python-dotenv 등)
2. `.env` 작성 (`.env.example` 참고):
   - `NOTION_API_KEY` — Notion internal integration 토큰
   - `NOTION_DATA_SOURCE_ID` — 신형 API의 data source ID (권장)
     - 없으면 구형 폴백으로 `NOTION_DATABASE_ID` 사용 가능
   - integration을 대상 보드에 **Connections로 연결**해야 읽힘
3. data source ID를 모르면: `databases.retrieve(database_id)` 응답의
   `data_sources[].id`에서 얻거나 사용자에게 요청.

## 실행 절차

항상 **dry-run 먼저**, 결과를 사용자와 확인한 뒤 `--write`:

```bash
python scripts/notion_ingest.py                    # 1) dry-run 미리보기
python scripts/notion_ingest.py --write            # 2) 실제 스텁 생성/갱신
python scripts/build_graph.py                      # 3) 그래프 인덱스 재생성
```

옵션:
- `--write` : 실제 파일 생성/갱신 (없으면 미리보기만)
- `--overwrite` : 기존 **본문까지** 덮어쓰기 (주의 — 채워둔 분석이 날아감)
- `--type {guess|paper|concept|topic}` : 노드 타입 강제 (기본 guess)

## 동작 원칙 (중요)

- **본문 보존**: 이미 존재하는 파일은 frontmatter 메타(status/category/tags)만 머지하고
  본문과 사람이 손댄 분류(type/parents/relations)는 보존한다. `--overwrite` 시에만 덮어씀.
- **타입 추정**: 컬럼명을 모르므로 property '타입'으로 역할 추론
  (title→제목, status→상태, select→카테고리, multi_select→태그, url→코드 링크).
  추정이 틀리면 해당 `.md`의 frontmatter `type`을 직접 고치면 다음 ingest에서 존중됨.
- **신형/구형 자동 판별**: `NOTION_DATA_SOURCE_ID`가 있으면 `data_sources.query`,
  없고 `NOTION_DATABASE_ID`만 있으면 `databases.query` 사용.

## ingest 후 권장 흐름

1. `build_graph.py`로 dangling 링크(= 아직 안 만든 참조) 확인 → 다음 작성 후보
2. import된 스텁 중 우선순위 높은 것부터 정밀분석(수학/코드) 채우기
3. 변경분 커밋
