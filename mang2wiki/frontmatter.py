"""마크다운 frontmatter <-> WikiNode 직렬화.

형식:
    ---
    <yaml>
    ---
    <본문 마크다운>
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator

import yaml

from .models import NodeType, Status, WikiNode

WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")

# frontmatter에서 WikiNode 필드로 직접 매핑되는 키
_SCALAR_KEYS = {
    "id", "type", "title", "status", "category", "arxiv", "code",
    "notion_id", "created", "updated",
}
_LIST_KEYS = {"parents", "tags"}


def parse(text: str) -> tuple[dict, str]:
    """원문 -> (frontmatter dict, body)."""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            meta = yaml.safe_load(parts[1]) or {}
            return meta, parts[2].lstrip("\n")
    return {}, text


def load_node(path: str | Path) -> WikiNode:
    path = Path(path)
    meta, body = parse(path.read_text(encoding="utf-8"))

    known = set(_SCALAR_KEYS) | _LIST_KEYS | {"relations"}
    extra = {k: v for k, v in meta.items() if k not in known}

    return WikiNode(
        id=meta.get("id") or path.stem,
        type=NodeType(meta.get("type", "paper")),
        title=meta.get("title", path.stem),
        status=Status.coerce(meta.get("status")),
        category=meta.get("category"),
        arxiv=str(meta["arxiv"]) if meta.get("arxiv") is not None else None,
        code=meta.get("code"),
        parents=list(meta.get("parents") or []),
        relations=dict(meta.get("relations") or {}),
        tags=list(meta.get("tags") or []),
        notion_id=meta.get("notion_id"),
        created=str(meta["created"]) if meta.get("created") else None,
        updated=str(meta["updated"]) if meta.get("updated") else None,
        extra=extra,
        body=body,
    )


def to_frontmatter(node: WikiNode) -> dict:
    fm: dict = {
        "id": node.id,
        "type": node.type.value,
        "title": node.title,
        "status": node.status.value,
    }
    if node.category:
        fm["category"] = node.category
    if node.arxiv:
        fm["arxiv"] = node.arxiv
    if node.code:
        fm["code"] = node.code
    if node.parents:
        fm["parents"] = node.parents
    if node.relations:
        fm["relations"] = node.relations
    if node.tags:
        fm["tags"] = node.tags
    if node.notion_id:
        fm["notion_id"] = node.notion_id
    if node.created:
        fm["created"] = node.created
    if node.updated:
        fm["updated"] = node.updated
    fm.update(node.extra)
    return fm


def dump_node(node: WikiNode, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = yaml.safe_dump(
        to_frontmatter(node), allow_unicode=True, sort_keys=False, default_flow_style=False
    )
    path.write_text(f"---\n{fm}---\n\n{node.body.strip()}\n", encoding="utf-8")
    return path


def iter_nodes(wiki_dir: str | Path) -> Iterator[WikiNode]:
    """wiki/ 아래 모든 마크다운을 WikiNode로. _templates/ 는 제외."""
    wiki_dir = Path(wiki_dir)
    for md in sorted(wiki_dir.rglob("*.md")):
        if "_templates" in md.parts:
            continue
        yield load_node(md)


def extract_wikilinks(body: str) -> list[str]:
    """본문에서 [[id]] 참조 추출 (soft reference 엣지용)."""
    return [m.group(1).strip() for m in WIKILINK_RE.finditer(body)]
