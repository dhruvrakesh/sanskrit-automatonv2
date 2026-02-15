# scripts/watch_inbox.py
import time, os, sys, subprocess
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "inbox"

class Handler(FileSystemEventHandler):
    def on_created(self, event):
        p = Path(event.src_path)
        if p.suffix.lower() == ".pdf":
            print(f"[watch] new PDF: {p.name}")
            subprocess.Popen([sys.executable, str(ROOT/"scripts"/"ingest_pdf.py"),
                              "--pdf", str(p), "--db", str(ROOT/"data"/"context.db"),
                              "--doc", p.stem])

if __name__ == "__main__":
    INBOX.mkdir(exist_ok=True)
    obs = Observer()
    obs.schedule(Handler(), str(INBOX), recursive=False)
    obs.start()
    print(f"Watching: {INBOX}")
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        obs.stop()
    obs.join()
