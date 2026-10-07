#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_story_books_2026_10_07.py  (2026-10-07)  STORY_BOOKS_2026_10_07

scripts/stories.py gains three commands (nothing existing changes):

  illustrate --id N [--yes]
      One image idea for a story or a found episode, written from its passages,
      its retelling and its editorial notes (never depicting what the notes doubt).
      Stored in the image library as an ordinary idea (doc_images, status 'brief')
      and linked to the story. Drawing it is then the image library's own path
      (approve the idea, generate, approve the picture) - the Stories page does it
      with one button each. About $0.003 (one gemini-2.5-flash call), metered as
      image_brief and budget-gated.
  book --ids 2,5,7 --title "..." [--audience young|general|scholar] [--no-hindi]
       [--proof] [--out FILE]
      A reading book of the chosen stories, in the order given, each with its own
      plate: exports/book_<slug>_<date>.html (PDF: export_pdf.py). Approved stories
      only, unless --proof (drafts then carry a PROOF label). The audience changes
      the layout (type size, citations, notes, sources), not the wording.
  booksmith-source --ids ... --title "..." --out FILE
      The same stories as a Booksmith witness (section.chapter / div.verse / vref /
      sa / en / hi / footnotes), for booksmith_build.py --source-html.

All-or-nothing, marker-idempotent, backup .bak_books_<date>, py_compile.
  python scripts\\patch_story_books_2026_10_07.py --check
  python scripts\\patch_story_books_2026_10_07.py
Test: python -m unittest tests.test_story_books_2026_10_07 -v
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK = "STORY_BOOKS_2026_10_07"

