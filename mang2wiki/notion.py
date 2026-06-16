"""Notion 씨앗 import.

기존 'Sources' 보드(데이터베이스)의 페이지들을 읽어 WikiNode 스텁으로 변환한다.
이 프로젝트에서 Notion은 '씨앗'일 뿐 — 진실의 원천은 wiki/ 마크다운.

분석 결과를 Notion으로 다시 쓰지는 않는다(단방향). 필요해지면 push 함수를 추가.
"""

from __future__ import annotations

import os
from typing import Iterator

from .models import NodeType, Status, WikiNode, slugify


def _plain(rich: list[dict]) -> str:
    return "".join(part.get("plain_text", "") for part in (rich or []))


def _prop_text(prop: dict) -> str | None:
    """다양한 Notion 속성 타입에서 대표 텍스트 1개를 추출."""
    t = prop.get("type")
    if t == "title":
        return _plain(prop["title"]) or None
    if t == "rich_text":
        return _plain(prop["rich_text"]) or None
    if t == "select":
        return prop["select"]["name"] if prop.get("select") else None
    if t == "status":
        return prop["status"]["name"] if prop.get("status") else None
    if t == "multi_select":
        return ", ".join(o["name"] for o in prop.get("multi_select", [])) or None
    if t == "url":
        return prop.get("url")
    return None


def _multi(prop: dict) -> list[str]:
    if prop.get("type") == "multi_select":
        return [o["name"] for o in prop.get("multi_select", [])]
    return []


def _guess_type(title: str, category: str | None, tags: list[str]) -> NodeType:
    """제목/카테고리로 노드 타입 추정. 정밀분석 단계에서 사람이/내가 교정 가능."""
    text = f"{title} {category or ''} {' '.join(tags)}".lower()
    # 논문스러운 신호: 콜론 부제, arxiv 흔한 단어
    if ":" in title or any(w in text for w in ("learning", "model", "training", "rag", "retrieval-augmented")):
        return NodeType.PAPER
    # 짧은 명사구는 개념일 확률
    if len(title.split()) <= 4:
        return NodeType.CONCEPT
    return NodeType.PAPER


def fetch_pages(
    database_id: str | None = None,
    token: str | None = None,
    type_hint: str = "guess",
) -> Iterator[WikiNode]:
    """Notion DB의 모든 페이지를 WikiNode(스텁)로 yield.

    type_hint: 'guess' | 'paper' | 'concept' | 'topic'
    """
    from notion_client import Client  # 지연 import (의존성 없어도 lib import 가능)

    token = token or os.environ["NOTION_API_KEY"]
    database_id = database_id or os.environ["NOTION_DATABASE_ID"]
    client = Client(auth=token)

    cursor = None
    while True:
        kwargs = {"database_id": database_id, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor
        resp = client.databases.query(**kwargs)

        for page in resp["results"]:
            props = page.get("properties", {})
            title = None
            status_val = None
            category = None
            url = None
            tags: list[str] = []

            for name, prop in props.items():
                pt = prop.get("type")
                if pt == "title":
                    title = _prop_text(prop)
                elif pt == "status":
                    status_val = _prop_text(prop)
                elif pt in ("select",) and category is None:
                    category = _prop_text(prop)
                elif pt == "multi_select":
                    tags.extend(_multi(prop))
                elif pt == "url" and url is None:
                    url = _prop_text(prop)

            if not title:
                continue

            node_type = (
                _guess_type(title, category, tags)
                if type_hint == "guess"
                else NodeType(type_hint)
            )

            yield WikiNode(
                id=slugify(title),
                type=node_type,
                title=title,
                status=Status.coerce(status_val),
                category=category,
                code=url,
                tags=sorted(set(tags)),
                notion_id=page["id"],
            )

        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
