# 분류 체계 재정비 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** type/tags/status 분류 규칙을 명문화하고, 통제 어휘(`_taxonomy.yml`) + read-only lint 도구로 정합성을 점검한다. status enum을 사용자 기준("검토 대기 중")으로 바꾸되 하위호환을 유지한다.

**Architecture:** `Status.IN_PROGRESS` 표시값을 "검토 대기 중"으로 바꾸고 coerce가 legacy "분석 중"도 수용. 신규 `mang2wiki/taxonomy.py`가 허용 tag 로드 + 미허용 tag 검출 + 내용기반 status 제안을 제공. 신규 `scripts/wiki_lint.py`가 전 노드를 순회해 문제를 리포트(자동수정 없음). 허용목록은 private submodule(`knowledge/wiki/_taxonomy.yml`), 분류 규칙 문서는 공개(`docs/classification.md`).

**Tech Stack:** Python, pytest, PyYAML, rich.

설계 출처: `docs/superpowers/specs/2026-06-17-classification-overhaul-design.md`

## Global Constraints

- venv: 테스트 `.venv/bin/python -m pytest ...`, 린트 `.venv/bin/ruff check ...` (글로벌 PATH에 없음).
- 커밋 메시지: 변경 내용만. "Generated with Claude" / "Co-Authored-By: Claude" / 세션링크 트레일러 금지.
- 콘텐츠 경로는 `mang2wiki/paths.py`의 리졸버(`wiki_dir()` 등) 경유. 테스트는 `MANG2WIKI_KNOWLEDGE` 환경변수로 오버라이드.
- 작업 디렉터리: /home/jinmang2/mang2wiki.

---

## Task 1: status enum을 "검토 대기 중"으로 (하위호환 유지)

**Files:**
- Modify: `mang2wiki/models.py:22-43` (Status enum + coerce)
- Test: `tests/test_status.py`

**Interfaces:**
- Produces: `Status.IN_PROGRESS.value == "검토 대기 중"`; `Status.coerce(s)` maps `"분석 중"`, `"검토 대기 중"`, `"in progress"`, `"doing"` → `Status.IN_PROGRESS`.

- [ ] **Step 1: 실패하는 테스트 작성**

Create `tests/test_status.py`:
```python
from mang2wiki.models import Status


def test_in_progress_display_value():
    assert Status.IN_PROGRESS.value == "검토 대기 중"


def test_coerce_legacy_and_new():
    assert Status.coerce("분석 중") is Status.IN_PROGRESS       # legacy Notion 표기
    assert Status.coerce("검토 대기 중") is Status.IN_PROGRESS   # 새 표기
    assert Status.coerce("in progress") is Status.IN_PROGRESS
    assert Status.coerce("doing") is Status.IN_PROGRESS


def test_coerce_unchanged_values():
    assert Status.coerce("시작 전") is Status.TODO
    assert Status.coerce("완료") is Status.DONE
    assert Status.coerce(None) is Status.TODO
    assert Status.coerce("아무거나") is Status.TODO
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv/bin/python -m pytest tests/test_status.py -v`
Expected: FAIL — `test_in_progress_display_value` ("분석 중" != "검토 대기 중") 및 `test_coerce_legacy_and_new`의 "검토 대기 중" 케이스 실패.

- [ ] **Step 3: enum 값 변경**

`mang2wiki/models.py`에서:
```python
    TODO = "시작 전"
    IN_PROGRESS = "분석 중"
    DONE = "완료"
```
를 아래로 변경:
```python
    TODO = "시작 전"
    IN_PROGRESS = "검토 대기 중"
    DONE = "완료"
```

- [ ] **Step 4: coerce 하위호환 매핑 추가**

