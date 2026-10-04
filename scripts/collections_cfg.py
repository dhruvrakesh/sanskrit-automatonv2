#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
collections_cfg.py  (2026-10-04)  COLLECTIONS_2026_10_04

Shelves for the library: every text belongs to ONE collection (a header such as
"Vedas" or "Smrtis"), in a set order, optionally as a numbered member of a
series ("Harita Samhita, Sthana 3").

The truth is a human-editable file, configs/collections.json. This module
  * proposes a first draft from rules over the doc codes and docs.category
    (--draft writes it; it never overwrites an existing file without --force);
  * resolves membership for the Shelf page: the file when it exists, else the
    rules (and the page then says "draft");
  * moves one text to another collection (used by the Shelf page), with a backup.

Display titles stay in configs/doc_titles.json (DOC_TITLES_2026_09_27): a title is
shown only when a person has confirmed it; otherwise a title derived from the code
is shown and marked as such.

  python scripts\\collections_cfg.py --show
  python scripts\\collections_cfg.py --draft            # writes configs\\collections.json if absent
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import sqlite3
import sys
from pathlib import Path

MARK = "COLLECTIONS_2026_10_04"
ROOT = Path(__file__).resolve().parent.parent
CFG = ROOT / "configs" / "collections.json"
TITLES = ROOT / "configs" / "doc_titles.json"

# key, title (IAST), Devanagari title, order, rules: (regex on code, regex on category)
COLLECTIONS = [
    ("veda", "Vedas", "\u0935\u0947\u0926\u093e\u0903", 10,
     [r"rgveda|rig_?veda|yajur_veda|sama_veda|atharva", r"^veda$"]),
    ("brahmana", "Br\u0101hma\u1e47as and \u0100ra\u1e47yakas", "\u092c\u094d\u0930\u093e\u0939\u094d\u092e\u0923\u093e\u0930\u0923\u094d\u092f\u0915\u093e\u0928\u093f", 20,
     [r"brahmanam|brahmana|aranyaka", r"^(brahmana|aranyaka)$"]),
    ("vedanga", "Ved\u0101\u1e45gas", "\u0935\u0947\u0926\u093e\u0919\u094d\u0917\u093e\u0928\u093f", 30,
     [r"^nirukta|^shiksha_", r"^vedanga$"]),
    ("itihasa", "Itih\u0101sa", "\u0907\u0924\u093f\u0939\u093e\u0938\u0903", 40, [r"^MBh\d|mahabharata|ramayana", r"^itihasa$"]),
    ("upapurana", "Upapur\u0101\u1e47as", "\u0909\u092a\u092a\u0941\u0930\u093e\u0923\u093e\u0928\u093f", 60,
     [r"^upapurana_|^nilamata", r"^upapurana$"]),
    ("purana", "Pur\u0101\u1e47as", "\u092a\u0941\u0930\u093e\u0923\u093e\u0928\u093f", 50,
     [r"^markandeya|mallapurana|padma_puran|_purana$", r"^purana$"]),
    ("smrti", "Sm\u1e5btis and Dharmas\u016btras", "\u0938\u094d\u092e\u0943\u0924\u092f\u0903", 70,
     [r"^smriti_|^bodhyana|dharmasutra", r"^(smriti|dharmasutra)$"]),
    ("agama", "\u0100gama and Tantra", "\u0906\u0917\u092e\u0924\u0928\u094d\u0924\u094d\u0930\u093e\u0923\u093f", 80,
     [r"aagama|agama|tantra|tantric|pancaratra", r"^(agama|tantra)$"]),
    ("jyotisa", "Jyoti\u1e63a and Ga\u1e47ita", "\u091c\u094d\u092f\u094b\u0924\u093f\u0937\u092e\u094d", 90,
     [r"jyotish|siddhanta|ganita", r"^jyotish$"]),
    ("ayurveda", "\u0100yurveda", "\u0906\u092f\u0941\u0930\u094d\u0935\u0947\u0926\u0903", 100, [r"^harita_.*sthanam|samhita_ayur", r"^ayurveda$"]),
    ("dhanurveda", "Dhanurveda", "\u0927\u0928\u0941\u0930\u094d\u0935\u0947\u0926\u0903", 110, [r"dhanur_veda", r"^dhanur_veda$"]),
    ("natya", "N\u0101\u1e6dya and G\u0101ndharva", "\u0928\u093e\u091f\u094d\u092f\u0936\u093e\u0938\u094d\u0924\u094d\u0930\u092e\u094d", 120,
     [r"natya|gandharva", r"^natya$"]),
    ("bhakti", "Bhakti and Dar\u015bana", "\u092d\u0915\u094d\u0924\u093f\u0903", 130, [r"sandilya|bhakti|sutra", r"^(bhakti|darshana)$"]),
    ("bauddha", "Bauddha", "\u092c\u094c\u0926\u094d\u0927\u092e\u094d", 140, [r"lalitavistara|bodhicarya", r"^bauddha$"]),
]
OTHER = ("other", "Other texts", "", 999)

