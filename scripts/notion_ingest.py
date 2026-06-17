#!/usr/bin/env python3
"""① Notion 'Sources' 보드를 읽어 wiki/ 마크다운 스텁을 생성한다.

사용:
    pip install -e .
    cp .env.example .env  &&  # NOTION_API_KEY, NOTION_DATABASE_ID 채우기
    python scripts/notion_ingest.py            # 미리보기(dry-run)
    python scripts/notion_ingest.py --write     # 실제 파일 생성
    python scripts/notion_ingest.py --write --overwrite   # 본문까지 덮어쓰기(주의)

원칙: 이미 분석을 채운 파일(완료/분석중)은 기본적으로 건드리지 않는다.
      메타데이터(status/category/tags)만 갱신하고 본문은 보존.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
from rich.console import Console  # noqa: E402

from mang2wiki.frontmatter import dump_node, load_node  # noqa: E402
from mang2wiki.models import NodeType  # noqa: E402
from mang2wiki.notion import fetch_pages  # noqa: E402
from mang2wiki.paths import wiki_dir  # noqa: E402
from mang2wiki.templates import stub_body  # noqa: E402

console = Console()
SUBDIR = {NodeType.TOPIC: "topics", NodeType.PAPER: "papers", NodeType.CONCEPT: "concepts"}


def target_path(node) -> Path:
    return wiki_dir() / SUBDIR[node.type] / node.id / "index.md"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="실제 파일 생성/갱신")
    ap.add_argument("--overwrite", action="store_true", help="기존 본문까지 덮어쓰기")
    ap.add_argument("--type", default="guess", choices=["guess", "paper", "concept", "topic"])
    args = ap.parse_args()

    load_dotenv(ROOT / ".env")

    created = updated = skipped = 0
    for node in fetch_pages(type_hint=args.type):
        path = target_path(node)
        exists = path.exists()

        if exists and not args.overwrite:
            # 메타만 머지, 본문 보존
            old = load_node(path)
            node.body = old.body
            node.created = old.created or node.created
            # 사람이/내가 손댄 분류는 존중
            node.type = old.type
            node.parents = old.parents or node.parents
            node.relations = old.relations or node.relations
            path = target_path(node)
            action = "update"
        else:
            node.body = stub_body(node)
            action = "create"

        tag = f"[dim]{node.category or '-'}[/dim]"
        console.print(f"  {action:6} {node.type.value:7} {node.id}  {tag}")

        if args.write:
            dump_node(node, path)
            created += action == "create"
            updated += action == "update"
        else:
            skipped += 1

    if args.write:
        console.print(f"\n[green]완료[/green]: 생성 {created} · 갱신 {updated}")
    else:
        console.print(f"\n[yellow]dry-run[/yellow]: {skipped}건 미리보기. --write 로 실제 반영.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
