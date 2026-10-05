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
            except (FileNotFoundError, sqlite3.Error, ValueError, TypeError) as e:
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
            r = c.execute("SELECT id, status, title, path FROM doc_images WHERE id=?", (d["image_id"],)).fetchone()
            if r:
                img = {"id": r[0], "status": r[1], "title": r[2], "has_image": bool(r[3])}
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
        if not re.match(r"^anthology_\d{8}\.html$", name) or not (root / "exports" / name).is_file():
            return bad("no such anthology file")
        cmd = py(script("export_pdf.py"), str(root / "exports" / name))
        try:
            jid = launch("stories", name, cmd, mode="pdf")
        except TypeError:
            jid = launch("stories", name, cmd)
        return jsonify({"job": jid})

    return app