BLOCK = r'''# ------------------------------------------------------------------ STORY_BOOKS_2026_10_07
ILLUSTRATE_SYSTEM = (
    "You write ONE illustration brief for an episode of a Sanskrit text, for an illustrated, cited anthology. "
    "You are given the episode's passages (tag [page.idx], machine English) and, when there is one, the "
    "editor's retelling and editorial notes. Choose a single concrete moment the passages describe. Add no "
    "people, animals, objects or events that the passages do not give, and do not depict anything the notes "
    "call doubtful or damaged. For any deity or sage, state the iconography (heads, arms, attributes, vehicle, "
    "posture, dress) as the passages or standard iconography give it; if unsure, choose a place, object or act "
    "instead of a figure. Historically plausible dress and architecture; nothing modern; no text in the image. "
    "Respond with one JSON object only: {\"anchor\": \"page.idx\" (one of the tags given: the passage the "
    "moment rests on), \"title\": str (4-9 words), \"brief\": str (what to draw, 40-90 words), "
    "\"context_note\": str (why this moment, citing [page.idx]), \"caption_en\": str, \"caption_hi\": str}")
AUDIENCES = ("young", "general", "scholar")


def illustrate(con, sid: int, db: str, http=None, cap: int = 40) -> int:
    """Store one image idea (doc_images status 'brief') for story sid and link it. Returns the image id."""
    s = _row(con, sid)
    if s["status"] == "retired":
        raise SystemExit("FAIL: story #%d is retired." % sid)
    if s.get("image_id"):
        r = con.execute("SELECT status FROM doc_images WHERE id=?", (s["image_id"],)).fetchone()
        if r and r[0] != "retired":
            raise SystemExit("FAIL: story #%d already has image #%d (%s). Retire that image first to propose "
                             "another." % (sid, s["image_id"], r[0]))
    code = _code_of(con, s["doc_id"])
    rows = window(passages(con, code), (s["from_page"], s["from_idx"]), (s["to_page"], s["to_idx"]), pad=0, cap=cap)
    if not rows:
        raise SystemExit("FAIL: story #%d: no translated passages in its range." % sid)
    parts = ["Episode: %s" % (s.get("title") or ""), s.get("why") or ""]
    if (s.get("story_en") or "").strip():
        parts.append("RETELLING (%s):\n%s" % (s["status"], s["story_en"].strip()))
    if (s.get("notes") or "").strip():
        parts.append("EDITORIAL NOTES (do not depict what these doubt):\n%s" % s["notes"].strip())
    user = "\n\n".join(p for p in parts if p) + "\n\nPASSAGES\n\n" + _prompt_block(rows, False)
    t0 = time.time()
    data, resp = im.call_text_json(im.BRIEF_MODEL, ILLUSTRATE_SYSTEM, user, http=http)
    im.meter("image_brief", code, "gemini:" + im.BRIEF_MODEL, resp, db, time.time() - t0)
    if isinstance(data, list):
        data = data[0] if data else {}
    if not isinstance(data, dict) or not str(data.get("brief") or "").strip():
        raise SystemExit("FAIL: the model returned no usable image idea for story #%d." % sid)
    valid = {(r[0], r[1]) for r in rows}
    a = parse_ref(data.get("anchor"))
    if not a or a not in valid:
        mid = rows[len(rows) // 2]
        a = (mid[0], mid[1])
    cur = con.execute(
        """INSERT INTO doc_images(doc_id, kind, status, title, brief, context_note, caption_en, caption_hi,
                                  anchor_page, anchor_idx, model, provenance, created_at, updated_at)
           VALUES(?, 'generated', 'brief', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (s["doc_id"], data.get("title") or s.get("title") or "", data.get("brief"), data.get("context_note") or "",
         data.get("caption_en") or "", data.get("caption_hi") or "", a[0], a[1], im.BRIEF_MODEL,
         json.dumps({"brief_model": im.BRIEF_MODEL, "source": "stories.py illustrate", "story": sid}), now(), now()))
    iid = cur.lastrowid
    con.execute("UPDATE doc_images SET lineage_id=id WHERE id=?", (iid,))
    con.execute("UPDATE doc_stories SET image_id=?, updated_at=? WHERE id=?", (iid, now(), sid))
    con.commit()
    return iid


def _book_rows(con, ids: list, proof: bool = False) -> list:
    """Stories in the order given; approved only unless proof. Each: (story dict, code, image path or None)."""
    out = []
    for sid in ids:
        try:
            s = _row(con, int(sid))
        except SystemExit:
            continue
        if s["status"] == "approved" or (proof and s["status"] == "draft"):
            code = _code_of(con, s["doc_id"])
            img = None
            if s.get("image_id"):
                r = con.execute("SELECT path, title FROM doc_images WHERE id=? AND path IS NOT NULL AND status IN (%s)"
                                % ("'approved','draft'" if proof else "'approved'"), (s["image_id"],)).fetchone()
                if r:
                    img = (r[0] if os.path.isabs(r[0]) else str(ROOT / r[0]), r[1])
            out.append((s, code, img))
    return out


def _titles():
    try:
        import collections_cfg as cc
        return cc.load_titles(ROOT / "configs" / "doc_titles.json")
    except Exception:
        return {}


def _plain(text: str) -> str:
    """The retelling without its [page.idx] citations (for young readers)."""
    return re.sub(r"\s*\[[^\]]*\d+\.\d+[^\]]*\]", "", text or "")


def book(con, ids: list, title: str, out: Path, audience: str = "general", hindi: bool = True,
         proof: bool = False) -> tuple:
    import export_html as ex
    audience = audience if audience in AUDIENCES else "general"
    titles = _titles()
    rows = _book_rows(con, ids, proof)
    parts, src, n = [], [], 0
    for s, code, img in rows:
        n += 1
        book_t = titles.get(code) or code.replace("_", " ")
        rng = "%s-%s" % (ref(s["from_page"], s["from_idx"]), ref(s["to_page"], s["to_idx"]))
        fig = ""
        if img:
            uri = ex._fig_embed(img[0])
            if uri:
                fig = ("<figure class='plate'><img src='%s' alt='%s'/><figcaption>%s</figcaption></figure>"
                       % (uri, html.escape(img[1] or s.get("title") or "", quote=True), html.escape(im.GENERATED_LABEL)))
        en = s.get("story_en") or ""
        hi = s.get("story_hi") or ""
        body_en = ("<p>%s</p>" % html.escape(_plain(en))) if audience == "young" else ("<div class='en'>%s</div>" % _cite_html(en))
        body_hi = ""
        if hindi and hi:
            body_hi = ("<p class='hi'>%s</p>" % html.escape(_plain(hi))) if audience == "young" else (
                "<div class='hi'>%s</div>" % _cite_html(hi))
        epi = ""
        if s.get("quote_sa"):
            epi = ("<blockquote class='sa'>%s<span class='qref'> [%s]</span></blockquote>"
                   % (html.escape(s["quote_sa"]), html.escape(s.get("quote_ref") or "")))
        notes = ""
        if s.get("notes") and audience != "young":
            notes = "<div class='notes'>Editorial notes: %s</div>" % html.escape(s["notes"])
        badge = "<div class='proof'>PROOF - not yet approved</div>" if s["status"] != "approved" else ""
        parts.append("<section class='story' id='s%d'>%s<h2>%d. %s</h2>%s<div class='src'>%s, passages %s</div>%s%s%s%s%s"
                     "</section>" % (s["id"], badge, n, html.escape(s.get("title") or ""),
                                     ("<div class='th'>%s</div>" % html.escape(s["title_hi"])) if hindi and s.get("title_hi") else "",
                                     html.escape(book_t), rng, fig if audience == "young" else "", epi,
                                     "" if audience == "young" else fig, body_en, body_hi + notes))
        allp = {ref(r[0], r[1]): r for r in passages(con, code)}
        for c in json.loads(s.get("cites") or "[]"):
            r = allp.get(c)
            if not r:
                continue
            if audience == "scholar":
                src.append("<tr><td>%d</td><td>%s %s</td><td class='sa'>%s</td><td>%s</td></tr>"
                           % (n, html.escape(book_t), c, html.escape(r[2]), html.escape(r[4])))
            else:
                src.append("<tr><td>%d</td><td>%s %s</td><td>%s</td></tr>" % (n, html.escape(book_t), c, html.escape(r[4])))
    base = ("body{font-family:Georgia,'Noto Serif',serif;max-width:44rem;margin:2rem auto;padding:0 1rem;color:#222}"
            ".th,.hi,.sa{font-family:'Nirmala UI','Noto Serif Devanagari',serif}.src{color:#666;font-size:.9rem}"
            ".qref{color:#888;font-size:.8rem}.cite{color:#8a6d1d;font-size:.7rem}figure.plate{margin:1rem 0;"
            "text-align:center}figure.plate img{max-width:100%;max-height:70vh;border-radius:4px}figcaption{font-size:.75rem;"
            "color:#888}blockquote.sa{border-left:3px solid #c9a24a;padding-left:1rem;margin-left:0}.notes{font-size:.85rem;"
            "color:#7a4b00;background:#fdf6e3;padding:.5rem .8rem;margin-top:.8rem}.proof{color:#a33;font-weight:bold;"
            "font-size:.8rem;letter-spacing:.08em}table{border-collapse:collapse;font-size:.85rem}td{border-top:1px solid #ddd;"
            "padding:.3rem;vertical-align:top}.story{page-break-before:always}h1{text-align:center}")
    aud = {"young": "body{font-size:1.25rem;line-height:1.75}h2{font-size:1.7rem;color:#7a3d00}p{margin:.8rem 0}"
                    "figure.plate img{max-height:80vh}",
           "general": "body{font-size:1.05rem;line-height:1.65}",
           "scholar": "body{font-size:1rem;line-height:1.6}.notes{font-size:.9rem}"}[audience]
    intro = {"young": "Stories retold from an old Sanskrit book. The pictures are new paintings made for this book.",
             "general": "Retellings, each cited to the passages it rests on. Illustrations are generated, not historical "
                        "sources. Retellings were drafted by a model from the passages and approved by an editor.",
             "scholar": "Retellings with a citation after every sentence, the Sanskrit as printed, the machine English "
                        "of every cited passage, and the editor's notes. Illustrations are generated, not sources."}[audience]
    if src:
        head = ("<tr><th>#</th><th>Passage</th><th>Sanskrit (as printed)</th><th>English (machine translation)</th></tr>"
                if audience == "scholar" else "<tr><th>#</th><th>Passage</th><th>English (machine translation)</th></tr>")
        sources = "<h2>%s</h2><table>%s%s</table>" % ("Where these stories come from" if audience == "young" else "Sources",
                                                     head, "".join(src))
    else:
        sources = ""
    doc_html = ("<!doctype html><html lang='en'><head><meta charset='utf-8'><title>%s</title><style>%s%s</style></head>"
                "<body><!-- %s audience=%s --><h1>%s</h1><p style='text-align:center;color:#666'>%s</p>%s%s</body></html>"
                % (html.escape(title), base, aud, MARK, audience, html.escape(title), intro, "".join(parts), sources))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc_html, encoding="utf-8")
    return out, n


def booksmith_source(con, ids: list, title: str, out: Path) -> tuple:
    """The chosen APPROVED stories as a Booksmith witness: one section.chapter per story, one div.verse
    (vref = number, title, book and range; sa = the quotation; en, hi = the retelling), and footnotes =
    the cited passages (Sanskrit as printed, machine English) and the editorial notes."""
    titles = _titles()
    secs, n = [], 0
    for s, code, _img in _book_rows(con, ids, False):
        n += 1
        book_t = titles.get(code) or code.replace("_", " ")
        rng = "%s-%s" % (ref(s["from_page"], s["from_idx"]), ref(s["to_page"], s["to_idx"]))
        allp = {ref(r[0], r[1]): r for r in passages(con, code)}
        notes = []
        for k, c in enumerate(json.loads(s.get("cites") or "[]"), 1):
            r = allp.get(c)
            if r:
                notes.append("<li id='n%d-%d'>%s %s: %s | %s</li>" % (n, k, html.escape(book_t), c, html.escape(r[2]),
                                                                    html.escape(r[4])))
        if s.get("notes"):
            notes.append("<li id='n%d-ed'>Editorial note: %s</li>" % (n, html.escape(s["notes"])))
        secs.append("<section class='chapter' id='s%d'><div class='verse'><span class='vref'>%d. %s - %s %s</span>"
                    "<div class='sa'>%s</div><div class='en'>%s</div><div class='hi'>%s</div></div>"
                    "<div class='footnotes'><ol>%s</ol></div></section>"
                    % (s["id"], n, html.escape(s.get("title") or ""), html.escape(book_t), rng,
                       html.escape(s.get("quote_sa") or ""), html.escape(s.get("story_en") or ""),
                       html.escape(s.get("story_hi") or ""), "".join(notes)))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("<!doctype html><html lang='en'><head><meta charset='utf-8'><title>%s</title></head><body>"
                   "<!-- %s booksmith witness --><h1>%s</h1>%s</body></html>"
                   % (html.escape(title), MARK, html.escape(title), "".join(secs)), encoding="utf-8")
    return out, n


def _slug(t: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (t or "").lower()).strip("-")
    return (s or "stories")[:40]


# ------------------------------------------------------------------ CLI
'''

