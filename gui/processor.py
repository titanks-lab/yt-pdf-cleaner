"""Background processing thread with progress management for YT-PDFCleaner."""

import os
import threading
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional

from core.engine import convert_to_markdown, remove_watermark


class ProcessingStatus(Enum):
    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()
    STOPPED = auto()
    FINISHED = auto()
    ERROR = auto()


@dataclass
class ProgressInfo:
    """Snapshot of current processing progress."""

    total: int = 0
    completed: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    current_file: str = ""
    current_status: str = ""
    percent: float = 0.0
    status: ProcessingStatus = ProcessingStatus.IDLE


class ProcessingThread(threading.Thread):
    """Background thread that processes PDF files with progress reporting.

    Processes files one by one, calling either ``remove_watermark`` (PDF mode)
    or ``convert_to_markdown`` (Markdown mode). Reports progress via a callback
    and supports graceful stop via a stop flag.
    """

    def __init__(
        self,
        files: List[Any],
        output_dir: str,
        mode: str = "pdf",
        on_progress: Optional[Callable[[ProgressInfo], None]] = None,
        on_complete: Optional[Callable[[ProgressInfo], None]] = None,
        on_log: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Initialize the processing thread.

        Args:
            files: List of FileEntry objects (or objects with ``.path``, ``.name`` attrs).
            output_dir: Directory where output files will be saved.
            mode: ``"pdf"`` for watermark removal or ``"markdown"`` for text conversion.
            on_progress: Callback invoked on each file completion with ProgressInfo.
            on_complete: Callback invoked when processing finishes.
            on_log: Callback for log messages with timestamp.
        """
        super().__init__(daemon=True)
        self._files = files
        self._output_dir = output_dir
        self._mode = mode
        self._on_progress = on_progress
        self._on_complete = on_complete
        self._on_log = on_log

        self._stop_flag = threading.Event()
        self._progress = ProgressInfo(
            total=len(files),
            status=ProcessingStatus.IDLE,
        )

    # ── Public control API ──────────────────────────────────────────────────

    def stop(self) -> None:
        """Signal the thread to stop after the current file."""
        self._stop_flag.set()
        self._log("⏹ 收到停止信号，处理将在当前文件完成后停止")

    @property
    def progress(self) -> ProgressInfo:
        return self._progress

    # ── Thread run ──────────────────────────────────────────────────────────

    def run(self) -> None:
        """Main processing loop — runs in a background thread."""
        self._progress.status = ProcessingStatus.RUNNING
        total = self._progress.total
        self._log(f"▶ 开始处理 {total} 个文件，输出格式: {'PDF' if self._mode == 'pdf' else 'Markdown'}")
        self._log(f"📁 输出目录: {self._output_dir}")

        # Ensure output directory exists
        try:
            os.makedirs(self._output_dir, exist_ok=True)
        except Exception as exc:
            self._progress.status = ProcessingStatus.ERROR
            self._log(f"❌ 无法创建输出目录: {exc}")
            self._fire_progress()
            if self._on_complete:
                self._on_complete(self._progress)
            return

        for idx, entry in enumerate(self._files):
            # Check stop flag
            if self._stop_flag.is_set():
                self._progress.status = ProcessingStatus.STOPPED
                self._log("⏹ 处理已中断")
                break

            # Get file path — support both FileEntry and string paths
            if hasattr(entry, "path"):
                filepath = entry.path
                filename = entry.name
            else:
                filepath = str(entry)
                filename = os.path.basename(filepath)

            # Check file existence
            if not os.path.isfile(filepath):
                self._progress.skipped += 1
                self._progress.current_file = filename
                self._progress.current_status = "⚠ 文件不存在，已跳过"
                self._log(f"⚠ [{idx+1}/{total}] {filename} — 文件不存在，跳过")
                self._progress.completed = idx + 1
                self._update_percent()
                self._fire_progress()
                continue

            self._progress.current_file = filename
            self._progress.current_status = "⏳ 处理中…"
            self._log(f"[{idx+1}/{total}] 处理中: {filename}")
            self._fire_progress()

            # Build output path
            base_name = os.path.splitext(filename)[0]
            if self._mode == "pdf":
                output_path = os.path.join(self._output_dir, f"{base_name}_去水印.pdf")
            else:
                output_path = os.path.join(self._output_dir, f"{base_name}.md")

            # Process the file
            try:
                if self._mode == "pdf":
                    result = remove_watermark(filepath, output_path)
                else:
                    result = convert_to_markdown(filepath, output_path)

                if result.get("success"):
                    self._progress.success += 1
                    self._progress.current_status = "✅ 处理成功"
                    if self._mode == "pdf":
                        streams = result.get("streams_cleared", 0)
                        self._log(f"  ✅ {filename} — 水印清除完成 (清除 {streams} 个流)")
                    else:
                        chars = result.get("char_count", 0)
                        self._log(f"  ✅ {filename} — Markdown 转换完成 ({chars} 字符)")
                else:
                    self._progress.failed += 1
                    error_msg = result.get("error", "未知错误")
                    self._progress.current_status = "❌ 处理失败"
                    self._log(f"  ❌ {filename} — 失败: {error_msg}")
            except Exception as exc:
                self._progress.failed += 1
                self._progress.current_status = "❌ 处理异常"
                self._log(f"  ❌ {filename} — 异常: {exc}")

            self._progress.completed = idx + 1
            self._update_percent()
            self._fire_progress()

        # Finished
        if self._progress.status != ProcessingStatus.STOPPED:
            self._progress.status = ProcessingStatus.FINISHED

        self._log("=" * 40)
        summary = (
            f"处理完成: {self._progress.success} 成功 / "
            f"{self._progress.failed} 失败 / "
            f"{self._progress.skipped} 跳过"
        )
        self._log(summary)
        self._log(f"输出目录: {self._output_dir}")

        if self._on_complete:
            self._on_complete(self._progress)

    # ── Internal helpers ────────────────────────────────────────────────────

    def _update_percent(self) -> None:
        """Recalculate percentage based on completed/total."""
        total = self._progress.total
        if total > 0:
            self._progress.percent = (self._progress.completed / total) * 100.0
        else:
            self._progress.percent = 100.0

    def _fire_progress(self) -> None:
        """Emit progress callback with a copy of the current state."""
        if self._on_progress:
            # Create a snapshot to avoid threading issues
            snapshot = ProgressInfo(
                total=self._progress.total,
                completed=self._progress.completed,
                success=self._progress.success,
                failed=self._progress.failed,
                skipped=self._progress.skipped,
                current_file=self._progress.current_file,
                current_status=self._progress.current_status,
                percent=self._progress.percent,
                status=self._progress.status,
            )
            self._on_progress(snapshot)

    def _log(self, message: str) -> None:
        """Emit a timestamped log message."""
        if self._on_log:
            timestamp = time.strftime("%H:%M:%S")
            self._on_log(f"[{timestamp}] {message}")
