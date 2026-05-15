"""Main GUI application window for YT-PDFCleaner — Pro Edition.

Completely redesigned layout: sidebar + tab navigation + light theme.
"""

import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox

from core.scanner import scan_directory
from .file_list import FileListFrame, FileEntry
from .processor import ProcessingThread, ProcessingStatus, ProgressInfo


APP_NAME = "YT-PDFCleaner"
APP_TITLE = "YT-PDFCleaner — PDF 水印清除工具"
APP_VERSION = "1.2.0"
DEFAULT_THEME = "minty"           # 🆕 清新浅色主题

# Brand colors
BRAND_PRIMARY = "#0E7C7B"    # 深青 — Pro 配色，与 minty 主题协调
BRAND_SECONDARY = "#282828"

# Window dimensions
WIN_WIDTH = 1300
WIN_HEIGHT = 850
WIN_MIN_WIDTH = 960
WIN_MIN_HEIGHT = 650

# ── Fonts ─────────────────────────────────────────────────────────────────────
FONT_LOGO = ("Segoe UI", 22, "bold")
FONT_HEADING = ("Segoe UI", 16, "bold")
FONT_SUBHEADING = ("Segoe UI", 13)
FONT_BODY = ("Segoe UI", 11)
FONT_SMALL = ("Segoe UI", 10)
FONT_MONO = ("Consolas", 10)

# ── Sidebar constants ────────────────────────────────────────────────────────
SIDEBAR_W = 200
SIDEBAR_COLOR = "#f8f9fa"


