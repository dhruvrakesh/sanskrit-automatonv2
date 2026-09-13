#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
booksmith_build.py  (2026-09-12)  BOOKSMITH_WIRING_2026_09_12

Library -> Booksmith -> PDF, as one job.

WHAT WAS ALREADY TRUE, AND WHAT WAS NOT
---------------------------------------
Booksmith was described to me as "also wired here". It is not: `grep -ri
booksmith` across this entire repository returns nothing. What IS true is
better than wiring - the seam already fits exactly, and somebody proved it
by hand on 8 September:

  * projects/harita-pancamam/source/source.html is BYTE-IDENTICAL to
    exports/harita_pancamam_kalpa_sthanam_1-11_tri.html. So are the sources
    of harita-prathama-sthanam and harita-tritiya-sthanam. I checked all
    three by sha256 before writing a line of this.
  * The classes export_html.py emits - chapter, verse, vref, footnotes, sa,
    iast, en, hi - are exactly the ones book.yaml's parser profile maps.
  * harita-pancamam went the whole way: build/book.pdf, 22 pages, 11 units,
    applied_decisions 0, warnings [], with a sha256 release identity.

So this script automates a path that is known to work, rather than
inventing one.

WHY IT DOES NOT SIMPLY CALL `booksmith build`
---------------------------------------------
pipeline.build() calls require_reading_ready(), which raises when
policy.output_mode == "reading" and the audit still has error-level
findings. That is not a bug to route around - it is the product. Six of
the seven existing Harita projects are parked at exactly that gate, with
work/audit.json present and work/manifest.json absent.

readiness.py itself names the way through:

    "Reading-edition build blocked. Generate a layout proof or an audit
     PDF first."

So this script produces the AUDIT edition - policy.output_mode "audit",
which require_reading_ready() lets past - for projects it creates. That is
the whole text, not a sample, and it is never blocked. If a build is
refused anyway it falls back to `proof` (build/layout-proof.pdf, eight
representative units) and records why, so a run always ends with a file
and an explanation rather than a traceback.

IT WILL NOT EDIT A book.yaml IT DID NOT WRITE. An existing project carries
a human's editorial configuration - parser xpaths, authority rule,
language selection. Overwriting that to force a build would be the exact
opposite of what this work is for. Existing projects are ingested,
audited, and built as configured; if that is blocked, the report says so
and the Library links you into Booksmith's own review UI.

LANGUAGES. Booksmith's EditorialPolicy requires between two and four
reading languages, so a single-language witness is outside its product
model. Every mode here therefore carries the Sanskrit and IAST source:

    tri  ->  --sanskrit --hindi --side-by-side   sa, iast, en, hi
    en   ->  --sanskrit                          sa, iast, en
    hi   ->  --sanskrit --hindi-only             sa, iast, hi

Usage:
  python scripts/booksmith_build.py --db data/context.db --doc <code>
         --mode tri|en|hi [--exports exports] [--booksmith-root DIR]
         [--product audit|proof] [--reingest]
  python scripts/booksmith_build.py --selftest [--booksmith-root DIR]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

MARK = "BOOKSMITH_WIRING_2026_09_12"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_BOOKSMITH_ROOT = r"D:\Nartiang_Booksmith_v0.1.0_2026-08-29\nartiang-booksmith"
SLUG_RE = re.compile(r"^[a-z0-9_-]{2,64}$")

# export_html.py names its own output; the page range in the filename is
# derived from the data, so it cannot be predicted. These are only the
# suffixes, used to narrow the glob that finds what it actually wrote.
MODE_FLAGS = {
    "tri": (["--sanskrit", "--hindi", "--side-by-side"], "_tri",
            ["sanskrit", "iast", "english", "hindi"]),
    "en":  (["--sanskrit"], "",
            ["sanskrit", "iast", "english"]),
    "hi":  (["--sanskrit", "--hindi-only"], "_hi",
            ["sanskrit", "iast", "hindi"]),
}


# BOOKSMITH_UTF8_2026_09_13
# run() decodes every Booksmith subprocess as UTF-8 with errors="replace", so
# a byte the child wrote in cp1252 arrives here as U+FFFD. Echoing that to a
# Windows console whose encoding is cp1252 then raises
#
#   UnicodeEncodeError: 'charmap' codec can't encode character U+FFFD
#
# which is what killed the first Hindi build of Shatpath at 15:04 on
# 2026-09-13 - after init had created the project, before the audit policy
# was applied. The dashboard sets PYTHONIOENCODING for the jobs it launches;
# a console does not. This script should not depend on who started it.
def _force_utf8_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


