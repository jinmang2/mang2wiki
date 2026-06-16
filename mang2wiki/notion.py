"""Notion 씨앗 import.

기존 'Sources' 보드(신형 Notion API의 data source)의 페이지들을 읽어
WikiNode 스텁으로 변환한다. 이 프로젝트에서 Notion은 '씨앗'일 뿐 —
진실의 원천은 wiki/ 마크다운. (단방향: 분석 결과를 Notion으로 되쓰지 않음)

설계는 dreamsori 프로젝트의 NotionClient 패턴을 경량화해 가져왔다:
타입별 리졸버 딕셔너리로 어떤 속성 타입이든 일관되게 파싱한다.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Iterator

from .models import NodeType, Status, WikiNode, slugify

# --------------------------------------------------------------------------- #
# 타입 리졸버 — Notion property type -> 파이썬 값
# --------------------------------------------------------------------------- #


def _pass(v: Any) -> Any:
    return v


def _name(v: Any) -> str | None:
    return v.get("name") if isinstance(v, dict) else None


def _list_name(v: Any) -> list[str]:
    if isinstance(v, list):
        return [i["name"] for i in v if isinstance(i, dict) and "name" in i]
    return []


def _list_id(v: Any) -> list[str]:
    if isinstance(v, list):
        return [i["id"] for i in v if isinstance(i, dict) and "id" in i]
    return []


def _date(v: Any) -> str | None:
    return v.get("start") if isinstance(v, dict) else None


def _plain_join(v: Any) -> str:
    """title / rich_text — 모든 세그먼트의 plain_text 결합."""
    if isinstance(v, list):
        return "".join(t.get("plain_text", "") for t in v if isinstance(t, dict))
    return ""


def _files(v: Any) -> str | None:
    if isinstance(v, list) and v:
        obj = v[0].get("file") or v[0].get("external", {})
        return obj.get("url")
    return None


def _formula(v: Any) -> Any:
    return v.get(v.get("type")) if isinstance(v, dict) and "type" in v else None


NOTION_TYPE_RESOLVERS: dict[str, Callable[[Any], Any]] = {
    "url": _pass,
    "number": _pass,
    "checkbox": _pass,
    "email": _pass,
    "phone_number": _pass,
    "created_time": _pass,
    "last_edited_time": _pass,
    "select": _name,
    "status": _name,
    "multi_select": _list_name,
    "relation": _list_id,
    "date": _date,
    "title": _plain_join,
    "rich_text": _plain_join,
    "files": _files,
    "formula": _formula,
}


def resolve_property(prop: dict) -> tuple[str, Any]:
    """단일 Notion property -> (type, 파싱된 값)."""
    ptype = prop.get("type")
    resolver = NOTION_TYPE_RESOLVERS.get(ptype, _pass)
    return ptype, resolver(prop.get(ptype))


def parse_page(page: dict) -> dict:
    """페이지의 모든 property를 {이름: 값} 으로 평탄화 + 시스템 필드 보존."""
    out: dict[str, Any] = {
        "_id": page.get("id"),
        "_url": page.get("url"),
        "_created_time": page.get("created_time"),
        "_last_edited_time": page.get("last_edited_time"),
        "_types": {},
    }
    for name, prop in (page.get("properties") or {}).items():
        ptype, value = resolve_property(prop)
        out[name] = value
        out["_types"][name] = ptype
    return out


# --------------------------------------------------------------------------- #
# 페이지 -> WikiNode 매핑
# --------------------------------------------------------------------------- #


def _guess_type(title: str, category: str | None, tags: list[str]) -> NodeType:
    """제목/카테고리로 노드 타입 추정. 정밀분석 단계에서 교정 가능."""
    text = f"{title} {category or ''} {' '.join(tags)}".lower()
    if ":" in title or any(
        w in text for w in ("learning", "model", "training", "rag", "retrieval-augmented")
    ):
        return NodeType.PAPER
    if len(title.split()) <= 4:
        return NodeType.CONCEPT
    return NodeType.PAPER


def page_to_node(parsed: dict, type_hint: str = "guess") -> WikiNode | None:
    """parse_page() 결과(타입 메타 포함)를 WikiNode로 변환.

    컬럼 이름을 모르므로 property '타입'으로 역할을 추론한다:
      title -> 제목, status -> 상태, select(첫) -> 카테고리,
      multi_select -> 태그, url(첫) -> 코드 링크
    """
    types: dict[str, str] = parsed.get("_types", {})
    title = status_val = category = url = None
    tags: list[str] = []

    for name, ptype in types.items():
        value = parsed.get(name)
        if ptype == "title" and not title:
            title = value
        elif ptype == "status" and not status_val:
            status_val = value
        elif ptype == "select" and category is None:
            category = value
        elif ptype == "multi_select":
            tags.extend(value or [])
        elif ptype == "url" and url is None:
            url = value

    if not title:
        return None

    node_type = (
        _guess_type(title, category, tags) if type_hint == "guess" else NodeType(type_hint)
    )

    def _date_part(ts: str | None) -> str | None:
        return ts.split("T")[0] if ts else None

    return WikiNode(
        id=slugify(title),
        type=node_type,
        title=title,
        status=Status.coerce(status_val),
        category=category,
        code=url,
        tags=sorted(set(tags)),
        notion_id=parsed.get("_id"),
        created=_date_part(parsed.get("_created_time")),
        updated=_date_part(parsed.get("_last_edited_time")),
    )


# --------------------------------------------------------------------------- #
# fetch
# --------------------------------------------------------------------------- #


def _query_pages(client, source_id: str, source_type: str) -> Iterator[dict]:
    """data_source(신형) 또는 database(구형)를 페이지네이션으로 순회."""
    cursor = None
    while True:
        kwargs: dict[str, Any] = {"page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor

        if source_type == "data_source":
            resp = client.data_sources.query(data_source_id=source_id, **kwargs)
        else:
            resp = client.databases.query(database_id=source_id, **kwargs)

        yield from resp.get("results", [])

        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")


def fetch_pages(
    source_id: str | None = None,
    token: str | None = None,
    type_hint: str = "guess",
    source_type: str | None = None,
) -> Iterator[WikiNode]:
    """Notion data source(또는 database)의 모든 페이지를 WikiNode(스텁)로 yield.

    env: NOTION_API_KEY, 그리고 NOTION_DATA_SOURCE_ID(신형) 또는 NOTION_DATABASE_ID(구형).
    source_type: 'data_source' | 'database' (미지정 시 env 로 자동 판별)
    """
    from notion_client import Client  # 지연 import

    token = token or os.environ["NOTION_API_KEY"]

    if source_id is None:
        ds = os.environ.get("NOTION_DATA_SOURCE_ID")
        db = os.environ.get("NOTION_DATABASE_ID")
        if ds:
            source_id, source_type = ds, source_type or "data_source"
        elif db:
            source_id, source_type = db, source_type or "database"
        else:
            raise RuntimeError("NOTION_DATA_SOURCE_ID 또는 NOTION_DATABASE_ID 가 필요합니다.")
    source_type = source_type or "data_source"

    client = Client(auth=token)
    for page in _query_pages(client, source_id, source_type):
        node = page_to_node(parse_page(page), type_hint=type_hint)
        if node is not None:
            yield node