같은 파일 coerce의 mapping 딕셔너리에 legacy 한글 표기를 추가한다. 기존:
```python
        mapping = {
            "todo": cls.TODO,
            "not started": cls.TODO,
            "in progress": cls.IN_PROGRESS,
            "doing": cls.IN_PROGRESS,
            "done": cls.DONE,
            "complete": cls.DONE,
        }
```
변경 후:
```python
        mapping = {
            "todo": cls.TODO,
            "not started": cls.TODO,
            "분석 중": cls.IN_PROGRESS,  # legacy 표기 (Notion 보드 호환)
            "in progress": cls.IN_PROGRESS,
            "doing": cls.IN_PROGRESS,
            "done": cls.DONE,
            "complete": cls.DONE,
        }
```
(새 표기 "검토 대기 중"은 coerce 상단의 `for s in cls: if v == s.value` 루프에서 이미 매칭되므로 mapping에 넣지 않아도 된다.)

- [ ] **Step 5: 테스트 통과 + 전체 스위트**

Run: `.venv/bin/python -m pytest tests/test_status.py -v` → PASS (3 passed)
Run: `.venv/bin/python -m pytest -q` → 전체 통과 (기존 테스트 회귀 없음)

- [ ] **Step 6: 린트 + 커밋**

```bash
.venv/bin/ruff check mang2wiki/models.py tests/test_status.py
git add mang2wiki/models.py tests/test_status.py
git commit -m "feat: status enum을 '검토 대기 중'으로 변경(분석 중 하위호환 유지)"
```

---

## Task 2: 분류 검증 모듈 `mang2wiki/taxonomy.py`

**Files:**
- Create: `mang2wiki/taxonomy.py`
- Test: `tests/test_taxonomy.py`

**Interfaces:**
- Consumes: `mang2wiki.paths.wiki_dir()`, `mang2wiki.models.{WikiNode, Status}`.
- Produces:
  - `taxonomy_path() -> Path` = `wiki_dir() / "_taxonomy.yml"`
  - `load_allowed_tags() -> set[str]` (파일 없으면 빈 set)
  - `unknown_tags(node: WikiNode, allowed: set[str]) -> list[str]`
  - `suggest_status(node: WikiNode) -> Status` (절대 `Status.DONE` 반환 안 함)
  - `status_mismatch(node: WikiNode) -> Status | None`

- [ ] **Step 1: 실패하는 테스트 작성**

Create `tests/test_taxonomy.py`:
```python
from mang2wiki import taxonomy
from mang2wiki.models import NodeType, Status, WikiNode


def _node(**kw):
    base = dict(id="x", type=NodeType.PAPER, title="x", body="")
    base.update(kw)
    return WikiNode(**base)


def test_unknown_tags():
    allowed = {"retrieval", "ranking"}
    n = _node(tags=["retrieval", "weird", "ranking", "bogus"])
    assert taxonomy.unknown_tags(n, allowed) == ["weird", "bogus"]
    assert taxonomy.unknown_tags(_node(tags=["retrieval"]), allowed) == []


def test_suggest_status_empty_body():
    assert taxonomy.suggest_status(_node(body="")) is Status.TODO
    # 헤딩/인용/주석/공백만 있으면 비어있는 것으로 본다
    only_scaffold = "## TL;DR\n\n> **status**: 시작 전\n\n<!-- 메모 -->\n"
    assert taxonomy.suggest_status(_node(body=only_scaffold)) is Status.TODO


def test_suggest_status_with_content():
    body = "## TL;DR\n질의·문서 토큰을 임베딩해 MaxSim으로 점수화한다.\n"
    assert taxonomy.suggest_status(_node(body=body)) is Status.IN_PROGRESS


def test_suggest_status_never_done():
    big = "## 개요\n" + ("실제 분석 내용 " * 200)
    assert taxonomy.suggest_status(_node(body=big)) is not Status.DONE


def test_status_mismatch():
    body = "## 개요\n실제 내용이 있다.\n"
    # 시작 전인데 본문 있음 -> 제안
    assert taxonomy.status_mismatch(_node(status=Status.TODO, body=body)) is Status.IN_PROGRESS
    # 이미 검토 대기 중 / 완료 -> 불일치로 보지 않음
    assert taxonomy.status_mismatch(_node(status=Status.IN_PROGRESS, body=body)) is None
    assert taxonomy.status_mismatch(_node(status=Status.DONE, body=body)) is None
    # 시작 전이고 본문도 비었음 -> 일치
    assert taxonomy.status_mismatch(_node(status=Status.TODO, body="## TL;DR\n")) is None


def test_load_allowed_tags(tmp_path, monkeypatch):
    monkeypatch.setenv("MANG2WIKI_KNOWLEDGE", str(tmp_path))
    (tmp_path / "wiki").mkdir()
    (tmp_path / "wiki" / "_taxonomy.yml").write_text(
        "tags:\n  - retrieval\n  - ranking\n", encoding="utf-8"
    )
    assert taxonomy.load_allowed_tags() == {"retrieval", "ranking"}


def test_load_allowed_tags_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("MANG2WIKI_KNOWLEDGE", str(tmp_path))
    assert taxonomy.load_allowed_tags() == set()
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv/bin/python -m pytest tests/test_taxonomy.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mang2wiki.taxonomy'`

