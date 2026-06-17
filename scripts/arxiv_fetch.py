#!/usr/bin/env python3
"""② 논문 메타데이터(arxiv) + 공식 코드 후보를 가져와 분석 준비를 돕는다.

사용:
    python scripts/arxiv_fetch.py 2107.05720
    python scripts/arxiv_fetch.py "SPLADE sparse lexical"     # 제목 검색
    python scripts/arxiv_fetch.py 2107.05720 --node splade --write

--write 시: 해당 노드의 frontmatter(arxiv/code/title)를 채우고, abstract를 메모로 남긴다.
실제 정밀분석(수학/코드)은 이 메타를 받아 세션에서 내가 채운다.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rich.console import Console  # noqa: E402

from mang2wiki.paths import wiki_dir  # noqa: E402

console = Console()
ARXIV_ID_RE = re.compile(r"\d{4}\.\d{4,5}(v\d+)?")


def search(query: str):
    import arxiv  # 지연 import

    client = arxiv.Client()
    if ARXIV_ID_RE.fullmatch(query):
        s = arxiv.Search(id_list=[query])
    else:
        s = arxiv.Search(query=query, max_results=5, sort_by=arxiv.SortCriterion.Relevance)
    return list(client.results(s))


def github_from_text(text: str) -> str | None:
    m = re.search(r"https?://github\.com/[\w.-]+/[\w.-]+", text or "")
    return m.group(0).rstrip(".") if m else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query", help="arxiv id 또는 검색어")
    ap.add_argument("--node", help="갱신할 wiki 노드 id")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    results = search(args.query)
    if not results:
        console.print("[red]검색 결과 없음[/red]")
        return 1

    for i, r in enumerate(results):
        aid = r.entry_id.split("/abs/")[-1]
        code = github_from_text(r.summary) or github_from_text(r.comment or "")
        console.print(f"\n[bold]{i}. {r.title}[/bold]")
        console.print(f"   arxiv: {aid} · {r.published.date()}")
        console.print(f"   authors: {', '.join(a.name for a in r.authors[:5])}")
        if code:
            console.print(f"   code?: {code}")
        console.print(f"   {r.summary.strip()[:400]}...")

    if args.write and args.node:
        from mang2wiki.frontmatter import dump_node, load_node

        r = results[0]
        aid = r.entry_id.split("/abs/")[-1]
        path = next(wiki_dir().glob(f"**/{args.node}/index.md"), None)
        if not path:
            console.print(f"[red]노드 없음[/red]: {args.node}")
            return 1
        node = load_node(path)
        node.arxiv = aid.split("v")[0]
        node.code = node.code or github_from_text(r.summary)
        if "_abstract" not in node.body:
            node.body += f"\n\n<!-- _abstract (arxiv) -->\n> {r.summary.strip()}\n"
        node.extra["authors"] = [a.name for a in r.authors[:8]]
        node.extra["published"] = str(r.published.date())
        dump_node(node, path)
        console.print(f"\n[green]갱신[/green]: {path.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
