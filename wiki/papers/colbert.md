---
id: colbert
type: paper
title: "ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT"
status: 시작 전
category: information retrieval
arxiv: "2004.12832"
code: https://github.com/stanford-futuredata/ColBERT
parents: [late-interaction]
relations:
  uses: [late-interaction]
  cites: [bert]
tags: [retrieval, late-interaction, bert]
---

> **status**: 시작 전 · 이 파일은 그래프 동작 확인용 시드. 정밀분석은 세션에서 채움.

## TL;DR
질의·문서 토큰을 BERT로 임베딩하고, 질의 토큰마다 문서 토큰과의 최대 유사도(MaxSim)를
합산해 점수화하는 late interaction 검색 모델.

## 문제 정의 (Problem)

## 핵심 아이디어 (Key Idea)

## 수학적 정밀분석 (Math Deep-Dive)
<!-- MaxSim: score(q,d) = sum_i max_j (E_q_i · E_d_j) -->

## 아키텍처 · 알고리즘

## 공식 코드 분석 (Official Code Walkthrough)

## 실험 · 결과

## 그래프 상 위치 (Related Works)
상위 토픽: [[late-interaction]]

## 한계 · 후속 연구

## 내 메모 · 열린 질문
