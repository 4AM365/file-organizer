"""File Organizer — interactive filetree visualizer.

A standalone Qt application that scans a directory tree in the background and
renders it as a human-readable node-link tree diagram (boxes-and-lines), with
a synced hierarchical side panel.

Future hook: nodes carry a `dedup_tag` attribute which, when populated by the
deduplication pass, will be visually flagged in the tree.
"""
from __future__ import annotations

import os
import sys
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction, QColor, QKeySequence
from PySide6.QtWidgets import (QApplication, QMainWindow, QFileDialog,
                                QStatusBar, QToolBar, QLabel, QSplitter,
                                QTreeWidget, QTreeWidgetItem, QMessageBox,
                                QStyle)

from scanner import Node, ScanWorker
from treeview import TreeView, human_size


# ---------- side panel --------------------------------------------------------

class DirTree(QTreeWidget):
    """Hierarchical sidebar — lazy expansion, double-click jumps the main view."""

    jump_to = Signal(object)   # Node

    def __init__(self):
        super().__init__()
        self.setHeaderLabels(["Name", "Size"])
        self.setColumnWidth(0, 260)
        self.setAlternatingRowColors(True)
        self.itemExpanded.connect(self._on_expand)
        self.itemDoubleClicked.connect(self._on_double_click)

    def set_root(self, node: Optional[Node]) -> None:
        self.clear()
        if node is None:
            return
        top = self._make_item(node)
        self.addTopLevelItem(top)
        top.setExpanded(True)

    def _make_item(self, node: Node) -> QTreeWidgetItem:
        label = node.name + ("/" if node.is_dir else "")
        item = QTreeWidgetItem([label, human_size(node.size)])
        item.setData(0, Qt.UserRole, node)
        if node.is_dir and node.children:
            item.addChild(QTreeWidgetItem(["…"]))  # expand-arrow placeholder
        if node.dedup_tag:
            item.setForeground(0, QColor(200, 30, 30))
        return item

    def _on_expand(self, item: QTreeWidgetItem) -> None:
        if item.childCount() == 1 and item.child(0).text(0) == "…":
            item.takeChildren()
            node: Node = item.data(0, Qt.UserRole)
            kids = sorted(node.children, key=lambda c: (-c.size, c.name.lower()))
            for child in kids:
                item.addChild(self._make_item(child))

    def _on_double_click(self, item: QTreeWidgetItem, _column: int) -> None:
        node: Node = item.data(0, Qt.UserRole)
        if node is not None:
            self.jump_to.emit(node)