class YTPDFCleanerApp(ttk.Window):
    """Main application window — Pro Edition with sidebar layout."""

    def __init__(self) -> None:
        super().__init__(title=APP_TITLE, themename=DEFAULT_THEME)

        # ── Window setup ────────────────────────────────────────────────
        self.geometry(f"{WIN_WIDTH}x{WIN_HEIGHT}")
        self.minsize(WIN_MIN_WIDTH, WIN_MIN_HEIGHT)
        self._center_window()
        self._set_app_icon()

        # ── State ───────────────────────────────────────────────────────
        self._last_output_dir: Optional[str] = None
        self._output_mode = ttk.StringVar(value="pdf")
        self._processor: Optional[ProcessingThread] = None

        # ── Build layout ────────────────────────────────────────────────
        self._build_layout()

        # ── Bind close event ────────────────────────────────────────────
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ═════════════════════════════════════════════════════════════════════
    # Layout — Sidebar + Main
    # ═════════════════════════════════════════════════════════════════════

    def _build_layout(self) -> None:
        """Build the main horizontal layout: sidebar | content."""
        # ── Top bar (full width) ────────────────────────────────────────
        self._build_topbar()

        # ── Body: sidebar + main ────────────────────────────────────────
        body = ttk.Frame(self)
        body.pack(fill=BOTH, expand=True)

        self._build_sidebar(body)
        self._build_main_panel(body)

        # ── Bottom bar (full width) ─────────────────────────────────────
        self._build_bottombar()

    # ── Top bar ─────────────────────────────────────────────────────────────

    def _build_topbar(self) -> None:
        """Build a sleek top navigation bar."""
        bar = ttk.Frame(self, bootstyle="light", padding=(16, 10))
        bar.pack(fill=X)

        # Left: Logo
        logo_frame = ttk.Frame(bar, bootstyle="light")
        logo_frame.pack(side=LEFT)

        ttk.Label(
            logo_frame, text="YT",
            font=FONT_LOGO, foreground=BRAND_PRIMARY,
            bootstyle="light",
        ).pack(side=LEFT)

        ttk.Label(
            logo_frame, text="PDFCleaner",
            font=("Segoe UI", 20), foreground="#2c2c2c",
            bootstyle="light",
        ).pack(side=LEFT, padx=(6, 0))

        # Version pill
        pill = ttk.Label(
            logo_frame, text=f"v{APP_VERSION}",
            font=("Segoe UI", 9, "bold"),
            foreground="#999", bootstyle="light",
        )
        pill.pack(side=LEFT, padx=(8, 0))

        # Spacer
        ttk.Label(bar, text="", bootstyle="light").pack(side=LEFT, fill=X, expand=True)

        # Right: status indicator
        self._top_status = ttk.Label(
            bar, text="● 就绪",
            font=FONT_SMALL, foreground="#78c2ad",
            bootstyle="light",
        )
        self._top_status.pack(side=RIGHT)

        # Separator line
        sep = ttk.Separator(self, orient=HORIZONTAL)
        sep.pack(fill=X)

    # ── Sidebar ─────────────────────────────────────────────────────────────

    def _build_sidebar(self, parent: ttk.Frame) -> None:
        """Build the navigation sidebar."""
        sidebar = ttk.Frame(parent, width=SIDEBAR_W, bootstyle="light")
        sidebar.pack(side=LEFT, fill=Y, padx=(0, 1))
        sidebar.pack_propagate(False)

        # Spacer — push about button to bottom
        ttk.Label(sidebar, text="", bootstyle="light").pack(fill=Y, expand=True)

        # About button at bottom
        self._btn_about = ttk.Button(
            sidebar, text="ℹ  关于",
            command=self._on_about,
            bootstyle="light",
        )
        self._btn_about.pack(fill=X, padx=8, pady=(0, 12))

    # ── Main panel ──────────────────────────────────────────────────────────

    def _build_main_panel(self, parent: ttk.Frame) -> None:
        """Build the main content area."""
        main = ttk.Frame(parent, padding=(20, 16))
        main.pack(side=LEFT, fill=BOTH, expand=True)

        # ── Toolbar row ─────────────────────────────────────────────────
        toolbar = ttk.Frame(main)
        toolbar.pack(fill=X, pady=(0, 12))

        left = ttk.Frame(toolbar)
        left.pack(side=LEFT)
        ttk.Label(left, text="📋 文件列表", font=FONT_HEADING).pack(side=LEFT)
        self._summary_label = ttk.Label(
            left, text="0 / 0 个文件 · 0 MB",
            font=FONT_SMALL, foreground="#999",
        )
        self._summary_label.pack(side=LEFT, padx=(12, 0))

        right = ttk.Frame(toolbar)
        right.pack(side=RIGHT)

        self._btn_files = ttk.Button(
            right, text="📄 选择文件",
            command=self._on_select_files,
            bootstyle="primary-outline", width=12,
        )
        self._btn_files.pack(side=LEFT, padx=(0, 4))

        self._btn_folder = ttk.Button(
            right, text="📁 文件夹",
            command=self._on_select_folder,
            bootstyle="primary-outline", width=10,
        )
        self._btn_folder.pack(side=LEFT, padx=(0, 4))

        self._btn_clear_tool = ttk.Button(
            right, text="🗑 清空",
            command=self._on_clear_list,
            bootstyle="secondary-outline", width=8,
        )
        self._btn_clear_tool.pack(side=LEFT)

        self.bind("<Alt-f>", lambda e: self._on_select_files())
        self.bind("<Alt-d>", lambda e: self._on_select_folder())
        self.bind("<Alt-l>", lambda e: self._on_clear_list())

        # ── File list ───────────────────────────────────────────────────
        file_panel = ttk.Frame(main)
        file_panel.pack(fill=BOTH, expand=True)

        self._file_list = FileListFrame(
            file_panel,
            on_files_changed=self._on_files_changed,
            on_file_double_click=self._on_file_double_click,
        )
        self._file_list.pack(fill=BOTH, expand=True)

        # ── Settings card ───────────────────────────────────────────────
        settings_frame = ttk.LabelFrame(
            main, text="⚙ 输出设置",
        )
        settings_frame.pack(fill=X, pady=(10, 0))
        settings = ttk.Frame(settings_frame, padding=(16, 12))
        settings.pack(fill=X, pady=(10, 0))

        # Format
        fmt_row = ttk.Frame(settings)
        fmt_row.pack(fill=X, pady=(0, 8))

        ttk.Label(fmt_row, text="输出格式：", font=FONT_BODY).pack(side=LEFT, padx=(0, 12))

        self._rb_pdf = ttk.Radiobutton(
            fmt_row, text="PDF（保留原排版）",
            variable=self._output_mode, value="pdf",
            bootstyle="success-toolbutton",
        )
        self._rb_pdf.pack(side=LEFT, padx=(0, 4))

        self._rb_md = ttk.Radiobutton(
            fmt_row, text="Markdown（纯文本）",
            variable=self._output_mode, value="markdown",
            bootstyle="success-toolbutton",
        )
        self._rb_md.pack(side=LEFT)

        # Directory
        dir_row = ttk.Frame(settings)
        dir_row.pack(fill=X)

        ttk.Label(dir_row, text="输出目录：", font=FONT_BODY).pack(side=LEFT, padx=(0, 12))

        self._output_dir_var = ttk.StringVar(value="")
        self._output_dir_entry = ttk.Entry(
            dir_row, textvariable=self._output_dir_var, font=FONT_BODY,
        )
        self._output_dir_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 6))

        self._btn_browse = ttk.Button(
            dir_row, text="📁 浏览",
            command=self._on_browse_output_dir,
            bootstyle="primary-outline", width=7,
        )
        self._btn_browse.pack(side=LEFT, padx=(0, 4))

        self._btn_open_dir = ttk.Button(
            dir_row, text="📂 打开",
            command=self._on_open_output_dir,
            bootstyle="secondary-outline", width=7,
        )
        self._btn_open_dir.pack(side=LEFT)

        # ── Actions row ─────────────────────────────────────────────────
        actions = ttk.Frame(main)
        actions.pack(fill=X, pady=(10, 0))

        self._btn_start = ttk.Button(
            actions, text="▶  开始处理",
            command=self._on_start_processing,
            bootstyle="success", width=18,
        )
        self._btn_start.pack(side=LEFT, padx=(0, 8))

        self._btn_stop = ttk.Button(
            actions, text="⏹  停止",
            command=self._on_stop_processing,
            bootstyle="danger-outline", width=12,
            state=DISABLED,
        )
        self._btn_stop.pack(side=LEFT)

        ttk.Label(actions, text="").pack(side=LEFT, fill=X, expand=True)

        self._btn_clear = ttk.Button(
            actions, text="🗑  清空列表",
            command=self._on_clear_list,
            bootstyle="secondary-outline", width=14,
        )
        self._btn_clear.pack(side=RIGHT)

        # ── Progress row ────────────────────────────────────────────────
        progress = ttk.Frame(main)
        progress.pack(fill=X, pady=(10, 0))

        self._progress_bar = ttk.Progressbar(
            progress, mode="determinate", value=0,
            bootstyle="success-striped",
        )
        self._progress_bar.pack(fill=X, pady=(0, 4))

        info_row = ttk.Frame(progress)
        info_row.pack(fill=X)

        self._progress_label = ttk.Label(
            info_row, text="就绪 — 请选择 PDF 文件",
            font=FONT_BODY,
        )
        self._progress_label.pack(side=LEFT)

        self._result_label = ttk.Label(
            info_row, text="0 成功 / 0 失败 / 0 跳过",
            font=FONT_BODY, foreground="#999",
        )
        self._result_label.pack(side=RIGHT)

        # ── Log area ────────────────────────────────────────────────────
        log_label = ttk.Label(main, text="📋 处理日志", font=FONT_SMALL, foreground="#888")
        log_label.pack(anchor=W, pady=(6, 2))

        self._log_frame = ttk.Frame(main, borderwidth=1, relief=SOLID)
        self._log_text = ttk.Text(
            self._log_frame, height=6, wrap=WORD,
            font=FONT_MONO, state=DISABLED,
            foreground="#333", background="#f5f5f5",
        )
        self._log_scroll = ttk.Scrollbar(
            self._log_frame, orient=VERTICAL,
            command=self._log_text.yview,
        )
        self._log_text.configure(yscrollcommand=self._log_scroll.set)
        self._log_text.pack(side=LEFT, fill=BOTH, expand=True)
        self._log_scroll.pack(side=RIGHT, fill=Y)
        self._log_frame.pack(fill=BOTH, expand=False, pady=(0, 0))

    # ── Bottom bar ──────────────────────────────────────────────────────────

    def _build_bottombar(self) -> None:
        """Build a status footer."""
        bar = ttk.Frame(self, bootstyle="light", padding=(16, 6))
        bar.pack(fill=X, side=BOTTOM)

        self._status_label = ttk.Label(
            bar, text="就绪",
            font=FONT_SMALL, bootstyle="light",
        )
        self._status_label.pack(side=LEFT)

        ttk.Label(
            bar, text="",
            bootstyle="light",
        ).pack(side=LEFT, fill=X, expand=True)

        ttk.Label(
            bar, text=f"YT-PDFCleaner · v{APP_VERSION}",
            font=("Segoe UI", 9), foreground="#bbb",
            bootstyle="light",
        ).pack(side=RIGHT)

    # ═════════════════════════════════════════════════════════════════════
    # Event Handlers
    # ═════════════════════════════════════════════════════════════════════

    def _on_select_files(self) -> None:
        import tkinter.filedialog as fd
        paths = fd.askopenfilenames(
            title="选择 PDF 文件",
            filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*.*")],
            parent=self,
        )
        if paths:
            self._file_list.add_files(list(paths))

    def _on_select_folder(self) -> None:
        import tkinter.filedialog as fd
        directory = fd.askdirectory(
            title="选择包含 PDF 的文件夹",
            parent=self,
        )
        if not directory:
            return
        self._update_status("正在扫描文件夹…")
        self._progress_label.configure(text="正在扫描文件夹中的 PDF 文件…")

        def _scan():
            try:
                results = scan_directory(directory)
                pdf_paths = [r["path"] for r in results if "error" not in r or not r.get("error")]
                if not pdf_paths:
                    self.after(0, lambda: self._progress_label.configure(
                        text="未在所选文件夹中找到 PDF 文件"
                    ))
                else:
                    self.after(0, lambda p=pdf_paths: self._file_list.add_files(p))
            except Exception as exc:
                self.after(0, lambda: Messagebox.show_error(
                    title="扫描失败",
                    message=f"扫描文件夹时出错:\n{exc}",
                ))
            finally:
                self.after(0, lambda: self._update_status("就绪"))

        thread = threading.Thread(target=_scan, daemon=True)
        thread.start()

    def _on_about(self) -> None:
        """Show about dialog."""
        win = ttk.Toplevel(self)
        win.title(f"关于 {APP_NAME}")
        win.geometry("520x540")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        win.update_idletasks()
        px = self.winfo_x() + (self.winfo_width() - 520) // 2
        py = self.winfo_y() + (self.winfo_height() - 540) // 2
        win.geometry(f"+{px}+{py}")

        main = ttk.Frame(win, padding=(32, 24))
        main.pack(fill=BOTH, expand=True)

        icon_about_path = self._resolve_gui_path("icon_about.png")
        if os.path.isfile(icon_about_path):
            try:
                icon_img = ttk.PhotoImage(file=icon_about_path)
                icon_lbl = ttk.Label(main, image=icon_img)
                icon_lbl.image = icon_img
                icon_lbl.pack(pady=(0, 12))
            except Exception:
                pass

        badge_frame = ttk.Frame(main)
        badge_frame.pack(pady=(0, 8))
        ttk.Label(
            badge_frame, text="YT",
            font=("Segoe UI", 26, "bold"),
            foreground=BRAND_PRIMARY,
        ).pack(side=LEFT)
        ttk.Label(
            badge_frame, text="PDFCleaner",
            font=("Segoe UI", 24),
        ).pack(side=LEFT, padx=(8, 0))

        ttk.Label(
            main, text=f"v{APP_VERSION}",
            font=FONT_BODY, foreground="#999",
        ).pack(pady=(0, 16))

        ttk.Label(
            main, text="PDF 水印清除工具（绿色免安装版）",
            font=("Segoe UI", 13, "bold"),
        ).pack(pady=(0, 12))

        ttk.Separator(main, orient=HORIZONTAL).pack(fill=X, pady=(4, 16))

        info_frame = ttk.Frame(main)
        info_frame.pack(fill=X, pady=(0, 16))

        for label, value in [
            ("✍  作者", "xbshen"),
            ("📋  功能", "检测并移除 SGCC 追踪水印"),
            ("🔧  技术栈", "Python · PyMuPDF · ttkbootstrap"),
            ("🎨  主题", f"{DEFAULT_THEME}（清新浅色）"),
            ("📐  布局", "侧边栏导航 + 主面板"),
        ]:
            row = ttk.Frame(info_frame)
            row.pack(fill=X, pady=4)
            ttk.Label(
                row, text=label, font=FONT_BODY, width=10, anchor=E
            ).pack(side=LEFT, padx=(0, 16))
            ttk.Label(
                row, text=value, font=FONT_BODY
            ).pack(side=LEFT)

        ttk.Separator(main, orient=HORIZONTAL).pack(fill=X, pady=(4, 16))
        ttk.Label(
            main, text="© 2026 YT Technologies",
            font=("Segoe UI", 10), foreground="#888",
        ).pack(pady=(0, 16))

        ttk.Button(
            main, text="✔  确定",
            command=win.destroy, bootstyle="success", width=18,
        ).pack()

    def _on_open_output_dir(self) -> None:
        directory = self._output_dir_var.get()
        if not directory or not os.path.isdir(directory):
            Messagebox.show_info(
                title="目录不存在",
                message="请先设置一个有效的输出目录。",
            )
            return
        self._open_folder_in_explorer(directory)

    @staticmethod
    def _open_folder_in_explorer(folder: str) -> None:
        try:
            if os.name == "nt":
                subprocess.run(["explorer", folder], check=False)
            elif sys.platform == "darwin":
                subprocess.run(["open", folder], check=False)
            else:
                subprocess.run(["xdg-open", folder], check=False)
        except Exception as exc:
            Messagebox.show_error(
                title="打开失败",
                message=f"无法打开文件夹:\n{exc}",
            )

    def _on_files_changed(self) -> None:
        entries = self._file_list.get_all_entries()
        checked = self._file_list.get_checked_entries()
        total_size = sum(e.size for e in entries)

        if total_size < 1024 * 1024:
            size_str = f"{total_size / 1024:.1f} KB"
        else:
            size_str = f"{total_size / (1024 * 1024):.1f} MB"

        self._summary_label.configure(
            text=f"{len(checked)} / {len(entries)} 个文件 · {size_str}"
        )

        if not self._output_dir_var.get() and entries:
            self._auto_set_output_dir(entries[0].path)

    def _on_file_double_click(self, entry: FileEntry) -> None:
        try:
            if os.name == "nt":
                os.startfile(entry.path)
            elif sys.platform == "darwin":
                subprocess.run(["open", entry.path], check=False)
            else:
                subprocess.run(["xdg-open", entry.path], check=False)
        except Exception as exc:
            Messagebox.show_error(
                title="打开失败",
                message=f"无法打开文件:\n{exc}",
            )

    def _auto_set_output_dir(self, file_path: str) -> None:
        base_dir = os.path.dirname(file_path)
        output_dir = os.path.join(base_dir, "YT_output")
        self._output_dir_var.set(output_dir)
        self._last_output_dir = output_dir

    def _on_browse_output_dir(self) -> None:
        import tkinter.filedialog as fd
        initial = self._output_dir_var.get() or os.path.expanduser("~")
        directory = fd.askdirectory(
            title="选择输出目录",
            initialdir=initial,
            parent=self,
        )
        if directory:
            self._output_dir_var.set(directory)
            self._last_output_dir = directory

    def _on_start_processing(self) -> None:
        entries = self._file_list.get_checked_entries()
        if not entries:
            Messagebox.show_info(
                title="没有文件",
                message="请先添加 PDF 文件并勾选要处理的文件。",
            )
            return

        output_dir = self._output_dir_var.get().strip()
        if not output_dir:
            if entries:
                output_dir = os.path.join(os.path.dirname(entries[0].path), "YT_output")
                self._output_dir_var.set(output_dir)

        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as exc:
            Messagebox.show_error(
                title="目录错误",
                message=f"无法创建输出目录:\n{exc}",
            )
            return

        self._btn_start.configure(state=DISABLED)
        self._btn_stop.configure(state=NORMAL)
        self._btn_clear.configure(state=DISABLED)
        self._btn_clear_tool.configure(state=DISABLED)
        self._progress_bar.configure(value=0)
        self._result_label.configure(text="0 成功 / 0 失败 / 0 跳过")
        self._top_status.configure(text="● 处理中…", foreground="#f3969a")

        mode = self._output_mode.get()

        self._processor = ProcessingThread(
            files=entries,
            output_dir=output_dir,
            mode=mode,
            on_progress=self._on_processing_progress,
            on_complete=self._on_processing_complete,
            on_log=self._on_processing_log,
        )
        self._processor.start()

    def _on_stop_processing(self) -> None:
        if self._processor and self._processor.is_alive():
            self._processor.stop()
            self._btn_stop.configure(state=DISABLED)
            self._update_status("正在停止…")

    def _on_clear_list(self) -> None:
        if self._file_list.get_entry_count() == 0:
            return
        answer = Messagebox.yesno(
            title="清空列表",
            message="确定要清空所有文件吗？",
        )
        if answer == "Yes":
            self._file_list.clear_all()
            self._result_label.configure(text="0 成功 / 0 失败 / 0 跳过")
            self._progress_label.configure(text="就绪 — 请选择 PDF 文件")
            self._progress_bar.configure(value=0)

    def _on_processing_progress(self, progress: ProgressInfo) -> None:
        self.after(0, lambda p=progress: self._apply_progress(p))

    def _apply_progress(self, p: ProgressInfo) -> None:
        self._progress_bar.configure(value=p.percent)
        self._progress_label.configure(text=f"{p.current_file} — {p.current_status}")
        self._result_label.configure(text=f"{p.success} 成功 / {p.failed} 失败 / {p.skipped} 跳过")
        self._update_status(f"{p.completed}/{p.total} — {p.current_file}")

    def _on_processing_complete(self, progress: ProgressInfo) -> None:
        self.after(0, lambda p=progress: self._apply_complete(p))

    def _apply_complete(self, p: ProgressInfo) -> None:
        self._btn_start.configure(state=NORMAL)
        self._btn_stop.configure(state=DISABLED)
        self._btn_clear.configure(state=NORMAL)
        self._btn_clear_tool.configure(state=NORMAL)
        self._progress_bar.configure(value=100.0)
        self._top_status.configure(text="● 就绪", foreground="#78c2ad")

        for entry in self._file_list.get_all_entries():
            if entry.checked:
                self._file_list.update_entry_status(entry, "processed")

        if p.status == ProcessingStatus.STOPPED:
            self._update_status("已停止")
            self._progress_label.configure(text="⏹ 处理已中断")
        else:
            self._update_status("处理完成")
            self._progress_label.configure(text=f"✅ 处理完成 — {p.success} 成功, {p.failed} 失败, {p.skipped} 跳过")

        self._show_completion_dialog(p)

    def _show_completion_dialog(self, p: ProgressInfo) -> None:
        win = ttk.Toplevel(self)
        win.title("处理结果")
        win.geometry("620x420")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        win.update_idletasks()
        px = self.winfo_x() + (self.winfo_width() - 620) // 2
        py = self.winfo_y() + (self.winfo_height() - 420) // 2
        win.geometry(f"+{px}+{py}")

        main = ttk.Frame(win, padding=(24, 20))
        main.pack(fill=BOTH, expand=True)

        icon_frame = ttk.Frame(main)
        icon_frame.pack(pady=(0, 4))

        dialog_icon = "icon_dialog_warn.png" if p.failed > 0 else "icon_dialog_check.png"
        icon_path = self._resolve_gui_path(dialog_icon)
        if os.path.isfile(icon_path):
            try:
                icon_img = ttk.PhotoImage(file=icon_path)
                icon_lbl = ttk.Label(icon_frame, image=icon_img)
                icon_lbl.image = icon_img
                icon_lbl.pack()
            except Exception:
                icon_lbl = ttk.Label(
                    icon_frame, text="⚠️" if p.failed > 0 else "✅",
                    font=("Segoe UI Emoji", 40),
                )
                icon_lbl.pack()
        else:
            icon_lbl = ttk.Label(
                icon_frame, text="⚠️" if p.failed > 0 else "✅",
                font=("Segoe UI Emoji", 40),
            )
            icon_lbl.pack()

        title_text = "处理完成（部分异常）" if p.failed > 0 else "全部处理完成"
        ttk.Label(
            main, text=title_text,
            font=("Segoe UI", 16, "bold"),
        ).pack(pady=(0, 16))

        stats_frame = ttk.Frame(main)
        stats_frame.pack(fill=X, pady=(0, 20))

        for label, value in [
            ("📄 总计", f"{p.total} 个文件"),
            ("✅ 成功", f"{p.success}"),
            ("❌ 失败", f"{p.failed}"),
            ("⏭  跳过", f"{p.skipped}"),
        ]:
            row = ttk.Frame(stats_frame)
            row.pack(fill=X, pady=2)
            ttk.Label(
                row, text=label, font=("Segoe UI", 12),
                width=10, anchor=E,
            ).pack(side=LEFT, padx=(0, 16))
            ttk.Label(
                row, text=value, font=("Segoe UI", 12, "bold"),
                anchor=W,
            ).pack(side=LEFT)

        btn_row = ttk.Frame(main)
        btn_row.pack(fill=X, pady=(12, 0))

        center = ttk.Frame(btn_row)
        center.pack()

        output_dir = self._output_dir_var.get()
        if output_dir and os.path.isdir(output_dir):
            ttk.Button(
                center, text="📂 打开输出目录",
                command=lambda: (self._open_folder_in_explorer(output_dir), win.destroy()),
                bootstyle="info", width=18,
            ).pack(side=LEFT, padx=(0, 12))

        ttk.Button(
            center, text="✔  确定",
            command=win.destroy,
            bootstyle="success", width=18,
        ).pack(side=LEFT)

    def _on_processing_log(self, message: str) -> None:
        self.after(0, lambda m=message: self._append_log(m))

    def _append_log(self, message: str) -> None:
        self._log_text.configure(state=NORMAL)
        self._log_text.insert(END, message + "\n")
        self._log_text.see(END)
        self._log_text.configure(state=DISABLED)

    def _on_close(self) -> None:
        if self._processor and self._processor.is_alive():
            answer = Messagebox.yesno(
                title="确认退出",
                message="有处理任务正在运行，确定要退出吗？",
                alert=True,
            )
            if answer == "No":
                return
            self._processor.stop()
        self.destroy()

    def _center_window(self) -> None:
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, (sw // 2) - (WIN_WIDTH // 2))
        y = max(0, (sh // 2) - (WIN_HEIGHT // 2))
        self.geometry(f"{WIN_WIDTH}x{WIN_HEIGHT}+{x}+{y}")

    @staticmethod
    def _resolve_icon_path() -> Optional[str]:
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            base = os.path.join(sys._MEIPASS, "gui")
        else:
            base = os.path.dirname(__file__)
        ico = os.path.join(base, "icon.ico")
        png = os.path.join(base, "icon.png")
        return ico if os.path.isfile(ico) else (png if os.path.isfile(png) else None)

    @staticmethod
    def _resolve_gui_path(filename: str) -> str:
        """Resolve a GUI resource path (works in dev and frozen PyInstaller builds)."""
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            base = os.path.join(sys._MEIPASS, "gui")
        else:
            base = os.path.dirname(__file__)
        return os.path.join(base, filename)

    def _set_app_icon(self) -> None:
        icon = self._resolve_icon_path()
        if not icon:
            return
        try:
            if icon.endswith(".ico"):
                self.iconbitmap(icon)
            else:
                photo = ttk.PhotoImage(file=icon)
                self.tk.call('wm', 'iconphoto', self._w, photo)
        except Exception:
            pass

    def _update_status(self, text: str) -> None:
        self._status_label.configure(text=text)


def launch_gui() -> None:
    app = YTPDFCleanerApp()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