_force_utf8_streams()


def log(msg: str) -> None:
    print(msg, flush=True)


# BOOKSMITH_MODES_2026_09_13
# Archive scan identifiers that belong in provenance, not on a cover:
# "2015_405693_Shatpath-Brahmanam" -> "Shatpath Brahmanam".
SCAN_ID = re.compile(r"^(?:\d{4}[_\-]\d{3,}[_\-]?)+")
PIPELINE_SUFFIX = re.compile(r"[ _-](seg|segmented|ocr|raw|clean|v\d+)$", re.I)


def slug_for(doc: str, mode: str = "tri") -> str:
    """Project id from a doc code AND its language composition.

    Booksmith's model is one project = one witness, and a different language
    composition is a different witness. Sharing one project between modes is
    what made a Hindi re-export collide with a frozen trilingual manifest.

    tri keeps the bare slug so the seven projects created by hand on
    2026-09-08 continue to resolve; en and hi are suffixed. The SLUG rule is
    2-64 chars of lowercase letters, digits, underscore or hyphen.
    """
    s = doc.strip().lower().replace("_", "-")
    s = re.sub(r"[^a-z0-9_-]+", "-", s).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    suffix = "" if mode == "tri" else ("-" + mode)
    return s[: 64 - len(suffix)] + suffix


def title_for(doc: str, override: str | None = None) -> str:
    """A cover title, not a filename. Conservative on purpose: it drops a
    leading scan id and one trailing pipeline suffix, and nothing else. Words
    that already carry capitals keep them, so MBh01 does not become Mbh01."""
    if override:
        return override
    t = SCAN_ID.sub("", doc or "")
    t = t.replace("_", " ").replace("-", " ")
    t = re.sub(r"\s+", " ", t).strip()
    t = PIPELINE_SUFFIX.sub("", " " + t).strip()
    if not t:
        return doc or "Untitled"
    return " ".join(w if any(ch.isupper() for ch in w) else w.capitalize()
                    for w in t.split())