# ---------- main window -------------------------------------------------------

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Organizer — Filetree Visualizer")
        self.resize(1280, 800)

        self._root: Optional[Node] = None
        self._current: Optional[Node] = None
        self._worker: Optional[ScanWorker] = None
        self._thread: Optional[QThread] = None

        self._build_ui()

    # UI construction ---------------------------------------------------

    def _build_ui(self):
        style = self.style()

        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        act_open = QAction(style.standardIcon(QStyle.SP_DirOpenIcon),
                           "Open Folder…", self)
        act_open.setShortcut(QKeySequence.Open)
        act_open.triggered.connect(self.pick_folder)
        toolbar.addAction(act_open)

        self.act_up = QAction(style.standardIcon(QStyle.SP_ArrowUp), "Up", self)
        self.act_up.setShortcut("Alt+Up")
        self.act_up.triggered.connect(self.go_up)
        self.act_up.setEnabled(False)
        toolbar.addAction(self.act_up)

        self.act_home = QAction(style.standardIcon(QStyle.SP_DirHomeIcon),
                                "Root", self)
        self.act_home.setShortcut("Alt+Home")
        self.act_home.triggered.connect(self.go_home)
        self.act_home.setEnabled(False)
        toolbar.addAction(self.act_home)

        toolbar.addSeparator()
        self.breadcrumb = QLabel("  No folder loaded.  ")
        self.breadcrumb.setStyleSheet("color: #444; padding: 2px 6px;")
        self.breadcrumb.setTextInteractionFlags(Qt.TextSelectableByMouse)
        toolbar.addWidget(self.breadcrumb)

        splitter = QSplitter(Qt.Horizontal)
        self.side = DirTree()
        self.side.jump_to.connect(self._on_side_jump)
        self.view = TreeView()
        self.view.focus_requested.connect(self.navigate_to)
        self.view.hovered.connect(self._on_hover)
        self.view.selected_changed.connect(self._on_select)
        splitter.addWidget(self.side)
        splitter.addWidget(self.view)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([320, 960])
        self.setCentralWidget(splitter)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self._status_left = QLabel(
            "Open a folder.  Click chevron to expand, "
            "double-click a folder to focus, Ctrl+wheel to zoom, "
            "middle-drag to pan.")
        self._status_right = QLabel("")
        self._status_right.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.status.addWidget(self._status_left, 1)
        self.status.addPermanentWidget(self._status_right)

    # scan flow ---------------------------------------------------------

    def pick_folder(self):
        path = QFileDialog.getExistingDirectory(self,
                                                 "Choose a folder to visualize",
                                                 os.path.expanduser("~"))
        if path:
            self.scan(path)

    def scan(self, path: str):
        self._cancel_scan()
        self._status_left.setText(f"Scanning {path} …")
        self._status_right.setText("")
        self.breadcrumb.setText(f"  {path}  (scanning)")

        worker = ScanWorker(path)
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_progress)
        worker.finished.connect(self._on_scan_done)
        worker.failed.connect(self._on_scan_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_thread_refs)

        self._worker = worker
        self._thread = thread
        thread.start()

    def _clear_thread_refs(self):
        self._worker = None
        self._thread = None

    def _cancel_scan(self):
        try:
            if self._worker is not None:
                self._worker.cancel()
            if self._thread is not None and self._thread.isRunning():
                self._thread.quit()
                self._thread.wait(2000)
        except RuntimeError:
            pass
        self._worker = None
        self._thread = None

    def _on_progress(self, files: int, bytes_total: int):
        self._status_left.setText(
            f"Scanning… {files:,} files, {human_size(bytes_total)}")

    def _on_scan_done(self, root: Node):
        self._root = root
        self.navigate_to(root)
        self.act_home.setEnabled(True)
        self._status_left.setText(f"Done — {human_size(root.size)} total")

    def _on_scan_failed(self, msg: str):
        self._status_left.setText(f"Scan failed: {msg}")
        QMessageBox.warning(self, "Scan failed", msg)

    # navigation --------------------------------------------------------

    def navigate_to(self, node: Node):
        if node is None:
            return
        self._current = node
        self.view.set_root(node)
        self.side.set_root(node)
        self.breadcrumb.setText(f"  {node.path}")
        self.act_up.setEnabled(node.parent is not None)
        self._status_right.setText(
            f"{len(node.children):,} children · {human_size(node.size)}")

    def go_up(self):
        if self._current is None:
            return
        parent = self._current.parent
        if parent is not None:
            self.navigate_to(parent)

    def go_home(self):
        if self._root is not None:
            self.navigate_to(self._root)

    def _on_side_jump(self, node: Node):
        # If user double-clicks the side panel: expand path in view & focus on it
        if self._current is None:
            return
        # Walk up from `node` to find the chain back to current root, opening
        # each directory along the way so the visual tree has it laid out.
        chain: list[Node] = []
        cur: Optional[Node] = node
        while cur is not None and cur is not self._current:
            chain.append(cur)
            cur = cur.parent
        if cur is None:
            # node isn't a descendant of current — focus on its own subtree
            self.navigate_to(node if node.is_dir else (node.parent or node))
            return
        # Expand every ancestor (skip the node itself if it's a file)
        for n in reversed(chain):
            if n.is_dir and not self.view.is_expanded(n):
                self.view._expanded[id(n)] = True
        self.view.rebuild(fit=False)
        self.view.focus_on(node)

    def _on_hover(self, node: Optional[Node]):
        if node is None:
            if self._current is not None:
                self._status_left.setText(self._current.path)
            return
        suffix = "/" if node.is_dir else ""
        self._status_left.setText(
            f"{node.path}{suffix}  —  {human_size(node.size)}")

    def _on_select(self, node: Node):
        self._status_right.setText(f"{node.name} · {human_size(node.size)}")

    def closeEvent(self, event):
        self._cancel_scan()
        super().closeEvent(event)


def main(argv: Optional[list[str]] = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    app = QApplication(argv)
    win = MainWindow()
    extra = [a for a in argv[1:] if not a.startswith("-")]
    win.show()
    if extra and os.path.isdir(extra[0]):
        win.scan(extra[0])
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
