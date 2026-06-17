"""分類検証: 統制語彙(tags) + 内容基づきstatus提案.

自動修正はしない — 検出・提案のみを提供し、決定は人間が行う。
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
