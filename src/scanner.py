"""Background filesystem scanner.

Walks a directory tree without following symlinks, building a Node tree with
recursive byte sizes. Designed to run inside a QThread via ScanWorker.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from PySide6.QtCore import QObject, Signal


@dataclass
class Node:
    name: str
    path: str
    is_dir: bool
    size: int = 0
    children: list["Node"] = field(default_factory=list)
    parent: Optional["Node"] = None
    error: Optional[str] = None
    # Reserved for dedup-pass integration. When populated, the visualizer
    # tints this node to flag it as a duplicate / waste-of-space.
    dedup_tag: Optional[str] = None


class ScanWorker(QObject):
    progress = Signal(int, int)          # files_scanned, bytes_scanned
    finished = Signal(object)            # root Node
    failed = Signal(str)

    PROGRESS_EVERY = 750

    def __init__(self, root_path: str):
        super().__init__()
        self.root_path = os.path.abspath(root_path)
        self._cancel = False
        self._counter = [0, 0]  # [files, bytes]

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        try:
            root = self._scan(self.root_path, parent=None)
            if root is None:
                self.failed.emit("Scan cancelled.")
                return
            self.progress.emit(self._counter[0], self._counter[1])
            self.finished.emit(root)
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")

    def _scan(self, path: str, parent: Optional[Node]) -> Optional[Node]:
        if self._cancel:
            return None

        name = os.path.basename(path.rstrip(os.sep)) or path
        try:
            is_dir = os.path.isdir(path) and not os.path.islink(path)
        except OSError as exc:
            return Node(name=name, path=path, is_dir=False, error=str(exc), parent=parent)

        node = Node(name=name, path=path, is_dir=is_dir, parent=parent)

        if not is_dir:
            try:
                node.size = os.path.getsize(path)
            except OSError as exc:
                node.error = str(exc)
            self._tick(node.size)
            return node

        total = 0
        try:
            with os.scandir(path) as it:
                for entry in it:
                    if self._cancel:
                        return None
                    total += self._handle_entry(entry, node)
        except (PermissionError, OSError) as exc:
            node.error = str(exc)

        node.size = total
        return node

    def _handle_entry(self, entry: os.DirEntry, parent: Node) -> int:
        try:
            if entry.is_symlink():
                # Record but don't follow — avoids cycles and double counting.
                child = Node(name=entry.name, path=entry.path, is_dir=False,
                             parent=parent, error="symlink (not followed)")
                parent.children.append(child)
                return 0
            if entry.is_dir(follow_symlinks=False):
                child = self._scan(entry.path, parent=parent)
                if child is None:
                    return 0
                parent.children.append(child)
                return child.size
            if entry.is_file(follow_symlinks=False):
                try:
                    size = entry.stat(follow_symlinks=False).st_size
                except OSError as exc:
                    child = Node(name=entry.name, path=entry.path, is_dir=False,
                                 parent=parent, error=str(exc))
                    parent.children.append(child)
                    return 0
                child = Node(name=entry.name, path=entry.path, is_dir=False,
                             size=size, parent=parent)
                parent.children.append(child)
                self._tick(size)
                return size
        except (PermissionError, OSError) as exc:
            parent.children.append(Node(name=entry.name, path=entry.path,
                                        is_dir=False, parent=parent, error=str(exc)))
        return 0

    def _tick(self, size: int) -> None:
        self._counter[0] += 1
        self._counter[1] += size
        if self._counter[0] % self.PROGRESS_EVERY == 0:
            self.progress.emit(self._counter[0], self._counter[1])