- [ ] **Step 3: 모듈 구현**

Create `mang2wiki/taxonomy.py`:
```python
"""분류 검증: 통제 어휘(tags) + 내용기반 status 제안.

자동수정은 하지 않는다 — 검출/제안만 제공하고 결정은 사람이 한다.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from .models import Status, WikiNode
from .paths import wiki_dir

_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def taxonomy_path() -> Path:
    return wiki_dir() / "_taxonomy.yml"


def load_allowed_tags() -> set[str]:
    p = taxonomy_path()
    if not p.exists():
        return set()
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return set(data.get("tags") or [])


def unknown_tags(node: WikiNode, allowed: set[str]) -> list[str]:
    """노드 tags 중 허용목록에 없는 것 (입력 순서 보존)."""
    return [t for t in node.tags if t not in allowed]


def _has_real_content(body: str) -> bool:
    """본문에 실질 텍스트가 있는지. 헤딩·인용구·HTML주석·공백은 내용으로 치지 않는다."""
    text = _HTML_COMMENT_RE.sub("", body)
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#") or s.startswith(">"):
            continue
        return True
    return False


def suggest_status(node: WikiNode) -> Status:
    """내용 기반 status 제안. '완료'는 사람만 정하므로 절대 제안하지 않는다."""
    return Status.IN_PROGRESS if _has_real_content(node.body) else Status.TODO


def status_mismatch(node: WikiNode) -> Status | None:
    """현재 status가 '시작 전'인데 본문이 있으면 제안값 반환, 아니면 None."""
    if node.status is Status.TODO and _has_real_content(node.body):
        return Status.IN_PROGRESS
    return None
```

- [ ] **Step 4: 테스트 통과 + 전체 스위트**

Run: `.venv/bin/python -m pytest tests/test_taxonomy.py -v` → PASS (7 passed)
Run: `.venv/bin/python -m pytest -q` → 전체 통과

- [ ] **Step 5: 린트 + 커밋**

```bash
.venv/bin/ruff check mang2wiki/taxonomy.py tests/test_taxonomy.py
git add mang2wiki/taxonomy.py tests/test_taxonomy.py
git commit -m "feat: 분류 검증 모듈(taxonomy) — 통제 어휘 + status 제안"
```

---

## Task 3: lint CLI `scripts/wiki_lint.py`

**Files:**
- Create: `scripts/wiki_lint.py`
- Test: `tests/test_wiki_lint.py`

**Interfaces:**
- Consumes: `mang2wiki.taxonomy.{unknown_tags, status_mismatch, load_allowed_tags}`, `mang2wiki.frontmatter.iter_nodes`, `mang2wiki.paths.wiki_dir`.
- Produces: `lint_report(nodes: Iterable[WikiNode], allowed: set[str]) -> list[tuple[str, str]]` returning `(node_id, message)` 문제 목록.

- [ ] **Step 1: 실패하는 테스트 작성**

