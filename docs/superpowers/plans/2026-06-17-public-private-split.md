# 공개/비공개 분리 기반공사 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** mang2wiki의 모든 wiki 콘텐츠·graph·queue를 비공개 git submodule(`knowledge/`)로 옮기고, 노드를 `<id>/index.md` 폴더 단위로 재편하며, 모든 코드 경로를 환경변수 기반 리졸버 경유로 바꾼다.

**Architecture:** 공개 repo는 코드/도구만 보유. 신규 `mang2wiki/paths.py`가 `MANG2WIKI_KNOWLEDGE`(기본 `./knowledge`)로 wiki/graph/queue 경로를 계산한다. `iter_nodes`는 `**/index.md`만 노드로 인식하고 id는 폴더명에서 가져온다. 1회성 마이그레이션 스크립트가 기존 flat 파일을 노드 폴더로 변환해 private repo 초기 트리를 만든다.

**Tech Stack:** Python, pytest, networkx, PyYAML, gh CLI, git submodule.

설계 출처: `docs/superpowers/specs/2026-06-17-public-private-split-design.md`

---

## File Structure

| 파일 | 책임 |
|---|---|
| `mang2wiki/paths.py` (신규) | knowledge 디렉터리/하위 경로 리졸버 (env 오버라이드) |
| `mang2wiki/frontmatter.py` (수정) | `iter_nodes`가 `index.md`만 순회, `load_node`가 폴더명에서 id 도출 |
| `scripts/build_graph.py` (수정) | `paths` 경유로 wiki 읽기 / graph 저장 |
| `scripts/notion_ingest.py` (수정) | 스텁 출력 경로 = `<type>/<id>/index.md` |
| `scripts/discover.py` (수정) | wiki/queue 경로 `paths` 경유 |
| `scripts/arxiv_fetch.py` (수정) | wiki 경로 + 노드 조회 `index.md` 기반 |
| `scripts/migrate_to_node_folders.py` (신규) | flat wiki/graph/queue → `knowledge/` 트리 변환 (1회성) |
| `tests/test_paths.py` (신규) | 경로 리졸버 단위테스트 |
| `tests/test_frontmatter_node_folder.py` (신규) | 노드 폴더 인식 회귀 테스트 |
| `tests/test_migrate.py` (신규) | 마이그레이션 변환 테스트 |
| `.env.example` `.claude/skills/notion-ingest/SKILL.md` `README.md` (수정) | 경로/세팅 문서 갱신 |

---

## Task 1: 경로 리졸버 `mang2wiki/paths.py`

**Files:**
- Create: `mang2wiki/paths.py`
- Test: `tests/test_paths.py`

- [ ] **Step 1: 실패하는 테스트 작성**

Create `tests/test_paths.py`:
```python
from pathlib import Path

from mang2wiki import paths


def test_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("MANG2WIKI_KNOWLEDGE", str(tmp_path))
    root = tmp_path.resolve()
    assert paths.knowledge_dir() == root
    assert paths.wiki_dir() == root / "wiki"
    assert paths.graph_path() == root / "graph" / "graph.json"
    assert paths.queue_path() == root / "queue" / "to_study.md"


def test_default_is_repo_knowledge(monkeypatch):
    monkeypatch.delenv("MANG2WIKI_KNOWLEDGE", raising=False)
    d = paths.knowledge_dir()
    assert d.name == "knowledge"
    assert isinstance(d, Path)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_paths.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mang2wiki.paths'`

- [ ] **Step 3: 최소 구현**

