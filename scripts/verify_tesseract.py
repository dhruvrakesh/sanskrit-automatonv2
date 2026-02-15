# scripts/verify_tesseract.py
import os, sys, shutil, subprocess, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

def load_env(dotenv_path: Path = ROOT/".env"):
    """Minimal .env loader (KEY=VALUE lines). Sets os.environ in-place."""
    if not dotenv_path.exists():
        return
    for raw in dotenv_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        os.environ[k] = v

def which(exe):
    return shutil.which(exe)

def list_langs(tesseract_cmd):
    try:
        out = subprocess.check_output([tesseract_cmd, "--list-langs"], stderr=subprocess.STDOUT)
        lines = out.decode("utf-8", errors="ignore").splitlines()
        # First line is "List of available languages in ...", rest are langs
        langs = [ln.strip() for ln in lines[1:] if ln.strip()]
        return lines[0].strip(), langs
    except Exception as e:
        return f"(error: {e})", []

def resolve_tessdata():
    """Return (tessdata_dir, mode) where mode is 'prefix-parent', 'tessdata', or 'auto'."""
    # Preferred: TESSDATA_PREFIX points to the PARENT of 'tessdata' (official way)
    tdp = os.environ.get("TESSDATA_PREFIX", "").strip()
    if tdp:
        p = Path(tdp)
        # If they pointed to parent (…\Tesseract-OCR), use it
        if (p/"tessdata").is_dir():
            return str(p/"tessdata"), "prefix-parent"
        # If they pointed directly to the tessdata folder, accept it
        if (p).is_dir() and (p/"eng.traineddata").exists():
            return str(p), "tessdata"
    # Common Windows default
    guess = Path(r"C:\Program Files\Tesseract-OCR\tessdata")
    if guess.is_dir():
        return str(guess), "auto"
    return "", "none"

def small_ocr_probe(tesseract_cmd, tessdata_dir):
    """Try a tiny OCR in English to confirm the engine can read a PNG."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return "(skipped: Pillow not installed)"

    # Make a tiny test image
    img = Image.new("L", (240, 60), 255)
    d = ImageDraw.Draw(img)
    d.text((10, 10), "TEST", fill=0)
    test_png = ROOT/"data"/"tmp_verify_tesseract.png"
    test_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(test_png)

    cmd = [tesseract_cmd, str(test_png), "stdout", "-l", "eng"]
    # Do NOT pass --tessdata-dir if TESSDATA_PREFIX is set to the parent.
    # Tesseract reads tessdata via TESSDATA_PREFIX.
    env = os.environ.copy()
    if tessdata_dir and not env.get("TESSDATA_PREFIX"):
        # If user set TESSDATA_PREFIX directly to the tessdata folder,
        # we can pass --tessdata-dir for clarity.
        cmd += ["--tessdata-dir", tessdata_dir]

    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, env=env)
        text = out.decode("utf-8", errors="ignore").strip()
        return f"OK: OCR returned: {text!r}"
    except subprocess.CalledProcessError as e:
        return f"ERROR: {e.output.decode('utf-8', errors='ignore')}"
    except Exception as e:
        return f"ERROR: {e}"

def main():
    load_env()  # read .env into the process

    tesseract = os.environ.get("TESSERACT_PATH") or which("tesseract")
    tess_langs = os.environ.get("TESS_LANGS", "san+hin+eng")
    tessdata_dir, mode = resolve_tessdata()

    result = {
        "tesseract_cmd": tesseract or "(not found)",
        "tessdata_dir_resolved": tessdata_dir or "(not found)",
        "tessdata_mode": mode,
        "TESSDATA_PREFIX": os.environ.get("TESSDATA_PREFIX", "(unset)"),
        "TESS_LANGS": tess_langs,
        "PATH_has_tesseract": bool(which("tesseract")),
    }

    if not tesseract:
        print(json.dumps({"ok": False, "why": "tesseract.exe not found", **result}, indent=2, ensure_ascii=False))
        sys.exit(1)

    head, langs = list_langs(tesseract)
    result["list_langs_header"] = head
    result["langs"] = langs

    probe = small_ocr_probe(tesseract, tessdata_dir)
    result["ocr_probe"] = probe

    ok = bool(langs) and any(x in langs for x in ["eng", "hin", "san"])
    print(json.dumps({"ok": ok, **result}, indent=2, ensure_ascii=False))
    sys.exit(0 if ok else 2)

if __name__ == "__main__":
    main()
