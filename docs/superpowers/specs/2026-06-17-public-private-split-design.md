# Sub-project A — 공개/비공개 분리 기반공사 (Design)

> 날짜: 2026-06-17
> 상태: 승인됨 (브레인스토밍)
> 출처: `mang2wikirequirements.md` §5–6, 4기둥 중 기반공사

## 배경 / 동기

mang2wiki는 Notion 씨앗 → `wiki/` 마크다운 → `graph.json` → 공부 큐로 이어지는
Graph-RAG 위키다. 요구사항(§5)상 **그래프 파일과 내가 작성한 상세 본문은 공개 git에
올라가면 안 된다.** 동시에 원격/임시 세션에서도 살아남도록 **영속 위치**가 필요하다(§6).

이 서브프로젝트는 나머지 모든 작업(B 분류 재정비 ~ F tistory 포스팅)의 **선행조건**이다.
콘텐츠가 공개 repo 밖으로 나가기 전에는 다른 작업을 안전하게 쌓을 수 없다.

## 결정 사항 (브레인스토밍에서 확정)

1. **비공개 영속 위치** = 별도 private repo `jinmang2/mang2wiki-knowledge`, git **submodule**로 연결.
2. **공개 경계** = 공개 repo엔 **코드/도구만**. 모든 wiki 콘텐츠·graph·초안은 private.
3. **private 레이아웃** = **노드별 폴더**(각 논문/개념이 자기 폴더 안에 본문·수식·snippet·초안).
4. **디컴포지션** = A를 먼저 spec→구현, B~F는 이후 각각 별도 사이클.

## A.1 두 repo 토폴로지

**공개 `mang2wiki` (현재 repo)** — 코드/도구만:
```
mang2wiki/        코어 라이브러리 (models, frontmatter, notion, graph, rag, paths)
scripts/          ①~④ 실행 스크립트
.claude/skills/   notion-ingest 등
docs/             설계 문서 (이 spec 포함)
README.md  pyproject.toml  .env.example  .gitignore
knowledge/        → submodule (mang2wiki-knowledge). 포인터만 커밋됨.
```

**비공개 `mang2wiki-knowledge` (submodule, `knowledge/`에 마운트)**:
```
wiki/{topics,papers,concepts}/<id>/index.md  (+ math.md, snippets/, tistory.md)
graph/graph.json
queue/to_study.md
.gitignore        graph/*.sqlite, graph/*.graphml 등 대용량 제외
```

공개 repo엔 `.gitmodules`(private URL)와 gitlink(커밋 SHA)만 들어간다 →
private repo가 **존재**한다는 사실만 노출되고 **내용은 0** 공개.

## A.2 노드별 폴더 구조

노드 = `index.md`를 품은 폴더. 한 개념의 모든 자산이 한 폴더에 모인다.
```
wiki/papers/colbert/
  index.md      frontmatter + 본문 (현재 colbert.md 내용 그대로 이동)
  math.md       수식 정리 (선택, 없으면 생략)
  snippets/     코드 조각 (선택)
  tistory.md    tistory 초안 (선택, 서브프로젝트 F에서 채움)
```
- `index.md`의 frontmatter 스키마는 현행 유지(id/type/title/status/category/arxiv/code/parents/relations/tags).
- 본문 내 `[[id]]` soft reference 그래프 엣지 규칙 유지.
- 그래프·큐는 노드 폴더 밖 최상위.

## A.3 경로 설정 (핵심)

하드코딩된 `wiki/`·`graph/`·`queue/` 경로를 전부 리졸버 경유로 바꾼다.

**신규 `mang2wiki/paths.py`**:
- `knowledge_dir()` → 환경변수 `MANG2WIKI_KNOWLEDGE` (기본 `./knowledge`).
- `wiki_dir()` → `knowledge_dir()/wiki`
- `graph_path()` → `knowledge_dir()/graph/graph.json`
- `queue_path()` → `knowledge_dir()/queue/to_study.md`
- `iter_nodes()` → `wiki/**/index.md` 글롭으로 노드 폴더 순회.

`.env.example`에 `MANG2WIKI_KNOWLEDGE=./knowledge` 주석 추가.

## A.4 마이그레이션 (1회 실행)

1. `gh repo create jinmang2/mang2wiki-knowledge --private`
2. 공개 repo 밖 **임시 디렉터리**(예: `/tmp/m2w-knowledge`)에 현재 `wiki/`·`graph/`·`queue/`를
   복사하며 노드별 폴더로 변환 (`wiki/papers/colbert.md` → `wiki/papers/colbert/index.md`).
3. 임시 디렉터리에서 `git init` → 커밋 → private repo로 push.
4. 공개 repo에서 원본 `wiki/`·`graph/`·`queue/`를 `git rm` 하고 커밋.
5. 공개 repo에서 `git submodule add <url> knowledge` → private repo가 `knowledge/`로 새로 clone됨.
   임시 디렉터리는 삭제.
6. scripts/skill 경로 패치 (A.5).

> 마이그레이션 스크립트는 멱등하지 않아도 됨(1회성). 단, 변환 전 파일 목록을 출력해
> 누락 검증 가능하게 한다.

## A.5 코드 변경 범위

| 파일 | 변경 |
|---|---|
| `mang2wiki/paths.py` | **신규** — 경로 리졸버 |
| `mang2wiki/graph.py` | 노드 순회를 `iter_nodes()`(index.md) 기반으로 |
| `mang2wiki/frontmatter.py` | 노드 경로=폴더/index.md 인식 (필요 시) |
| `scripts/build_graph.py` | `paths` 사용, 출력 `graph_path()` |
| `scripts/notion_ingest.py` | 스텁 출력 경로 `wiki_dir()/<type>/<id>/index.md` |
| `scripts/discover.py` | 큐 경로 `queue_path()` |
| `scripts/arxiv_fetch.py` | wiki 경로 `paths` 경유 |
| `.claude/skills/notion-ingest/SKILL.md` | 출력 경로 갱신 |
| `README.md` | 토폴로지·세팅 절차 갱신 (submodule clone 포함) |
| `pyproject.toml` | 변경 없음 |

## A.6 테스트

- `tests/test_paths.py`: `MANG2WIKI_KNOWLEDGE` 오버라이드 시 각 경로 함수가 올바른 경로 반환.
- `tests/test_graph_build.py`: 임시 `knowledge/wiki/.../index.md` 픽스처로 `build_graph`가
  노드·엣지를 포함한 `graph.json`을 생성하는지 (노드별 폴더 구조 인식 회귀 방지).
- 실행: `pytest`, 린트: `ruff check`.

## A.7 커밋 규칙 (프로젝트 표준)

- 커밋 메시지에 세션 링크(`https://claude.ai/code/...`) 줄 넣지 않음.
- "Generated with Claude / Co-authored-by: Claude" 류 서명 넣지 않음.
- 메시지는 변경 내용만 간결히.

## 비범위 (이 서브프로젝트에서 안 함)

- 분류 체계(type/tags/status) 재정의 — 서브프로젝트 B.
- 정밀분석 본문 채우기 — C.
- 관계도(extends/uses) 설계 — D.
- 주기 스케줄링 — E.
- tistory 초안 포맷/길이 — F.
```