Create `mang2wiki/paths.py`:
```python
"""knowledge(비공개) 디렉터리 경로 리졸버.

모든 콘텐츠(wiki/graph/queue)는 private submodule(`knowledge/`)에 있다.
위치는 환경변수 MANG2WIKI_KNOWLEDGE 로 오버라이드(기본 <repo>/knowledge).
"""

from __future__ import annotations

import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]


def knowledge_dir() -> Path:
    env = os.environ.get("MANG2WIKI_KNOWLEDGE")
    if env:
        return Path(env).expanduser().resolve()
    return _REPO_ROOT / "knowledge"


def wiki_dir() -> Path:
    return knowledge_dir() / "wiki"


def graph_path() -> Path:
    return knowledge_dir() / "graph" / "graph.json"


def queue_path() -> Path:
    return knowledge_dir() / "queue" / "to_study.md"
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_paths.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: 커밋**

```bash
git add mang2wiki/paths.py tests/test_paths.py
git commit -m "feat: knowledge 경로 리졸버(paths.py) 추가"
```

---

## Task 2: 노드 폴더(`index.md`) 인식 — frontmatter

기존 `iter_nodes`는 모든 `*.md`를 노드로 보고 `load_node`는 `path.stem`을 id로 쓴다.
노드 폴더 구조(`wiki/papers/colbert/index.md`)에서는 `index.md`만 노드여야 하고
id는 부모 폴더명(`colbert`)에서 와야 한다. `math.md`/`tistory.md`는 노드가 아니다.

**Files:**
- Modify: `mang2wiki/frontmatter.py:40-63` (`load_node`), `mang2wiki/frontmatter.py:105-111` (`iter_nodes`)
- Test: `tests/test_frontmatter_node_folder.py`

- [ ] **Step 1: 실패하는 테스트 작성**

Create `tests/test_frontmatter_node_folder.py`:
```python
from mang2wiki.frontmatter import iter_nodes, load_node


def _write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_iter_nodes_only_index_md(tmp_path):
    wiki = tmp_path / "wiki"
    _write(
        wiki / "papers" / "colbert" / "index.md",
        "---\nid: colbert\ntype: paper\ntitle: ColBERT\n---\n\n본문 [[late-interaction]]\n",
    )
    # 같은 폴더의 보조 파일은 노드가 아님
    _write(wiki / "papers" / "colbert" / "math.md", "# 수식\n")
    _write(wiki / "papers" / "colbert" / "tistory.md", "# 초안\n")
    # 템플릿은 제외
    _write(wiki / "_templates" / "paper.md", "---\ntype: paper\n---\nx\n")

    nodes = list(iter_nodes(wiki))
    assert [n.id for n in nodes] == ["colbert"]


