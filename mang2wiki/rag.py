"""Graph-RAG 검색.

초기 버전은 의존성을 가볍게 가져가기 위해 키워드 점수 + 그래프 이웃 확장으로 구현한다.
(추후 임베딩 기반 시드 선택으로 교체 가능 — retrieve() 시그니처는 유지.)

흐름:
  1) 질의 토큰과 노드(title/tags/category/body) 매칭으로 시드 노드 점수화
  2) 상위 시드에서 그래프를 N-hop 확장해 관련 노드 수집
  3) 각 노드의 마크다운을 컨텍스트 번들로 반환
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import networkx as nx

from .frontmatter import iter_nodes
from .graph import build_graph

_TOKEN_RE = re.compile(r"[a-zA-Z0-9가-힣]+")


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text or "")}


@dataclass
class Hit:
    id: str
    title: str
    score: float
    hops: int  # 시드(0)로부터의 거리


class GraphRAG:
    def __init__(self, wiki_dir: str | Path):
        self.wiki_dir = Path(wiki_dir)
        self.nodes = {n.id: n for n in iter_nodes(wiki_dir)}
        self.graph = build_graph(wiki_dir)
        # 검색용 토큰 인덱스 (제목/태그/카테고리에 가중치)
        self._index: dict[str, set[str]] = {}
        for nid, n in self.nodes.items():
            toks = _tokens(n.title) | _tokens(" ".join(n.tags)) | _tokens(n.category or "")
            toks |= _tokens(n.body)
            self._index[nid] = toks

    def _seed_scores(self, query: str) -> list[tuple[str, float]]:
        q = _tokens(query)
        scored = []
        for nid, n in self.nodes.items():
            title_t = _tokens(n.title) | _tokens(" ".join(n.tags))
            body_t = self._index[nid]
            score = 3.0 * len(q & title_t) + 1.0 * len(q & body_t)
            if score:
                scored.append((nid, score))
        return sorted(scored, key=lambda x: x[1], reverse=True)

    def retrieve(self, query: str, k: int = 6, hops: int = 1) -> list[Hit]:
        """질의에 대해 관련 노드를 점수순으로 반환 (그래프 이웃 확장 포함)."""
        seeds = self._seed_scores(query)[:k]
        und = self.graph.to_undirected(as_view=True)
        hits: dict[str, Hit] = {}

        for nid, score in seeds:
            hits[nid] = Hit(nid, self.nodes[nid].title, score, 0)

        for nid, score in seeds:
            try:
                lengths = nx.single_source_shortest_path_length(und, nid, cutoff=hops)
            except nx.NodeNotFound:
                continue
            for neighbor, dist in lengths.items():
                if dist == 0 or neighbor not in self.nodes:
                    continue
                inherited = score / (dist + 1)
                if neighbor not in hits or hits[neighbor].score < inherited:
                    prev_hops = hits[neighbor].hops if neighbor in hits else dist
                    hits[neighbor] = Hit(
                        neighbor, self.nodes[neighbor].title, inherited, min(prev_hops, dist)
                    )

        return sorted(hits.values(), key=lambda h: (-h.score, h.hops))

    def context(self, query: str, k: int = 6, hops: int = 1, max_chars: int = 12000) -> str:
        """retrieve 결과를 LLM 컨텍스트용 마크다운 번들로 합친다."""
        hits = self.retrieve(query, k=k, hops=hops)
        chunks, total = [], 0
        for h in hits:
            n = self.nodes[h.id]
            block = f"## [{n.id}] {n.title} ({n.type.value}, {h.hops}-hop)\n{n.body.strip()}\n"
            if total + len(block) > max_chars:
                break
            chunks.append(block)
            total += len(block)
        return "\n---\n".join(chunks)
