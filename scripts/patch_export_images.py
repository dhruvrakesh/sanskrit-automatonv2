#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_export_images.py  (2026-10-04)  EXPORT_IMAGES_2026_10_04   (phase I4)

Adds an OPT-IN switch to scripts/export_html.py:

    --images none       (default) output is byte-for-byte what it is today
    --images approved   every APPROVED image of the doc (doc_images, status
                        'approved') is placed as a <figure> directly after the
                        verse it is anchored to (anchor_page, anchor_idx). An
                        anchor whose verse is filtered out of the export lands
                        at the end of the section that holds its page.

Why the default stays "none": booksmith_build.py feeds this HTML to Booksmith
as a witness and freezes its sha256. Changing the default output would make
every existing Booksmith project look "changed" and clear its manifest. With
the switch off nothing moves.

With --images approved:
  * images are embedded as data: URIs (downscaled to 1400 px JPEG when Pillow
    is present), so the HTML is self-contained and export_pdf.py - which prints
    a copy from exports\\_print\\ - finds them;
  * the file name gains "_img" (e.g. Mallapurana_1-137_tri_img.html), so the
    plain edition is never overwritten;
  * every generated image carries the label "Illustration - generated, not a
    historical source." (and its Hindi equivalent in a Hindi edition);
  * the figure CSS is added only to these files;
  * a summary line is always printed: placed / at section end / outside range.

  python scripts/patch_export_images.py --check
  python scripts/patch_export_images.py
Test: python -m unittest tests.test_export_images -v   (fails before, passes after)
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK = "EXPORT_IMAGES_2026_10_04"
TARGET = Path("scripts/export_html.py")