# Series: (collection key, series title, regex with an ordering group, ordering map or None)
SERIES = [
    ("ayurveda", "H\u0101r\u012bta Sa\u1e43hit\u0101", r"^harita_(prathama|dvitiya|tritiya|caturtha|pancamam|shashtham)",
     {"prathama": 1, "dvitiya": 2, "tritiya": 3, "caturtha": 4, "pancamam": 5, "shashtham": 6}),
    ("smrti", "Eighteen Sm\u1e5btis", r"^smriti_(\d{2})", None),
    ("vedanga", "\u015aik\u1e63\u0101", r"^shiksha_(\w+)", None),
]

SCAN_ID = re.compile(r"^(?:\d{4}[_\-]\d{3,}[_\-]?)+|^SP_\d+_|^\d+-")
SUFFIX = re.compile(r"[ _-](seg|segmented|ocr|raw|clean|v\d+)$", re.I)


def derived_title(code: str) -> str:
    """A readable title from a code - shown as 'derived', never stored."""
    t = SCAN_ID.sub("", code or "")
    t = re.sub(r"^(upapurana|smriti|shiksha|jyotish|dhanur_veda)_(\d{2})?", "", t)
    t = t.replace("_", " ").replace("-", " ")
    t = SUFFIX.sub("", " " + t.strip()).strip()
    t = re.sub(r"\s+", " ", t)
    return " ".join(w if any(c.isupper() for c in w) else w.capitalize() for w in t.split()) or code


def load_titles(path: Path = TITLES) -> dict:
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        return d.get("titles", {}) if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def rule_collection(code: str, category: str | None) -> str:
    for key, _t, _s, _o, (code_rx, cat_rx) in COLLECTIONS:
        if re.search(code_rx, code or "", re.I):
            return key
    for key, _t, _s, _o, (code_rx, cat_rx) in COLLECTIONS:
        if category and re.search(cat_rx, category, re.I):
            return key
    return OTHER[0]


def series_of(code: str):
    for ckey, stitle, rx, order in SERIES:
        m = re.search(rx, code or "", re.I)
        if m:
            g = m.group(1).lower()
            n = order.get(g) if order else (int(g) if g.isdigit() else None)
            return {"title": stitle, "number": n}
    return None


def draft(docs: list[tuple]) -> dict:
    """docs: [(code, category)] -> the collections.json structure."""
    cols = {k: {"key": k, "title": t, "title_sa": s, "order": o, "members": []}
            for k, t, s, o, _ in COLLECTIONS}
    cols[OTHER[0]] = {"key": OTHER[0], "title": OTHER[1], "title_sa": OTHER[2], "order": OTHER[3], "members": []}
    for code, cat in docs:
        cols[rule_collection(code, cat)]["members"].append(code)
    for c in cols.values():
        def k(code):
            s = series_of(code)
            return (s["title"] if s else "~", s["number"] if s and s["number"] is not None else 9999, code.lower())
        c["members"].sort(key=k)
    return {"_about": "Shelves for the library (%s). Edit freely: order, titles, members. A text listed in no "
                      "collection is shown under 'Other texts'. Written by collections_cfg.py --draft on %s; "
                      "the Shelf page's 'move to' writes here too, with a backup." % (MARK, datetime.date.today()),
            "collections": sorted(cols.values(), key=lambda c: c["order"])}