def sha256_of(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def prepare_existing(project: Path, html: Path) -> tuple[str, str]:
    """Decide what to do about an existing project whose witness is about to
    change. Returns (action, detail); action is one of same / fresh /
    refrozen / refuse."""
    src = project / "source" / "source.html"
    manifest = project / "work" / "manifest.json"
    decisions = project / "work" / "decisions.jsonl"

    if not src.exists():
        return ("fresh", "no witness yet")
    if sha256_of(src) == sha256_of(html):
        return ("same", "witness unchanged")
    if not manifest.exists():
        return ("fresh", "witness changed, nothing frozen")
    if decisions.exists() and decisions.stat().st_size > 0:
        return ("refuse",
                "the witness changed and work/decisions.jsonl holds human "
                "review decisions frozen against the previous one. Re-freezing "
                "would invalidate them silently. Open the project in Booksmith "
                "and decide there.")

    derived = [manifest,
               project / "build" / "book.pdf",
               project / "build" / "layout-proof.pdf",
               project / "build" / "build-report.json",
               project / "build" / "qa-report.json"]
    removed = []
    for p in derived:
        if p.exists():
            p.unlink()
            removed.append(p.name)
    return ("refrozen", "witness changed; cleared " + (", ".join(removed) or "nothing"))


def booksmith_exe(root: Path) -> Path:
    """The venv console script. Booksmith is installed editable into its own
    .venv with Python 3.13 native bits; the automaton's interpreter cannot
    import it, so every Booksmith step is a subprocess into that venv."""
    exe = root / ".venv" / "Scripts" / "booksmith.exe"
    if exe.exists():
        return exe
    exe = root / ".venv" / "bin" / "booksmith"
    if exe.exists():
        return exe
    raise SystemExit(
        "Booksmith is not installed at %s\n"
        "  expected .venv/Scripts/booksmith.exe\n"
        "  Run Launch_Booksmith.bat once in that folder to create it." % root
    )


def _utf8_env() -> dict:
    """BOOKSMITH_UTF8_2026_09_13 - stop U+FFFD being created in the first
    place rather than only surviving it. Without this the Booksmith venv's
    python encodes its own output in the console's cp1252, and the Devanagari
    and IAST it is reporting on comes back here as replacement characters -
    unreadable in the log and, worse, unprintable."""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    log("  $ " + " ".join(str(c) for c in cmd))
    p = subprocess.run([str(c) for c in cmd], cwd=str(cwd) if cwd else None,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=_utf8_env())
    for line in (p.stdout or "").splitlines():
        log("    " + line)
    if p.returncode != 0:
        for line in (p.stderr or "").splitlines()[-25:]:
            log("    ! " + line)
        if check:
            raise RuntimeError("command failed (%d): %s" % (p.returncode, cmd[0]))
    return p


def export_html(db: str, doc: str, mode: str, exports: Path) -> Path:
    flags, suffix, _ = MODE_FLAGS[mode]
    titles = {
        "tri": "%s - Sanskrit / English / Hindi" % title_for(doc),
        "en":  "%s - Sanskrit / English" % title_for(doc),
        "hi":  "%s - Sanskrit / Hindi" % title_for(doc),
    }
    before = {p: os.path.getmtime(p) for p in glob.glob(str(exports / "*.html"))}
    cmd = [sys.executable, "-u", str(HERE / "export_html.py"),
           "--db", db, "--doc", doc, "--out", str(exports),
           "--title", titles[mode], "--debug"] + flags
    p = run(cmd, cwd=ROOT)

    # export_html.py prints the path it wrote under --debug. Trust that first.
    for line in (p.stdout or "").splitlines():
        if line.startswith("[export] wrote "):
            found = line[len("[export] wrote "):].split(" |")[0].strip()
            if os.path.exists(found):
                return Path(found)

    # Fall back to the newest file matching this doc and suffix. The glob is
    # narrowed by suffix because <doc>_1-75.html and <doc>_1-75_tri.html both
    # begin with the doc code, and picking the wrong one would hand Booksmith
    # a witness in the wrong languages without any error.
    pattern = str(exports / ("%s_*%s.html" % (doc, suffix)))
    cands = [p for p in glob.glob(pattern)
             if suffix or not re.search(r"_(tri|hi)\.html$", p)]
    fresh = [p for p in cands if before.get(p, 0) < os.path.getmtime(p)]
    pool = fresh or cands
    if not pool:
        raise RuntimeError("export produced nothing matching %s" % pattern)
    return Path(max(pool, key=os.path.getmtime))


def _half_created(project: Path, mode: str) -> bool:
    """BOOKSMITH_UTF8_2026_09_13 - True for a project whose init succeeded and
    whose policy step did not.

    Deliberately narrow. tri is excluded because the trilingual projects were
    made by hand and three of them (harita-prathama-sthanam,
    harita-shashtham-sharira-sthanam, harita-tritiya-sthanam) also have a
    work/ directory and no manifest, so a looser test would silently flip
    their output_mode - a decision that belongs to the operator, not here.
    en and hi projects only exist because this script created them."""
    if mode == "tri":
        return False
    cfg = project / "book.yaml"
    if not cfg.exists():
        return False
    if (project / "work" / "manifest.json").exists():
        return False                      # a witness is frozen against it
    decisions = project / "work" / "decisions.jsonl"
    try:
        if decisions.exists() and decisions.read_text(
                encoding="utf-8", errors="replace").strip():
            return False                  # a human has reviewed something
    except OSError:
        return False
    try:
        return "output_mode: audit" not in cfg.read_text(
            encoding="utf-8", errors="replace")
    except OSError:
        return False


def set_audit_policy(bs: Path, project: Path, languages: list[str]) -> None:
    """Set output_mode=audit and the reading languages, THROUGH Booksmith's own
    model so the result is validated rather than merely well-formed YAML.
    Called only for projects this script created."""
    py = project_python(bs)
    script = (
        "import sys, json\n"
        "from pathlib import Path\n"
        "from nartiang_booksmith.config import load_yaml, save_yaml, project_paths\n"
        "from nartiang_booksmith.domain import BookConfig\n"
        "p = Path(sys.argv[1]); langs = sys.argv[2].split(',')\n"
        "paths = project_paths(p)\n"
        "c = load_yaml(paths['config'], BookConfig)\n"
        "d = c.model_dump(mode='json')\n"
        "d['policy']['output_mode'] = 'audit'\n"
        "d['policy']['reading_languages'] = langs\n"
        "d['edition_label'] = 'Audit proof'\n"
        # BOOKSMITH_MODES_2026_09_13. subtitle is a hardcoded BookConfig
        # default - "Sanskrit - IAST - English - Hindi" - rendered on the
        # cover and the front matter, and independent of reading_languages.
        # A Hindi-only edition was therefore advertising English. The middot
        # is written as an escape so nothing non-ASCII crosses the command
        # line on a Windows console.
        "labels = {'sanskrit':'Sanskrit','iast':'IAST','english':'English','hindi':'Hindi'}\n"
        "d['subtitle'] = ' \\u00b7 '.join(labels.get(x, x.title()) for x in langs)\n"
        "save_yaml(paths['config'], BookConfig.model_validate(d))\n"
        "print('policy: output_mode=audit reading_languages=' + ','.join(langs))\n"
    )
    run([py, "-c", script, str(project), ",".join(languages)])


def project_python(bs: Path) -> Path:
    p = bs.parent / "python.exe"
    if p.exists():
        return p
    p = bs.parent / "python"
    if p.exists():
        return p
    raise SystemExit("no python next to %s" % bs)


def count_audit_errors(project: Path) -> tuple[int, int]:
    f = project / "work" / "audit.json"
    if not f.exists():
        return (0, 0)
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return (0, 0)
    findings = data.get("findings") or data.get("issues") or []
    if not isinstance(findings, list):
        return (0, 0)
    errors = sum(1 for x in findings
                 if isinstance(x, dict) and str(x.get("severity", "")).lower() == "error")
    return (errors, len(findings))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc")
    ap.add_argument("--mode", default="tri", choices=sorted(MODE_FLAGS))
    ap.add_argument("--exports", default="exports")
    ap.add_argument("--booksmith-root", default=os.getenv("BOOKSMITH_ROOT", DEFAULT_BOOKSMITH_ROOT))
    ap.add_argument("--product", default="audit", choices=["audit", "proof"],
                    help="audit = the whole text, never gated. proof = eight representative units.")
    ap.add_argument("--title", default=None,
                    help="cover title; overrides the one derived from the doc code")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    bs_root = Path(args.booksmith_root)
    exe = booksmith_exe(bs_root)
    home = bs_root / "projects"

    if args.selftest:
        log("%s selftest" % MARK)
        log("  booksmith    : %s" % exe)
        log("  projects home: %s  (exists=%s)" % (home, home.exists()))
        log("  export_html  : %s  (exists=%s)"
            % (HERE / "export_html.py", (HERE / "export_html.py").exists()))
        run([exe, "--help"])
        existing = sorted(p.name for p in home.glob("*") if (p / "book.yaml").exists())
        log("  %d existing project(s): %s" % (len(existing), ", ".join(existing) or "none"))
        log("  selftest OK")
        return 0

    if not args.doc:
        raise SystemExit("--doc is required unless --selftest")
    doc = args.doc
    slug = slug_for(doc, args.mode)
    if not SLUG_RE.fullmatch(slug):
        raise SystemExit("doc %r does not reduce to a legal project id (got %r)" % (doc, slug))

    exports = (ROOT / args.exports) if not os.path.isabs(args.exports) else Path(args.exports)
    exports.mkdir(parents=True, exist_ok=True)
    project = home / slug
    sidecar_dir = exports / "booksmith"
    sidecar_dir.mkdir(parents=True, exist_ok=True)
    # LIBRARY_MODES_2026_09_13 - one sidecar per witness, not per doc code.
    # slug_for() suffixes en and hi and leaves tri bare; the sidecar follows
    # the same rule, so a Hindi build can no longer overwrite the trilingual
    # card's account of itself. Every sidecar written before today is
    # trilingual and keeps resolving under its bare name.
    sidecar = sidecar_dir / (("%s.json" % doc) if args.mode == "tri"
                             else ("%s__%s.json" % (doc, args.mode)))

    state = {"marker": MARK, "doc": doc, "slug": slug, "mode": args.mode,
             "product": args.product, "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             "ok": False}

    def save() -> None:
        sidecar.write_text(json.dumps(state, indent=2), encoding="utf-8")

    try:
        log("%s  doc=%s slug=%s mode=%s" % (MARK, doc, slug, args.mode))

        log("[1/6] export HTML")
        html = export_html(args.db, doc, args.mode, exports)
        state["html"] = str(html)
        log("      witness: %s" % html)
        save()

        created = not (project / "book.yaml").exists()
        if created:
            log("[2/6] init project (new)")
            run([exe, "--home", home, "init", slug,
                 "--title", title_for(doc, args.title)])
            set_audit_policy(exe, project, MODE_FLAGS[args.mode][2])
        elif _half_created(project, args.mode):
            # BOOKSMITH_UTF8_2026_09_13 - init landed, the policy did not.
            # Without this branch the project keeps Booksmith's init defaults
            # for ever, because the else branch below deliberately never
            # touches an existing book.yaml.
            log("[2/6] project exists but its policy was never applied "
                "- applying it now")
            set_audit_policy(exe, project, MODE_FLAGS[args.mode][2])
            state["policy_repaired"] = True
        else:
            log("[2/6] project exists - its book.yaml is left exactly as it is")
        state["project"] = str(project)
        state["created"] = created

        # BOOKSMITH_MODES_2026_09_13 - never ingest a different witness into a
        # project that is frozen against the old one. That is what killed the
        # nilamata Hindi run.
        action, detail = prepare_existing(project, html)
        state["witness"] = action
        state["witness_detail"] = detail
        log("      witness: %s - %s" % (action, detail))
        if action == "refuse":
            raise RuntimeError("refusing to re-ingest: " + detail)
        save()

        log("[3/6] ingest")
        run([exe, "--home", home, "ingest", slug, str(html)])

        log("[4/6] audit")
        run([exe, "--home", home, "audit", slug])
        errs, total = count_audit_errors(project)
        state["audit_errors"] = errs
        state["audit_findings"] = total
        log("      %d finding(s), %d at error level" % (total, errs))
        save()

        pdf = None
        if args.product == "audit":
            log("[5/6] build")
            p = run([exe, "--home", home, "build", slug], check=False)
            if p.returncode == 0:
                pdf = project / "build" / "book.pdf"
                state["blocked"] = False
            else:
                blockers = (p.stderr or "").strip().splitlines()[-1:] or ["build failed"]
                state["blocked"] = True
                state["blockers"] = blockers
                log("      build refused - falling back to the layout proof")
                log("      %s" % blockers[0][:300])
                # check=False: when the proof ALSO fails, a raised RuntimeError
                # replaced the informative build error with "command failed (1)"
                # in the sidecar. Record both and let the caller see the real
                # reason.
                q = run([exe, "--home", home, "proof", slug], check=False)
                if q.returncode != 0:
                    tail = (q.stderr or "").strip().splitlines()[-1:] or ["proof failed"]
                    state["proof_blockers"] = tail
                    save()
                    raise RuntimeError("build and proof both refused. build: %s | proof: %s"
                                       % (blockers[0][:200], tail[0][:200]))
                pdf = project / "build" / "layout-proof.pdf"
        else:
            log("[5/6] proof")
            run([exe, "--home", home, "proof", slug])
            pdf = project / "build" / "layout-proof.pdf"
            state["blocked"] = False

        if not pdf or not pdf.exists():
            raise RuntimeError("no PDF at %s" % pdf)
        state["pdf"] = str(pdf)
        state["pdf_bytes"] = pdf.stat().st_size
        state["pdf_kind"] = pdf.name
        save()

        if pdf.name == "book.pdf":
            log("[6/6] qa")
            run([exe, "--home", home, "qa", slug], check=False)
            br = project / "build" / "build-report.json"
            if br.exists():
                try:
                    rep = json.loads(br.read_text(encoding="utf-8"))
                    state["pages"] = rep.get("page_count")
                    state["pdf_sha256"] = rep.get("pdf_sha256")
                    state["release_identity"] = rep.get("release_identity")
                    state["source_units"] = rep.get("source_units")
                except Exception:
                    pass
        else:
            log("[6/6] qa skipped - a layout proof is a sample, not a release")

        state["ok"] = True
        state["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        save()
        log("DONE  %s  (%s, %s bytes)" % (pdf, state.get("pdf_kind"), state.get("pdf_bytes")))
        return 0

    except Exception as e:
        state["error"] = "%s: %s" % (type(e).__name__, e)
        state["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        save()
        log("FAILED  %s" % state["error"])
        return 1


if __name__ == "__main__":
    sys.exit(main())
