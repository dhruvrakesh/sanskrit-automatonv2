#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_images_quality_2026_10_04.py  (2026-10-04)  IMAGE_QUALITY_2026_10_04 + COVERS_2026_10_04

What was seen on 2026-10-04 (four images opened and looked at; all 12 files measured):
  * Every image is 1408 x 768 (about 16:9, "1K"). Fine on screen; a landscape strip
    on a portrait book page; too small for a full-page plate or a cover.
  * The style reads as a modern storybook wash rather than Indian manuscript painting.
  * Karan_Aagama #25 draws a five-faced Siva as one face with four heads stuck sideways and
    two arms, plus floating icons and a scroll of script-like squiggles: the brief did
    not carry the iconography, so the model improvised it.
  * Sandilya #53 (Rama, Hanuman, an attendant with a chamara) and Mallapurana #3, #6
    are competent and usable.

This patch (opt-in where it changes output; all-or-nothing; backups; py_compile):
  scripts/images.py
    * SA_IMAGE_ASPECT (e.g. 3:4) and SA_IMAGE_SIZE (1K / 2K / 4K) are sent as
      generationConfig.imageConfig {aspectRatio, imageSize}. Unset = today's request,
      byte for byte. SA_IMAGE_CONFIG_FIELD=responseFormat sends
      generationConfig.responseFormat.image instead (the form Google's newer page shows).
      After each image the returned size is checked against the ratio asked for and a
      WARN is printed if the API ignored it.
    * Aspect and size are part of the prompt hash, so a redraw at 3:4 is a new image,
      not a cache hit on the 16:9 one. Hashes made without them are unchanged.
    * SA_IMAGE_STYLE presets: pahari, palm-leaf, mural (default STYLE unchanged).
    * The idea prompt now asks for iconography (heads, arms, attributes, vehicle,
      posture) as the text or standard iconography gives it, and for a symbol or scene
      instead of a figure when unsure.
    * `images.py cover --doc X [--brief "..."] [--title T] [--yes]` stores ONE cover
      idea (kind='cover', status 'brief'), proposed by the model from the text or
      written by you. It goes through the same approve -> generate -> approve steps,
      is drawn at 2:3 portrait with the top third kept calm, and never contains
      lettering: the title is typeset by the edition, not drawn by the model.
    * `brief` and `cover` ask the budget before calling the model.
  scripts/images_web.py  POST /api/images/cover (runs as an images job, in the queue).
  scripts/images_static.html  a "Propose a cover" button; the job tray names it.
  scripts/export_html.py  with --images approved: the approved cover appears on the
    title page; covers are never placed among the verse figures.

  python scripts/patch_images_quality_2026_10_04.py --check
  python scripts/patch_images_quality_2026_10_04.py
Test: python -m unittest tests.test_images_quality_2026_10_04 -v
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK = "IMAGE_QUALITY_2026_10_04"
IMG, WEB, HTML, EXP = (Path("scripts/images.py"), Path("scripts/images_web.py"),
                       Path("scripts/images_static.html"), Path("scripts/export_html.py"))

IMG_CONSTS = r'''GENERATED_LABEL = "Illustration - generated, not a historical source."

# IMAGE_QUALITY_2026_10_04 -----------------------------------------------------
IMAGE_ASPECT = os.environ.get("SA_IMAGE_ASPECT") or None   # e.g. "3:4"; None = the model's default
IMAGE_SIZE = os.environ.get("SA_IMAGE_SIZE") or None       # "1K" | "2K" | "4K"
IMAGE_CONFIG_FIELD = os.environ.get("SA_IMAGE_CONFIG_FIELD", "imageConfig")
COVER_ASPECT = "2:3"
NO_MARKS = (" No letters, words, numerals, script-like squiggles, seals or inscriptions anywhere, "
            "including on scrolls, books and banners.")
STYLE_PRESETS = {
    "pahari": ("Illustration for a scholarly reading edition of a Sanskrit text, in the manner of an 18th-century "
               "Pahari (Kangra/Guler) miniature: fine brush line, flat mineral and vegetable pigments, lyrical "
               "landscape, figures in profile or three-quarter view, a plain painted border." + NO_MARKS +
               " Respectful depiction of persons and deities; no caricature; nothing modern."),
    "palm-leaf": ("Illustration in the manner of an Odia or Pala palm-leaf manuscript painting: incised or fine ink "
                  "line on warm leaf-coloured ground, sparse red and black accents, frieze-like composition."
                  + NO_MARKS + " Respectful depiction of persons and deities; nothing modern."),
    "mural": ("Illustration in the manner of a Kerala temple mural: ochre, green and red earth pigments, strong "
              "outlines, crowded devotional composition, ornamented figures." + NO_MARKS +
              " Respectful depiction of persons and deities; nothing modern."),
}
if (os.environ.get("SA_IMAGE_STYLE") or "") in STYLE_PRESETS:
    STYLE = STYLE_PRESETS[os.environ["SA_IMAGE_STYLE"]]
COVER_NOTE = ("\n\nComposition: book-cover artwork in portrait format. Keep the upper third calm and "
              "uncluttered (plain sky, wall or ground) so a title can be typeset there later." + NO_MARKS)
COVER_SYSTEM = (
    "You write ONE cover illustration brief for a scholarly edition of a Sanskrit text. Choose a single "
    "emblematic image grounded in what the text itself describes: a deity, sage, place, object or scene. Give "
    "its iconography exactly (heads, arms, attributes, vehicle, posture, dress) as the text or standard "
    "iconography has it; if unsure, choose an object or landscape instead of a figure. Portrait composition, "
    "calm upper third, no lettering. Respond with one JSON object only: {\"title\": str, \"brief\": str "
    "(40-90 words), \"context_note\": str (why this image, citing the text), \"caption_en\": str, "
    "\"caption_hi\": str}.")
'''

IMG_EDITS = [
    ("constants", 'GENERATED_LABEL = "Illustration - generated, not a historical source."\n', IMG_CONSTS, 1),
    ("hash",
     'def prompt_hash(model: str, brief: str) -> str:\n'
     '    return hashlib.sha256((model + "\\x00" + prompt_for(brief)).encode("utf-8")).hexdigest()\n',
     'def prompt_hash(model: str, brief: str, aspect=None, size=None, extra: str = "") -> str:\n'
     '    s = model + "\\x00" + prompt_for(brief) + extra\n'
     '    if aspect or size:   # IMAGE_QUALITY_2026_10_04: hashes made without them are unchanged\n'
     '        s += "\\x00ar=%s|sz=%s" % (aspect or "", size or "")\n'
     '    return hashlib.sha256(s.encode("utf-8")).hexdigest()\n', 1),
    ("call_image",
     'def call_image(model: str, prompt: str, http=None) -> tuple[bytes, str, dict]:\n'
     '    http = http or http_json\n'
     '    resp = http("%s/models/%s:generateContent" % (API, model),\n'
     '                {"contents": [{"role": "user", "parts": [{"text": prompt}]}],\n'
     '                 "generationConfig": {"responseModalities": ["IMAGE"]}})\n',
     'def call_image(model: str, prompt: str, http=None, aspect=None, size=None) -> tuple[bytes, str, dict]:\n'
     '    http = http or http_json\n'
     '    gc = {"responseModalities": ["IMAGE"]}\n'
     '    if aspect or size:   # IMAGE_QUALITY_2026_10_04\n'
     '        ic = {k: v for k, v in (("aspectRatio", aspect), ("imageSize", size)) if v}\n'
     '        if IMAGE_CONFIG_FIELD == "responseFormat":\n'
     '            gc["responseFormat"] = {"image": ic}\n'
     '        else:\n'
     '            gc["imageConfig"] = ic\n'
     '    resp = http("%s/models/%s:generateContent" % (API, model),\n'
     '                {"contents": [{"role": "user", "parts": [{"text": prompt}]}],\n'
     '                 "generationConfig": gc})\n', 1),
    ("iconography in briefs",
     '    "\\"context_note\\": str (why here, citing the passage), \\"caption_en\\": str, \\"caption_hi\\": str}.")\n',
     '    "\\"context_note\\": str (why here, citing the passage), \\"caption_en\\": str, \\"caption_hi\\": str}. "\n'
     '    # IMAGE_QUALITY_2026_10_04\n'
     '    "For any deity or sage, state the iconography in the brief (number of heads and arms, attributes held, "\n'
     '    "vehicle, posture, dress) as the text or standard iconography gives it; if you are not sure of it, "\n'
     '    "choose a depictable object, place or ritual act instead of a figure.")\n', 1),
    ("generate hash",
     '    ph = prompt_hash(model, row["brief"] or "")\n',
     '    _cover = (row.get("kind") == "cover")   # IMAGE_QUALITY_2026_10_04 / COVERS_2026_10_04\n'
     '    _aspect = COVER_ASPECT if _cover else IMAGE_ASPECT\n'
     '    _extra = COVER_NOTE if _cover else ""\n'
     '    _prompt = prompt_for(row["brief"] or "") + _extra\n'
     '    ph = prompt_hash(model, row["brief"] or "", _aspect, IMAGE_SIZE, _extra)\n', 1),
    ("generate call",
     '    data, mime, resp = call_image(model, prompt_for(row["brief"] or ""), http=http)\n',
     '    data, mime, resp = call_image(model, _prompt, http=http, aspect=_aspect, size=IMAGE_SIZE)\n', 1),
    ("ratio check",
     '    prov = json.loads(row.get("provenance") or "{}")\n'
     '    prov.update({"image_model": model, "prompt": prompt_for(row["brief"] or ""), "generated_at": now(),\n',
     '    if _aspect and w and h:   # IMAGE_QUALITY_2026_10_04: did the API honour the ratio?\n'
     '        try:\n'
     '            _a, _b = (float(x) for x in _aspect.split(":"))\n'
     '            if abs((w / h) - (_a / _b)) > 0.05 * (_a / _b):\n'
     '                print("  WARN #%d: asked %s, got %dx%d - the API ignored the image config (try "\n'
     '                      "SA_IMAGE_CONFIG_FIELD=responseFormat, or another model)" % (row["id"], _aspect, w, h))\n'
     '        except ValueError:\n'
     '            pass\n'
     '    prov = json.loads(row.get("provenance") or "{}")\n'
     '    prov.update({"image_model": model, "prompt": _prompt, "aspect": _aspect, "size": IMAGE_SIZE,\n'
     '                 "generated_at": now(),\n', 1),
    ("cover parser",
     '    m = sub.add_parser("manifest"); m.add_argument("--doc", required=True)\n',
     '    cv = sub.add_parser("cover"); cv.add_argument("--doc", required=True)   # COVERS_2026_10_04\n'
     '    cv.add_argument("--brief", default=None, help="write the cover idea yourself (no model call)")\n'
     '    cv.add_argument("--title", default=None); cv.add_argument("--model", default=BRIEF_MODEL)\n'
     '    cv.add_argument("--more", action="store_true"); cv.add_argument("--yes", action="store_true")\n'
     '    m = sub.add_parser("manifest"); m.add_argument("--doc", required=True)\n', 1),
    ("brief budget",
     '            t0 = time.time()\n            _progress(args.progress, phase="asking',
     '            try:   # IMAGE_QUALITY_2026_10_04: ask the budget first\n'
     '                from usage_meter import budget_ok as _bok\n'
     '                if not _bok(args.db):\n'
     '                    print("Refusing: the spend cap is reached."); return 1\n'
     '            except ImportError:\n'
     '                pass\n'
     '            t0 = time.time()\n            _progress(args.progress, phase="asking', 1),
    ("cover command",
     '        if args.cmd == "edit":\n            row = get(con, args.id); f = {}\n',
     '        if args.cmd == "cover":   # COVERS_2026_10_04\n'
     '            did = doc_id(con, args.doc)\n'
     '            n_open = con.execute("SELECT COUNT(*) FROM doc_images WHERE doc_id=? AND kind=\'cover\' "\n'
     '                                 "AND status<>\'retired\'", (did,)).fetchone()[0]\n'
     '            if n_open and not args.more:\n'
     '                print("REFUSING: %s already has %d cover(s) not retired. Review or retire them, or pass --more."\n'
     '                      % (args.doc, n_open)); return 1\n'
     '            if args.brief:\n'
     '                item = {"title": args.title or "Cover", "brief": args.brief, "caption_en": "", "caption_hi": "",\n'
     '                        "context_note": "Cover idea written by a person."}\n'
     '                src_note = "written"\n'
     '            else:\n'
     '                text, _valid = gather_text(con, args.doc, budget_chars=12000, sections=12)\n'
     '                if not text:\n'
     '                    print("FAIL: no translated passages for %s." % args.doc); return 1\n'
     '                user = "Text: %s\\nTitle: %s\\n\\n%s" % (args.doc, args.title or args.doc, text)\n'
     '                print("cover: %s  model %s  prompt %d chars" % (args.doc, args.model, len(user)))\n'
     '                if not args.yes:\n'
     '                    print("Dry run. Add --yes to ask the model. Nothing was written."); return 0\n'
     '                try:\n'
     '                    from usage_meter import budget_ok as _bok\n'
     '                    if not _bok(args.db):\n'
     '                        print("Refusing: the spend cap is reached."); return 1\n'
     '                except ImportError:\n'
     '                    pass\n'
     '                _progress(args.progress, phase="asking %s for a cover idea" % args.model, step=0, total=1,\n'
     '                          started=time.time())\n'
     '                t0 = time.time()\n'
     '                got, resp = call_text_json(args.model, COVER_SYSTEM, user)\n'
     '                meter("image_brief", args.doc, "gemini:" + args.model, resp, args.db, time.time() - t0)\n'
     '                item = got[0] if isinstance(got, list) and got else got\n'
     '                if not isinstance(item, dict) or not str(item.get("brief") or "").strip():\n'
     '                    print("FAIL: the model returned no usable cover idea."); return 1\n'
     '                src_note = "images.py cover"\n'
     '            cur = con.execute(\n'
     '                """INSERT INTO doc_images(doc_id, kind, status, title, brief, context_note, caption_en, caption_hi,\n'
     '                                          anchor_page, anchor_idx, model, provenance, created_at, updated_at)\n'
     '                   VALUES(?, \'cover\', \'brief\', ?,?,?,?,?, 0, 0, ?,?,?,?)""",\n'
     '                (did, item.get("title") or "Cover", item.get("brief"), item.get("context_note"),\n'
     '                 item.get("caption_en"), item.get("caption_hi"), args.model,\n'
     '                 json.dumps({"source": src_note}), now(), now()))\n'
     '            con.execute("UPDATE doc_images SET lineage_id=id WHERE id=?", (cur.lastrowid,))\n'
     '            con.commit()\n'
     '            _progress(args.progress, phase="stored cover idea #%d" % cur.lastrowid, step=1, total=1, done=True)\n'
     '            print("stored cover idea #%d (status brief): approve it, then generate (drawn 2:3, no lettering)."\n'
     '                  % cur.lastrowid)\n'
     '            return 0\n'
     '        if args.cmd == "edit":\n            row = get(con, args.id); f = {}\n', 1),
]

WEB_EDITS = [
    ("cover endpoint", '    @app.get("/api/images/jobs")\n',
     '    @app.post("/api/images/cover")   # COVERS_2026_10_04 / IMAGE_QUALITY_2026_10_04\n'
     '    def images_cover():\n'
     '        data = request.get_json(force=True) or {}\n'
     '        doc = data.get("doc", "")\n'
     '        if not DOC_RE.match(doc):\n'
     '            return bad("invalid doc")\n'
     '        argv = ["cover", "--doc", doc, "--yes"] + (["--more"] if data.get("more") else [])\n'
     '        if (data.get("brief") or "").strip():\n'
     '            argv += ["--brief", data["brief"].strip()[:2000]]\n'
     '        return _job("images_brief", doc, argv, "cover")\n\n'
     '    @app.get("/api/images/jobs")\n', 1),
]

HTML_EDITS = [
    ("marker", "<!-- IMAGES_UI_2026_10_03 + IMAGES_QUEUE_2026_10_04 - served by images_web.py at /images -->",
     "<!-- IMAGES_UI_2026_10_03 + IMAGES_QUEUE_2026_10_04 + IMAGE_QUALITY_2026_10_04 - served by images_web.py at /images -->", 1),
    ("button", '  <button id="btnGen" class="primary"',
     '  <button id="btnCover" title="Ask for ONE cover idea (portrait, no lettering); it is reviewed like any idea">Propose a cover</button>\n'
     '  <button id="btnGen" class="primary"', 1),
    ("label", "  if(j.kind==='images_brief') return 'Proposing ideas';",
     "  if(j.kind==='images_brief') return m==='cover' ? 'Proposing a cover' : 'Proposing ideas';", 1),
    ("handler", "$('#btnGen').addEventListener('click', async () => {",
     "$('#btnCover').addEventListener('click', async () => {\n"
     "  const open = rows.filter(r=>r.kind==='cover' && r.status!=='retired').length;\n"
     "  let more = false;\n"
     "  if(open){ if(!confirm(open + ' cover(s) already exist. Ask for another?')) return; more = true; }\n"
     "  const brief = prompt('Describe the cover yourself, or leave empty to let the model propose one from the text:', '') ;\n"
     "  if(brief === null) return;\n"
     "  try { const j = await api('/api/images/cover', {doc:getDoc(), brief, more}); track(j.job, 'Proposing a cover'); }\n"
     "  catch(e){ toast(e.message); }\n"
     "});\n"
     "$('#btnGen').addEventListener('click', async () => {", 1),
]

EXP_HELPER = '''def _load_cover(con, doc, root=None):
    """COVERS_2026_10_04: the newest APPROVED cover (kind='cover') as a figure for the title page, or ''."""
    if not doc or "doc_images" not in _tables(con):
        return ""
    root = root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    r = con.execute("""SELECT i.id, i.title, i.path FROM doc_images i JOIN docs d ON d.id = i.doc_id
                       WHERE d.code = ? AND i.status = 'approved' AND i.kind = 'cover' AND i.path IS NOT NULL
                       ORDER BY i.approved_at DESC, i.id DESC LIMIT 1""", (doc,)).fetchone()
    if not r:
        return ""
    full = r[2] if os.path.isabs(r[2]) else os.path.join(root, r[2])
    uri = _fig_embed(full)
    if not uri:
        return ""
    return ("<figure class='plate cover' id='cover-%s' style='max-width:24rem'><img src='%s' alt='%s'/>"
            "<figcaption><span class='plate-label'>%s</span></figcaption></figure>"
            % (r[0], uri, html.escape(r[1] or "cover", quote=True), html.escape(_FIG_LABEL_EN)))


def _with_fig_css(doc_html, on):'''

EXP_EDITS = [
    ("no covers among figures",
     "           WHERE d.code = ? AND i.status = 'approved' AND i.path IS NOT NULL\n",
     "           WHERE d.code = ? AND i.status = 'approved' AND i.path IS NOT NULL\n"
     "             AND COALESCE(i.kind, '') <> 'cover'   -- COVERS_2026_10_04: the cover goes on the title page\n", 1),
    ("cover helper", "def _with_fig_css(doc_html, on):", EXP_HELPER, 1),
    ("load cover",
     '    figs = _load_figures(con, doc) if images == "approved" else {}   # EXPORT_IMAGES_2026_10_04\n',
     '    figs = _load_figures(con, doc) if images == "approved" else {}   # EXPORT_IMAGES_2026_10_04\n'
     '    cover = _load_cover(con, doc) if images == "approved" else ""   # COVERS_2026_10_04\n', 1),
    ("place cover",
     '        f.write(_with_fig_css(_html(title or (doc or "Export"), body, lang_attr=lang_attr), bool(figs)))\n',
     '        if cover:   # COVERS_2026_10_04\n'
     '            body = body.replace("<div class=\'titlepage\'>", "<div class=\'titlepage\'>" + cover, 1)\n'
     '        f.write(_with_fig_css(_html(title or (doc or "Export"), body, lang_attr=lang_attr), bool(figs) or bool(cover)))\n', 1),
]


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


TARGETS = [(IMG, IMG_EDITS, True), (WEB, WEB_EDITS, True), (HTML, HTML_EDITS, False), (EXP, EXP_EDITS, True)]


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    for p, _, _ in TARGETS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
    loaded = [(p, *load(p), e, c) for p, e, c in TARGETS]
    marks = [MARK in s for _, s, _, _, _ in loaded]
    if all(marks):
        print("Already patched (%s). Nothing to do." % MARK); return 0
    if any(marks):
        print("REFUSING: marker in some files only - inspect by hand."); return 1
    problems, out = [], []
    for p, src, nl, edits, comp in loaded:
        for label, old, new, n in edits:
            c = src.count(old)
            if c != n:
                problems.append("%s %s: matched %d times, expected %d" % (p.name, label, c, n))
            else:
                src = src.replace(old, new)
        if p != HTML and MARK not in src:
            src = src.rstrip("\n") + "\n# %s\n" % MARK
        out.append((p, src, nl, comp))
    if problems:
        print("REFUSING TO WRITE:"); [print("  " + x) for x in problems]; return 1
    if args.check:
        print("CHECK OK: %d anchored edits in 4 files. Nothing written." % sum(len(e) for _, e, _ in TARGETS)); return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    tmps = []
    for p, text, nl, comp in out:
        t = p.with_name(p.name + ".tmp_iqual")
        t.write_bytes(text.replace("\n", nl).encode("utf-8"))
        if comp:
            try:
                py_compile.compile(str(t), doraise=True)
            except py_compile.PyCompileError as e:
                for x, _ in tmps + [(t, p)]:
                    x.unlink(missing_ok=True)
                print("REFUSING TO WRITE: %s would not compile:\n%s" % (p, e)); return 1
        tmps.append((t, p))
    for t, p in tmps:
        shutil.copy2(p, p.with_name(p.name + ".bak_iqual_" + stamp))
    for t, p in tmps:
        os.replace(t, p)
        print("patched %s" % p)
    print("images.py and export_html.py: at the next run. The cover endpoint: at the next dashboard restart.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
