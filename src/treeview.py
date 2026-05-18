"""Node-link tree visualization.

Renders a directory tree as a left-to-right hierarchical diagram: nodes are
rounded rectangles, edges are right-angled connectors from parent to child.
Layout uses a simple postorder traversal that centers each parent against the
vertical span of its visible children — produces a clean, non-overlapping
tree without the complexity of Reingold–Tilford / Buchheim.

Interaction:
  - Click the chevron (▶ / ▼) to expand or collapse a directory.
  - Click anywhere else on a node to select it.
  - Double-click a directory to focus on it (it becomes the view root).
  - Mouse wheel zooms about the cursor; middle-mouse drag pans.

Sibling cap: at most MAX_CHILDREN_VISIBLE children are drawn per parent
(largest by size first). The side panel still shows everything.
"""
from __future__ import annotations

import os
from typing import Optional

from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import (QBrush, QColor, QPainter, QPen, QFont,
                            QFontMetricsF, QPainterPath)
from PySide6.QtWidgets import (QGraphicsItem, QGraphicsPathItem,
                                QGraphicsScene, QGraphicsView)

from scanner import Node


# ---------- shared helpers (kept local; main.py has its own copies for now) --

def human_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    v = float(n)
    for unit in ("KB", "MB", "GB", "TB", "PB"):
        v /= 1024.0
        if v < 1024:
            return f"{v:.1f} {unit}"
    return f"{v:.1f} EB"


_EXT_FAMILY = {
    "image":  {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tif", ".tiff",
               ".heic", ".raw", ".cr2", ".nef", ".arw", ".svg", ".ico"},
    "video":  {".mp4", ".mkv", ".mov", ".avi", ".wmv", ".webm", ".flv", ".m4v",
               ".mpg", ".mpeg", ".ts"},
    "audio":  {".mp3", ".flac", ".wav", ".aac", ".ogg", ".m4a", ".opus", ".wma"},
    "doc":    {".pdf", ".doc", ".docx", ".odt", ".rtf", ".txt", ".md", ".tex",
               ".epub", ".mobi", ".xls", ".xlsx", ".ods", ".csv", ".ppt", ".pptx",
               ".odp"},
    "code":   {".py", ".js", ".ts", ".tsx", ".jsx", ".c", ".cpp", ".h", ".hpp",
               ".rs", ".go", ".rb", ".java", ".kt", ".swift", ".cs", ".php",
               ".html", ".css", ".scss", ".sh", ".ps1", ".lua", ".sql", ".json",
               ".yaml", ".yml", ".toml", ".xml"},
    "archive":{".zip", ".7z", ".rar", ".tar", ".gz", ".bz2", ".xz", ".iso",
               ".dmg", ".pkg", ".deb", ".rpm"},
    "exe":    {".exe", ".msi", ".bat", ".cmd", ".app"},
}

_FAMILY_COLOR = {
    "dir":     QColor( 90, 130, 180),
    "image":   QColor(220, 170,  80),
    "video":   QColor(200,  80,  80),
    "audio":   QColor(160,  90, 180),
    "doc":     QColor( 90, 170, 110),
    "code":    QColor( 70, 170, 170),
    "archive": QColor(220, 130,  60),
    "exe":     QColor(140, 140, 140),
    "other":   QColor(170, 170, 170),
}


def _family(node: Node) -> str:
    if node.is_dir:
        return "dir"
    ext = os.path.splitext(node.name)[1].lower()
    for fam, exts in _EXT_FAMILY.items():
        if ext in exts:
            return fam
    return "other"


def _color(node: Node) -> QColor:
    base = QColor(_FAMILY_COLOR[_family(node)])
    return base.lighter(135) if not node.is_dir else base.lighter(115)


# ---------- graphics items ----------------------------------------------------

class EdgeItem(QGraphicsPathItem):
    """Elbow connector from (x1, y1) to (x2, y2)."""

    def __init__(self, x1: float, y1: float, x2: float, y2: float):
        super().__init__()
        path = QPainterPath()
        path.moveTo(x1, y1)
        mid = (x1 + x2) / 2.0
        path.lineTo(mid, y1)
        path.lineTo(mid, y2)
        path.lineTo(x2, y2)
        self.setPath(path)
        pen = QPen(QColor(150, 150, 155), 1.2)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.setZValue(-1)


