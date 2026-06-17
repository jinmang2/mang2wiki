"""위키 노드 데이터 모델.

각 마크다운 파일 = 하나의 WikiNode. frontmatter가 메타데이터, 본문이 분석 내용.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class NodeType(str, Enum):
    TOPIC = "topic"  # 상위 토픽 (구 is_high_level_topic). 예: late-interaction, RL
    PAPER = "paper"  # 개별 논문. 예: SPLADE, ColBERT
    CONCEPT = "concept"  # 개념/기법. 예: continuous batching, MIPS


class Status(str, Enum):
    """Notion 상태값과 1:1 매핑 (한글 표기 유지)."""

    TODO = "시작 전"
    IN_PROGRESS = "분석 중"
    DONE = "완료"

    @classmethod
    def coerce(cls, value: str | None) -> "Status":
        if not value:
            return cls.TODO
        v = value.strip()
        for s in cls:
            if v == s.value:
                return s
        # 영문/기타 표기 보정
        mapping = {
            "todo": cls.TODO,
            "not started": cls.TODO,
            "in progress": cls.IN_PROGRESS,
            "doing": cls.IN_PROGRESS,
            "done": cls.DONE,
            "complete": cls.DONE,
        }
        return mapping.get(v.lower(), cls.TODO)


# frontmatter에서 허용하는 관계(엣지) 타입. 그래프 빌드시 그대로 엣지 라벨이 됨.
RELATION_TYPES = {
    "extends",  # 선행 연구를 확장 (SPLADE -> SPLADE-v2)
    "cites",  # 인용/기반
    "inference",  # 추론/서빙 변형 (SPLADE -> SPLADE-doc)
    "variant_of",  # 변종
    "uses",  # 특정 기법/개념 사용 (ColBERT uses late-interaction)
    "compares",  # 비교 대상
    "supersedes",  # 대체
}


def slugify(text: str) -> str:
    """제목 -> 파일/노드 id. 영문 소문자+하이픈, 한글은 유지."""
    text = text.strip().lower()
    text = re.sub(r"[\s_/]+", "-", text)
    text = re.sub(r"[^\w\-가-힣]", "", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or "untitled"


@dataclass
class WikiNode:
    id: str
    type: NodeType
    title: str
    status: Status = Status.TODO
    category: str | None = None  # Notion 보드 컬럼 (inference, RAG, RL, ...)
    arxiv: str | None = None  # arxiv id (예: 2107.05720)
    code: str | None = None  # 공식 코드 URL
    parents: list[str] = field(default_factory=list)  # 상위 토픽 id 들
    relations: dict[str, list[str]] = field(default_factory=dict)  # {type: [id,...]}
    tags: list[str] = field(default_factory=list)
    notion_id: str | None = None
    created: str | None = None
    updated: str | None = None
    extra: dict = field(default_factory=dict)  # 기타 frontmatter 키 보존
    body: str = ""  # 마크다운 본문 (분석 내용)

    def __post_init__(self):
        if isinstance(self.type, str):
            self.type = NodeType(self.type)
        if isinstance(self.status, str):
            self.status = Status.coerce(self.status)
        # 미지정 관계 키 정리
        self.relations = {k: v for k, v in (self.relations or {}).items() if v}

    @property
    def filename(self) -> str:
        return f"{self.id}.md"

    def edges(self) -> list[tuple[str, str, str]]:
        """(source_id, target_id, relation) 리스트로 펼치기."""
        out: list[tuple[str, str, str]] = []
        for p in self.parents:
            out.append((self.id, p, "subtopic_of"))
        for rel, targets in self.relations.items():
            for t in targets:
                out.append((self.id, t, rel))
        return out
