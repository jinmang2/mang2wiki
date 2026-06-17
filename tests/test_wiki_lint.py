from mang2wiki.models import NodeType, Status, WikiNode
from scripts.wiki_lint import lint_report


def _node(**kw):
    base = dict(id="x", type=NodeType.PAPER, title="x", body="")
    base.update(kw)
    return WikiNode(**base)


def test_lint_report_flags_unknown_tag_and_status():
    allowed = {"retrieval"}
    nodes = [
        _node(id="ok", tags=["retrieval"], status=Status.TODO, body="## TL;DR\n"),
        _node(id="badtag", tags=["retrieval", "weird"], status=Status.IN_PROGRESS, body="x 실제"),
        _node(id="badstatus", tags=["retrieval"], status=Status.TODO, body="## 개요\n실제 내용"),
    ]
    report = lint_report(nodes, allowed)
    ids = {nid for nid, _ in report}
    assert "ok" not in ids
    assert "badtag" in ids
    assert "badstatus" in ids
    msgs = {nid: msg for nid, msg in report}
    assert "weird" in msgs["badtag"]
    assert "검토 대기 중" in msgs["badstatus"]