class NodeItem(QGraphicsItem):
    CHEVRON_W = 22

    def __init__(self, node: Node, rect: QRectF, view: "TreeView"):
        super().__init__()
        self._node = node
        self._rect = QRectF(rect)
        self._view = view
        self._selected = False
        self.setAcceptHoverEvents(True)
        if node.is_dir:
            self.setCursor(Qt.PointingHandCursor)
        suffix = "/" if node.is_dir else ""
        tip = f"{node.path}{suffix}\n{human_size(node.size)}"
        if node.is_dir:
            tip += f"\n{len(node.children):,} children"
        if node.dedup_tag:
            tip += f"\n[dedup] {node.dedup_tag}"
        if node.error:
            tip += f"\n[!] {node.error}"
        self.setToolTip(tip)

    def node(self) -> Node:
        return self._node

    def set_selected(self, on: bool) -> None:
        if self._selected != on:
            self._selected = on
            self.update()

    def boundingRect(self) -> QRectF:
        return self._rect.adjusted(-2, -2, 2, 2)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        fill = _color(self._node)
        painter.setBrush(QBrush(fill))
        if self._node.dedup_tag:
            pen = QPen(QColor(220, 40, 40), 2.0)
        elif self._selected:
            pen = QPen(QColor(20, 80, 200), 2.0)
        else:
            pen = QPen(QColor(70, 70, 75, 200), 1.0)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.drawRoundedRect(self._rect, 5, 5)

        # chevron for directories
        font = painter.font()
        font.setPointSizeF(9.5)
        painter.setFont(font)
        fm = QFontMetricsF(font)

        chev_text = ""
        if self._node.is_dir and self._node.children:
            chev_text = "▼" if self._view.is_expanded(self._node) else "▶"
        if chev_text:
            painter.setPen(QColor(30, 30, 30))
            painter.drawText(QRectF(self._rect.x(), self._rect.y(),
                                    self.CHEVRON_W, self._rect.height()),
                             int(Qt.AlignVCenter | Qt.AlignHCenter),
                             chev_text)

        # name (with trailing slash for dirs)
        name = self._node.name + ("/" if self._node.is_dir else "")
        size_txt = human_size(self._node.size)
        right_pad = fm.horizontalAdvance(size_txt) + 14
        name_rect = self._rect.adjusted(self.CHEVRON_W + 4, 0, -right_pad, 0)
        elided = fm.elidedText(name, Qt.ElideMiddle, name_rect.width())
        painter.setPen(QColor(20, 20, 20))
        painter.drawText(name_rect, int(Qt.AlignVCenter | Qt.AlignLeft), elided)

        # size on the right
        size_rect = self._rect.adjusted(0, 0, -8, 0)
        painter.setPen(QColor(70, 70, 75))
        painter.drawText(size_rect, int(Qt.AlignVCenter | Qt.AlignRight), size_txt)

    def mousePressEvent(self, ev):
        if ev.button() != Qt.LeftButton:
            super().mousePressEvent(ev)
            return
        local_x = ev.pos().x() - self._rect.x()
        if (self._node.is_dir and self._node.children
                and 0 <= local_x <= self.CHEVRON_W):
            self._view.toggle(self._node)
            ev.accept()
            return
        self._view.select(self._node)
        ev.accept()

    def mouseDoubleClickEvent(self, ev):
        if self._node.is_dir:
            self._view.focus_requested.emit(self._node)
            ev.accept()
            return
        super().mouseDoubleClickEvent(ev)


# ---------- view --------------------------------------------------------------

