# 분류 규칙 (type / status / tags)

> 자동추정하지 않는다. type/status는 내가 규칙에 따라 수동 결정하고,
> lint(`scripts/wiki_lint.py`)는 점검·제안만 한다.

## type (판정 우선순위)

1. **topic** — 하위 노드를 묶는 허브. 다른 노드가 `parents`로 이 노드를 가리킨다.
   예: late-interaction, RL.
2. **concept** — 여러 논문/맥락에 걸쳐 재사용되는 기법·수식·메커니즘.
   예: MaxSim, continuous batching, MIPS.
3. **paper** — 위에 해당하지 않는, '단일 연구 산출물' 단위 노드. **arxiv 유무와 무관.**

판정: 허브인가? → topic / 재사용 기법인가? → concept / 그 외 단일 연구 → paper.

## status

- `시작 전` — 본문에 실질 내용 없음(스텁/빈 본문).
- `검토 대기 중` — 내용은 있으나 말투·정보 정리를 더 해야 함.
- `완료` — 내가 만족한 노드. **수동으로만 지정**(lint가 제안하지 않음).

lint는 "시작 전인데 본문 있음"을 `검토 대기 중` 후보로 제안한다.

## tags

통제 어휘. 허용 목록은 `knowledge/wiki/_taxonomy.yml`(비공개)의 `tags`.
목록 밖 tag는 lint가 경고한다. 새 tag가 필요하면 먼저 목록에 추가한다.
