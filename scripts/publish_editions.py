#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
publish_editions.py  (2026-10-18)  EDITIONS_SITE_2026_10_18

The scholarly editions on Srangam, open to everyone. Each edition named in configs/editions.json (and "enabled") is
made from the database as export_html.py --scholar makes it (read only: the Sanskrit, the scholarly English, the
notes, a dagger on what a person has not yet read), given a bar back to the site, its credits and its licence, and
written into the Srangam repo as public/scholarly/<slug>.html, with public/scholarly/index.json, which the site's
/editions page reads. The site serves the files as they are: no database, no sign-in, nothing to deploy but the
files you commit.

Refused: a text the register (data/source_verdicts.jsonl) holds in repair or has withdrawn; a witness (an e-text,
<doc>__w_<site>) whose entry gives no source and licence; an edition with no scholarly English. An edition whose
content has not changed is left as it is (its date too).

  python scripts\\publish_editions.py                      (the plan: what would be written; free, nothing written)
  python scripts\\publish_editions.py --apply              (writes into the Srangam repo; never runs git)
  python scripts\\publish_editions.py --only devimahatmya --apply
  python scripts\\publish_editions.py --list               (the editions in the config, and the site's index)

Then, in the Srangam repo: git pull --rebase --autostash; git add public/scholarly; git commit; git push (you push).
"""
from __future__ import annotations
import argparse, datetime, hashlib, html, json, os, re, subprocess, sys, tempfile
from pathlib import Path

MARK = "EDITIONS_SITE_2026_10_18"
ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
CONFIG = ROOT / "configs" / "editions.json"
DEFAULT_SITE = Path(r"D:\srangam-42267")
SITE_URL = "https://srangam.nartiang.org"
SUBDIR = Path("public") / "scholarly"
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,59}$")
DOC_RE = re.compile(r"^[A-Za-z0-9_\-]+$")
STATS_RE = re.compile(r"<b>Scholarly English:</b> (\d+) of (\d+) verses \(passed (\d+), flagged (\d+), doubted for the "
                      r"reading (\d+); accepted by a person (\d+), rejected (\d+)")
MADE_RE = re.compile(r"made by ([^;]+); judged by ([^;]+); prompt ([^<]+?)\.(?=\s|<|$)")
HELD = ("in_repair", "withdrawn")
BAR_CSS = (".site-bar{font-family:system-ui,-apple-system,'Segoe UI',sans-serif;font-size:.85rem;display:flex;flex-wrap:"
           "wrap;gap:.4rem 1rem;align-items:center;justify-content:space-between;padding:.6rem 0 .9rem;border-bottom:"
           "1px solid var(--rule);margin-bottom:1rem}.site-bar a{color:var(--accent)}.credits{font-family:system-ui,"
           "-apple-system,'Segoe UI',sans-serif;font-size:.8rem;color:var(--muted);background:#f7f5ef;border:1px solid "
           "var(--rule);border-radius:6px;padding:.7rem 1rem;margin:0 0 1.2rem;line-height:1.6}.credits b{color:"
           "var(--ink)}.credits a{color:var(--accent)}")


def say(verdict: str, nxt: str = "", also=()):
    print("VERDICT: " + verdict)
    print("NEXT: " + nxt)
    for x in also:
        print("ALSO: " + x)


def register(path: Path) -> dict:
    """The latest record of each text in the register (repair_text.py's, etext_witness.py's)."""
    last = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r, dict) and r.get("doc"):
                    last[r["doc"]] = r
    except OSError:
        pass
    return last


def load_config(path: Path) -> dict:
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        raise SystemExit("FAIL: %s not found" % path)
    except ValueError as e:
        raise SystemExit("FAIL: %s is not JSON: %s" % (path, e))
    if not isinstance(cfg, dict) or not isinstance(cfg.get("editions"), list):
        raise SystemExit("FAIL: %s needs an \"editions\" list" % path)
    return cfg


def check_entry(e: dict, reg: dict) -> str:
    """'' when the entry may be published, else why not."""
    if not isinstance(e, dict):
        return "not an object"
    if not SLUG_RE.match(str(e.get("slug") or "")):
        return "slug: lower-case letters, digits and hyphens"
    if not DOC_RE.match(str(e.get("doc") or "")):
        return "doc: a text's code"
    pages = e.get("pages")
    if not (isinstance(pages, list) and len(pages) == 2 and all(isinstance(x, int) and x > 0 for x in pages)
            and pages[0] <= pages[1]):
        return "pages: [first, last]"
    if not str(e.get("title") or "").strip():
        return "title is needed"
    st = (reg.get(e["doc"]) or {}).get("status")
    if st in HELD:
        return "the register holds %s (%s): not for the site" % (e["doc"], st)
    src = e.get("source") or {}
    if "__w_" in e["doc"] or st == "witness":
        if not (str(src.get("name") or "").strip() and str(src.get("licence") or "").strip()):
            return "a witness (an e-text) needs its source and licence in the entry"
    return ""


def export(db: Path, e: dict, out: Path, py: str = sys.executable) -> Path:
    cmd = [py, str(SCRIPTS / "export_html.py"), "--db", str(db), "--doc", e["doc"], "--scholar", "--sanskrit",
           "--side-by-side", "--from", str(e["pages"][0]), "--to", str(e["pages"][1]), "--title", e["title"],
           "--out", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    files = sorted(out.glob("*_scholar.html"))
    if r.returncode != 0 or len(files) != 1:
        raise RuntimeError("export_html.py: rc %s, %d file(s): %s" % (r.returncode, len(files), (r.stderr or r.stdout)[-400:]))
    return files[0]


def stats_of(page: str) -> dict:
    m = STATS_RE.search(page)
    if not m:
        return {}
    k = ("verses", "shown", "passed", "flagged", "doubt", "accepted", "rejected")
    s = dict(zip(k, (int(x) for x in m.groups())))
    m2 = MADE_RE.search(page[m.end():m.end() + 800])
    if m2:
        s["engines"] = html.unescape(m2.group(1)).strip()
        s["judge"] = html.unescape(m2.group(2)).strip()
        s["prompt"] = html.unescape(m2.group(3)).strip()
    return s


def friendly(s: str) -> str:
    """'anthropic:claude-sonnet-5-5 (669)' as 'Claude Sonnet 5.5'; 'gemini:gemini-2.5-flash' as 'Gemini 2.5 Flash'."""
    s = re.sub(r"\s*\(\d+\)", "", s or "")
    s = re.sub(r"anthropic:claude-([a-z]+)-(\d+)-(\d+)", lambda m: "Claude %s %s.%s" % (m.group(1).title(), m.group(2),
                                                                                     m.group(3)), s)
    return re.sub(r"gemini:gemini-(\d+\.\d+)-([a-z]+)", lambda m: "Gemini %s %s" % (m.group(1), m.group(2).title()), s)


def _a(url: str, text: str) -> str:
    if not re.match(r"^https://[^\s\"'<>]+$", url or ""):
        return html.escape(text)
    return "<a href='%s' rel='noopener'>%s</a>" % (html.escape(url, quote=True), html.escape(text))


def credits_html(e: dict, st: dict) -> str:
    src = e.get("source") or {}
    lic = e.get("english_licence") or {}
    lines = []
    if src.get("name"):
        s = "<b>The Sanskrit:</b> " + _a(src.get("url") or "", src["name"])
        if src.get("credit"):
            s += "; " + html.escape(src["credit"])
        if src.get("licence"):
            s += ". " + _a(src.get("licence_url") or "", src["licence"])
        if src.get("note"):
            s += ". " + html.escape(src["note"])
        lines.append(s + ".")
    lines.append("<b>The English:</b> the scholarly English of the Sanskrit Automaton, made by %s, read by a critic and "
                 "revised, judged verse by verse by %s%s. %s verses of %s passed the judge; %s, marked &#8224;, are "
                 "flagged for a person to read."
                 % (html.escape(friendly(st.get("engines")) or "the models named below"), html.escape(friendly(st.get("judge")) or "a judge"),
                    html.escape(e.get("audit") or ""), st.get("passed", 0), st.get("verses", 0),
                    st.get("flagged", 0) + st.get("doubt", 0)))
    if lic.get("name"):
        lines.append("<b>Licence of this edition:</b> " + _a(lic.get("url") or "", lic["name"])
                     + (". " + html.escape(lic["note"]) if lic.get("note") else "") + ".")
    lines.append("A machine translation, to be read beside the Sanskrit; corrections are welcome through the "
                 "Researchers' Corner.")
    return "<div class='credits'>" + "<br/>".join(lines) + "</div>"


def dress(page: str, e: dict, st: dict) -> str:
    """The exported edition, given its place on the site: a bar back to /editions, its credits, its canonical address."""
    slug = e["slug"]
    url = "%s/scholarly/%s.html" % (SITE_URL, slug)
    desc = "%s: %s" % (e["title"], e.get("subtitle") or "the Sanskrit with a scholarly English and notes")
    head = ("<link rel='canonical' href='%s'/><meta name='description' content='%s'/>"
            "<meta name='robots' content='index,follow'/><!-- %s -->"
            % (html.escape(url, quote=True), html.escape(desc, quote=True), MARK))
    page = page.replace("</head>", head + "</head>", 1)
    page = page.replace("</style>", BAR_CSS + "</style>", 1)
    bar = ("<div class='site-bar'><a href='/editions'>&larr; Srangam: the scholarly editions</a>"
           "<span>%s</span></div>" % html.escape(e.get("subtitle") or ""))
    m = re.search(r"<body[^>]*>", page)
    if not m:
        raise RuntimeError("the export has no <body>")
    page = page[:m.end()] + bar + page[m.end():]
    i = page.find("<div class='methodology'>")
    if i < 0:
        raise RuntimeError("the export has no methodology block")
    return page[:i] + credits_html(e, st) + page[i:]


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def plan(a, cfg: dict, reg: dict, site: Path, now: str) -> tuple:
    out_dir = site / SUBDIR
    try:
        old = json.loads((out_dir / "index.json").read_text(encoding="utf-8"))
        old = {x.get("slug"): x for x in old.get("editions", []) if isinstance(x, dict)}
    except (OSError, ValueError):
        old = {}
    rows, writes, problems = [], [], []
    for e in cfg["editions"]:
        slug = (e or {}).get("slug") if isinstance(e, dict) else None
        if a.only and slug not in a.only:
            if slug in old:
                rows.append(old[slug])
            continue
        if isinstance(e, dict) and e.get("enabled") is False:
            print("  %-22s off (%s)" % (slug, e.get("why_off") or "enabled: false"))
            if slug in old:
                print("  %-22s   its published file stays until it is removed by hand" % "")
            continue
        why = check_entry(e, reg)
        if why:
            problems.append("%s: %s" % (slug or "?", why))
            continue
        with tempfile.TemporaryDirectory() as td:
            try:
                f = export(Path(a.db), e, Path(td))
            except RuntimeError as x:
                problems.append("%s: %s" % (slug, x)); continue
            page = f.read_text(encoding="utf-8")
        st = stats_of(page)
        if not st.get("verses"):
            problems.append("%s: no scholarly English in %s pages %d to %d" % (slug, e["doc"], *e["pages"]))
            continue
        page = dress(page, e, st)
        body = page.replace("\r\n", "\n").encode("utf-8")
        h = sha(body)
        prev = old.get(slug) or {}
        same = prev.get("content_sha256") == h and (out_dir / ("%s.html" % slug)).exists()
        rec = {"slug": slug, "title": e["title"], "subtitle": e.get("subtitle") or "", "file": "/scholarly/%s.html" % slug,
               "doc": e["doc"], "pages": e["pages"], "verses": st["verses"], "shown": st["shown"], "passed": st["passed"],
               "flagged": st["flagged"] + st["doubt"], "accepted": st["accepted"], "engines": friendly(st.get("engines")),
               "judge": friendly(st.get("judge")), "source": e.get("source") or {}, "licence": e.get("english_licence") or {},
               "bytes": len(body), "content_sha256": h, "made_at": prev.get("made_at") if same else now, "mark": MARK}
        rows.append(rec)
        print("  %-22s %s  %d verses (%d passed, %d flagged), %.2f MB%s"
              % (slug, "unchanged" if same else ("new" if not prev else "changed"), rec["verses"], rec["passed"],
                 rec["flagged"], len(body) / 1e6, "" if same else " -> %s" % (SUBDIR / ("%s.html" % slug)).as_posix()))
        if not same:
            writes.append((out_dir / ("%s.html" % slug), body))
    gone = [s for s in old if s not in {r.get("slug") for r in rows} and not (a.only and s not in a.only)]
    for s in gone:
        print("  %-22s no longer in the config (or off): dropped from the index; its file stays until removed by hand" % s)
    return rows, writes, problems, old


def write_atomic(p: Path, data: bytes):
    p.parent.mkdir(parents=True, exist_ok=True)
    t = p.with_name(p.name + ".tmp_editions")
    t.write_bytes(data)
    os.replace(t, p)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="The scholarly editions on Srangam (public/scholarly/).")
    ap.add_argument("--config", default=str(CONFIG))
    ap.add_argument("--db", default=str(ROOT / "data" / "context.db"))
    ap.add_argument("--site", default=None, help="the Srangam repo (default: the config's site_repo, else %s)" % DEFAULT_SITE)
    ap.add_argument("--verdicts", default=str(ROOT / "data" / "source_verdicts.jsonl"))
    ap.add_argument("--only", action="append", default=[], help="this slug only (repeatable)")
    ap.add_argument("--apply", action="store_true", help="write the files (else the plan only)")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args(argv)
    cfg = load_config(Path(a.config))
    site = Path(a.site or cfg.get("site_repo") or DEFAULT_SITE)
    print("publish_editions.py  %s  %s   site: %s" % (MARK, "APPLY" if a.apply else "PLAN (nothing written)", site))
    if a.list:
        for e in cfg["editions"]:
            print("  %-22s %-36s pages %s  %s" % (e.get("slug"), e.get("doc"), e.get("pages"),
                                                  "on" if e.get("enabled", True) else "off"))
        try:
            idx = json.loads((site / SUBDIR / "index.json").read_text(encoding="utf-8"))
            print("  on the site's index: %s" % ", ".join(x.get("slug", "?") for x in idx.get("editions", [])))
        except (OSError, ValueError):
            print("  the site has no index yet")
        say("listed", "")
        return 0
    if not (site / "src" / "App.tsx").exists() or not (site / "package.json").exists():
        say("refused: %s is not the Srangam repo (no src/App.tsx)" % site, "")
        return 1
    if not Path(a.db).exists():
        say("refused: %s not found" % a.db, "")
        return 1
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    rows, writes, problems, old = plan(a, cfg, register(Path(a.verdicts)), site, now)
    for p in problems:
        print("  REFUSED " + p)
    index = {"generated_by": "publish_editions.py (%s)" % MARK, "site": SITE_URL, "editions": rows}
    idx_bytes = (json.dumps(index, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    try:
        same_index = (site / SUBDIR / "index.json").read_bytes().replace(b"\r\n", b"\n") == idx_bytes
    except OSError:
        same_index = False
    if not same_index:
        writes.append((site / SUBDIR / "index.json", idx_bytes))
    if not writes:
        say("nothing to write: %d edition(s) on the site as they are%s" % (len(rows), "; %d refused" % len(problems)
                                                                           if problems else ""), "")
        return 1 if problems and not rows else 0
    if not a.apply:
        say("%d file(s) to write in %s%s" % (len(writes), site / SUBDIR, "; %d refused" % len(problems) if problems else ""),
            "python scripts\\publish_editions.py --apply" + "".join(" --only %s" % s for s in a.only))
        return 0
    for p, data in writes:
        write_atomic(p, data)
        print("wrote %s (%d bytes)" % (p, len(data)))
    say("%d file(s) written in %s: %s" % (len(writes), site / SUBDIR, ", ".join(r["slug"] for r in rows)),
        "cd \"%s\" ; git pull --rebase --autostash ; git add -- public/scholarly ; git commit -m \"The scholarly "
        "editions (%s)\" ; git push" % (site, now[:10]),
        ["%s/editions once the site is built (Lovable builds from main)" % SITE_URL])
    return 0


if __name__ == "__main__":
    sys.exit(main())
