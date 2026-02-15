# scripts/env_loader.py
from __future__ import annotations
import os
from pathlib import Path

def _load_dotenv():
    # Import lazily to avoid new hard deps if you don't want them
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    root = Path(__file__).resolve().parents[1]
    # load repo .env first, then system env
    load_dotenv(dotenv_path=root / ".env", override=False)

def load_env() -> None:
    """Load .env once per process (no-op if python-dotenv isn't installed)."""
    _load_dotenv()

def find_tesseract_and_tessdata():
    """
    Return (tesseract_cmd, tessdata_dir_candidates[list]).
    Accept both styles:
      TESSDATA_PREFIX = C:\Program Files\Tesseract-OCR
      TESSDATA_PREFIX = C:\Program Files\Tesseract-OCR\tessdata
    """
    load_env()
    tcmd = os.environ.get("TESSERACT_PATH") or "tesseract"
    tprefix = os.environ.get("TESSDATA_PREFIX", "")

    cands = []
    if tprefix:
        p = Path(tprefix)
        if (p / "tessdata").is_dir():
            cands.append(str(p / "tessdata"))
        if p.is_dir():
            cands.append(str(p))  # in case user already points to tessdata itself

    # also try alongside the tesseract binary
    try:
        exe = Path(tcmd)
        if exe.exists():
            td = exe.parent / "tessdata"
            if td.is_dir():
                cands.append(str(td))
    except Exception:
        pass

    # de-dupe while preserving order
    seen = set()
    uniq = []
    for x in cands:
        if x and x not in seen:
            seen.add(x); uniq.append(x)
    return tcmd, uniq

def poppler_path():
    load_env()
    return os.environ.get("POPPLER_PATH") or ""
