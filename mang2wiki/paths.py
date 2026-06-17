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