Create `tests/test_wiki_lint.py`:
```python
from mang2wiki.models import NodeType, Status, WikiNode
from scripts.wiki_lint import lint_report


def _node(**kw):
    base = dict(id="x", type=NodeType.PAPER, title="x", body="")
    base.update(kw)
    return WikiNode(**base)


def test_lint_report_flags_unknown_tag_and_status():
    allowed = {"retrieval"}
    nodes = [
        _node(id="ok", tags=["retrieval"], status=Status.TODO, body="## TL;DR\n"),
        _node(id="badtag", tags=["retrieval", "weird"], status=Status.IN_PROGRESS, body="x 실제"),
        _node(id="badstatus", tags=["retrieval"], status=Status.TODO, body="## 개요\n실제 내용"),
    ]
    report = lint_report(nodes, allowed)
    ids = {nid for nid, _ in report}
    assert "ok" not in ids
    assert "badtag" in ids
    assert "badstatus" in ids
    msgs = {nid: msg for nid, msg in report}
    assert "weird" in msgs["badtag"]
    assert "검토 대기 중" in msgs["badstatus"]
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv/bin/python -m pytest tests/test_wiki_lint.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.wiki_lint'` (scripts는 `tests/conftest.py`가 sys.path에 루트를 넣어 import 가능).

- [ ] **Step 3: 스크립트 구현**

Create `scripts/wiki_lint.py`:
```python
#!/usr/bin/env python3
"""분류 정합성 lint — read-only 리포트 (자동수정 없음).

    python scripts/wiki_lint.py

전 노드를 순회하며 ① 미허용 tag, ② 내용기반 status 제안 불일치를 보고한다.
허용 tag 목록은 knowledge/wiki/_taxonomy.yml.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rich.console import Console  # noqa: E402

from mang2wiki.frontmatter import iter_nodes  # noqa: E402
from mang2wiki.models import WikiNode  # noqa: E402
from mang2wiki.paths import wiki_dir  # noqa: E402
from mang2wiki.taxonomy import (  # noqa: E402
    load_allowed_tags,
    status_mismatch,
    unknown_tags,
)

console = Console()


def lint_report(nodes: Iterable[WikiNode], allowed: set[str]) -> list[tuple[str, str]]:
    """(node_id, message) 문제 목록. 문제 없으면 빈 리스트."""
    issues: list[tuple[str, str]] = []
    for n in nodes:
        unk = unknown_tags(n, allowed)
        if unk:
            issues.append((n.id, f"미허용 tag: {', '.join(unk)}"))
        sug = status_mismatch(n)
        if sug is not None:
            issues.append((n.id, f"status 제안: {n.status.value} → {sug.value}"))
    return issues


def main() -> int:
    allowed = load_allowed_tags()
    nodes = list(iter_nodes(wiki_dir()))
    report = lint_report(nodes, allowed)

    if not report:
        console.print(f"[green]정합성 OK[/green] · 노드 {len(nodes)}개 · 허용 tag {len(allowed)}개")
        return 0

    console.print(f"[yellow]분류 점검 {len(report)}건[/yellow] (노드 {len(nodes)}개)")
    for nid, msg in report:
        console.print(f"  [bold]{nid}[/bold] — {msg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 테스트 통과 + 전체 스위트**

Run: `.venv/bin/python -m pytest tests/test_wiki_lint.py -v` → PASS (1 passed)
Run: `.venv/bin/python -m pytest -q` → 전체 통과

- [ ] **Step 5: 린트 + 커밋**

```bash
.venv/bin/ruff check scripts/wiki_lint.py tests/test_wiki_lint.py
git add scripts/wiki_lint.py tests/test_wiki_lint.py
git commit -m "feat: 분류 정합성 lint 스크립트(wiki_lint)"
```

---

## Task 4: 분류 규칙 문서 + 어휘 시드 + 적용

공개 규칙 문서를 쓰고, private submodule에 어휘 시드를 만든 뒤 실제 노드에 lint를 돌려
검증한다. submodule 변경은 `knowledge/` 안에서 커밋하고, 공개 repo의 gitlink를 갱신한다.

**Files:**
- Create: `docs/classification.md` (공개)
- Create: `knowledge/wiki/_taxonomy.yml` (private submodule)

- [ ] **Step 1: 분류 규칙 문서 작성**

Create `docs/classification.md`:
```markdown
# 분류 규칙 (type / status / tags)

