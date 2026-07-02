"""
DiskMaster Pro - Scanner

多线程文件元数据扫描器：
- 递归遍历目录
-多线程读取文件元数据
Rich 实时进度显示
统计文件数， 目录数，总大小
支持取消扫描
"""

from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

@dataclass(frozen=True)
class ScanResult:
    """单个文件的扫描结果。"""
    path: Path
    size: int
    modified_time: float

class Scanner:
    """高性能目录扫描器。"""
    def __init__(self, workers: int = 8, batch_size: int = 500) -> None:
        if workers < 1:
            raise ValueError("workers 必须大于或等于 1。")
        if batch_size < 1:
            raise ValueError("batch_size 必须大于或等于 1。")

        self.workers = workers
        self.batch_size = batch_size

        self.file_count = 0
        self.folder_count = 0
        self.total_size = 0
        self.error_count = 0
        self.current_path = ""

        self.results: list[ScanResult] = []

        self._lock = threading.Lock()
        self._cancel_event = threading.Event()
        self._start_time = 0.0
        self._console = Console()

@property
def elapsed_seconds(self) -> float:
    """返回本次扫描已耗时秒数。"""
    if self._start_time == 0:
        return 0.0
    return time.monotonic() - self._start_time

@property
def files_per_second(self) -> float:
    elapsed = self.elapsed_seconds
    if elapsed <= 0:
        return 0.0
    return self.file_count / elapsed

def cancel(self) -> None:
    self._cancel_event.set()
    
def reset(self) -> None:
    with self._lock:
        self.file_count = 0
        self.folder_count = 0
        self.total_size = 0
        self.error_count = 0
        self.current_path = ""
        self.results = []
    
    self._cancel_event.clear()
    self._start_time = 0.0

def scan(self, root: Path) -> list[ScanResult]:
    root = root.expanduser().resolve()

    if not root.exists():
        raise FileNotFoundError(f"扫描路径不存在: {root}")
    
    if not root.is_dir():
        raise NotADirectoryError(f"扫描路径不存在: {root}")
    
    self.rest()
    self._start_time = time.monotonic()

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]正在扫描"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("[white]{task.description}"),
        TimeElapsedColumn(),
        console=self._console,
        transient=False,
    )

    with progress:
        task_id = progress.add_task(
            "正在枚举文件...",
            total=None,
        )

        with ThreadPoolExecutor(
            max_workers=self.workers,
            thread_name_prefix="diskmaster-worker",
        ) as executor:
            for batch in self._iter_batches(self._walk_files(root)):
                if self._cancel_event.is_set():
                    break
                
                futures = [
                    executor.submit(self._read_file_metadata, file_path)
                    for file_path in batch
                ]

                for future in as_completed(futures):
                    if self._cancel_event.is_set():
                        break

                    result = future.result()

                    if result is not None:
                        self._record_result(result)

                progress.update(
                    task_id,
                    description=self._progress_description(),
                )

    if self._cancel_event.is_set():
        self._console.print("[yellow]扫描已取消。[/yellow]")
    else:
        self._console.print("[green]扫描已完成。[/green]")

    return list(self.results)

def _walk_files(self, root: Path) -> Iterator[Path]:
    def on_error(_: OSError) -> None:
        with self._lock:
            self.error_count += 1

    for directory, _, filenames in os.walk(
        root,
        topdown=True,
        onerror=on_error,
        followlinks=False,
    ):
        if self._cancel_event.is_set():
            return
        
        with self._lock:
            self.folder_count += 1

        directory_path = Path(directory)

        for filename in filenames:
            if self._cancel_event.is_set():
                return
            
            yield directory_path / filename

def _read_file_metadata(self, path: Path) -> ScanResult | None:
    try:
        stat = path.stat()

        if not path.is_file():
            return None
        
        return ScanResult(
            path=path,
            size=stat.st_size,
            modified_time=stat.st_mtime,
        )
    
    except (OSError, PermissionError):
        with self._lock:
            self.error_count += 1
        return None

def _record_result(self, result: ScanResult) -> None:
    with self._lock:
        self.results.append(result)
        self.file_count += 1
        self.total_size += result.size
        self.current_path = str(result.path)

def _iter_batches(
        self,
        items: Iterator[Path],
) -> Iterator[list[Path]]:
    batch: list[Path] = []

    for item in items:
        batch.append(item)

        if len(batch) >= self.batch_size:
            yield batch
            batch = []

    if batch:
        yield batch

def _progress_description(self) -> str:
    size_mb = self.total_size / 1024 / 1024
    speed = self.files_per_second

    return (
        f"文件： {self.file_count:,} | "
        f"目录： {self.folder_count:,} | "
        f"大小： {size_mb:,.2f} MB | "
        f"速度： {speed:,.0f} 文件/秒 | "
        f"错误： {self.error_count:,} | "
    )