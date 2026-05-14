"""Main GUI application window for YT-PDFCleaner."""

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
APP_VERSION = "1.1.1"
DEFAULT_THEME = "superhero"

# Brand colors for YT identity
BRAND_PRIMARY = "#E62429"  # YT Red
BRAND_SECONDARY = "#282828"

# Window dimensions (doubled from original 800x600)
WIN_WIDTH = 1600
WIN_HEIGHT = 1100
WIN_MIN_WIDTH = 1100
WIN_MIN_HEIGHT = 700


class YTPDFCleanerApp(ttk.Window):
    """Main application window for YT-PDFCleaner."""

    def __init__(self) -> None:
        super().__init__(title=APP_TITLE, themename=DEFAULT_THEME)

        # ── Window setup ────────────────────────────────────────────────
        self.geometry(f"{WIN_WIDTH}x{WIN_HEIGHT}")
        self.minsize(WIN_MIN_WIDTH, WIN_MIN_HEIGHT)
        self._set_app_icon()
        self._center_window()

        # ── State ───────────────────────────────────────────────────────
        self._last_output_dir: Optional[str] = None
        self._output_mode = ttk.StringVar(value="pdf")
        self._processor: Optional[ProcessingThread] = None
        self._log_expanded = False

        # ── Build UI ────────────────────────────────────────────────────
        self._build_header()
        self._build_toolbar()
        self._build_summary_bar()
        self._build_file_list()
        self._build_output_settings()
        self._build_action_buttons()
        self._build_progress_area()
        self._build_log_area()
        self._build_status_bar()

        # ── Bind close event ────────────────────────────────────────────
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ═════════════════════════════════════════════════════════════════════
    # UI Construction
    # ═════════════════════════════════════════════════════════════════════

    # ── Header ──────────────────────────────────────────────────────────────

    def _build_header(self) -> None:
        """Build the branded header bar."""
        header = ttk.Frame(self, bootstyle="dark")
        header.pack(fill=X, padx=0, pady=0)

        brand_frame = ttk.Frame(header, bootstyle="dark")
        brand_frame.pack(side=LEFT, padx=16, pady=10)

        # YT logo badge — larger
        badge = ttk.Label(
            brand_frame,
            text="YT",
            font=("Helvetica", 20, "bold"),
            foreground=BRAND_PRIMARY,
            bootstyle="dark",
        )
        badge.pack(side=LEFT)

        title_lbl = ttk.Label(
            brand_frame,
            text="PDFCleaner",
            font=("Helvetica", 18),
            foreground="white",
            bootstyle="dark",
        )
        title_lbl.pack(side=LEFT, padx=(6, 0))

        # Version
        ver_lbl = ttk.Label(
            header,
            text=f"v{APP_VERSION}",
            font=("Helvetica", 10),
            foreground="#888888",
            bootstyle="dark",
        )
        ver_lbl.pack(side=LEFT, padx=(8, 0), pady=10)

        # Separator
        sep = ttk.Separator(self, orient=HORIZONTAL, bootstyle="secondary")
        sep.pack(fill=X, padx=0, pady=0)

    # ── Toolbar ─────────────────────────────────────────────────────────────

    def _build_toolbar(self) -> None:
        """Build the toolbar with file selection, clear and about buttons."""
        toolbar = ttk.Frame(self, padding=(12, 8))
        toolbar.pack(fill=X)

        # Select Files
        self._btn_files = ttk.Button(
            toolbar,
            text="📄 选择文件 (F)",
            command=self._on_select_files,
            bootstyle="info-outline",
        )
        self._btn_files.pack(side=LEFT, padx=(0, 6))

        # Select Folder
        self._btn_folder = ttk.Button(
            toolbar,
            text="📁 选择文件夹 (D)",
            command=self._on_select_folder,
            bootstyle="info-outline",
        )
        self._btn_folder.pack(side=LEFT, padx=(0, 12))

        # Clear all (toolbar — more visible)
        self._btn_clear_tool = ttk.Button(
            toolbar,
            text="🗑 清空全部 (L)",
            command=self._on_clear_list,
            bootstyle="secondary-outline",
        )
        self._btn_clear_tool.pack(side=LEFT, padx=(0, 6))

        # Keyboard shortcuts
        self.bind("<Alt-f>", lambda e: self._on_select_files())
        self.bind("<Alt-d>", lambda e: self._on_select_folder())
        self.bind("<Alt-l>", lambda e: self._on_clear_list())

        # Spacer
        ttk.Label(toolbar, text="").pack(side=LEFT, fill=X, expand=True)

        # About button
        self._btn_about = ttk.Button(
            toolbar,
            text="ℹ 关于 (A)",
            command=self._on_about,
            bootstyle="secondary-outline",
        )
        self._btn_about.pack(side=RIGHT)
        self.bind("<Alt-a>", lambda e: self._on_about())

    # ── Summary bar ─────────────────────────────────────────────────────────

    def _build_summary_bar(self) -> None:
        """Build the summary bar showing file counts."""
        self._summary_bar = ttk.Frame(self, padding=(12, 3))
        self._summary_bar.pack(fill=X)

        self._summary_label = ttk.Label(
            self._summary_bar,
            text="已选: 0 / 0 个文件  │  总大小: 0 MB",
            font=("Helvetica", 11),
        )
        self._summary_label.pack(side=LEFT)

    # ── File list ───────────────────────────────────────────────────────────

    def _build_file_list(self) -> None:
        """Build the file list Treeview component."""
        container = ttk.Frame(self, padding=(12, 6))
        container.pack(fill=BOTH, expand=True)

        self._file_list = FileListFrame(
            container,
            on_files_changed=self._on_files_changed,
            on_file_double_click=self._on_file_double_click,
        )
        self._file_list.pack(fill=BOTH, expand=True)

    # ── Output settings ─────────────────────────────────────────────────────

    def _build_output_settings(self) -> None:
        """Build output format and directory settings panel."""
        frame = ttk.LabelFrame(self, text="输出设置")
        frame.pack(fill=X, padx=12, pady=(4, 0))

        # Format selection row
        fmt_row = ttk.Frame(frame)
        fmt_row.pack(fill=X, pady=(0, 8))

        ttk.Label(fmt_row, text="输出格式:", font=("Helvetica", 11)).pack(side=LEFT, padx=(0, 12))

        rb_pdf = ttk.Radiobutton(
            fmt_row,
            text="PDF（保留原排版）",
            variable=self._output_mode,
            value="pdf",
            bootstyle="info",
        )
        rb_pdf.pack(side=LEFT, padx=(0, 20))

        rb_md = ttk.Radiobutton(
            fmt_row,
            text="Markdown（纯文本）",
            variable=self._output_mode,
            value="markdown",
            bootstyle="info",
        )
        rb_md.pack(side=LEFT)

        # Output directory row
        dir_row = ttk.Frame(frame)
        dir_row.pack(fill=X)

        ttk.Label(dir_row, text="输出目录:", font=("Helvetica", 11)).pack(side=LEFT, padx=(0, 12))

        self._output_dir_var = ttk.StringVar(value="")
        self._output_dir_entry = ttk.Entry(
            dir_row,
            textvariable=self._output_dir_var,
            bootstyle="info",
        )
        self._output_dir_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 6))

        # Browse button
        self._btn_browse = ttk.Button(
            dir_row,
            text="📁 浏览",
            command=self._on_browse_output_dir,
            bootstyle="info-outline",
            width=8,
        )
        self._btn_browse.pack(side=LEFT, padx=(0, 4))

        # Open directory button (NEW)
        self._btn_open_dir = ttk.Button(
            dir_row,
            text="📂 打开目录",
            command=self._on_open_output_dir,
            bootstyle="secondary-outline",
            width=10,
        )
        self._btn_open_dir.pack(side=LEFT)

    # ── Action buttons ──────────────────────────────────────────────────────

    def _build_action_buttons(self) -> None:
        """Build the main action buttons (Start, Stop, Clear)."""
        frame = ttk.Frame(self, padding=(12, 8))
        frame.pack(fill=X)

        self._btn_start = ttk.Button(
            frame,
            text="▶  开始处理",
            command=self._on_start_processing,
            bootstyle="success",
            width=16,
        )
        self._btn_start.pack(side=LEFT, padx=(0, 8))

        self._btn_stop = ttk.Button(
            frame,
            text="■  停止",
            command=self._on_stop_processing,
            bootstyle="danger-outline",
            width=12,
            state=DISABLED,
        )
        self._btn_stop.pack(side=LEFT, padx=(0, 8))

        # Spacer
        ttk.Label(frame, text="").pack(side=LEFT, fill=X, expand=True)

        self._btn_clear = ttk.Button(
            frame,
            text="🗑  清空列表",
            command=self._on_clear_list,
            bootstyle="secondary-outline",
            width=12,
        )
        self._btn_clear.pack(side=RIGHT)

    # ── Progress area ───────────────────────────────────────────────────────

    def _build_progress_area(self) -> None:
        """Build the progress bar and status display."""
        frame = ttk.Frame(self, padding=(12, 4))
        frame.pack(fill=X)

        # Progress bar — taller, more visible
        self._progress_bar = ttk.Progressbar(
            frame,
            mode="determinate",
            value=0,
            bootstyle="info-striped",
            length=800,
        )
        self._progress_bar.pack(fill=X, pady=(0, 4))

        # Progress text
        self._progress_label = ttk.Label(
            frame,
            text="就绪 — 请选择 PDF 文件开始处理",
            font=("Helvetica", 10),
        )
        self._progress_label.pack(anchor=W)

        # Result summary
        self._result_label = ttk.Label(
            frame,
            text="结果汇总: 0 成功 / 0 失败 / 0 跳过",
            font=("Helvetica", 10),
            foreground="#aaaaaa",
        )
        self._result_label.pack(anchor=W)

    # ── Log area ────────────────────────────────────────────────────────────

    def _build_log_area(self) -> None:
        """Build the expandable log display area."""
        self._log_container = ttk.Frame(self)
        self._log_container.pack(fill=X, padx=12, pady=(0, 4))

        # Toggle button
        self._log_toggle_btn = ttk.Button(
            self._log_container,
            text="▶ 展开日志",
            command=self._toggle_log,
            bootstyle="secondary-outline",
            width=14,
        )
        self._log_toggle_btn.pack(anchor=W, pady=(2, 0))

        # Log text widget (initially hidden)
        self._log_frame = ttk.Frame(self, borderwidth=1, relief=SOLID)
        self._log_text = ttk.Text(
            self._log_frame,
            height=10,
            wrap=WORD,
            font=("Consolas", 10),
            state=DISABLED,
            foreground="#cccccc",
            background="#1a1a2e",
        )
        self._log_scroll = ttk.Scrollbar(
            self._log_frame,
            orient=VERTICAL,
            command=self._log_text.yview,
        )
        self._log_text.configure(yscrollcommand=self._log_scroll.set)
        self._log_text.pack(side=LEFT, fill=BOTH, expand=True)
        self._log_scroll.pack(side=RIGHT, fill=Y)

    # ── Status bar ──────────────────────────────────────────────────────────

    def _build_status_bar(self) -> None:
        """Build the bottom status bar."""
        self._status_bar = ttk.Frame(self, bootstyle="secondary", padding=(12, 4))
        self._status_bar.pack(fill=X, side=BOTTOM)

        self._status_label = ttk.Label(
            self._status_bar,
            text="就绪",
            font=("Helvetica", 10),
            bootstyle="secondary",
        )
        self._status_label.pack(side=LEFT)

    # ═════════════════════════════════════════════════════════════════════
    # Event Handlers
    # ═════════════════════════════════════════════════════════════════════

    # ── File selection ──────────────────────────────────────────────────────

    def _on_select_files(self) -> None:
        """Open file dialog to select PDF files."""
        import tkinter.filedialog as fd

        paths = fd.askopenfilenames(
            title="选择 PDF 文件",
            filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*.*")],
            parent=self,
        )
        if paths:
            self._file_list.add_files(list(paths))

    def _on_select_folder(self) -> None:
        """Open directory dialog to scan for PDF files."""
        import tkinter.filedialog as fd

        directory = fd.askdirectory(
            title="选择包含 PDF 的文件夹",
            parent=self,
        )
        if not directory:
            return

        self._update_status("正在扫描文件夹…")
        self._progress_label.configure(text="正在扫描文件夹中的 PDF 文件…")

        # Run scan in background thread
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
        """Show custom about dialog with author info and wider layout."""
        win = ttk.Toplevel(self)
        win.title(f"关于 {APP_NAME}")
        win.geometry("480x420")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        # Center on parent
        win.update_idletasks()
        px = self.winfo_x() + (self.winfo_width() - 480) // 2
        py = self.winfo_y() + (self.winfo_height() - 420) // 2
        win.geometry(f"+{px}+{py}")

        main = ttk.Frame(win, padding=(30, 24))
        main.pack(fill=BOTH, expand=True)

        # App icon (use dedicated about PNG for reliable PhotoImage load)
        icon_about_path = os.path.join(os.path.dirname(__file__), "icon_about.png")
        if os.path.isfile(icon_about_path):
            try:
                icon_img = ttk.PhotoImage(file=icon_about_path)
                icon_lbl = ttk.Label(main, image=icon_img)
                icon_lbl.image = icon_img  # Keep reference!
                icon_lbl.pack(pady=(0, 8))
            except Exception:
                pass

        # Brand title
        badge_frame = ttk.Frame(main)
        badge_frame.pack(pady=(0, 4))
        ttk.Label(
            badge_frame,
            text="YT", font=("Helvetica", 22, "bold"),
            foreground=BRAND_PRIMARY,
        ).pack(side=LEFT)
        ttk.Label(
            badge_frame,
            text="PDFCleaner", font=("Helvetica", 20),
        ).pack(side=LEFT, padx=(6, 0))

        # Version
        ttk.Label(
            main,
            text=f"v{APP_VERSION}",
            font=("Helvetica", 11),
            foreground="#999999",
        ).pack(pady=(0, 12))

        # Description
        ttk.Label(
            main,
            text="PDF 水印清除工具（绿色免安装版）",
            font=("Helvetica", 13, "bold"),
        ).pack(pady=(0, 8))

        # Separator
        ttk.Separator(main, orient=HORIZONTAL).pack(fill=X, pady=(4, 12))

        # Info rows
        info_frame = ttk.Frame(main)
        info_frame.pack(fill=X, pady=(0, 12))

        info_items = [
            ("✍ 作者", "xbshen"),
            ("📋 功能", "检测并移除 SGCC 追踪水印"),
            ("🔧 技术栈", "Python · PyMuPDF · ttkbootstrap"),
        ]
        for label, value in info_items:
            row = ttk.Frame(info_frame)
            row.pack(fill=X, pady=3)
            ttk.Label(row, text=label, font=("Helvetica", 11), width=8, anchor=E).pack(side=LEFT, padx=(0, 12))
            ttk.Label(row, text=value, font=("Helvetica", 11)).pack(side=LEFT)

        # Footer
        ttk.Separator(main, orient=HORIZONTAL).pack(fill=X, pady=(4, 12))
        ttk.Label(
            main,
            text="© 2026 YT Technologies",
            font=("Helvetica", 10),
            foreground="#888888",
        ).pack(pady=(0, 12))

        # OK button
        btn_ok = ttk.Button(
            main,
            text="✔ 确定",
            command=win.destroy,
            bootstyle="success",
            width=16,
        )
        btn_ok.pack()

    # ── Output directory helpers ────────────────────────────────────────────

    def _on_open_output_dir(self) -> None:
        """Open the output directory in the system file manager."""
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
        """Open a folder in the OS file manager."""
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

    # ── File list callbacks ─────────────────────────────────────────────────

    def _on_files_changed(self) -> None:
        """Update summary bar when file list changes."""
        entries = self._file_list.get_all_entries()
        checked = self._file_list.get_checked_entries()
        total_size = sum(e.size for e in entries)

        if total_size < 1024 * 1024:
            size_str = f"{total_size / 1024:.1f} KB"
        else:
            size_str = f"{total_size / (1024 * 1024):.1f} MB"

        self._summary_label.configure(
            text=f"已选: {len(checked)} / {len(entries)} 个文件  │  总大小: {size_str}"
        )

        # Auto-set output directory if not set
        if not self._output_dir_var.get() and entries:
            self._auto_set_output_dir(entries[0].path)

    def _on_file_double_click(self, entry: FileEntry) -> None:
        """Open file with system PDF viewer on double-click."""
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
        """Auto-set output directory to YT_output next to the first file."""
        base_dir = os.path.dirname(file_path)
        output_dir = os.path.join(base_dir, "YT_output")
        self._output_dir_var.set(output_dir)
        self._last_output_dir = output_dir

    # ── Output settings ─────────────────────────────────────────────────────

    def _on_browse_output_dir(self) -> None:
        """Open directory browser for output path."""
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

    # ── Processing control ──────────────────────────────────────────────────

    def _on_start_processing(self) -> None:
        """Start background processing of checked files."""
        entries = self._file_list.get_checked_entries()
        if not entries:
            Messagebox.show_info(
                title="没有文件",
                message="请先添加 PDF 文件并勾选要处理的文件。",
            )
            return

        # Resolve output directory
        output_dir = self._output_dir_var.get().strip()
        if not output_dir:
            # Default: YT_output in first file's directory
            if entries:
                output_dir = os.path.join(os.path.dirname(entries[0].path), "YT_output")
                self._output_dir_var.set(output_dir)

        # Ensure output dir exists
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as exc:
            Messagebox.show_error(
                title="目录错误",
                message=f"无法创建输出目录:\n{exc}",
            )
            return

        # Update UI state
        self._btn_start.configure(state=DISABLED)
        self._btn_stop.configure(state=NORMAL)
        self._btn_clear.configure(state=DISABLED)
        self._btn_clear_tool.configure(state=DISABLED)
        self._progress_bar.configure(value=0)
        self._result_label.configure(text="结果汇总: 0 成功 / 0 失败 / 0 跳过")

        mode = self._output_mode.get()

        # Expand log automatically during processing
        if not self._log_expanded:
            self._toggle_log()

        # Start processing thread
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
        """Signal the processing thread to stop."""
        if self._processor and self._processor.is_alive():
            self._processor.stop()
            self._btn_stop.configure(state=DISABLED)
            self._update_status("正在停止…")

    def _on_clear_list(self) -> None:
        """Clear the entire file list."""
        if self._file_list.get_entry_count() == 0:
            return
        answer = Messagebox.yesno(
            title="清空列表",
            message="确定要清空所有文件吗？",
        )
        if answer == "Yes":
            self._file_list.clear_all()
            self._result_label.configure(text="结果汇总: 0 成功 / 0 失败 / 0 跳过")
            self._progress_label.configure(text="就绪 — 请选择 PDF 文件开始处理")
            self._progress_bar.configure(value=0)

    # ── Processing callbacks ────────────────────────────────────────────────

    def _on_processing_progress(self, progress: ProgressInfo) -> None:
        """Update UI with progress from the processing thread."""
        self.after(0, lambda p=progress: self._apply_progress(p))

    def _apply_progress(self, p: ProgressInfo) -> None:
        """Apply progress update on the main thread."""
        self._progress_bar.configure(value=p.percent)
        self._progress_label.configure(
            text=f"{p.current_file} — {p.current_status}"
        )
        self._result_label.configure(
            text=f"结果汇总: {p.success} 成功 / {p.failed} 失败 / {p.skipped} 跳过"
        )
        self._update_status(
            f"{p.completed}/{p.total} — {p.current_file}"
        )

    def _on_processing_complete(self, progress: ProgressInfo) -> None:
        """Handle processing completion."""
        self.after(0, lambda p=progress: self._apply_complete(p))

    def _apply_complete(self, p: ProgressInfo) -> None:
        """Apply completion state on the main thread."""
        self._btn_start.configure(state=NORMAL)
        self._btn_stop.configure(state=DISABLED)
        self._btn_clear.configure(state=NORMAL)
        self._btn_clear_tool.configure(state=NORMAL)
        self._progress_bar.configure(value=100.0)

        # Mark all files as processed
        for entry in self._file_list.get_all_entries():
            if entry.checked:
                self._file_list.update_entry_status(entry, "processed")

        if p.status == ProcessingStatus.STOPPED:
            self._update_status("已停止")
            self._progress_label.configure(text="⏹ 处理已中断")
        else:
            self._update_status("处理完成")
            self._progress_label.configure(
                text=f"✅ 处理完成 — {p.success} 成功, {p.failed} 失败, {p.skipped} 跳过"
            )

        # Show custom summary dialog (doubled width)
        self._show_completion_dialog(p)

    def _show_completion_dialog(self, p: ProgressInfo) -> None:
        """Show a custom completion summary dialog with aligned buttons and icons."""
        win = ttk.Toplevel(self)
        win.title("处理结果")
        win.geometry("620x420")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        # Center on parent
        win.update_idletasks()
        px = self.winfo_x() + (self.winfo_width() - 620) // 2
        py = self.winfo_y() + (self.winfo_height() - 420) // 2
        win.geometry(f"+{px}+{py}")

        # Main frame
        main = ttk.Frame(win, padding=(24, 20))
        main.pack(fill=BOTH, expand=True)

        # ── Status icon: use YT-branded PNG icons for consistency ──
        icon_frame = ttk.Frame(main)
        icon_frame.pack(pady=(0, 4))

        dialog_icon = "icon_dialog_warn.png" if p.failed > 0 else "icon_dialog_check.png"
        icon_path = os.path.join(os.path.dirname(__file__), dialog_icon)
        if os.path.isfile(icon_path):
            try:
                icon_img = ttk.PhotoImage(file=icon_path)
                icon_lbl = ttk.Label(icon_frame, image=icon_img)
                icon_lbl.image = icon_img  # Keep reference!
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

        # Title
        title_text = "处理完成（部分异常）" if p.failed > 0 else "全部处理完成"
        title_lbl = ttk.Label(
            main,
            text=title_text,
            font=("Helvetica", 16, "bold"),
        )
        title_lbl.pack(pady=(0, 16))

        # ── Stats table ──
        stats_frame = ttk.Frame(main)
        stats_frame.pack(fill=X, pady=(0, 20))

        stats = [
            ("📄 总计", f"{p.total} 个文件"),
            ("✅ 成功", f"{p.success}"),
            ("❌ 失败", f"{p.failed}"),
            ("⏭  跳过", f"{p.skipped}"),
        ]

        for label, value in stats:
            row = ttk.Frame(stats_frame)
            row.pack(fill=X, pady=2)
            ttk.Label(row, text=label, font=("Helvetica", 12), width=10, anchor=E).pack(side=LEFT, padx=(0, 16))
            ttk.Label(row, text=value, font=("Helvetica", 12, "bold"), anchor=W).pack(side=LEFT)

        # ── Button row (centered, equal width) ──
        btn_row = ttk.Frame(main)
        btn_row.pack(fill=X, pady=(12, 0))

        # Center-align container
        center = ttk.Frame(btn_row)
        center.pack()

        output_dir = self._output_dir_var.get()
        if output_dir and os.path.isdir(output_dir):
            btn_open = ttk.Button(
                center,
                text="📂 打开输出目录",
                command=lambda: (self._open_folder_in_explorer(output_dir), win.destroy()),
                bootstyle="info",
                width=18,
            )
            btn_open.pack(side=LEFT, padx=(0, 12))

        btn_ok = ttk.Button(
            center,
            text="✔ 确定",
            command=win.destroy,
            bootstyle="success",
            width=18,
        )
        btn_ok.pack(side=LEFT)

    def _on_processing_log(self, message: str) -> None:
        """Add a log message to the log area."""
        self.after(0, lambda m=message: self._append_log(m))

    def _append_log(self, message: str) -> None:
        """Append a line to the log text widget."""
        self._log_text.configure(state=NORMAL)
        self._log_text.insert(END, message + "\n")
        self._log_text.see(END)
        self._log_text.configure(state=DISABLED)

    # ── Log area toggle ─────────────────────────────────────────────────────

    def _toggle_log(self) -> None:
        """Expand or collapse the log area."""
        if self._log_expanded:
            self._log_frame.pack_forget()
            self._log_toggle_btn.configure(text="▶ 展开日志")
            self._log_expanded = False
        else:
            self._log_frame.pack(fill=BOTH, expand=True, padx=0, pady=(2, 0))
            self._log_toggle_btn.configure(text="▼ 收起日志")
            self._log_expanded = True

    # ── Window management ───────────────────────────────────────────────────

    def _on_close(self) -> None:
        """Handle window close — stop any running process first."""
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
        """Center the window on screen."""
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, (sw // 2) - (WIN_WIDTH // 2))
        y = max(0, (sh // 2) - (WIN_HEIGHT // 2))
        self.geometry(f"{WIN_WIDTH}x{WIN_HEIGHT}+{x}+{y}")

    @staticmethod
    def _resolve_icon_path() -> Optional[str]:
        """Resolve icon path, handling PyInstaller --onefile bundle."""
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # PyInstaller bundle: icon lives inside the extracted data dir
            base = os.path.join(sys._MEIPASS, "gui")
        else:
            base = os.path.dirname(__file__)  # gui/ directory
        ico = os.path.join(base, "icon.ico")
        png = os.path.join(base, "icon.png")
        return ico if os.path.isfile(ico) else (png if os.path.isfile(png) else None)

    def _set_app_icon(self) -> None:
        """Set the window/taskbar icon."""
        icon = self._resolve_icon_path()
        if not icon:
            return
        try:
            if icon.endswith(".ico"):
                self.iconbitmap(icon)
            else:
                # PNG via PhotoImage
                photo = ttk.PhotoImage(file=icon)
                self.tk.call('wm', 'iconphoto', self._w, photo)
        except Exception:
            pass  # Non-critical — ignore icon load failures

    def _update_status(self, text: str) -> None:
        """Update the status bar text."""
        self._status_label.configure(text=text)


# ═════════════════════════════════════════════════════════════════════════
# Entry point (when run directly)
# ═════════════════════════════════════════════════════════════════════════

def launch_gui() -> None:
    """Launch the main GUI application."""
    app = YTPDFCleanerApp()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
