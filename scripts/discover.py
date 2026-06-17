#!/usr/bin/env python3
"""④ 신규 논문/토픽 발굴 — arxiv 최신 검색으로 '공부할 거리' 큐를 채운다.

사용:
    python scripts/discover.py "late interaction retrieval"
    python scripts/discover.py "reinforcement learning LLM" --days 30 --write

--write 시 queue/to_study.md 에 후보를 append (이미 위키에 있는 건 제외).
정기 실행(예: 주 1회 세션)으로 흐름을 놓치지 않게 한다.
웹 전반 검색/심층 조사는 세션에서 WebSearch + deep-research 스킬로 보강.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rich.console import Console  # noqa: E402

from mang2wiki.frontmatter import iter_nodes  # noqa: E402
from mang2wiki.models import slugify  # noqa: E402
from mang2wiki.paths import queue_path, wiki_dir  # noqa: E402

console = Console()


def existing_ids() -> set[str]:
    ids = set()
    for n in iter_nodes(wiki_dir()):
        ids.add(n.id)
        if n.arxiv:
            ids.add(n.arxiv)
    return ids


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--days", type=int, default=60, help="최근 N일 내 논문만")
    ap.add_argument("--max", type=int, default=15)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    import arxiv

    client = arxiv.Client()
    s = arxiv.Search(
        query=args.query, max_results=args.max * 2, sort_by=arxiv.SortCriterion.SubmittedDate
    )
    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    have = existing_ids()

    new_rows = []
    for r in client.results(s):
        if r.published < cutoff:
            continue
        aid = r.entry_id.split("/abs/")[-1].split("v")[0]
        if aid in have or slugify(r.title) in have:
            continue
        new_rows.append((aid, r.published.date(), r.title))
        if len(new_rows) >= args.max:
            break

    if not new_rows:
        console.print("[yellow]신규 후보 없음[/yellow] (이미 위키에 있거나 기간 밖)")
        return 0

    console.print(f"[bold]신규 후보 {len(new_rows)}건[/bold] (query: {args.query})")
    lines = []
    for aid, pub, title in new_rows:
        console.print(f"  - {pub} [{aid}] {title}")
        lines.append(f"- [ ] **{title}** — arxiv:{aid} ({pub}) · query: `{args.query}`")

    if args.write:
        queue = queue_path()
        queue.parent.mkdir(parents=True, exist_ok=True)
        header = "" if queue.exists() else "# 공부할 거리 (discover 큐)\n\n"
        with queue.open("a", encoding="utf-8") as f:
            f.write(header + f"\n## {datetime.now().date()} · {args.query}\n" + "\n".join(lines) + "\n")
        console.print(f"\n[green]추가[/green]: {queue}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
