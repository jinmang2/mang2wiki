"""마크다운 위키 -> 지식 그래프 빌드 및 직렬화.

frontmatter의 parents/relations + 본문 [[wikilink]] 를 모아 방향 그래프를 만든다.
"""

from __future__ import annotations

import json
from pathlib import Path

import networkx as nx

from .frontmatter import extract_wikilinks, iter_nodes


def build_graph(wiki_dir: str | Path) -> nx.MultiDiGraph:
    g = nx.MultiDiGraph()
    nodes = list(iter_nodes(wiki_dir))

    for n in nodes:
        g.add_node(
            n.id,
            type=n.type.value,
            title=n.title,
            status=n.status.value,
            category=n.category,
            arxiv=n.arxiv,
            tags=n.tags,
        )

    for n in nodes:
        for src, dst, rel in n.edges():
            g.add_edge(src, dst, key=rel, relation=rel)
        for ref in extract_wikilinks(n.body):
            if ref != n.id:
                g.add_edge(n.id, ref, key="references", relation="references")

    return g


def dangling_links(g: nx.MultiDiGraph) -> list[tuple[str, str, str]]:
    """존재하지 않는 노드를 가리키는 엣지 (= 아직 안 만든 페이지). 다음에 만들 후보.

    실제 마크다운 파일이 있는 노드만 '정의됨'으로 본다. 엣지로 자동 추가된
    스텁 노드(파일 없음)는 ``type`` 속성이 없으므로 dangling 대상.
    """
    defined = {n for n in g.nodes if g.nodes[n].get("type")}
    out = []
    for src, dst, data in g.edges(data=True):
        if dst not in defined:
            out.append((src, dst, data.get("relation", "")))
    return sorted(set(out))


def to_json(g: nx.MultiDiGraph) -> dict:
    return {
        "nodes": [{"id": n, **g.nodes[n]} for n in g.nodes],
        "edges": [
            {"source": s, "target": t, "relation": d.get("relation")}
            for s, t, d in g.edges(data=True)
        ],
    }


def save_json(g: nx.MultiDiGraph, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_json(g), ensure_ascii=False, indent=2), encoding="utf-8")
    return path