HELPERS = r'''# --- EXPORT_IMAGES_2026_10_04: approved images as figures (opt-in) -----------
_FIG_LABEL_EN = "Illustration - generated, not a historical source."
_FIG_LABEL_HI = "\u091a\u093f\u0924\u094d\u0930\u0923 - \u0915\u0943\u0924\u094d\u0930\u093f\u092e \u0930\u0942\u092a \u0938\u0947 \u0928\u093f\u0930\u094d\u092e\u093f\u0924, \u0910\u0924\u093f\u0939\u093e\u0938\u093f\u0915 \u0938\u094d\u0930\u094b\u0924 \u0928\u0939\u0940\u0902\u0964"
_FIG_CSS = (
    "figure.plate { margin: 1.6rem auto 2rem; max-width: 36rem; text-align: center; break-inside: avoid; }"
    "figure.plate img { max-width: 100%; max-height: 70vh; border: 1px solid var(--rule); border-radius: 3px; }"
    "figure.plate figcaption { font-size: .84rem; color: var(--muted); margin-top: .5rem; line-height: 1.6; text-align: left; }"
    "figure.plate figcaption b { color: var(--ink); }"
    "figure.plate .plate-hi { font-family: 'Noto Sans Devanagari','Nirmala UI','Mangal',serif; }"
    "figure.plate .plate-note { display: block; margin-top: .3rem; }"
    "figure.plate .plate-label { display: block; margin-top: .3rem; font-style: italic; font-size: .76rem; }"
    "@media print { figure.plate { break-inside: avoid; page-break-inside: avoid; }"
    " figure.plate img { max-height: 150mm; } }"
)


def _fig_key(page, idx):
    try:
        return (int(page), int(idx))
    except (TypeError, ValueError):
        return (page, idx)


def _fig_embed(path: str):
    """data: URI for the image file, or None when it cannot be read."""
    import base64, io
    try:
        raw = open(path, "rb").read()
    except OSError:
        return None
    try:
        from PIL import Image
        with Image.open(io.BytesIO(raw)) as im:
            im = im.convert("RGB")
            im.thumbnail((1400, 1400))
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=84, optimize=True)
            raw, mime = buf.getvalue(), "image/jpeg"
    except Exception:
        ext = os.path.splitext(path)[1].lower()
        mime = {".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}.get(ext, "image/jpeg")
    return "data:%s;base64,%s" % (mime, base64.b64encode(raw).decode("ascii"))


def _load_figures(con, doc, root=None):
    """{(page, idx): [figure dict, ...]} for the doc's APPROVED images. Empty when
    the doc_images table does not exist yet (no image library) or nothing is approved."""
    if not doc or "doc_images" not in _tables(con):
        return {}
    root = root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rows = con.execute(
        """SELECT i.id, i.version, i.kind, i.title, i.caption_en, i.caption_hi, i.context_note,
                  i.path, i.anchor_page, i.anchor_idx
           FROM doc_images i JOIN docs d ON d.id = i.doc_id
           WHERE d.code = ? AND i.status = 'approved' AND i.path IS NOT NULL
           ORDER BY i.anchor_page, i.anchor_idx, i.id""", (doc,)).fetchall()
    out = {}
    for (iid, ver, kind, title, cen, chi, note, path, pg, ix) in rows:
        full = path if os.path.isabs(path) else os.path.join(root, path)
        uri = _fig_embed(full)
        if not uri:
            print("[export] image #%s skipped: file not found (%s)" % (iid, full))
            continue
        out.setdefault(_fig_key(pg, ix), []).append(
            {"id": iid, "version": ver, "kind": kind or "", "title": title or "", "caption_en": cen or "",
             "caption_hi": chi or "", "note": note or "", "uri": uri, "page": pg, "idx": ix})
    return out


def _fig_copy(figs):
    return {k: list(v) for k, v in (figs or {}).items()}


def _figure_html(fg, include_en, include_hi):
    cap = []
    if fg["title"]:
        cap.append("<b>%s</b>" % html.escape(fg["title"]))
    if include_en and fg["caption_en"]:
        cap.append(html.escape(fg["caption_en"]))
    if include_hi and fg["caption_hi"]:
        cap.append("<span class='plate-hi'>%s</span>" % html.escape(fg["caption_hi"]))
    if not include_en and not (include_hi and fg["caption_hi"]) and fg["caption_en"]:
        cap.append(html.escape(fg["caption_en"]))
    if include_en and fg["note"]:
        cap.append("<span class='plate-note'>%s</span>" % html.escape(fg["note"]))
    if fg["kind"] == "generated":
        lab = _FIG_LABEL_EN if include_en or not include_hi else _FIG_LABEL_HI
        if include_en and include_hi:
            lab = _FIG_LABEL_EN + " / " + _FIG_LABEL_HI
        cap.append("<span class='plate-label'>%s</span>" % html.escape(lab))
    elif fg["kind"] == "edition-plate":
        cap.append("<span class='plate-label'>Plate from the source edition.</span>")
    alt = html.escape(fg["title"] or "illustration", quote=True)
    return ("<figure class='plate' id='img-%s' data-kind='%s'><img src='%s' alt='%s'/>"
            "<figcaption>%s</figcaption></figure>"
            % (fg["id"], html.escape(fg["kind"], quote=True), fg["uri"], alt, " ".join(cap)))


def _with_fig_css(doc_html, on):
    return doc_html.replace("</style>", _FIG_CSS + "</style>", 1) if on else doc_html


'''