def test_load_node_id_from_folder_when_index(tmp_path):
    d = tmp_path / "papers" / "splade"
    d.mkdir(parents=True)
    (d / "index.md").write_text(
        "---\ntype: paper\ntitle: SPLADE\n---\n\n본문\n", encoding="utf-8"
    )
    node = load_node(d / "index.md")
    assert node.id == "splade"
    assert node.title == "SPLADE"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_frontmatter_node_folder.py -v`
Expected: FAIL — `test_iter_nodes_only_index_md`에서 `math.md`/`tistory.md`/`paper.md`까지 잡혀 id 목록 불일치, `test_load_node_id_from_folder_when_index`에서 id가 `"index"`.

- [ ] **Step 3: `load_node` 수정 — 폴더명 fallback**

`mang2wiki/frontmatter.py`의 `load_node` 안에서, `parse(...)` 다음 줄에 default id 계산을 추가하고 `id`/`title` 기본값을 교체한다.

기존:
```python
    meta, body = parse(path.read_text(encoding="utf-8"))

    known = set(_SCALAR_KEYS) | _LIST_KEYS | {"relations"}
    extra = {k: v for k, v in meta.items() if k not in known}

    return WikiNode(
        id=meta.get("id") or path.stem,
        type=NodeType(meta.get("type", "paper")),
        title=meta.get("title", path.stem),
```
변경 후:
```python
    meta, body = parse(path.read_text(encoding="utf-8"))

    # 노드 폴더 구조: <id>/index.md 이면 id 는 부모 폴더명에서 온다.
    default_id = path.parent.name if path.stem == "index" else path.stem

    known = set(_SCALAR_KEYS) | _LIST_KEYS | {"relations"}
    extra = {k: v for k, v in meta.items() if k not in known}

    return WikiNode(
        id=meta.get("id") or default_id,
        type=NodeType(meta.get("type", "paper")),
        title=meta.get("title", default_id),
```

- [ ] **Step 4: `iter_nodes` 수정 — index.md만 순회**

기존:
```python
def iter_nodes(wiki_dir: str | Path) -> Iterator[WikiNode]:
    """wiki/ 아래 모든 마크다운을 WikiNode로. _templates/ 는 제외."""
    wiki_dir = Path(wiki_dir)
    for md in sorted(wiki_dir.rglob("*.md")):
        if "_templates" in md.parts:
            continue
        yield load_node(md)
```
변경 후:
```python
def iter_nodes(wiki_dir: str | Path) -> Iterator[WikiNode]:
    """wiki/<type>/<id>/index.md 각각을 WikiNode로. _templates/ 는 제외."""
    wiki_dir = Path(wiki_dir)
    for md in sorted(wiki_dir.rglob("index.md")):
        if "_templates" in md.parts:
            continue
        yield load_node(md)
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `pytest tests/test_frontmatter_node_folder.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: 커밋**

```bash
git add mang2wiki/frontmatter.py tests/test_frontmatter_node_folder.py
git commit -m "feat: 노드를 <id>/index.md 폴더 단위로 인식"
```

---

## Task 3: 스크립트 경로를 `paths` 경유로 전환

4개 스크립트의 하드코딩된 `ROOT/"wiki"|"graph"|"queue"`를 제거한다.
빌드/그래프 기능이 노드 폴더 구조 + 리졸버에서 동작하는지 통합 테스트로 못박는다.

**Files:**
- Modify: `scripts/build_graph.py:26-33`, `scripts/notion_ingest.py:32-38,64`, `scripts/discover.py:28-30,81-85`, `scripts/arxiv_fetch.py:25-26,73`
- Test: `tests/test_build_graph_integration.py`

- [ ] **Step 1: 통합(특성) 테스트 작성**

Create `tests/test_build_graph_integration.py`:
```python
from mang2wiki.frontmatter import iter_nodes
from mang2wiki.graph import build_graph, save_json, to_json


def _node(wiki, type_, nid, body):
    p = wiki / (type_ + "s") / nid / "index.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        f"---\nid: {nid}\ntype: {type_}\ntitle: {nid}\n---\n\n{body}\n",
        encoding="utf-8",
    )


def test_build_graph_from_node_folders(tmp_path):
    wiki = tmp_path / "wiki"
    _node(wiki, "paper", "colbert", "uses [[late-interaction]]")
    _node(wiki, "topic", "late-interaction", "허브 토픽")

    nodes = {n.id for n in iter_nodes(wiki)}
    assert nodes == {"colbert", "late-interaction"}

    g = build_graph(wiki)
    data = to_json(g)
    ids = {n["id"] for n in data["nodes"]}
    assert {"colbert", "late-interaction"} <= ids
    rels = {(e["source"], e["target"], e["relation"]) for e in data["edges"]}
    assert ("colbert", "late-interaction", "references") in rels

    out = save_json(g, tmp_path / "graph" / "graph.json")
    assert out.exists()
```

- [ ] **Step 2: 테스트 통과 확인**

Run: `pytest tests/test_build_graph_integration.py -v`
Expected: PASS (1 passed) — `build_graph` 라이브러리는 Task 2에서 이미 노드 폴더를 지원한다.

> 이 테스트는 라이브러리 레벨(`build_graph`)이 노드 폴더에서 동작함을 고정한다(회귀 방지).
> 이어지는 스크립트 수정(Step 3~6)은 경로 소스만 `paths`로 바꾸는 리팩터다.

- [ ] **Step 3: `build_graph.py` 수정**

기존:
```python
from mang2wiki.frontmatter import iter_nodes  # noqa: E402
from mang2wiki.graph import build_graph, dangling_links, save_json  # noqa: E402

console = Console()
WIKI = ROOT / "wiki"


def main() -> int:
    nodes = list(iter_nodes(WIKI))
    g = build_graph(WIKI)
    out = save_json(g, ROOT / "graph" / "graph.json")
```
변경 후:
```python
from mang2wiki.frontmatter import iter_nodes  # noqa: E402
from mang2wiki.graph import build_graph, dangling_links, save_json  # noqa: E402
from mang2wiki.paths import graph_path, wiki_dir  # noqa: E402

console = Console()


def main() -> int:
    wiki = wiki_dir()
    nodes = list(iter_nodes(wiki))
    g = build_graph(wiki)
    out = save_json(g, graph_path())
```
그리고 마지막 줄의 `out.relative_to(ROOT)` 를 `out` 로 바꾼다(knowledge가 ROOT 밖일 수 있음):
```python
    console.print(f"\n[green]그래프 저장[/green]: {out}")
```

- [ ] **Step 4: `notion_ingest.py` 수정**

기존:
```python
from mang2wiki.templates import stub_body  # noqa: E402

console = Console()
WIKI = ROOT / "wiki"
SUBDIR = {NodeType.TOPIC: "topics", NodeType.PAPER: "papers", NodeType.CONCEPT: "concepts"}


def target_path(node) -> Path:
    return WIKI / SUBDIR[node.type] / node.filename
```
변경 후:
```python
from mang2wiki.paths import wiki_dir  # noqa: E402
from mang2wiki.templates import stub_body  # noqa: E402

console = Console()
SUBDIR = {NodeType.TOPIC: "topics", NodeType.PAPER: "papers", NodeType.CONCEPT: "concepts"}


def target_path(node) -> Path:
    return wiki_dir() / SUBDIR[node.type] / node.id / "index.md"
```

- [ ] **Step 5: `discover.py` 수정**

기존:
```python
from mang2wiki.frontmatter import iter_nodes  # noqa: E402
from mang2wiki.models import slugify  # noqa: E402

console = Console()
WIKI = ROOT / "wiki"
QUEUE = ROOT / "queue" / "to_study.md"


def existing_ids() -> set[str]:
    ids = set()
    for n in iter_nodes(WIKI):
```
변경 후:
```python
from mang2wiki.frontmatter import iter_nodes  # noqa: E402
from mang2wiki.models import slugify  # noqa: E402
from mang2wiki.paths import queue_path, wiki_dir  # noqa: E402

console = Console()


def existing_ids() -> set[str]:
    ids = set()
    for n in iter_nodes(wiki_dir()):
```
그리고 `main()` 안의 `QUEUE` 참조 3곳을 `queue_path()`로 바꾼다. 기존:
```python
    if args.write:
        QUEUE.parent.mkdir(parents=True, exist_ok=True)
        header = "" if QUEUE.exists() else "# 공부할 거리 (discover 큐)\n\n"
        with QUEUE.open("a", encoding="utf-8") as f:
            f.write(header + f"\n## {datetime.now().date()} · {args.query}\n" + "\n".join(lines) + "\n")
        console.print(f"\n[green]추가[/green]: {QUEUE.relative_to(ROOT)}")
```
변경 후:
```python
    if args.write:
        queue = queue_path()
        queue.parent.mkdir(parents=True, exist_ok=True)
        header = "" if queue.exists() else "# 공부할 거리 (discover 큐)\n\n"
        with queue.open("a", encoding="utf-8") as f:
            f.write(header + f"\n## {datetime.now().date()} · {args.query}\n" + "\n".join(lines) + "\n")
        console.print(f"\n[green]추가[/green]: {queue}")
```

- [ ] **Step 6: `arxiv_fetch.py` 수정**

기존:
```python
console = Console()
WIKI = ROOT / "wiki"
ARXIV_ID_RE = re.compile(r"\d{4}\.\d{4,5}(v\d+)?")
```
변경 후:
```python
from mang2wiki.paths import wiki_dir  # noqa: E402

console = Console()
ARXIV_ID_RE = re.compile(r"\d{4}\.\d{4,5}(v\d+)?")
```
그리고 노드 조회부. 기존:
```python
        path = next(WIKI.rglob(f"{args.node}.md"), None)
```
변경 후:
```python
        path = next(wiki_dir().glob(f"**/{args.node}/index.md"), None)
```

- [ ] **Step 7: 전체 테스트 + 린트**

Run: `pytest -q && ruff check`
Expected: 전부 PASS, ruff 무경고. (import 정렬 경고가 나면 `ruff check --fix` 후 재확인.)

- [ ] **Step 8: 커밋**

```bash
git add scripts/build_graph.py scripts/notion_ingest.py scripts/discover.py scripts/arxiv_fetch.py tests/test_build_graph_integration.py
git commit -m "refactor: 스크립트 wiki/graph/queue 경로를 paths 리졸버 경유로"
```

---

## Task 4: 마이그레이션 스크립트 (flat → 노드 폴더, 1회성)

기존 `wiki/<type>/<id>.md`를 `knowledge/wiki/<type>/<id>/index.md`로 변환하고,
`_templates/`·`graph/`·`queue/`를 그대로 `knowledge/` 아래로 복사하는 트리 빌더.

**Files:**
- Create: `scripts/migrate_to_node_folders.py`
- Test: `tests/test_migrate.py`

- [ ] **Step 1: 실패하는 테스트 작성**

Create `tests/test_migrate.py`:
```python
from scripts.migrate_to_node_folders import build_knowledge_tree


def _w(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_flat_md_becomes_index_md(tmp_path):
    src = tmp_path / "src"
    _w(src / "wiki" / "papers" / "colbert.md", "---\nid: colbert\ntype: paper\n---\n\n본문\n")
    _w(src / "wiki" / "_templates" / "paper.md", "tmpl\n")
    _w(src / "graph" / "graph.json", "{}\n")
    _w(src / "queue" / "to_study.md", "# 큐\n")

    dest = tmp_path / "knowledge"
    moved = build_knowledge_tree(src, dest)

    assert (dest / "wiki" / "papers" / "colbert" / "index.md").read_text(
        encoding="utf-8"
    ).strip().endswith("본문")
    # 템플릿/그래프/큐는 경로 유지 복사
    assert (dest / "wiki" / "_templates" / "paper.md").exists()
    assert (dest / "graph" / "graph.json").exists()
    assert (dest / "queue" / "to_study.md").exists()
    # 노드 변환 카운트 반환
    assert moved == 1
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_migrate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.migrate_to_node_folders'`

> `scripts/`를 패키지로 import하려면 빈 `tests/conftest.py`가 repo 루트를 `sys.path`에 넣어야 한다. 없으면 Step 3에서 함께 만든다.

- [ ] **Step 3: 마이그레이션 스크립트 구현**

Create `scripts/migrate_to_node_folders.py`:
```python
#!/usr/bin/env python3
"""1회성: flat wiki/graph/queue -> knowledge/ 노드 폴더 트리.

    python scripts/migrate_to_node_folders.py --dest /tmp/m2w-knowledge

wiki/<type>/<id>.md  ->  <dest>/wiki/<type>/<id>/index.md
_templates/·graph/·queue/ 는 경로 유지하여 <dest> 아래로 복사.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def build_knowledge_tree(src_root: Path, dest_root: Path) -> int:
    src_root = Path(src_root)
    dest_root = Path(dest_root)
    moved = 0

    wiki = src_root / "wiki"
    if wiki.is_dir():
        for md in sorted(wiki.rglob("*.md")):
            rel = md.relative_to(wiki)
            if rel.parts and rel.parts[0] == "_templates":
                target = dest_root / "wiki" / rel  # 템플릿은 경로 유지
            else:
                # papers/colbert.md -> papers/colbert/index.md
                target = dest_root / "wiki" / rel.with_suffix("") / "index.md"
                moved += 1
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(md, target)

    for sub in ("graph", "queue"):
        s = src_root / sub
        if s.is_dir():
            shutil.copytree(s, dest_root / sub, dirs_exist_ok=True)

    return moved


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(ROOT), help="공개 repo 루트 (기본: 현재 repo)")
    ap.add_argument("--dest", required=True, help="생성할 knowledge 트리 위치")
    args = ap.parse_args()

    moved = build_knowledge_tree(Path(args.src), Path(args.dest))
    print(f"노드 {moved}개를 <id>/index.md 로 변환 → {args.dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Create `tests/conftest.py` (이미 있으면 생략):
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_migrate.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: 커밋**

```bash
git add scripts/migrate_to_node_folders.py tests/test_migrate.py tests/conftest.py
git commit -m "feat: flat 위키 -> knowledge 노드 폴더 마이그레이션 스크립트"
```

---

## Task 5: 운영 — private repo 생성 + 콘텐츠 이전 + submodule 연결

> ⚠️ **사용자 확인 필요 작업.** gh 인증·네트워크가 필요하고 원격 repo를 새로 만든다(되돌리기 번거로움).
> 실행 전 `gh auth status`로 로그인 확인. 각 명령 결과를 보고 다음으로 진행.
> 자동 실행 워커는 이 Task를 건너뛰고 사용자에게 명령 블록을 제시할 것.

- [ ] **Step 1: 현재 콘텐츠를 임시 knowledge 트리로 변환**

```bash
python scripts/migrate_to_node_folders.py --dest /tmp/m2w-knowledge
```
Expected: `노드 N개를 <id>/index.md 로 변환 → /tmp/m2w-knowledge`
확인: `find /tmp/m2w-knowledge -name index.md` 로 노드들이 보이는지.

- [ ] **Step 2: private repo 생성 + 초기 푸시**

```bash
cd /tmp/m2w-knowledge
git init -q && git add -A
git commit -q -m "init: mang2wiki 비공개 지식 트리 (노드별 index.md)"
gh repo create jinmang2/mang2wiki-knowledge --private --source=. --remote=origin --push
cd /home/jinmang2/mang2wiki
```
Expected: `https://github.com/jinmang2/mang2wiki-knowledge` 생성됨.

- [ ] **Step 3: 공개 repo에서 원본 콘텐츠 제거**

```bash
git rm -r -q wiki graph queue
git commit -m "chore: wiki/graph/queue를 private knowledge submodule로 이전"
```

- [ ] **Step 4: submodule 연결**

```bash
git submodule add git@github.com:jinmang2/mang2wiki-knowledge.git knowledge
git commit -m "chore: knowledge private submodule 연결"
```
Expected: `.gitmodules` 생성, `knowledge/`가 private repo로 clone됨.

- [ ] **Step 5: 동작 검증**

```bash
python scripts/build_graph.py
```
Expected: 그래프 현황 테이블 출력 + `그래프 저장: .../knowledge/graph/graph.json`. 노드 수가 이전과 동일.

- [ ] **Step 6: 임시 디렉터리 정리**

```bash
rm -rf /tmp/m2w-knowledge
```

---

## Task 6: 문서/설정 갱신

**Files:**
- Modify: `.env.example`, `.claude/skills/notion-ingest/SKILL.md`, `README.md`

- [ ] **Step 1: `.env.example`에 knowledge 경로 추가**

`.env.example` 끝에 추가:
```bash

# 비공개 콘텐츠(wiki/graph/queue) 위치. 기본은 ./knowledge (submodule).
# 다른 경로의 private 클론을 쓰려면 절대경로로 오버라이드.
# MANG2WIKI_KNOWLEDGE=./knowledge
```

- [ ] **Step 2: notion-ingest 스킬 출력 경로 갱신**

`.claude/skills/notion-ingest/SKILL.md`에서 위키 출력 경로를 언급한 부분을
`knowledge/wiki/<type>/<id>/index.md` (노드별 폴더)로 수정한다.
Run: `grep -n "wiki/" .claude/skills/notion-ingest/SKILL.md` 로 대상 줄을 찾아 갱신.

- [ ] **Step 3: README 토폴로지/세팅 갱신**

`README.md`에서:
- 디렉터리 트리를 "공개=코드, `knowledge/`=private submodule(wiki/graph/queue)"로 갱신.
- 노드 스키마 설명에 노드 폴더 구조(`<id>/index.md` + `math.md`/`snippets/`/`tistory.md`) 추가.
- 시작하기에 submodule 클론 절차 추가:
```bash
git clone --recurse-submodules <repo>        # 또는
git submodule update --init                   # 기존 클론에서
```

- [ ] **Step 4: 커밋**

```bash
git add .env.example .claude/skills/notion-ingest/SKILL.md README.md
git commit -m "docs: 공개/비공개 분리에 맞춰 README·env·스킬 경로 갱신"
```

---

## 완료 기준

- `pytest -q` 전부 통과, `ruff check` 무경고.
- `python scripts/build_graph.py`가 `knowledge/graph/graph.json`을 생성하고 노드 수가 이전과 일치.
- 공개 repo에 `wiki/`·`graph/`·`queue/` 실체 파일이 없고, `.gitmodules`만 private repo를 가리킴.
- 모든 커밋 메시지에 Claude 서명/세션 링크 없음.
