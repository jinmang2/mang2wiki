from mang2wiki import taxonomy
from mang2wiki.models import NodeType, Status, WikiNode


def _node(**kw):
    base = dict(id="x", type=NodeType.PAPER, title="x", body="")
    base.update(kw)
    return WikiNode(**base)


def test_unknown_tags():
    allowed = {"retrieval", "ranking"}
    n = _node(tags=["retrieval", "weird", "ranking", "bogus"])
    assert taxonomy.unknown_tags(n, allowed) == ["weird", "bogus"]
    assert taxonomy.unknown_tags(_node(tags=["retrieval"]), allowed) == []


def test_suggest_status_empty_body():
    assert taxonomy.suggest_status(_node(body="")) is Status.TODO
    # 헤딩/인용/주석/공백만 있으면 비어있는 것으로 본다
    only_scaffold = "## TL;DR\n\n> **status**: 시작 전\n\n<!-- 메모 -->\n"
    assert taxonomy.suggest_status(_node(body=only_scaffold)) is Status.TODO


def test_suggest_status_with_content():
    body = "## TL;DR\n질의·문서 토큰을 임베딩해 MaxSim으로 점수화한다.\n"
    assert taxonomy.suggest_status(_node(body=body)) is Status.IN_PROGRESS


def test_suggest_status_never_done():
    big = "## 개요\n" + ("실제 분석 내용 " * 200)
    assert taxonomy.suggest_status(_node(body=big)) is not Status.DONE


def test_status_mismatch():
    body = "## 개요\n실제 내용이 있다.\n"
    # 시작 전인데 본문 있음 -> 제안
    assert taxonomy.status_mismatch(_node(status=Status.TODO, body=body)) is Status.IN_PROGRESS
    # 이미 검토 대기 중 / 완료 -> 불일치로 보지 않음
    assert taxonomy.status_mismatch(_node(status=Status.IN_PROGRESS, body=body)) is None
    assert taxonomy.status_mismatch(_node(status=Status.DONE, body=body)) is None
    # 시작 전이고 본문도 비었음 -> 일치
    assert taxonomy.status_mismatch(_node(status=Status.TODO, body="## TL;DR\n")) is None


def test_load_allowed_tags(tmp_path, monkeypatch):
    monkeypatch.setenv("MANG2WIKI_KNOWLEDGE", str(tmp_path))
    (tmp_path / "wiki").mkdir()
    (tmp_path / "wiki" / "_taxonomy.yml").write_text(
        "tags:\n  - retrieval\n  - ranking\n", encoding="utf-8"
    )
    assert taxonomy.load_allowed_tags() == {"retrieval", "ranking"}


def test_load_allowed_tags_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("MANG2WIKI_KNOWLEDGE", str(tmp_path))
    assert taxonomy.load_allowed_tags() == set()
