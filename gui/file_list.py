"""File list component with Treeview, drag-drop, and right-click context menu.

Apple-style UI: 44px row height, alternating rows, clean heading.
"""

import os
import sys
import subprocess
import threading
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from core.engine import detect_watermark


# ── Apple 风格品牌色 ─────────────────────────────────────────────────────────
BRAND_ALT_ROW = "#FAFAFA"
BRAND_WHITE = "#FFFFFF"
BRAND_HEADING_BG = "#F5F5F7"
BRAND_HEADING_FG = "#86868B"
BRAND_SELECTION_BG = "#E8F0FE"
BRAND_PRIMARY = "#0071E3"
BRAND_SUCCESS = "#30D158"

# ── Status icons ─────────────────────────────────────────────────────────────
STATUS_ICONS = {
    "unchecked": "⚪",    # Not yet detected
    "clean": "🟢",       # No watermark
    "watermark": "🔴",   # Has watermark
    "processed": "✅",    # Already processed
    "error": "❌",       # Error occurred
    "processing": "⏳",  # Currently processing
}

STATUS_LABELS = {
    "unchecked": "未检测",
    "clean": "无水印",
    "watermark": "有水印",
    "processed": "已处理",
    "error": "出错",
    "processing": "处理中…",
}


class FileEntry:
    """Data model for a single file entry in the list."""

    __slots__ = ("path", "name", "size", "status", "status_info", "checked")

    def __init__(self, path: str) -> None:
        self.path = os.path.abspath(path)
        self.name = os.path.basename(path)
        self.size = os.path.getsize(path) if os.path.exists(path) else 0
        self.status: str = "unchecked"
        self.status_info: Dict[str, Any] = {}
        self.checked: bool = True  # Selected by default

    @property
    def size_formatted(self) -> str:
        if self.size < 1024:
            return f"{self.size} B"
        elif self.size < 1024 * 1024:
            return f"{self.size / 1024:.1f} KB"
        else:
            return f"{self.size / (1024 * 1024):.1f} MB"

    @property
    def status_icon(self) -> str:
        return STATUS_ICONS.get(self.status, "⚪")

    @property
    def status_label(self) -> str:
        return STATUS_LABELS.get(self.status, "未知")

    def to_row(self) -> List[str]:
        """Convert to display row for Treeview."""
        return [
            "☑" if self.checked else "☐",
            self.name,
            self.size_formatted,
            f"{self.status_icon} {self.status_label}",
        ]


