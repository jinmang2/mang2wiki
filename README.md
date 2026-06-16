# mang2wiki

LLM/IR 연구를 위한 **Graph 기반 지식 위키**. Notion에 쌓아둔 논문·개념 보드를 씨앗으로
가져와, 논문을 수학·코드 수준까지 정밀분석하고, related works를 그래프로 엮어
**Graph-RAG**로 잊지 않고 다시 찾을 수 있게 관리한다.

> 진실의 원천(source of truth)은 `wiki/**.md` (frontmatter + `[[wikilink]]`).
> Obsidian으로 바로 열리고, git으로 버전관리된다. Notion은 최초 import용 '씨앗'.

## 파이프라인

```
① Notion(Sources 보드) ──▶ wiki/ 마크다운 스텁      scripts/notion_ingest.py
② arxiv + 공식 코드     ──▶ 메타 채움 / 정밀분석     scripts/arxiv_fetch.py  (+ 세션에서 Opus 분석)
③ wiki/ 마크다운        ──▶ 지식 그래프 인덱스        scripts/build_graph.py  -> graph/graph.json
④ arxiv/web 주기 검색   ──▶ 공부할 거리 큐            scripts/discover.py     -> queue/to_study.md
```

## 디렉터리

```
wiki/
  topics/     상위 토픽 (is_high_level_topic). 하위 노드를 묶는 허브
  papers/     개별 논문
  concepts/   개념·기법
  _templates/ 사람이 읽는 템플릿 사본
mang2wiki/    코어 라이브러리 (models, frontmatter, notion, graph, rag)
scripts/      ①~④ 실행 스크립트
graph/        파생 그래프 인덱스 (graph.json)
queue/        공부할 거리 큐
```

## 노드 스키마 (frontmatter)

```yaml
id: colbert                # 파일명/노드 id (slug)
type: paper                # topic | paper | concept
title: "ColBERT: ..."
status: 시작 전            # 시작 전 | 분석 중 | 완료  (Notion 상태와 1:1)
category: information retrieval
arxiv: "2004.12832"
code: https://github.com/...
parents: [late-interaction]   # 상위 토픽 -> 그래프에서 subtopic_of 엣지
relations:                    # 타입별 엣지
  extends: [...]              # 선행 연구 확장
  cites: [...]                # 인용/기반
  inference: [...]            # 추론/서빙 변형 (예: SPLADE -> SPLADE-doc)
  uses: [late-interaction]    # 특정 기법/개념 사용
tags: [retrieval]
```

본문 안의 `[[id]]`는 soft reference 엣지(`references`)로 그래프에 들어간다.

## 시작하기

```bash
pip install -e .
cp .env.example .env          # NOTION_API_KEY, NOTION_DATABASE_ID 채우기

python scripts/notion_ingest.py            # ① dry-run 미리보기
python scripts/notion_ingest.py --write    #    실제 스텁 생성
python scripts/build_graph.py              # ③ 그래프 + 상태 리포트
python scripts/arxiv_fetch.py 2004.12832 --node colbert --write   # ②
python scripts/discover.py "late interaction" --write             # ④
```

## Graph-RAG

`mang2wiki.rag.GraphRAG` — 질의에 대해 키워드 점수로 시드 노드를 고르고 그래프를
N-hop 확장해 관련 노드를 모아 LLM 컨텍스트 번들을 만든다. (추후 임베딩 시드로 교체 가능)

```python
from mang2wiki.rag import GraphRAG
rag = GraphRAG("wiki")
print(rag.context("late interaction 검색 점수 계산", k=6, hops=1))
```

## 작업 원칙
- `notion_ingest`는 이미 분석을 채운 파일의 본문을 덮어쓰지 않는다(메타만 머지).
- 정밀분석(수학/코드)은 세션에서 채우고, `build_graph`로 인덱스를 갱신해 커밋.
- `dangling` 링크 = 아직 안 만든 페이지 → 다음 작성 후보.