ST_EDITS = [
    ("story books block", "# ------------------------------------------------------------------ CLI\n", BLOCK, 1),
    ("cli parsers",
     '''    an.add_argument("--out", default=None)
    args = ap.parse_args()
''',
     '''    an.add_argument("--out", default=None)
    il = sub.add_parser("illustrate"); il.add_argument("--id", type=int, required=True)   # STORY_BOOKS_2026_10_07
    il.add_argument("--yes", action="store_true")
    bk = sub.add_parser("book"); bk.add_argument("--ids", required=True); bk.add_argument("--title", required=True)
    bk.add_argument("--audience", default="general", choices=AUDIENCES); bk.add_argument("--no-hindi", action="store_true")
    bk.add_argument("--proof", action="store_true"); bk.add_argument("--out", default=None)
    bsx = sub.add_parser("booksmith-source"); bsx.add_argument("--ids", required=True)
    bsx.add_argument("--title", required=True); bsx.add_argument("--out", required=True)
    args = ap.parse_args()
''', 1),
    ("cli dispatch",
     '''        if args.cmd == "verify":
''',
     '''        if args.cmd == "illustrate":   # STORY_BOOKS_2026_10_07
            s = _row(con, args.id)
            print("illustrate #%d %s: one image idea with %s, about $0.003" % (args.id, s.get("title") or "",
                                                                              im.BRIEF_MODEL))
            if not args.yes:
                print("Dry run. Add --yes."); return 0
            if not budget_ok(args.db):
                print("Refusing: the spend cap is reached."); return 1
            iid = illustrate(con, args.id, args.db)
            print("image idea #%d stored (status brief) and linked to story #%d. Next: approve the idea and draw it "
                  "(Stories page, or images.py approve-brief %d then generate --doc %s --id %d --yes)."
                  % (iid, args.id, iid, _code_of(con, s["doc_id"]), iid))
            return 0
        if args.cmd in ("book", "booksmith-source"):
            ids = [int(x) for x in re.findall(r"\\d+", args.ids)]
            if args.cmd == "booksmith-source":
                path, n = booksmith_source(con, ids, args.title, Path(args.out))
                print("wrote %s (%d approved stories, Booksmith witness)" % (path, n)); return 0 if n else 1
            out = Path(args.out) if args.out else ROOT / "exports" / ("book_%s_%s.html" % (
                _slug(args.title), datetime.date.today().strftime("%Y%m%d")))
            path, n = book(con, ids, args.title, out, args.audience, not args.no_hindi, args.proof)
            print("wrote %s (%d stories, audience %s). PDF: python scripts\\\\export_pdf.py \\"%s\\"" % (path, n, args.audience, path))
            return 0 if n else 1
        if args.cmd == "verify":
''', 1),
]

