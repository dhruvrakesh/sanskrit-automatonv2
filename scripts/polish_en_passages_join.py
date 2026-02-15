import argparse, csv, os, re, shutil, sqlite3
from datetime import datetime

DB_PATH = os.getenv("SA_DB_PATH", "data/context.db")

RE_SPACES = re.compile(r"[ \t]+")
RE_SMART = str.maketrans({"“":'"',"”":'"',"‘":"'", "’":"'", "—":"-","–":"-","…":"..."})
RE_HARD_BREAKS = re.compile(r"[ \t]*\n[ \t]*")
RE_HYPHEN_WRAP = re.compile(r"(\w)-\n(\w)")
RE_DIGITS_ONLY = re.compile(r"^\s*[\dIVXLC]+[\.\)]?\s*$")
RE_OPENING = [
    (re.compile(r"^\s*There used to be\b", re.I), "There was"),
    (re.compile(r"^\s*There was once\b", re.I), "There was"),
    (re.compile(r"^\s*Once upon a time[,]?\s*", re.I), ""),
    (re.compile(r"\bThere (?:lived|resided)\b", re.I), "lived"),
]

def load_map(path):
    mp=[]
    if os.path.exists(path):
        with open(path, newline='', encoding="utf-8") as f:
            r=csv.DictReader(f)
            for row in r:
                s=row.get("source","").strip(); t=row.get("target","").strip()
                if s and t:
                    mp.append(("regex", re.compile(rf"\b{re.escape(s)}\b"), t))
                    mp.append(("plain", s, t))
    return mp

def apply_map(text, mp):
    for kind, a, b in mp:
        text = a.sub(b, text) if kind=="regex" else text.replace(a,b)
    return text

def clean_en(en):
    if not en: return en
    en = en.translate(RE_SMART)
    en = RE_HYPHEN_WRAP.sub(r"\1\2", en)
    en = RE_HARD_BREAKS.sub(" ", en)
    en = RE_SPACES.sub(" ", en).strip()
    for pat, repl in RE_OPENING:
        en2 = pat.sub(repl, en)
        if en2 != en: en = en2.strip()
    en = re.sub(r"\s+([,.;:?!])", r"\1", en)
    en = re.sub(r"([,.;:?!])([^\s])", r"\1 \2", en)
    en = RE_SPACES.sub(" ", en).strip()
    if RE_DIGITS_ONLY.match(en): return ""
    return en

def detect_page_col(cur):
    cols=[r[1] for r in cur.execute("PRAGMA table_info(pages)")]
    for c in ("page","number","pageno","index"):
        if c in cols: return c
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", required=True)
    ap.add_argument("--map", default="style_terms.csv")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = f"{DB_PATH.rsplit('.',1)[0]}_backup_{ts}.db"
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    shutil.copyfile(DB_PATH, backup)
    print("[backup]", backup)

    mp = load_map(args.map)

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    page_col = detect_page_col(cur)

    base = """
        SELECT pa.id, pa.san, pa.en {page_sel}
        FROM passages pa
        JOIN pages p ON p.id = pa.page_id
        WHERE p.doc = ?
    """
    page_sel = f", p.{page_col}" if page_col else ", NULL"
    q = base.format(page_sel=page_sel)
    if args.limit:
        rows = cur.execute(q + " LIMIT ?", (args.doc, args.limit)).fetchall()
    else:
        rows = cur.execute(q, (args.doc,)).fetchall()

    updates = 0
    for pid, san, en, pg in rows:
        en0 = en or ""
        en1 = apply_map(en0, mp)
        en2 = clean_en(en1)
        if en2 != en0:
            cur.execute("UPDATE passages SET en=? WHERE id=?", (en2, pid))
            updates += 1

    con.commit(); con.close()
    print(f"[done] updated {updates} rows")

if __name__ == "__main__":
    main()
