#!/usr/bin/env python3
"""1회성: flat wiki/graph/queue -> knowledge/ 노드 폴더 트리.

    python scripts/migrate_to_node_folders.py --dest /tmp/m2w-knowledge

wiki/<type>/<id>.md  ->  <dest>/wiki/<type>/<id>/index.md
_templates/·graph/·queue/ 는 경로 유지하여 <dest> 아래로 복사.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def build_knowledge_tree(src_root: Path, dest_root: Path) -> int:
    src_root = Path(src_root)
    dest_root = Path(dest_root)
    moved = 0

    wiki = src_root / "wiki"
    if wiki.is_dir():
        for md in sorted(wiki.rglob("*.md")):
            rel = md.relative_to(wiki)
            if rel.parts and rel.parts[0] == "_templates":
                target = dest_root / "wiki" / rel  # 템플릿은 경로 유지
            else:
                # papers/colbert.md -> papers/colbert/index.md
                target = dest_root / "wiki" / rel.with_suffix("") / "index.md"
                moved += 1
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(md, target)

    for sub in ("graph", "queue"):
        s = src_root / sub
        if s.is_dir():
            shutil.copytree(s, dest_root / sub, dirs_exist_ok=True)

    return moved


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(ROOT), help="공개 repo 루트 (기본: 현재 repo)")
    ap.add_argument("--dest", required=True, help="생성할 knowledge 트리 위치")
    args = ap.parse_args()

    moved = build_knowledge_tree(Path(args.src), Path(args.dest))
    print(f"노드 {moved}개를 <id>/index.md 로 변환 → {args.dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
