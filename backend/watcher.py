from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class _CSVHandler(FileSystemEventHandler):
    def __init__(self, callback: Callable[[str], None]) -> None:
        self._callback = callback
        self._seen: set[str] = set()

    def on_created(self, event):
        if event.is_directory:
            return
        path = event.src_path
        if path.lower().endswith(".csv") and path not in self._seen:
            self._seen.add(path)
            time.sleep(0.8)  # Wait for the file to finish writing
            self._callback(path)

    def on_modified(self, event):
        # Some systems emit modified instead of created for new files
        if event.is_directory:
            return
        path = event.src_path
        if path.lower().endswith(".csv") and path not in self._seen:
            self._seen.add(path)
            time.sleep(0.8)
            self._callback(path)


class DirectoryWatcher:
    def __init__(self, callback: Callable[[str], None]) -> None:
        self._callback = callback
        self._observer: Observer | None = None

    def start(self, directory: str) -> None:
        self.stop()
        path = Path(directory)
        if not path.exists():
            print(f"[watcher] Directory does not exist: {directory}")
            return
        handler = _CSVHandler(self._callback)
        self._observer = Observer()
        self._observer.schedule(handler, str(path), recursive=False)
        self._observer.start()
        print(f"[watcher] Watching: {directory}")

    def stop(self) -> None:
        if self._observer and self._observer.is_alive():
            self._observer.stop()
            self._observer.join()
        self._observer = None
