import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from config import DIRECTORIES_TO_WATCH, TEXT_EXTENSIONS, IMAGE_EXTENSIONS

class _Handler(FileSystemEventHandler):
    def __init__(self, q):
        self.q = q

    def on_created(self, event):
        if not event.is_directory:
            self._handle(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self._handle(event.dest_path)

    def _handle(self, path):
        _, ext = os.path.splitext(path.lower())
        if ext in TEXT_EXTENSIONS + IMAGE_EXTENSIONS:
            time.sleep(0.2) # Wait for file to be fully written
            self.q.put(path)

class FileMonitor:
    def __init__(self, q):
        self.q = q
        self.observer = Observer()

    def start(self):
        handler = _Handler(self.q)
        for d in DIRECTORIES_TO_WATCH:
            os.makedirs(d, exist_ok=True)
            self.observer.schedule(handler, d, recursive=False)
        self.observer.start()
        print('📂 Monitoring started on:', DIRECTORIES_TO_WATCH)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        self.observer.stop()
        self.observer.join()
