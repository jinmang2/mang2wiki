from pathlib import Path

from mang2wiki import paths


def test_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("MANG2WIKI_KNOWLEDGE", str(tmp_path))
    root = tmp_path.resolve()
    assert paths.knowledge_dir() == root
    assert paths.wiki_dir() == root / "wiki"
    assert paths.graph_path() == root / "graph" / "graph.json"
    assert paths.queue_path() == root / "queue" / "to_study.md"


def test_default_is_repo_knowledge(monkeypatch):
    monkeypatch.delenv("MANG2WIKI_KNOWLEDGE", raising=False)
    d = paths.knowledge_dir()
    assert d.name == "knowledge"
    assert isinstance(d, Path)
