"""Headless smoke test: imports + scanner + tree layout on a tiny tree.

Does NOT open the Qt window — exercises non-UI logic only.
Run with: python tests/smoke_test.py
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from scanner import ScanWorker, Node  # noqa: E402


def _build_fixture(root: pathlib.Path) -> None:
    (root / "a").mkdir()
    (root / "a" / "f1.txt").write_bytes(b"x" * 100)
    (root / "a" / "f2.bin").write_bytes(b"y" * 400)
    (root / "b").mkdir()
    (root / "b" / "c").mkdir()
    (root / "b" / "c" / "deep.log").write_bytes(b"z" * 1000)
    (root / "lonely.md").write_bytes(b"# hi\n")


def _ensure_app():
    return QApplication.instance() or QApplication([])


def _run_sync(path: str) -> Node:
    _ensure_app()  # held alive by Qt's app registry
    worker = ScanWorker(path)
    result = {"node": None, "err": None}
    worker.finished.connect(lambda n: result.__setitem__("node", n))
    worker.failed.connect(lambda m: result.__setitem__("err", m))
    worker.run()
    if result["err"]:
        raise RuntimeError(result["err"])
    assert result["node"] is not None
    return result["node"]


def test_scanner_totals():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        _build_fixture(root)
        node = _run_sync(str(root))
        assert node.is_dir
        names = {c.name for c in node.children}
        assert names == {"a", "b", "lonely.md"}
        # 100 + 400 + 1000 + 5 = 1505
        assert node.size == 1505, node.size
        a = next(c for c in node.children if c.name == "a")
        b = next(c for c in node.children if c.name == "b")
        assert a.size == 500 and b.size == 1000
        assert b.children[0].name == "c" and b.children[0].size == 1000
        print(f"[ok] scanner: root={node.size} a={a.size} b={b.size}")


def test_tree_layout():
    _ensure_app()
    from treeview import TreeView

    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        _build_fixture(root)
        node = _run_sync(str(root))

        view = TreeView()
        view.set_root(node)

        # Root + 3 children placed when root is expanded by default.
        assert id(node) in view._positions, "root has no position"
        for child in node.children:
            assert id(child) in view._positions, f"{child.name} not laid out"

        # Root x should be 0 (column 0); children x is one step right.
        rx, _ry = view._positions[id(node)]
        assert rx == 0
        for child in node.children:
            cx, _cy = view._positions[id(child)]
            assert cx == view.NODE_W + view.X_GAP, cx

        # Expanding b should place its child 'c' another column right.
        b = next(c for c in node.children if c.name == "b")
        view.toggle(b)  # expand
        assert view.is_expanded(b)
        c = b.children[0]
        cx, _cy = view._positions[id(c)]
        assert cx == 2 * (view.NODE_W + view.X_GAP), cx

        # And expanding c places its file one more column right.
        view.toggle(c)
        deep = c.children[0]
        dx, _dy = view._positions[id(deep)]
        assert dx == 3 * (view.NODE_W + view.X_GAP), dx

        # Collapsing b drops descendants from the layout.
        view.toggle(b)
        assert not view.is_expanded(b)
        # c may still have a stale entry from earlier layout; rebuild clears it.
        # The contract is: after rebuild, only currently-visible nodes are present.
        present = set(view._positions.keys())
        # b is still visible (it's a direct child of root), c is not.
        assert id(b) in present
        assert id(c) not in present

        print(f"[ok] tree layout: {len(view._positions)} nodes placed")


def test_main_imports_cleanly():
    import main
    assert hasattr(main, "MainWindow")
    assert hasattr(main, "main")
    print("[ok] main module imports and exposes expected symbols")


if __name__ == "__main__":
    test_scanner_totals()
    test_tree_layout()
    test_main_imports_cleanly()
    print("\nAll smoke tests passed.")
