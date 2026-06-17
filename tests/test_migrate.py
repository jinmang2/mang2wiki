from scripts.migrate_to_node_folders import build_knowledge_tree


def _w(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_flat_md_becomes_index_md(tmp_path):
    src = tmp_path / "src"
    _w(src / "wiki" / "papers" / "colbert.md", "---\nid: colbert\ntype: paper\n---\n\n본문\n")
    _w(src / "wiki" / "_templates" / "paper.md", "tmpl\n")
    _w(src / "graph" / "graph.json", "{}\n")
    _w(src / "queue" / "to_study.md", "# 큐\n")

    dest = tmp_path / "knowledge"
    moved = build_knowledge_tree(src, dest)

    assert (dest / "wiki" / "papers" / "colbert" / "index.md").read_text(
        encoding="utf-8"
    ).strip().endswith("본문")
    # 템플릿/그래프/큐는 경로 유지 복사
    assert (dest / "wiki" / "_templates" / "paper.md").exists()
    assert (dest / "graph" / "graph.json").exists()
    assert (dest / "queue" / "to_study.md").exists()
    # 노드 변환 카운트 반환
    assert moved == 1
