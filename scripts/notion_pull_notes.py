#!/usr/bin/env python3
"""② Notion 페이지 *본문*을 끌어와 로컬 전용 knowledge/notes/<id>.md 로 저장.

ingest(notion_ingest.py)는 메타데이터만 가져와 wiki/ 스텁을 만든다.
이 스크립트는 그와 별개로, 이미 작성해 둔 Notion 페이지 본문을 마크다운으로
끌어와 로컬 작업공간(knowledge/, gitignore)에 보존한다. 공개 git에는 올리지 않는다.

사용:
    python scripts/notion_pull_notes.py --ids grpo,dapo        # 특정 노드
    python scripts/notion_pull_notes.py --tag RL               # 태그 필터
    python scripts/notion_pull_notes.py --status 완료          # 상태 필터
    python scripts/notion_pull_notes.py --all                  # notion_id 있는 전체
    python scripts/notion_pull_notes.py --tag RL --overwrite   # 기존 노트 덮어쓰기
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
from rich.console import Console  # noqa: E402

from mang2wiki.frontmatter import iter_nodes  # noqa: E402
from mang2wiki.notion_blocks import blocks_to_markdown  # noqa: E402

console = Console()
WIKI = ROOT / "wiki"
NOTES = ROOT / "knowledge" / "notes"


def _selected(node, args) -> bool:
    if not node.notion_id:
        return False
    if args.ids:
        return node.id in args.ids
    if args.tag:
        return args.tag in node.tags
    if args.category:
        return node.category == args.category
    if args.status:
        return node.status.value == args.status
    return bool(args.all)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", type=lambda s: set(s.split(",")), default=None)
    ap.add_argument("--tag", default=None)
    ap.add_argument("--category", default=None)
    ap.add_argument("--status", default=None)
    ap.add_argument("--all", action="store_true", help="notion_id 있는 모든 노드")
    ap.add_argument("--overwrite", action="store_true", help="기존 노트 덮어쓰기")
    ap.add_argument("--write", action="store_true", help="실제 저장 (없으면 dry-run)")
    args = ap.parse_args()

    if not any([args.ids, args.tag, args.category, args.status, args.all]):
        ap.error("선택자가 필요합니다: --ids/--tag/--category/--status/--all 중 하나")

    load_dotenv(ROOT / ".env")

    from notion_client import Client
    import os

    client = Client(auth=os.environ["NOTION_API_KEY"])

    targets = [n for n in iter_nodes(WIKI) if _selected(n, args)]
    console.print(f"[cyan]대상 {len(targets)}개[/cyan] (notion_id 보유)")

    pulled = skipped = empty = 0
    for n in targets:
        dest = NOTES / f"{n.id}.md"
        if dest.exists() and not args.overwrite:
            console.print(f"  skip   {n.id} (이미 있음, --overwrite 로 갱신)")
            skipped += 1
            continue

        body = blocks_to_markdown(client, n.notion_id) if args.write else ""
        if args.write and not body:
            console.print(f"  [dim]empty  {n.id} (Notion 본문 없음)[/dim]")
            empty += 1
            continue

        console.print(f"  pull   {n.id}  ({len(body)} chars)" if args.write else f"  would pull {n.id}")

        if args.write:
            dest.parent.mkdir(parents=True, exist_ok=True)
            header = (
                f"---\nid: {n.id}\nsource: notion\nnotion_id: {n.notion_id}\n"
                f"wiki: wiki/{ {'paper':'papers','concept':'concepts','topic':'topics'}[n.type.value] }/{n.id}.md\n"
                f"pulled: '{date.today().isoformat()}'\n---\n\n"
                f"# {n.title}\n\n"
            )
            dest.write_text(header + body + "\n", encoding="utf-8")
            pulled += 1

    if args.write:
        console.print(f"\n[green]완료[/green]: pull {pulled} · skip {skipped} · empty {empty}")
    else:
        console.print(f"\n[yellow]dry-run[/yellow]: --write 로 실제 저장")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
