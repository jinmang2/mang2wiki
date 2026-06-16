# mang2wiki — 프로젝트 가이드

개인 지식 위키. 진실의 원천은 `wiki/**.md`이고, Notion은 단방향 import 씨앗이다.

## 커밋 규칙 (중요)

- 커밋 메시지에 **세션 링크(`https://claude.ai/code/...`)를 넣지 않는다.**
- 커밋 메시지에 **"Generated with Claude" / "Co-authored-by: Claude" 류의 서명을 넣지 않는다.**
- 메시지는 변경 내용만 간결히 기술한다.

## 구조

- `wiki/papers/`, `wiki/concepts/`, `wiki/topics/` — 노드(마크다운). frontmatter=메타, 본문=분석.
- `wiki/_templates/` — 스텁 템플릿 (그래프 빌드에서 제외).
- `mang2wiki/` — 라이브러리 (models, frontmatter, notion, graph).
- `scripts/notion_ingest.py` — Notion 보드 → 스텁. `scripts/build_graph.py` → `graph/graph.json`.

## 원칙

- ingest는 기존 파일의 **본문과 사람이 손댄 분류(type/parents/relations)를 보존**하고 메타만 머지한다.
- 본문까지 덮어쓰려면 `--overwrite` (주의).
- 노드 타입 추정이 틀리면 해당 `.md`의 frontmatter `type`을 고치면 다음 ingest에서 존중된다.