def load_cfg(path: Path = CFG):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def resolve(docs: list[tuple], path: Path = CFG) -> tuple[list[dict], bool]:
    """(collections with members in order, from_file). Docs missing from the file go to Other."""
    cfg = load_cfg(path)
    from_file = bool(cfg and cfg.get("collections"))
    if not from_file:
        cfg = draft(docs)
    codes = {c for c, _ in docs}
    seen, out = set(), []
    for c in sorted(cfg["collections"], key=lambda c: c.get("order", 500)):
        mem = [m for m in c.get("members", []) if m in codes and m not in seen]
        seen.update(mem)
        out.append({"key": c["key"], "title": c.get("title") or c["key"], "title_sa": c.get("title_sa", ""),
                    "order": c.get("order", 500), "members": mem})
    rest = sorted(codes - seen, key=str.lower)
    if rest:
        other = next((c for c in out if c["key"] == OTHER[0]), None)
        if other is None:
            other = {"key": OTHER[0], "title": OTHER[1], "title_sa": "", "order": OTHER[3], "members": []}
            out.append(other)
        other["members"] += rest
    return [c for c in out if c["members"]], from_file


def move(code: str, key: str, docs: list[tuple], path: Path = CFG) -> dict:
    """Put `code` in collection `key` (creating the file from the draft if absent). Backup first."""
    cfg = load_cfg(path)
    if not (cfg and cfg.get("collections")):
        cfg = draft(docs)
    keys = {c["key"] for c in cfg["collections"]}
    if key not in keys:
        raise ValueError("unknown collection %r" % key)
    for c in cfg["collections"]:
        c["members"] = [m for m in c.get("members", []) if m != code]
        if c["key"] == key:
            c["members"].append(code)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        shutil.copy2(path, path.with_name(path.name + ".bak_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")))
    t = path.with_name(path.name + ".tmp")
    t.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(t, path)
    return cfg


def set_title(code: str, title: str, title_sa: str = "", path: Path = TITLES) -> dict:
    """A person-confirmed display title into doc_titles.json (DOC_TITLES_2026_09_27), with a backup."""
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {"_about": "Human-confirmed display titles for doc codes.", "_sources": {}, "titles": {}}
    d.setdefault("titles", {}); d.setdefault("_sources", {})
    if title.strip():
        d["titles"][code] = title.strip()
        d["_sources"][code] = "confirmed in the Shelf page (%s) on %s" % (MARK, datetime.date.today())
    if title_sa.strip():
        d.setdefault("titles_sa", {})[code] = title_sa.strip()
    if path.exists():
        shutil.copy2(path, path.with_name(path.name + ".bak_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")))
    t = path.with_name(path.name + ".tmp")
    t.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(t, path)
    return d


def live_docs(db: str) -> list[tuple]:
    con = sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True)
    try:
        con.execute("PRAGMA query_only=1")
        try:
            retired = {r[0] for r in con.execute("SELECT doc_code FROM doc_stage WHERE stage='retired'")}
        except sqlite3.Error:
            retired = set()
        return [(c, cat) for c, cat in con.execute("SELECT code, category FROM docs ORDER BY code")
                if c not in retired and not c.endswith("-RETIRED")]
    finally:
        con.close()


def main() -> int:
    ap = argparse.ArgumentParser(description="Library collections (shelves)")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--draft", action="store_true", help="write configs/collections.json from the rules")
    ap.add_argument("--force", action="store_true", help="with --draft: replace an existing file (backed up)")
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args()
    docs = live_docs(args.db)
    if args.draft:
        if CFG.exists() and not args.force:
            print("REFUSING: %s exists (edit it, or pass --force; a backup is kept)." % CFG); return 1
        if CFG.exists():
            shutil.copy2(CFG, CFG.with_name(CFG.name + ".bak_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")))
        CFG.parent.mkdir(parents=True, exist_ok=True)
        CFG.write_text(json.dumps(draft(docs), ensure_ascii=False, indent=1), encoding="utf-8")
        print("wrote %s" % CFG)
    cols, from_file = resolve(docs)
    titles = load_titles()
    print("%s  %d texts in %d collections (%s)" % (MARK, len(docs), len(cols), "file" if from_file else "rules draft"))
    for c in cols:
        print("\n== %s %s" % (c["title"], ("(" + c["title_sa"] + ")") if c["title_sa"] else ""))
        for m in c["members"]:
            s = series_of(m)
            print("   %-48s %s%s" % (m[:48], titles.get(m) or derived_title(m) + "  [derived]",
                                    ("   - %s %s" % (s["title"], s["number"] or "")) if s else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