TARGETS = [(Path("scripts/stories.py"), ST_EDITS)]


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    for p, _ in TARGETS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
    loaded = [(p, *load(p), e) for p, e in TARGETS]
    if all(MARK in s for _, s, _, _ in loaded):
        print("Already patched (%s). Nothing to do." % MARK); return 0
    problems, out = [], []
    for p, src, nl, edits in loaded:
        for label, old, new, n in edits:
            c = src.count(old)
            if c != n:
                problems.append("%s %s: matched %d times, expected %d" % (p.name, label, c, n))
            else:
                src = src.replace(old, new)
        out.append((p, src, nl))
    if problems:
        print("REFUSING TO WRITE:"); [print("  " + x) for x in problems]; return 1
    if args.check:
        print("CHECK OK: %d anchored edits in %d files. Nothing written." % (sum(len(e) for _, e in TARGETS), len(TARGETS)))
        return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    tmps = []
    for p, text, nl in out:
        t = p.with_name(p.name + ".tmp_books")
        t.write_bytes(text.replace("\n", nl).encode("utf-8"))
        try:
            py_compile.compile(str(t), doraise=True)
        except py_compile.PyCompileError as e:
            for x, _ in tmps + [(t, p)]:
                x.unlink(missing_ok=True)
            print("REFUSING TO WRITE: %s would not compile:\n%s" % (p, e)); return 1
        tmps.append((t, p))
    for t, p in tmps:
        shutil.copy2(p, p.with_name(p.name + ".bak_books_" + stamp))
    for t, p in tmps:
        os.replace(t, p)
        print("patched %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
