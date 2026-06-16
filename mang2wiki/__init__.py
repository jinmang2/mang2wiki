"""mang2wiki — LLM 연구 위키 코어 라이브러리.

진실의 원천은 ``wiki/**.md`` (frontmatter + [[wikilink]]).
이 패키지는 그 마크다운을 읽고/쓰고/그래프로 엮는 도구를 제공한다.
"""

from .models import NodeType, Status, WikiNode
from .frontmatter import load_node, dump_node, iter_nodes

__all__ = [
    "NodeType",
    "Status",
    "WikiNode",
    "load_node",
    "dump_node",
    "iter_nodes",
]