class FileListFrame(ttk.Frame):
    """File list panel with Treeview, drag-drop, and context menus."""

    # ── Signals / callbacks ──────────────────────────────────────────────────
    on_files_changed: Optional[Callable[[], None]] = None
    """Called whenever the file list changes (add, remove, status update)."""

    on_file_double_click: Optional[Callable[[FileEntry], None]] = None
    """Called when a file row is double-clicked."""

    def __init__(
        self,
        master,
        on_files_changed: Optional[Callable[[], None]] = None,
        on_file_double_click: Optional[Callable[[FileEntry], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self.on_files_changed = on_files_changed
        self.on_file_double_click = on_file_double_click

        # ── Data ─────────────────────────────────────────────────────────
        self._entries: List[FileEntry] = []
        self._entries_by_path: Dict[str, FileEntry] = {}

        # ── Build UI ─────────────────────────────────────────────────────
        self._build_ui()

        # ── Bind drag-drop ──────────────────────────────────────────────
        self._setup_drag_drop()

    # ── UI Construction ──────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Create the Treeview and scrollbar with Apple-style aesthetics."""
        # Outer frame with thin border
        outer = ttk.Frame(self, borderwidth=1, relief=SOLID)
        outer.pack(fill=BOTH, expand=True, padx=0, pady=0)

        # Columns
        columns = ("select", "name", "size", "status")
        self._tree = ttk.Treeview(
            outer,
            columns=columns,
            show="headings",
            selectmode="extended",
            height=12,
        )

        # Define headings
        self._tree.heading("select", text="", anchor=CENTER)
        self._tree.heading("name", text="文件名", anchor=W)
        self._tree.heading("size", text="大小", anchor=E)
        self._tree.heading("status", text="水印状态", anchor=CENTER)

        # Column widths
        self._tree.column("select", width=40, minwidth=30, anchor=CENTER, stretch=False)
        self._tree.column("name", width=320, minwidth=150, anchor=W, stretch=True)
        self._tree.column("size", width=90, minwidth=70, anchor=E, stretch=False)
        self._tree.column("status", width=120, minwidth=100, anchor=CENTER, stretch=False)

        # ── Apple-style styling ───────────────────────────────────────
        style = ttk.Style()

        # Row height: 44px (Apple HIG touch standard)
        style.configure("Treeview", rowheight=44, font=("Segoe UI", 11))

        # Heading style: #F5F5F7 background, #86868B text
        style.configure("Treeview.Heading",
                        background=BRAND_HEADING_BG,
                        foreground=BRAND_HEADING_FG,
                        font=("Segoe UI", 10, "bold"),
                        borderwidth=0,
                        relief="flat")
        style.map("Treeview.Heading",
                  background=[("active", "#E8E8ED")])

        # Alternating row tags
        self._tree.tag_configure("evenrow", background=BRAND_WHITE)
        self._tree.tag_configure("oddrow", background=BRAND_ALT_ROW)

        # Selection color: Apple blue tint
        style.map("Treeview",
                  background=[("selected", BRAND_SELECTION_BG)],
                  foreground=[("selected", "#1D1D1F")],
                  fieldbackground=[("selected", BRAND_SELECTION_BG)])

        # Scrollbar
        vsb = ttk.Scrollbar(outer, orient=VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)

        self._tree.grid(row=0, column=0, sticky=NSEW)
        vsb.grid(row=0, column=1, sticky=NS)
        outer.grid_rowconfigure(0, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        # ── Bind events ──────────────────────────────────────────────
        self._tree.bind("<ButtonRelease-1>", self._on_click)
        self._tree.bind("<Double-1>", self._on_double_click)
        self._tree.bind("<Button-3>", self._on_right_click)  # Right-click

        # Keyboard
        self._tree.bind("<Delete>", lambda e: self.remove_selected())
        self._tree.bind("<space>", self._on_space_toggle)

    def _setup_drag_drop(self) -> None:
        """Set up drag-and-drop from file manager (tkinterdnd2 or basic)."""
        # Try to register with tkinterdnd2 if available
        try:
            from tkinterdnd2 import DND_FILES
            self._tree.drop_target_register(DND_FILES)
            self._tree.dnd_bind("<<Drop>>", self._on_drop)
            self._has_dnd = True
        except (ImportError, AttributeError):
            self._has_dnd = False
            # Fallback: register on the tree root window
            try:
                root = self.winfo_toplevel()
                root.drop_target_register(DND_FILES)
                root.dnd_bind("<<Drop>>", self._on_drop)
                self._has_dnd = True
            except Exception:
                self._has_dnd = False

    # ── Drag-drop handler ────────────────────────────────────────────────────

    def _on_drop(self, event) -> None:
        """Handle files dropped from the OS file manager."""
        raw = event.data
        files = []
        # Handle both space-separated and newline-separated file lists
        # from different DnD implementations
        if hasattr(event, "files"):
            files = list(event.files)
        elif isinstance(raw, str):
            # Parse file paths — tkinterdnd2 wraps paths in {}
            import re
            files = re.findall(r"\{([^}]+)\}|(\S+)", raw)
            files = [f[0] or f[1] for f in files]

        pdfs = [f for f in files if f.lower().endswith(".pdf") and os.path.isfile(f)]
        if pdfs:
            self.add_files(pdfs)

    # ── Public API ───────────────────────────────────────────────────────────

    def add_files(self, paths: List[str]) -> None:
        """Add PDF files to the list (skips duplicates)."""
        added = 0
        big_files_confirmed = True

        for path in paths:
            path = os.path.abspath(path)
            if not os.path.isfile(path):
                continue
            if not path.lower().endswith(".pdf"):
                continue
            if path in self._entries_by_path:
                continue

            # Check for large files (>100MB)
            size = os.path.getsize(path)
            if not big_files_confirmed and size > 100 * 1024 * 1024:
                mb = size / (1024 * 1024)
                answer = ttk.dialogs.Messagebox.yesno(
                    title="大文件确认",
                    message=(
                        f"文件 \"{os.path.basename(path)}\" 大小为 {mb:.1f} MB，"
                        f"超过 100 MB。\n\n是否继续添加？"
                    ),
                    alert=True,
                )
                if answer == "No":
                    continue
                big_files_confirmed = True

            entry = FileEntry(path)
            self._entries.append(entry)
            self._entries_by_path[path] = entry
            self._insert_row(entry)
            added += 1

            # Start watermark detection in background
            self._detect_watermark_async(entry)

        if added > 0:
            self._fire_changed()

    def remove_file(self, entry: FileEntry) -> None:
        """Remove a single file entry."""
        for item_id in self._tree.get_children():
            values = self._tree.item(item_id, "values")
            if values and values[1] == entry.name and entry.path in self._entries_by_path:
                self._tree.delete(item_id)
                break

        if entry.path in self._entries_by_path:
            del self._entries_by_path[entry.path]
        if entry in self._entries:
            self._entries.remove(entry)
        self._fire_changed()

    def remove_selected(self) -> None:
        """Remove all selected file entries."""
        selected = self._tree.selection()
        if not selected:
            return
        for item_id in selected:
            values = self._tree.item(item_id, "values")
            if values:
                # Find the matching entry
                name = values[1]
                for entry in list(self._entries):
                    if entry.name == name and entry.path in self._entries_by_path:
                        self.remove_file(entry)
                        break

    def clear_all(self) -> None:
        """Remove all entries from the list."""
        for item_id in self._tree.get_children():
            self._tree.delete(item_id)
        self._entries.clear()
        self._entries_by_path.clear()
        self._fire_changed()

    def get_checked_entries(self) -> List[FileEntry]:
        """Return entries that are checked (selected for processing)."""
        return [e for e in self._entries if e.checked]

    def get_all_entries(self) -> List[FileEntry]:
        """Return all entries."""
        return list(self._entries)

    def get_entry_count(self) -> int:
        return len(self._entries)

    def update_entry_status(self, entry: FileEntry, status: str) -> None:
        """Update the status of a file entry and refresh the display."""
        entry.status = status
        self._refresh_row(entry)

    def update_entry_info(self, entry: FileEntry, info: Dict[str, Any]) -> None:
        """Store additional info on the entry."""
        entry.status_info = info

    # ── Event handlers ──────────────────────────────────────────────────────

    def _on_click(self, event) -> None:
        """Handle left-click on checkbox column to toggle selection."""
        region = self._tree.identify_region(event.x, event.y)
        if region == "heading":
            return

        column = self._tree.identify_column(event.x)
        if column == "#1":  # Select column
            item = self._tree.identify_row(event.y)
            if item:
                values = self._tree.item(item, "values")
                if values:
                    name = values[1]
                    for entry in self._entries:
                        if entry.name == name:
                            entry.checked = not entry.checked
                            self._refresh_row(entry)
                            self._fire_changed()
                            break

    def _on_double_click(self, event) -> None:
        """Double-click: open file with system PDF viewer."""
        item = self._tree.identify_row(event.y)
        if not item:
            return
        values = self._tree.item(item, "values")
        if not values:
            return

        name = values[1]
        for entry in self._entries:
            if entry.name == name:
                if self.on_file_double_click:
                    self.on_file_double_click(entry)
                else:
                    self._open_file_external(entry.path)
                break

    def _on_right_click(self, event) -> None:
        """Show context menu on right-click."""
        item = self._tree.identify_row(event.y)
        if not item:
            return

        # Select the item under cursor
        self._tree.selection_set(item)
        values = self._tree.item(item, "values")
        if not values:
            return

        name = values[1]
        entry = None
        for e in self._entries:
            if e.name == name:
                entry = e
                break
        if entry is None:
            return

        menu = ttk.Menu(self, tearoff=False)

        menu.add_command(
            label="📄 查看详情",
            command=lambda e=entry: self._show_details(e),
        )
        menu.add_command(
            label="📂 打开所在文件夹",
            command=lambda e=entry: self._open_containing_folder(e.path),
        )
        menu.add_separator()
        menu.add_command(
            label="🗑 从列表移除",
            command=lambda e=entry: self.remove_file(e),
        )
        menu.add_command(
            label="🗑 清空全部",
            command=self.clear_all,
        )

        menu.post(event.x_root, event.y_root)

    def _on_space_toggle(self, event) -> None:
        """Toggle checkbox for selected items with spacebar."""
        selected = self._tree.selection()
        for item in selected:
            values = self._tree.item(item, "values")
            if values:
                name = values[1]
                for entry in self._entries:
                    if entry.name == name:
                        entry.checked = not entry.checked
                        self._refresh_row(entry)
                        break
        self._fire_changed()

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _insert_row(self, entry: FileEntry) -> None:
        """Insert a new row into the Treeview with alternating row tag."""
        index = len(self._tree.get_children())
        tag = "evenrow" if index % 2 == 0 else "oddrow"
        self._tree.insert("", END, values=entry.to_row(), tags=(entry.path, tag))

    def _refresh_row(self, entry: FileEntry) -> None:
        """Update the display for a single entry."""
        for item in self._tree.get_children():
            vals = self._tree.item(item, "values")
            if vals and vals[1] == entry.name:
                self._tree.item(item, values=entry.to_row())
                break

    def _detect_watermark_async(self, entry: FileEntry) -> None:
        """Run watermark detection in a background thread."""
        def _detect():
            try:
                has_wm, info = detect_watermark(entry.path)
                new_status = "watermark" if has_wm else "clean"
                # Schedule GUI update on main thread
                self.after(0, lambda: self._apply_detect_result(entry, new_status, info))
            except Exception as exc:
                self.after(0, lambda: self._apply_detect_result(entry, "error", {"error": str(exc)}))

        thread = threading.Thread(target=_detect, daemon=True)
        thread.start()

    def _apply_detect_result(self, entry: FileEntry, status: str, info: Dict[str, Any]) -> None:
        """Apply detection result on the main thread."""
        entry.status = status
        entry.status_info = info
        self._refresh_row(entry)
        self._fire_changed()

    def _open_file_external(self, path: str) -> None:
        """Open a file with the system default application."""
        try:
            if os.name == "nt":
                os.startfile(path)  # noqa:  Windows
            elif sys.platform == "darwin":
                subprocess.run(["open", path], check=False)
            else:
                subprocess.run(["xdg-open", path], check=False)
        except Exception as exc:
            ttk.dialogs.Messagebox.show_error(
                title="打开失败",
                message=f"无法打开文件:\n{exc}",
            )

    def _open_containing_folder(self, path: str) -> None:
        """Open the folder containing the file in the file manager."""
        folder = os.path.dirname(path)
        try:
            if os.name == "nt":
                subprocess.run(["explorer", "/select,", path], check=False)
            elif sys.platform == "darwin":
                subprocess.run(["open", "-R", path], check=False)
            else:
                subprocess.run(["xdg-open", folder], check=False)
        except Exception as exc:
            ttk.dialogs.Messagebox.show_error(
                title="打开失败",
                message=f"无法打开文件夹:\n{exc}",
            )

    def _show_details(self, entry: FileEntry) -> None:
        """Show a details dialog for a file entry."""
        info = entry.status_info or {}
        lines = [
            f"文件名: {entry.name}",
            f"路径: {entry.path}",
            f"大小: {entry.size_formatted}",
            f"状态: {entry.status_icon} {entry.status_label}",
        ]
        if info.get("page_count") is not None:
            lines.append(f"页数: {info['page_count']}")
        if info.get("stream_count") is not None:
            lines.append(f"内容流数: {info['stream_count']}")
        if info.get("watermark_pages"):
            pages = ", ".join(str(p + 1) for p in info["watermark_pages"])
            lines.append(f"水印页码: {pages}")
        if info.get("error"):
            lines.append(f"错误: {info['error']}")

        ttk.dialogs.Messagebox.ok(
            title=f"文件详情 — {entry.name}",
            message="\n".join(lines),
        )

    def _fire_changed(self) -> None:
        """Emit the files-changed callback."""
        if self.on_files_changed:
            self.on_files_changed()

    def get_selected_entries(self) -> List[FileEntry]:
        """Return all entries that are currently selected in the tree."""
        selected = self._tree.selection()
        result = []
        for item in selected:
            vals = self._tree.item(item, "values")
            if vals:
                name = vals[1]
                for entry in self._entries:
                    if entry.name == name:
                        result.append(entry)
                        break
        return result
