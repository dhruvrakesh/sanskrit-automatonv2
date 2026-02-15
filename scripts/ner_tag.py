# scripts/ner_tag.py
import sys, os, json, argparse, unicodedata, pathlib

# Devanagari block and normalizers (ASCII-only source)
DEV_START = 0x0900
DEV_END   = 0x097F
ZWS   = "\u200b\u200c\u200d\u2060"
DANDAS= "\u0964\u0965|"
HYPHS = "-\u2010\u2011\u2012\u2013"

def is_devanagari_char(ch: str) -> bool:
    cp = ord(ch)
    return DEV_START <= cp <= DEV_END

def has_devanagari(s: str) -> bool:
    return any(is_devanagari_char(ch) for ch in s)

def nfc(s: str) -> str:
    if not isinstance(s, str): return ""
    s = unicodedata.normalize("NFC", s)
    s = s.replace("\uFEFF", "")
    for ch in ZWS: s = s.replace(ch, "")
    for d in DANDAS: s = s.replace(d, "|")
    for h in HYPHS:  s = s.replace(h, "-")
    return s.strip()

def load_gaz(path: str):
    p = pathlib.Path(path)
    txt = p.read_text(encoding="utf-8", errors="ignore")
    # Try JSON (array or object)
    try:
        data = json.loads(txt)
        if isinstance(data, dict): data = [data]
        if isinstance(data, list): return data
    except json.JSONDecodeError:
        pass
    # Fallback JSONL
    out = []
    for line in txt.splitlines():
        line = line.strip()
        if not line: continue
        out.append(json.loads(line))
    return out

def all_forms(entry):
    surface = entry.get("surface") or entry.get("name") or ""
    aliases = entry.get("aliases") or []
    forms = [surface] + [a for a in aliases if a]
    return [nfc(f) for f in forms if f and has_devanagari(f)]

def find_all(text: str, form: str):
    # Simple substring search. We accept hits even without strict word boundaries
    # because OCR often lacks clean tokenization.
    hits = []
    start = 0
    L = len(form)
    while True:
        i = text.find(form, start)
        if i < 0: break
        j = i + L
        hits.append((i, j))
        start = i + 1
    return hits

def read_stdin_utf8():
    # Robust against Windows console encoding: read bytes and decode UTF-8
    data = sys.stdin.buffer.read()
    # Try UTF-8 with BOM first, then plain UTF-8; ignore any bad bytes
    try:
        return data.decode("utf-8-sig", errors="ignore")
    except Exception:
        return data.decode("utf-8", errors="ignore")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gaz", default=os.environ.get("SA_GAZ_PATH", "data/gazetteer.json"),
                    help="path to gazetteer (JSON or JSONL)")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    ap.add_argument("--text", help="analyze this text (bypass stdin)")
    args = ap.parse_args()

    raw = args.text if args.text is not None else read_stdin_utf8()
    text = nfc(raw)

    try:
        gaz = load_gaz(args.gaz)
    except Exception as e:
        out = {"engine":"gazetteer","error":str(e),"gazetteer":args.gaz}
        print(json.dumps(out, ensure_ascii=False))
        sys.exit(1)

    entities = []
    for idx, entry in enumerate(gaz):
        etype = entry.get("type","unknown")
        canon = nfc(entry.get("surface") or entry.get("name") or "")
        for f in all_forms(entry):
            for s,e in find_all(text, f):
                entities.append({
                    "text": text[s:e],
                    "label": etype,
                    "start": s,
                    "end": e,
                    "canonical": canon or f,
                    "gaz_index": idx
                })

    # dedupe identical spans
    seen=set(); dedup=[]
    for ent in entities:
        key=(ent["start"],ent["end"],ent["label"])
        if key in seen: continue
        seen.add(key); dedup.append(ent)

    out = {"engine":"gazetteer","entities":dedup,"gazetteer":str(pathlib.Path(args.gaz).resolve())}
    print(json.dumps(out, ensure_ascii=False) if args.json else out)

if __name__ == "__main__":
    main()
