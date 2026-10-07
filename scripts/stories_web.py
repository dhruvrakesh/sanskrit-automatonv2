#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
stories_web.py  (2026-10-05)  STORIES_UI_2026_10_05

The Stories page at http://127.0.0.1:5057/stories: the front end of scripts/stories.py.
For each text it shows every story beside its image and the passages it cites (Sanskrit
as printed, the machine English), so an editor can read, correct, verify, approve or
retire it in the browser, where Devanagari and IAST display properly.

  * Reads, edits and the no-API check run in the request (a few rows).
  * Anything that calls a model (find episodes, write stories) or builds the anthology
    runs as a dashboard job through launch(), visible in the job list and jobs.jsonl;
    the page polls /api/job/<id>.
  * An edit re-runs the check and returns the story to 'draft'; approval follows the
    same rule as the CLI (a failed check needs an explicit "approve anyway").
Registered from dashboard.py inside try/except, so a fault here cannot stop the dashboard.

STORY_BOOKS_2026_10_07 (same page, more wiring):
  * Propose image: stories.py illustrate (one idea, linked to the story); drawing,
    approving and redrawing reuse the image library's own routes (/api/images/...).
  * Book: choose texts and stories, an audience and languages -> stories.py book
    (HTML, then PDF) or a Booksmith edition (booksmith_build.py --source-html).
  * Brain: what of the stories, episodes and images is not yet in the Ask index
    (brain_items.py), and a button to add it.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stories as st  # noqa: E402
import images as im   # noqa: E402

MARK = "STORIES_UI_2026_10_05"
MARK2 = "STORY_BOOKS_2026_10_07"
BOOK_RE = re.compile(r"^(anthology_\d{8}|book_[a-z0-9-]{1,40}_\d{8})\.html$")
AUDIENCES = ("young", "general", "scholar")
DOC_RE = re.compile(r"^[A-Za-z0-9_\-]+$")
EDITABLE = ("title", "title_hi", "story_en", "story_hi", "quote_sa", "quote_ref", "notes")
LIMITS = {"title": 300, "title_hi": 300, "story_en": 6000, "story_hi": 8000, "quote_sa": 400, "quote_ref": 20,
          "notes": 4000}


