# Sub-project B — 분류 체계 재정비 (Design)

> 날짜: 2026-06-17
> 상태: 승인됨 (브레인스토밍)
> 출처: `mang2wikirequirements.md` §1–2, §6. 선행: 서브프로젝트 A(공개/비공개 분리) 완료.

## 배경 / 동기

현재 type(topic/paper/concept)은 arxiv 유무로 자동추정돼 신뢰할 수 없고, tags는 자유
입력이라 정합성이 없으며, status enum("분석 중")은 사용자의 실제 기준과 어긋난다.
이 서브프로젝트는 **분류 규칙을 명문화**하고, **통제 어휘 + 검증 도구(lint)**로
정합성을 점진적으로 강제한다. 자동수정은 하지 않는다(사람이 최종 결정).

콘텐츠는 A에서 private submodule(`knowledge/`)로 이전됐다. lint/도구 코드는 공개,
어휘 목록(`_taxonomy.yml`)은 비공개에 둔다.

## 결정 사항 (브레인스토밍 확정)

1. type 체계 = topic/paper/concept **유지**, 자동추정 폐기, **수동 결정** + 규칙 명문화.
2. tags = **통제 어휘(허용목록) + lint 경고**.
3. status = **자동 제안 + 수동 확정** (완료는 수동만).

## B.1 분류 규칙 (공개 `docs/classification.md`)

**type** (판정 우선순위 순):
1. **topic** — 하위 노드를 묶는 허브. 다른 노드가 `parents`로 이 노드를 가리킨다. 예: late-interaction, RL.
2. **concept** — 여러 논문/맥락에 걸쳐 재사용되는 기법·수식·메커니즘. 예: MaxSim, continuous batching, MIPS.
3. **paper** — 위에 해당하지 않는, 내가 '단일 연구 산출물' 단위로 다루는 노드. **arxiv 유무와 무관.**

판정: 허브인가? → topic. 재사용 기법인가? → concept. 그 외 단일 연구? → paper.

**status**:
- `시작 전` — 본문에 실질 내용 없음(스텁/빈 본문).
- `검토 대기 중` — 내용은 있으나 말투·정보 정리를 더 해야 함.
- `완료` — 내가 만족한 노드. **수동으로만 지정**(자동 판별 불가).

이 문서는 방법론(비민감)이므로 공개 repo `docs/classification.md`에 둔다.

## B.2 status enum 변경 (`mang2wiki/models.py`)

- `Status.IN_PROGRESS` 값을 `"분석 중"` → `"검토 대기 중"`으로 변경.
- `Status.coerce`는 하위호환 유지: `"분석 중"`, `"검토 대기 중"`, `"in progress"`, `"doing"` 모두 `IN_PROGRESS`로 매핑. (Notion 보드가 "분석 중"을 쓰더라도 깨지지 않게.)
- `TODO`(시작 전)·`DONE`(완료) 값은 불변.

## B.3 통제 어휘 + lint

**어휘 파일 (private):** `knowledge/wiki/_taxonomy.yml`
```yaml
tags:
  - retrieval
  - ranking
  - late-interaction
  - bert
```
도메인 tag 목록은 "무엇을 공부하는지"를 드러내므로 비공개 submodule에 둔다.

**`mang2wiki/taxonomy.py` (신규):**
- `taxonomy_path() -> Path` — `paths.wiki_dir() / "_taxonomy.yml"`.
- `load_allowed_tags() -> set[str]` — yml의 `tags` 목록 로드. 파일 없으면 빈 set.
- `unknown_tags(node, allowed) -> list[str]` — 노드 tags 중 허용목록 밖인 것.
- `suggest_status(node) -> Status` — 본문(body)에서 frontmatter 제외 실질 텍스트가
  비어 있으면 `시작 전`, 있으면 `검토 대기 중`. (절대 `완료`를 제안하지 않는다.)
- `status_mismatch(node) -> Status | None` — 현재 status가 `시작 전`인데 본문이 있으면
  제안값(`검토 대기 중`) 반환; 그 외(특히 `완료`·`검토 대기 중`)는 None(불일치로 보지 않음).

> "실질 텍스트 비었음" 판정: 시드 노트의 안내 인용구(`> **status**: ...`)나 빈 줄/주석만
> 있는 경우도 비었다고 본다. 구현은 마크다운에서 헤딩·인용·HTML주석·공백을 제거한 뒤
> 남는 문자가 있는지로 판단한다.

**`scripts/wiki_lint.py` (신규):** read-only 리포트 (자동수정 없음)
- 전 노드 순회(`iter_nodes(wiki_dir())`).
- 보고 항목: ① type이 허용값 아님(이론상 load 시 예외라 방어적), ② status 값 비정상,
  ③ 미허용 tag 목록, ④ status 제안 불일치(시작 전인데 본문 있음).
- rich 테이블/목록으로 출력, 종료코드는 항상 0(경고 도구). 문제 0건이면 "정합성 OK".

## B.4 기존 노드 정리

- `_taxonomy.yml` 시드를 현재 사용 tags(retrieval, ranking, late-interaction, bert)로 구성 →
  colbert/late-interaction 모두 미허용 tag 0건.
- 두 노드는 본문이 시드 스텁 수준이므로 status `시작 전` 유지(규칙과 일치).
- 변경은 private submodule(`knowledge/`)에서 일어나며, 별도 커밋 후 공개 repo의 gitlink 갱신.

## B.5 테스트 (`tests/`)

- `test_status_coerce_compat`: `coerce("분석 중")`·`coerce("검토 대기 중")`·`coerce("in progress")`
  모두 `Status.IN_PROGRESS`, 그리고 `Status.IN_PROGRESS.value == "검토 대기 중"`.
- `test_unknown_tags`: 허용목록 밖 tag만 골라냄.
- `test_suggest_status`: 빈 본문→`시작 전`, 본문 있음→`검토 대기 중`, `완료` 제안 안 함.
- `test_wiki_lint_report` (통합): 픽스처 노드(미허용 tag 1개 + 시작 전인데 본문 있는 노드)로
  리포트가 두 문제를 정확히 잡는지. `MANG2WIKI_KNOWLEDGE`를 tmp로 오버라이드.
- 실행: `.venv/bin/python -m pytest -q`, 린트: `.venv/bin/ruff check`.

## B.6 커밋 규칙

세션 링크·"Generated with Claude / Co-authored-by" 서명 금지. 변경 내용만.

## 비범위

- 그래프 관계도(extends/uses 클러스터) 설계 — 서브프로젝트 D.
- 정밀분석 본문 채우기 — C.
- category 통제, tag 자동 부여 — 하지 않음(YAGNI).
- status 자동 덮어쓰기 — 하지 않음(제안만).