> 자동추정하지 않는다. type/status는 내가 규칙에 따라 수동 결정하고,
> lint(`scripts/wiki_lint.py`)는 점검·제안만 한다.

## type (판정 우선순위)

1. **topic** — 하위 노드를 묶는 허브. 다른 노드가 `parents`로 이 노드를 가리킨다.
   예: late-interaction, RL.
2. **concept** — 여러 논문/맥락에 걸쳐 재사용되는 기법·수식·메커니즘.
   예: MaxSim, continuous batching, MIPS.
3. **paper** — 위에 해당하지 않는, '단일 연구 산출물' 단위 노드. **arxiv 유무와 무관.**

판정: 허브인가? → topic / 재사용 기법인가? → concept / 그 외 단일 연구 → paper.

## status

- `시작 전` — 본문에 실질 내용 없음(스텁/빈 본문).
- `검토 대기 중` — 내용은 있으나 말투·정보 정리를 더 해야 함.
- `완료` — 내가 만족한 노드. **수동으로만 지정**(lint가 제안하지 않음).

lint는 "시작 전인데 본문 있음"을 `검토 대기 중` 후보로 제안한다.

## tags

통제 어휘. 허용 목록은 `knowledge/wiki/_taxonomy.yml`(비공개)의 `tags`.
목록 밖 tag는 lint가 경고한다. 새 tag가 필요하면 먼저 목록에 추가한다.
```

- [ ] **Step 2: 어휘 시드 작성 (private submodule)**

Create `knowledge/wiki/_taxonomy.yml`:
```yaml
# 허용 tag 통제 어휘. 새 tag는 여기 먼저 추가한 뒤 노드에 단다.
tags:
  - retrieval
  - ranking
  - late-interaction
  - bert
```

- [ ] **Step 3: 실제 노드에 lint 실행 (검증)**

Run: `.venv/bin/python scripts/wiki_lint.py`
Expected: 미허용 tag 0건 (colbert/late-interaction의 tags가 모두 시드에 포함됨).
colbert·late-interaction은 본문(시드 노트)이 있으므로 "status 제안: 시작 전 → 검토 대기 중"
경고가 뜰 수 있다 — 이는 의도된 동작(내용이 있으니 status를 올릴지 사람이 결정).
미허용 tag 경고가 하나라도 나오면 시드 목록을 맞춰 수정 후 재실행.

- [ ] **Step 4: submodule 커밋 + 공개 gitlink 갱신**

```bash
# private submodule 내부 커밋
git -C knowledge add wiki/_taxonomy.yml
git -C knowledge commit -m "feat: tag 통제 어휘 시드(_taxonomy.yml)"
# 공개 repo: 규칙 문서 + 갱신된 submodule 포인터
git add docs/classification.md knowledge
git commit -m "docs: 분류 규칙 문서 + tag 어휘 시드 연결"
```

> 참고: private submodule의 새 커밋을 원격에 올리려면 별도로 `git -C knowledge push`가
> 필요하다(공개 repo push와 마찬가지로 finishing 단계에서 사용자가 결정).

---

## 완료 기준

- `.venv/bin/python -m pytest -q` 전부 통과, `.venv/bin/ruff check mang2wiki/ scripts/ tests/` 무경고.
- `Status.IN_PROGRESS.value == "검토 대기 중"`, `coerce("분석 중")`는 여전히 `IN_PROGRESS`.
- `scripts/wiki_lint.py` 실행 시 미허용 tag 0건 (status 제안 경고는 허용).
- 공개 repo에 `docs/classification.md`, private submodule에 `_taxonomy.yml` 존재.
- 모든 커밋 메시지에 Claude 서명/세션 링크 없음.
