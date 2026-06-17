#!/usr/bin/env python3
"""분류 정합성 lint — read-only 리포트 (자동수정 없음).

    python scripts/wiki_lint.py

전 노드를 순회하며 ① 미허용 tag, ② 내용기반 status 제안 불일치를 보고한다.
허용 tag 목록은 knowledge/wiki/_taxonomy.yml.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rich.console import Console  # noqa: E402

from mang2wiki.frontmatter import iter_nodes  # noqa: E402
from mang2wiki.models import WikiNode  # noqa: E402
from mang2wiki.paths import wiki_dir  # noqa: E402
from mang2wiki.taxonomy import (  # noqa: E402
    load_allowed_tags,
    status_mismatch,
    unknown_tags,
)

console = Console()


def lint_report(nodes: Iterable[WikiNode], allowed: set[str]) -> list[tuple[str, str]]:
    """(node_id, message) 문제 목록. 문제 없으면 빈 리스트."""
    issues: list[tuple[str, str]] = []
    for n in nodes:
        unk = unknown_tags(n, allowed)
        if unk:
            issues.append((n.id, f"미허용 tag: {', '.join(unk)}"))
        sug = status_mismatch(n)
        if sug is not None:
            issues.append((n.id, f"status 제안: {n.status.value} → {sug.value}"))
    return issues


def main() -> int:
    allowed = load_allowed_tags()
    nodes = list(iter_nodes(wiki_dir()))
    report = lint_report(nodes, allowed)

    if not report:
        console.print(f"[green]정합성 OK[/green] · 노드 {len(nodes)}개 · 허용 tag {len(allowed)}개")
        return 0

    console.print(f"[yellow]분류 점검 {len(report)}건[/yellow] (노드 {len(nodes)}개)")
    for nid, msg in report:
        console.print(f"  [bold]{nid}[/bold] — {msg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
