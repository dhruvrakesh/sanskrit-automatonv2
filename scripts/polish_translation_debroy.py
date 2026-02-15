import argparse, csv, os, re, shutil, sqlite3
from datetime import datetime

DB_PATH = os.getenv("SA_DB_PATH", "data/context.db")

RE_SPACES = re.compile(r"[ \t]+")
RE_SMART  = str.maketrans({"“":'"',"”":'"',"‘":"'", "’":"'", "—":"-","–":"-","…":"..."})
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
        with open(path, newline="", encoding="utf-8") as f:
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
    # opening fillers
    for pat, repl in RE_OPENING:
        nxt = pat.sub(repl, en)
        if nxt != en: en = nxt.strip()
    # spacing around punctuation
    en = re.sub(r"\s+([,.;:?!])", r"\1", en)
    en = re.sub(r"([,.;:?!])([^\s])", r"\1 \2", en)
    en = RE_SPACES.sub(" ", en).strip()
    # drop digits-only stubs
    if RE_DIGITS_ONLY.match(en): return ""
    return en

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", required=True)
    ap.add_argument("--map", default="style_terms.csv")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only-nonempty", action="store_true", help="polish only rows that already have translation")
    args = ap.parse_args()

    # backup
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = f"{DB_PATH.rsplit('.',1)[0]}_backup_{ts}.db"
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    shutil.copyfile(DB_PATH, backup)
    print("[backup]", backup)

    mp = load_map(args.map)

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    base = """
      SELECT p.id, p.text, p.translation
      FROM passages p
      JOIN docs d ON d.id = p.doc_id
      WHERE d.code = ?
    """
    if args.only_nonempty:
        base += " AND p.translation IS NOT NULL AND TRIM(p.translation) <> ''"
    base += " ORDER BY p.page_no, p.idx"

    rows = cur.execute(base, (args.doc,)).fetchall()
    if args.limit: rows = rows[:args.limit]

    updates = 0
    for pid, san, en in rows:
        en0 = (en or "")
        en1 = apply_map(en0, mp)
        en2 = clean_en(en1)
        if en2 != en0:
            cur.execute("UPDATE passages SET translation=? WHERE id=?", (en2, pid))
            updates += 1

    con.commit(); con.close()
    print(f"[done] updated {updates} rows")

if __name__ == "__main__":
    main()
