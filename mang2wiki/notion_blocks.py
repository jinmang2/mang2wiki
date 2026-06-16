"""Notion 페이지 본문(blocks) -> 마크다운.

ingest(메타데이터)와 별개로, 이미 작성해 둔 Notion 페이지 본문을 끌어와
로컬 전용 knowledge/notes/<id>.md 로 보존하기 위한 변환기.

지원 블록: paragraph, heading_1~3, bulleted/numbered list, to_do, quote,
callout, toggle, code, equation, divider, image, bookmark/embed, table.
중첩(has_children)은 재귀로 들여쓰기 처리한다.
"""

from __future__ import annotations

from typing import Any, Callable

# --------------------------------------------------------------------------- #
# rich_text -> 인라인 마크다운
# --------------------------------------------------------------------------- #


def _annotate(text: str, ann: dict) -> str:
    if not text:
        return text
    if ann.get("code"):
        text = f"`{text}`"
    if ann.get("bold"):
        text = f"**{text}**"
    if ann.get("italic"):
        text = f"*{text}*"
    if ann.get("strikethrough"):
        text = f"~~{text}~~"
    return text


def rich_text(items: list[dict] | None) -> str:
    """rich_text 배열 -> 마크다운 인라인 (수식/링크/주석 포함)."""
    out: list[str] = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        if it.get("type") == "equation":
            expr = (it.get("equation") or {}).get("expression", "")
            out.append(f"${expr}$")
            continue
        content = it.get("plain_text", "")
        ann = it.get("annotations") or {}
        content = _annotate(content, ann)
        href = it.get("href")
        if href:
            content = f"[{content}]({href})"
        out.append(content)
    return "".join(out)


# --------------------------------------------------------------------------- #
# 블록 핸들러 — 각자 (block, render_children) -> 마크다운 라인들
# --------------------------------------------------------------------------- #


def _rt(block: dict, key: str) -> str:
    return rich_text((block.get(key) or {}).get("rich_text"))


def _para(b, _):
    return [_rt(b, "paragraph")]


def _h1(b, _):
    return [f"# {_rt(b, 'heading_1')}"]


def _h2(b, _):
    return [f"## {_rt(b, 'heading_2')}"]


def _h3(b, _):
    return [f"### {_rt(b, 'heading_3')}"]


def _bullet(b, children):
    return [f"- {_rt(b, 'bulleted_list_item')}", *_indent(children)]


def _numbered(b, children):
    return [f"1. {_rt(b, 'numbered_list_item')}", *_indent(children)]


def _todo(b, children):
    done = (b.get("to_do") or {}).get("checked")
    box = "[x]" if done else "[ ]"
    return [f"- {box} {_rt(b, 'to_do')}", *_indent(children)]


def _quote(b, _):
    return [f"> {_rt(b, 'quote')}"]


def _callout(b, children):
    icon = ((b.get("callout") or {}).get("icon") or {}).get("emoji", "💡")
    return [f"> {icon} {_rt(b, 'callout')}", *([">" ] + _indent(children) if children else [])]


def _toggle(b, children):
    return [f"<details><summary>{_rt(b, 'toggle')}</summary>", "", *children, "</details>"]


def _code(b, _):
    data = b.get("code") or {}
    lang = data.get("language", "")
    lang = "" if lang in ("plain text", "plaintext") else lang
    body = rich_text(data.get("rich_text"))
    return [f"```{lang}", body, "```"]


def _equation(b, _):
    expr = (b.get("equation") or {}).get("expression", "")
    return [f"$$\n{expr}\n$$"]


def _divider(b, _):
    return ["---"]


def _image(b, _):
    data = b.get("image") or {}
    url = (data.get("file") or data.get("external") or {}).get("url", "")
    cap = rich_text(data.get("caption")) or "image"
    return [f"![{cap}]({url})"]


def _link_block(key: str):
    def handler(b, _):
        data = b.get(key) or {}
        url = data.get("url") or (data.get("external") or {}).get("url", "")
        return [f"[{key}]({url})"] if url else []

    return handler


HANDLERS: dict[str, Callable[[dict, list[str]], list[str]]] = {
    "paragraph": _para,
    "heading_1": _h1,
    "heading_2": _h2,
    "heading_3": _h3,
    "bulleted_list_item": _bullet,
    "numbered_list_item": _numbered,
    "to_do": _todo,
    "quote": _quote,
    "callout": _callout,
    "toggle": _toggle,
    "code": _code,
    "equation": _equation,
    "divider": _divider,
    "image": _image,
    "bookmark": _link_block("bookmark"),
    "embed": _link_block("embed"),
}


def _indent(lines: list[str], prefix: str = "  ") -> list[str]:
    return [f"{prefix}{ln}" if ln else ln for ln in lines]


# --------------------------------------------------------------------------- #
# 페이지 -> 마크다운
# --------------------------------------------------------------------------- #


def _fetch_children(client, block_id: str) -> list[dict]:
    out: list[dict] = []
    cursor = None
    while True:
        kwargs: dict[str, Any] = {"block_id": block_id, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor
        resp = client.blocks.children.list(**kwargs)
        out.extend(resp.get("results", []))
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
    return out


def blocks_to_markdown(client, block_id: str) -> str:
    """block_id(페이지 또는 블록)의 자식들을 재귀적으로 마크다운으로."""
    lines: list[str] = []
    prev_type: str | None = None

    for block in _fetch_children(client, block_id):
        btype = block.get("type")
        children: list[str] = []
        if block.get("has_children") and btype not in ("table",):
            child_md = blocks_to_markdown(client, block["id"])
            children = child_md.split("\n") if child_md else []

        handler = HANDLERS.get(btype)
        if handler is None:
            # 미지원 타입: rich_text가 있으면 단락으로, 없으면 스킵
            rt = (block.get(btype) or {}).get("rich_text") if isinstance(block.get(btype), dict) else None
            rendered = [rich_text(rt)] if rt else []
        else:
            rendered = handler(block, children)

        # 리스트가 아닌 블록 사이에는 빈 줄
        list_types = {"bulleted_list_item", "numbered_list_item", "to_do"}
        if lines and not (btype in list_types and prev_type in list_types):
            lines.append("")
        lines.extend(rendered)
        prev_type = btype

    return "\n".join(lines).strip()
