#!/usr/bin/env python3
"""③ wiki/ 마크다운 -> 지식 그래프 인덱스 생성 + 상태 리포트.

사용:
    python scripts/build_graph.py
출력:
    knowledge/graph.json   (노드/엣지 — Graph-RAG 및 시각화용, 로컬 전용/gitignore)
    콘솔 리포트        (노드 수, 상태 분포, dangling 링크 = 다음에 만들 후보)
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rich.console import Console  # noqa: E402
from rich.table import Table  # noqa: E402

from mang2wiki.frontmatter import iter_nodes  # noqa: E402
from mang2wiki.graph import build_graph, dangling_links, save_json  # noqa: E402

console = Console()
WIKI = ROOT / "wiki"


def main() -> int:
    nodes = list(iter_nodes(WIKI))
    g = build_graph(WIKI)
    out = save_json(g, ROOT / "knowledge" / "graph.json")

    by_type = Counter(n.type.value for n in nodes)
    by_status = Counter(n.status.value for n in nodes)

    t = Table(title="mang2wiki 그래프 현황", show_header=True)
    t.add_column("metric")
    t.add_column("value", justify="right")
    t.add_row("노드", str(g.number_of_nodes()))
    t.add_row("엣지", str(g.number_of_edges()))
    for k, v in by_type.items():
        t.add_row(f"  type:{k}", str(v))
    for k, v in by_status.items():
        t.add_row(f"  status:{k}", str(v))
    console.print(t)

    dangling = dangling_links(g)
    if dangling:
        console.print("\n[yellow]아직 페이지 없는 참조 (다음 작성 후보):[/yellow]")
        for src, dst, rel in dangling[:30]:
            console.print(f"  {src} --{rel}--> [bold]{dst}[/bold]")
        if len(dangling) > 30:
            console.print(f"  ... 외 {len(dangling) - 30}건")

    console.print(f"\n[green]그래프 저장[/green]: {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