EDITS = [
    ("render signature",
     "            title=None):\n    # Group into ordered sections.\n",
     "            title=None, figures=None):   # EXPORT_IMAGES_2026_10_04: figures\n"
     "    # Group into ordered sections.\n", 1),
    ("place figures",
     "            kept += 1\n        # footnotes for this section\n",
     "            kept += 1\n"
     "            if figures:   # EXPORT_IMAGES_2026_10_04: right after the anchored verse\n"
     "                for _fg in figures.pop(_fig_key(r[\"page\"], r[\"idx\"]), []):\n"
     "                    out.append(_figure_html(_fg, include_en, include_hi))\n"
     "        if figures:   # anchors whose verse was filtered out: end of the section holding the page\n"
     "            _pages = {_fig_key(x[\"page\"], 0)[0] for x in rows}\n"
     "            for _k in sorted((k for k in list(figures) if k[0] in _pages), key=str):\n"
     "                for _fg in figures.pop(_k):\n"
     "                    _fg[\"_late\"] = True\n"
     "                    out.append(_figure_html(_fg, include_en, include_hi))\n"
     "        # footnotes for this section\n", 1),
    ("helpers",
     "# --- export core -------------------------------------------------------------\n",
     HELPERS + "# --- export core -------------------------------------------------------------\n", 1),
    ("export_one signature + load",
     "                keep_frontmatter=False):\n    san_col, en_col = _detect_cols(con, doc, force_san, force_en, debug=debug)\n",
     "                keep_frontmatter=False, images=\"none\"):\n"
     "    san_col, en_col = _detect_cols(con, doc, force_san, force_en, debug=debug)\n"
     "    figs = _load_figures(con, doc) if images == \"approved\" else {}   # EXPORT_IMAGES_2026_10_04\n"
     "    _fig_total = sum(len(v) for v in figs.values())\n", 1),
    ("render calls",
     "want_toc=want_toc, want_footnotes=want_footnotes, title=title)",
     "want_toc=want_toc, want_footnotes=want_footnotes, title=title,\n"
     "                         figures=_fig_copy(figs) if figs else None)", 2),
    ("file name",
     "    out_path = os.path.join(dest, f\"{_safe_filename(doc or 'export')}_{lo}-{hi}{suffix}.html\")\n",
     "    if images == \"approved\":   # EXPORT_IMAGES_2026_10_04: never overwrite the plain edition\n"
     "        suffix += \"_img\"\n"
     "    out_path = os.path.join(dest, f\"{_safe_filename(doc or 'export')}_{lo}-{hi}{suffix}.html\")\n", 1),
    ("write",
     "        f.write(_html(title or (doc or \"Export\"), body, lang_attr=lang_attr))\n",
     "        f.write(_with_fig_css(_html(title or (doc or \"Export\"), body, lang_attr=lang_attr), bool(figs)))\n"
     "    if images == \"approved\":   # EXPORT_IMAGES_2026_10_04\n"
     "        _n_in = body.count(\"<figure class='plate'\")\n"
     "        print(f\"[export] images: {_fig_total} approved, {_n_in} placed, \"\n"
     "              f\"{_fig_total - _n_in} outside pages {lo}-{hi}\")\n", 1),
    ("arg",
     "    ap.add_argument(\"--debug\", action=\"store_true\")\n",
     "    ap.add_argument(\"--images\", choices=[\"none\", \"approved\"], default=\"none\",\n"
     "                    help=\"EXPORT_IMAGES_2026_10_04: approved = place approved images from the \"\n"
     "                         \"image library at their verses (file name gains _img).\")\n"
     "    ap.add_argument(\"--debug\", action=\"store_true\")\n", 1),
    ("pass arg",
     "keep_frontmatter=args.keep_frontmatter)",
     "keep_frontmatter=args.keep_frontmatter, images=args.images)", 2),
]


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def apply(src: str):
    problems = []
    for label, old, new, n in EDITS:
        c = src.count(old)
        if c != n:
            problems.append("%s: matched %d times, expected %d" % (label, c, n))
        else:
            src = src.replace(old, new)
    return src, problems


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    if not TARGET.exists():
        print("FAIL: %s not found. Run from the repo root." % TARGET); return 2
    src, nl = load(TARGET)
    if MARK in src:
        print("Already patched (%s). Nothing to do." % MARK); return 0
    new, problems = apply(src)
    if problems:
        print("REFUSING TO WRITE:"); [print("  " + x) for x in problems]; return 1
    if args.check:
        print("CHECK OK: %d anchored edits. Nothing written." % len(EDITS)); return 0
    tmp = TARGET.with_name(TARGET.name + ".tmp_img")
    tmp.write_bytes(new.replace("\n", nl).encode("utf-8"))
    try:
        py_compile.compile(str(tmp), doraise=True)
    except py_compile.PyCompileError as e:
        tmp.unlink(missing_ok=True); print("REFUSING TO WRITE: would not compile:\n%s" % e); return 1
    bak = TARGET.with_name(TARGET.name + ".bak_img_" + datetime.date.today().strftime("%Y%m%d"))
    shutil.copy2(TARGET, bak)
    os.replace(tmp, TARGET)
    print("PATCHED %s (backup %s). Default output unchanged; use --images approved." % (TARGET, bak.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
