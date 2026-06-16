"""노드 타입별 본문 템플릿 (스텁 생성용).

정밀분석은 내가(Opus) 세션에서 이 골격을 채워 넣는다.
wiki/_templates/*.md 에 사람이 읽는 사본도 둔다.
"""

from __future__ import annotations

from .models import NodeType, WikiNode

_PAPER = """\
> **status**: {status} · **category**: {category} · arxiv: {arxiv} · code: {code}

## TL;DR
<!-- 한 문단 요약. 무엇을, 왜, 어떻게, 결과 -->

## 문제 정의 (Problem)

## 핵심 아이디어 (Key Idea)

## 수학적 정밀분석 (Math Deep-Dive)
<!-- objective / formulation / 주요 유도. $...$ 수식 사용 -->

## 아키텍처 · 알고리즘

## 공식 코드 분석 (Official Code Walkthrough)
<!-- 핵심 모듈/함수, 실제 구현이 논문과 다른 점 -->

## 실험 · 결과

## 그래프 상 위치 (Related Works)
<!-- 상위 토픽: [[...]], 확장: [[...]], 비교: [[...]] -->

## 한계 · 후속 연구

## 내 메모 · 열린 질문
"""

_CONCEPT = """\
> **status**: {status} · **category**: {category}

## 한 줄 정의

## 왜 필요한가 (Motivation)

## 동작 원리
<!-- 필요시 수식 $...$ -->

## 트레이드오프 · 변형

## 관련 개념 · 논문
<!-- [[...]] 로 연결 -->

## 내 메모
"""

_TOPIC = """\
> **status**: {status} · **category**: {category}
> 상위 토픽(is_high_level_topic) — 하위 논문/개념을 묶는 허브.

## 개요
<!-- 이 흐름이 풀려는 큰 문제와 갈래 -->

## 흐름 · 계보 (Timeline)
<!-- 시간순/계보. 각 항목 [[...]] 연결 -->

## 하위 노드
<!-- parents 로 이 토픽을 가리키는 노드들이 자동으로 그래프에 모임 -->

## 핵심 비교 표

## 미해결 · 다음에 볼 것
"""


def stub_body(node: WikiNode) -> str:
    tmpl = {NodeType.PAPER: _PAPER, NodeType.CONCEPT: _CONCEPT, NodeType.TOPIC: _TOPIC}[node.type]
    return tmpl.format(
        status=node.status.value,
        category=node.category or "-",
        arxiv=node.arxiv or "-",
        code=node.code or "-",
    )