def register(app, *, launch, root, py, script, db=None):
    from flask import jsonify, request, send_from_directory

    root = Path(root)
    dbp = Path(db) if db else root / "data" / "context.db"
    if not dbp.is_absolute():
        dbp = root / dbp
    cache = {"docs": None, "at": 0.0, "schema": False}

    def con():
        # Never create a database: a wrong path must fail, not leave an empty context.db behind.
        if not dbp.is_file():
            raise FileNotFoundError("database not found: %s" % dbp)
        c = im._connect(str(dbp))
        if not cache["schema"]:
            st.ensure_schema(c)   # CREATE ... IF NOT EXISTS, once per dashboard run
            cache["schema"] = True
        return c

    def guarded(fn):
        """A fault in one request answers JSON, never an HTML 500 page, and never reaches the dashboard."""
        import functools

        @functools.wraps(fn)
        def inner(*a, **k):
            try:
                return fn(*a, **k)
            except (FileNotFoundError, sqlite3.Error, ValueError, TypeError, AttributeError, SystemExit) as e:
                return jsonify({"error": "%s: %s" % (type(e).__name__, e)}), 500
        return inner

    def bad(msg, code=400):
        return jsonify({"error": msg}), code

    def row_out(c, d):
        d = dict(d)
        d.pop("provenance", None)
        try:
            d["verify"] = json.loads(d.get("verify") or "null")
        except ValueError:
            d["verify"] = None
        try:
            d["cites"] = json.loads(d.get("cites") or "[]")
        except ValueError:
            d["cites"] = []
        d["range"] = "%s-%s" % (st.ref(d["from_page"], d["from_idx"]), st.ref(d["to_page"], d["to_idx"]))
        img = None
        if d.get("image_id"):
            # STORY_BOOKS_2026_10_07: show the newest version of the picture's lineage that is not retired, so a
            # Redraw (images.py regenerate makes a new row) appears here; approving it relinks the story.
            r = c.execute("""SELECT i.id, i.status, i.title, i.path, i.brief, i.caption_en, i.kind FROM doc_images i
                             WHERE i.lineage_id = (SELECT COALESCE(lineage_id, id) FROM doc_images WHERE id=?)
                               AND i.status <> 'retired' ORDER BY i.version DESC, i.id DESC LIMIT 1""",
                          (d["image_id"],)).fetchone() or c.execute(
                "SELECT id, status, title, path, brief, caption_en, kind FROM doc_images WHERE id=?",
                (d["image_id"],)).fetchone()
            if r:
                img = {"id": r[0], "status": r[1], "title": r[2], "has_image": bool(r[3]), "brief": r[4] or "",
                       "caption_en": r[5] or "", "kind": r[6]}
        d["image"] = img
        return d

    def get_story(c, sid):
        c.row_factory = sqlite3.Row
        r = c.execute("SELECT * FROM doc_stories WHERE id=?", (sid,)).fetchone()
        c.row_factory = None
        return dict(r) if r else None

    def given_rows(c, s):
        code = c.execute("SELECT code FROM docs WHERE id=?", (s["doc_id"],)).fetchone()[0]
        return code, st.window(st.passages(c, code), (s["from_page"], s["from_idx"]),
                               (s["to_page"], s["to_idx"]), pad=2, cap=60)

    def job(doc, argv, mode):
        cmd = py(script("stories.py"), "--db", str(dbp), *argv)
        try:
            jid = launch("stories", doc, cmd, mode=mode)
        except TypeError:   # a dashboard without the mode argument
            jid = launch("stories", doc, cmd)
        return jsonify({"job": jid})

    @app.get("/stories")
    def stories_page():
        return send_from_directory(str(root / "scripts"), "stories_static.html")

    @app.get("/api/stories/docs")
    @guarded
    def stories_docs():
        c = con()
        try:
            if cache["docs"] is None or time.time() - cache["at"] > 60:
                cache["docs"] = {r[0]: r[1] for r in c.execute(
                    """SELECT d.code, COUNT(*) FROM passages p JOIN docs d ON d.id=p.doc_id
                       WHERE TRIM(COALESCE(p.translation,''))<>'' AND d.code NOT LIKE '%-RETIRED'
                       GROUP BY d.code""")}
                cache["at"] = time.time()
            counts, drawn = {}, {}
            for code, s, n in c.execute("""SELECT d.code, s.status, COUNT(*) FROM doc_stories s
                                           JOIN docs d ON d.id=s.doc_id GROUP BY d.code, s.status"""):
                counts.setdefault(code, {})[s] = n
            for code, n in c.execute("""SELECT d.code, COUNT(*) FROM doc_images i JOIN docs d ON d.id=i.doc_id
                                        WHERE i.kind='generated' AND i.status IN ('draft','approved')
                                          AND i.path IS NOT NULL GROUP BY d.code"""):
                drawn[code] = n
        finally:
            c.close()
        out = [{"doc": k, "translated": v, "stories": counts.get(k, {}), "images_drawn": drawn.get(k, 0)}
               for k, v in cache["docs"].items()]
        out.sort(key=lambda d: (-sum(d["stories"].values()), -d["images_drawn"], d["doc"].lower()))
        return jsonify(out)

    @app.get("/api/stories/list")
    @guarded
    def stories_list():
        doc = request.args.get("doc", "")
        if not DOC_RE.match(doc):
            return bad("invalid doc")
        c = con()
        try:
            did = c.execute("SELECT id FROM docs WHERE code=?", (doc,)).fetchone()
            if not did:
                return bad("unknown doc", 404)
            c.row_factory = sqlite3.Row
            rows = [dict(r) for r in c.execute(
                "SELECT * FROM doc_stories WHERE doc_id=? ORDER BY from_page, from_idx, id", (did[0],))]
            c.row_factory = None
            return jsonify([row_out(c, r) for r in rows])
        finally:
            c.close()

    @app.get("/api/stories/<int:sid>/passages")
    @guarded
    def stories_passages(sid):
        c = con()
        try:
            s = get_story(c, sid)
            if not s:
                return bad("unknown story", 404)
            _code, rows = given_rows(c, s)
            return jsonify([{"ref": st.ref(p, i), "sa": sa, "iast": ia, "en": en} for p, i, sa, ia, en in rows])
        finally:
            c.close()

    @app.post("/api/stories/<int:sid>/edit")
    @guarded
    def stories_edit(sid):
        data = request.get_json(force=True) or {}
        fields = {k: str(data[k])[:LIMITS[k]] for k in EDITABLE if k in data}
        if not fields:
            return bad("nothing to change")
        c = con()
        try:
            s = get_story(c, sid)
            if not s:
                return bad("unknown story", 404)
            if s["status"] == "retired":
                return bad("this story is retired")
            s.update(fields)
            _code, rows = given_rows(c, s)
            v = st.verify(s, rows)
            sets = ", ".join("%s=?" % k for k in fields)
            c.execute("UPDATE doc_stories SET %s, verify=?, cites=?, status=CASE WHEN status='candidate' THEN "
                      "'candidate' ELSE 'draft' END, approved_at=NULL, updated_at=? WHERE id=?" % sets,
                      list(fields.values()) + [json.dumps(v), json.dumps(v["cited"]), st.now(), sid])
            c.commit()
            return jsonify({"ok": True, "verify": v})
        finally:
            c.close()

    @app.post("/api/stories/<int:sid>/action")
    @guarded
    def stories_action(sid):
        data = request.get_json(force=True) or {}
        action = data.get("action", "")
        c = con()
        try:
            s = get_story(c, sid)
            if not s:
                return bad("unknown story", 404)
            if action == "verify":
                _code, rows = given_rows(c, s)
                v = st.verify(s, rows)
                c.execute("UPDATE doc_stories SET verify=?, updated_at=? WHERE id=?", (json.dumps(v), st.now(), sid))
                c.commit()
                return jsonify({"ok": True, "verify": v})
            if action == "approve":
                if s["status"] != "draft":
                    return bad("only a written draft can be approved (this one is %s)" % s["status"])
                ok = (json.loads(s.get("verify") or "{}") or {}).get("ok")
                if not ok and not data.get("force"):
                    return bad("the check failed; read the problems, then use 'Approve anyway'", 409)
                c.execute("UPDATE doc_stories SET status='approved', approved_at=?, updated_at=? WHERE id=?",
                          (st.now(), st.now(), sid))
                c.commit()
                return jsonify({"ok": True})
            if action == "retire":
                c.execute("UPDATE doc_stories SET status='retired', updated_at=? WHERE id=?", (st.now(), sid))
                c.commit()
                return jsonify({"ok": True})
            if action == "unretire":
                c.execute("UPDATE doc_stories SET status=CASE WHEN COALESCE(story_en,'')='' THEN 'candidate' "
                          "ELSE 'draft' END, updated_at=? WHERE id=?", (st.now(), sid))
                c.commit()
                return jsonify({"ok": True})
            return bad("unknown action")
        finally:
            c.close()

    @app.post("/api/stories/mine")
    @guarded
    def stories_mine():
        data = request.get_json(force=True) or {}
        doc = data.get("doc", "")
        if not DOC_RE.match(doc):
            return bad("invalid doc")
        n = max(1, min(40, int(data.get("max") or 12)))
        return job(doc, ["mine", "--doc", doc, "--max", str(n), "--yes"], "mine")

    @app.post("/api/stories/write")
    @guarded
    def stories_write():
        data = request.get_json(force=True) or {}
        doc = data.get("doc", "")
        if not DOC_RE.match(doc):
            return bad("invalid doc")
        n = max(1, min(30, int(data.get("max") or 6)))
        if data.get("id"):
            return job(doc, ["write", "--id", str(int(data["id"])), "--yes"], "id-%d" % int(data["id"]))
        if data.get("image"):
            argv = ["write", "--image", str(int(data["image"])), "--yes",
                    "--before", str(max(0, min(80, int(data.get("before") or 6)))),
                    "--after", str(max(0, min(80, int(data.get("after") or 6))))]
            return job(doc, argv, "image-%d" % int(data["image"]))
        which = data.get("which")
        if which not in ("images", "candidates"):
            return bad("give id, image, or which=images|candidates")
        return job(doc, ["write", "--doc", doc, "--" + which, "--max", str(n), "--yes"], which)

    @app.post("/api/stories/anthology")
    @guarded
    def stories_anthology():
        data = request.get_json(force=True) or {}
        docs = [d for d in (data.get("docs") or []) if DOC_RE.match(str(d))]
        if not docs:
            return bad("give docs")
        title = str(data.get("title") or "Episodes from the Sanskrit corpus")[:200]
        return job(docs[0], ["anthology", "--docs", ",".join(docs), "--title", title], "anthology")

    @app.post("/api/stories/pdf")
    @guarded
    def stories_pdf():
        data = request.get_json(force=True) or {}
        name = str(data.get("name") or "")
        if not BOOK_RE.match(name) or not (root / "exports" / name).is_file():
            return bad("no such anthology file")
        cmd = py(script("export_pdf.py"), str(root / "exports" / name))
        try:
            jid = launch("stories", name, cmd, mode="pdf")
        except TypeError:
            jid = launch("stories", name, cmd)
        return jsonify({"job": jid})

    # ---------------------------------------------------------------- STORY_BOOKS_2026_10_07
    @app.post("/api/stories/<int:sid>/illustrate")
    @guarded
    def stories_illustrate(sid):
        c = con()
        try:
            s = get_story(c, sid)
            if not s:
                return bad("unknown story", 404)
            if s["status"] == "retired":
                return bad("this story is retired")
            if s.get("image_id"):
                r = c.execute("SELECT status FROM doc_images WHERE id=?", (s["image_id"],)).fetchone()
                if r and r[0] != "retired":
                    return bad("story #%d already has image #%d (%s)" % (sid, s["image_id"], r[0]))
            code = c.execute("SELECT code FROM docs WHERE id=?", (s["doc_id"],)).fetchone()[0]
        finally:
            c.close()
        return job(code, ["illustrate", "--id", str(sid), "--yes"], "illus-%d" % sid)

    @app.post("/api/stories/<int:sid>/image")
    @guarded
    def stories_image(sid):
        """approve: approve the picture (the image library's rule: one approved version per lineage) and link
        it to the story; retire: retire the idea or picture, so another can be proposed."""
        data = request.get_json(force=True) or {}
        act, iid = data.get("action"), int(data.get("image") or 0)
        c = con()
        try:
            s = get_story(c, sid)
            if not s:
                return bad("unknown story", 404)
            row = c.execute("SELECT doc_id, lineage_id FROM doc_images WHERE id=?", (iid,)).fetchone()
            mine = c.execute("SELECT COALESCE(lineage_id, id) FROM doc_images WHERE id=?",
                             (s.get("image_id") or 0,)).fetchone()
            if not row or row[0] != s["doc_id"] or not mine or (row[1] or iid) != mine[0]:
                return bad("image #%d is not this story's picture" % iid)
            if act == "approve":
                im.approve(c, iid)
            elif act == "retire":
                im.set_status(c, iid, "retired")
            else:
                return bad("unknown action")
            if act == "approve":
                c.execute("UPDATE doc_stories SET image_id=?, updated_at=? WHERE id=?", (iid, st.now(), sid))
                c.commit()
            return jsonify({"ok": True})
        finally:
            c.close()

    @app.get("/api/stories/brain")
    @guarded
    def stories_brain():
        try:
            import brain_items as bi
        except Exception as e:
            return jsonify({"available": False, "error": "%s: %s" % (type(e).__name__, e)})
        c = con()
        try:
            p = bi.plan(c)
        finally:
            c.close()
        return jsonify({"available": True, "model": p["model"], "items": p["items"], "indexed": p["indexed"],
                        "add": p["add"], "update": p["update"], "drop": p["drop"]})

    @app.post("/api/stories/brain/refresh")
    @guarded
    def stories_brain_refresh():
        cmd = py(script("brain_items.py"), "--db", str(dbp))
        try:
            jid = launch("brain", "(corpus)", cmd, mode="items")
        except TypeError:
            jid = launch("brain", "(corpus)", cmd)
        return jsonify({"job": jid})

    @app.get("/api/stories/books/stories")
    @guarded
    def stories_for_books():
        docs = [d for d in (request.args.get("docs") or "").split(",") if DOC_RE.match(d)]
        if not docs:
            return bad("give docs")
        c = con()
        try:
            out = []
            for code, sid, st, title, th, fp, fi, tp, ti, iid, ipath, ist, en, vj in c.execute(
                    """SELECT d.code, s.id, s.status, s.title, s.title_hi, s.from_page, s.from_idx, s.to_page, s.to_idx,
                              s.image_id, i.path, i.status, COALESCE(s.story_en,''), s.verify
                       FROM doc_stories s JOIN docs d ON d.id = s.doc_id
                       LEFT JOIN doc_images i ON i.id = s.image_id
                       WHERE d.code IN (%s) AND s.status IN ('draft','approved')
                       ORDER BY d.code, s.from_page, s.from_idx, s.id""" % ",".join("?" * len(docs)), docs):
                try:
                    ok = (json.loads(vj or "null") or {}).get("ok")
                except ValueError:
                    ok = None
                out.append({"doc": code, "id": sid, "status": st, "title": title or "", "title_hi": th or "",
                            "range": "%s-%s" % (st_ref(fp, fi), st_ref(tp, ti)), "image_id": iid,
                            "image_ok": bool(ipath) and ist == "approved", "words": len(en.split()), "check_ok": ok})
            return jsonify(out)
        finally:
            c.close()

    def st_ref(p, i):
        return st.ref(p, i) if p is not None and i is not None else "?"

    def _ids(data):
        ids = []
        for x in (data.get("ids") or []):
            try:
                ids.append(int(x))
            except (TypeError, ValueError):
                pass
        return ids[:200]

    @app.post("/api/stories/book")
    @guarded
    def stories_book():
        data = request.get_json(force=True) or {}
        ids = _ids(data)
        if not ids:
            return bad("choose at least one story")
        title = str(data.get("title") or "Stories from the Sanskrit corpus").strip()[:200]
        aud = data.get("audience") if data.get("audience") in AUDIENCES else "general"
        argv = ["book", "--ids", ",".join(map(str, ids)), "--title", title, "--audience", aud]
        if not data.get("hindi", True):
            argv.append("--no-hindi")
        if data.get("proof"):
            argv.append("--proof")
        return job("(book)", argv, "book-" + st._slug(title) + "-" + aud)

    @app.post("/api/stories/booksmith")
    @guarded
    def stories_booksmith():
        """Write the Booksmith witness now (local, no API), then build it as a dashboard job."""
        data = request.get_json(force=True) or {}
        ids = _ids(data)
        if not ids:
            return bad("choose at least one story")
        title = str(data.get("title") or "Stories from the Sanskrit corpus").strip()[:200]
        label = "stories-" + st._slug(title)
        witness = root / "exports" / "booksmith" / ("%s.html" % label)
        c = con()
        try:
            _p, n = st.booksmith_source(c, ids, title, witness)
            plate_ids = []
            if data.get("plates", True):
                for sid in ids:
                    r = c.execute("""SELECT i.id FROM doc_stories s JOIN doc_images i ON i.id = s.image_id
                                     WHERE s.id=? AND s.status='approved' AND i.status='approved'
                                       AND i.path IS NOT NULL""", (sid,)).fetchone()
                    if r:
                        plate_ids.append(r[0])
        finally:
            c.close()
        if not n:
            return bad("none of the chosen stories is approved; a Booksmith edition takes approved stories only")
        argv = py(script("booksmith_build.py"), "--db", str(dbp), "--doc", label, "--mode", "story",
                  "--source-html", str(witness), "--title", title)
        if plate_ids:
            argv += ["--plate-ids", ",".join(map(str, plate_ids[:12]))]
        try:
            jid = launch("booksmith", label, argv, mode="story")
        except TypeError:
            jid = launch("booksmith", label, argv)
        return jsonify({"job": jid, "label": label, "stories": n, "plates": len(plate_ids[:12])})

    @app.get("/api/stories/booksmith/file")
    def stories_booksmith_file():
        from flask import send_file
        label = request.args.get("label", "")
        if not re.match(r"^stories-[a-z0-9-]{1,40}$", label):
            return bad("invalid label")
        side = root / "exports" / "booksmith" / ("%s__story.json" % label)
        try:
            pdf = Path(json.loads(side.read_text(encoding="utf-8")).get("pdf") or "")
        except (OSError, ValueError):
            return bad("no build recorded for %s" % label, 404)
        if pdf.name not in ("book.pdf", "layout-proof.pdf") or pdf.parent.name != "build" or not pdf.is_file():
            return bad("no PDF for %s" % label, 404)
        return send_file(str(pdf), mimetype="application/pdf", download_name="%s.pdf" % label)

    @app.get("/api/stories/books/files")
    @guarded
    def stories_book_files():
        ex = root / "exports"
        files = sorted([p for p in ex.glob("*.html") if BOOK_RE.match(p.name)], key=lambda p: -p.stat().st_mtime)[:30]
        out = [{"name": p.name, "pdf": (p.with_suffix(".pdf").name if p.with_suffix(".pdf").is_file() else None),
                "mtime": p.stat().st_mtime} for p in files]
        bsd = ex / "booksmith"
        for side in sorted(bsd.glob("stories-*__story.json"), key=lambda p: -p.stat().st_mtime)[:20] if bsd.is_dir() else []:
            try:
                d = json.loads(side.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            out.append({"booksmith": d.get("doc"), "ok": d.get("ok"), "pdf_kind": d.get("pdf_kind"),
                        "error": d.get("error"), "mtime": side.stat().st_mtime})
        return jsonify(out)

    return app
