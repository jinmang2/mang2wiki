from mang2wiki.frontmatter import iter_nodes, load_node


def _write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_iter_nodes_only_index_md(tmp_path):
    wiki = tmp_path / "wiki"
    _write(
        wiki / "papers" / "colbert" / "index.md",
        "---\nid: colbert\ntype: paper\ntitle: ColBERT\n---\n\n본문 [[late-interaction]]\n",
    )
    # 같은 폴더의 보조 파일은 노드가 아님
    _write(wiki / "papers" / "colbert" / "math.md", "# 수식\n")
    _write(wiki / "papers" / "colbert" / "tistory.md", "# 초안\n")
    # 템플릿은 제외
    _write(wiki / "_templates" / "paper.md", "---\ntype: paper\n---\nx\n")

    nodes = list(iter_nodes(wiki))
    assert [n.id for n in nodes] == ["colbert"]


def test_load_node_id_from_folder_when_index(tmp_path):
    d = tmp_path / "papers" / "splade"
    d.mkdir(parents=True)
    (d / "index.md").write_text(
        "---\ntype: paper\ntitle: SPLADE\n---\n\n본문\n", encoding="utf-8"
    )
    node = load_node(d / "index.md")
    assert node.id == "splade"
    assert node.title == "SPLADE"