class TreeView(QGraphicsView):
    """Left-to-right node-link tree."""

    focus_requested = Signal(object)   # Node (user double-clicked a dir)
    hovered = Signal(object)           # Node or None
    selected_changed = Signal(object)  # Node

    NODE_W = 230
    NODE_H = 28
    X_GAP = 60          # horizontal gap between levels
    Y_GAP = 8           # vertical gap between siblings
    MAX_CHILDREN_VISIBLE = 40

    def __init__(self):
        super().__init__()
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        self.setBackgroundBrush(QBrush(QColor(248, 248, 250)))
        self.setMouseTracking(True)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)

        self._root: Optional[Node] = None
        self._expanded: dict[int, bool] = {}
        self._positions: dict[int, tuple[float, float]] = {}
        self._items: dict[int, NodeItem] = {}
        self._selected_node: Optional[Node] = None

        # panning state
        self._panning = False
        self._pan_anchor = QPointF()

    # public API --------------------------------------------------------

    def set_root(self, node: Optional[Node]) -> None:
        self._root = node
        self._expanded.clear()
        self._selected_node = None
        if node is not None:
            self._expanded[id(node)] = True
        self.rebuild(fit=True)

    def current_root(self) -> Optional[Node]:
        return self._root

    def is_expanded(self, node: Node) -> bool:
        return self._expanded.get(id(node), False)

    def toggle(self, node: Node) -> None:
        self._expanded[id(node)] = not self.is_expanded(node)
        self.rebuild(fit=False)

    def select(self, node: Node) -> None:
        prev = self._selected_node
        self._selected_node = node
        if prev is not None and id(prev) in self._items:
            self._items[id(prev)].set_selected(False)
        if id(node) in self._items:
            self._items[id(node)].set_selected(True)
        self.selected_changed.emit(node)

    # layout + rendering ------------------------------------------------

    def _visible_children(self, node: Node) -> list[Node]:
        if not node.is_dir or not node.children:
            return []
        kids = sorted(node.children, key=lambda c: (-c.size, c.name.lower()))
        if len(kids) > self.MAX_CHILDREN_VISIBLE:
            kids = kids[:self.MAX_CHILDREN_VISIBLE]
        return kids

    def _layout(self, node: Node, depth: int, top: float) -> float:
        """Returns height consumed; positions are stored in self._positions."""
        x = depth * (self.NODE_W + self.X_GAP)
        if not self.is_expanded(node) or not self._visible_children(node):
            self._positions[id(node)] = (x, top)
            return self.NODE_H + self.Y_GAP

        cur = top
        first_y = None
        last_y = None
        for child in self._visible_children(node):
            h = self._layout(child, depth + 1, cur)
            cy = self._positions[id(child)][1]
            if first_y is None:
                first_y = cy
            last_y = cy
            cur += h
        ny = (first_y + last_y) / 2.0
        self._positions[id(node)] = (x, ny)
        return cur - top

    def rebuild(self, fit: bool = False) -> None:
        self._scene.clear()
        self._positions.clear()
        self._items.clear()
        if self._root is None:
            return

        self._layout(self._root, 0, 0)

        # scene rect = bbox of all node rectangles, padded
        xs = [p[0] for p in self._positions.values()]
        ys = [p[1] for p in self._positions.values()]
        min_x, max_x = min(xs), max(xs) + self.NODE_W
        min_y, max_y = min(ys), max(ys) + self.NODE_H
        pad = 40
        self._scene.setSceneRect(min_x - pad, min_y - pad,
                                  (max_x - min_x) + 2 * pad,
                                  (max_y - min_y) + 2 * pad)

        self._add_subtree(self._root)

        if self._selected_node is not None and id(self._selected_node) in self._items:
            self._items[id(self._selected_node)].set_selected(True)

        if fit:
            self.resetTransform()
            self.centerOn(self._scene.sceneRect().center())

    def _add_subtree(self, node: Node) -> None:
        px, py = self._positions[id(node)]
        item = NodeItem(node, QRectF(px, py, self.NODE_W, self.NODE_H), self)
        self._scene.addItem(item)
        self._items[id(node)] = item

        if not self.is_expanded(node):
            return
        kids = self._visible_children(node)
        if not kids:
            return

        parent_right = px + self.NODE_W
        parent_mid_y = py + self.NODE_H / 2
        for child in kids:
            cx, cy = self._positions[id(child)]
            child_mid_y = cy + self.NODE_H / 2
            self._scene.addItem(EdgeItem(parent_right, parent_mid_y,
                                          cx, child_mid_y))
            self._add_subtree(child)

        # overflow hint as a faint trailing label
        total = len(node.children)
        if total > self.MAX_CHILDREN_VISIBLE:
            from PySide6.QtWidgets import QGraphicsSimpleTextItem
            extra = total - self.MAX_CHILDREN_VISIBLE
            last = kids[-1]
            lx, ly = self._positions[id(last)]
            label = QGraphicsSimpleTextItem(f"… {extra:,} more (use side panel)")
            f = QFont(); f.setItalic(True); f.setPointSizeF(8.5)
            label.setFont(f)
            label.setBrush(QBrush(QColor(120, 120, 130)))
            label.setPos(lx, ly + self.NODE_H + 4)
            self._scene.addItem(label)

    # interaction -------------------------------------------------------

    def wheelEvent(self, event):
        # Ctrl+wheel zooms; plain wheel scrolls vertically.
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self.scale(factor, factor)
            event.accept()
            return
        super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._panning = True
            self._pan_anchor = event.position()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning:
            delta = event.position() - self._pan_anchor
            self._pan_anchor = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y()))
            event.accept()
            return
        item = self.itemAt(event.pos())
        if isinstance(item, NodeItem):
            self.hovered.emit(item.node())
        else:
            self.hovered.emit(None)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton and self._panning:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def focus_on(self, node: Node) -> None:
        """Center the view on a specific node (used by the side panel)."""
        if id(node) not in self._items:
            return
        item = self._items[id(node)]
        self.centerOn(item)
        self.select(node)
