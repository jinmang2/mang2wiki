from mang2wiki.frontmatter import iter_nodes
from mang2wiki.graph import build_graph, save_json, to_json


def _node(wiki, type_, nid, body):
    p = wiki / (type_ + "s") / nid / "index.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        f"---\nid: {nid}\ntype: {type_}\ntitle: {nid}\n---\n\n{body}\n",
        encoding="utf-8",
    )


def test_build_graph_from_node_folders(tmp_path):
    wiki = tmp_path / "wiki"
    _node(wiki, "paper", "colbert", "uses [[late-interaction]]")
    _node(wiki, "topic", "late-interaction", "허브 토픽")

    nodes = {n.id for n in iter_nodes(wiki)}
    assert nodes == {"colbert", "late-interaction"}

    g = build_graph(wiki)
    data = to_json(g)
    ids = {n["id"] for n in data["nodes"]}
    assert {"colbert", "late-interaction"} <= ids
    rels = {(e["source"], e["target"], e["relation"]) for e in data["edges"]}
    assert ("colbert", "late-interaction", "references") in rels

    out = save_json(g, tmp_path / "graph" / "graph.json")
    assert out.exists()
