#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
ocr_benchmark.py  (2026-10-22)  OCR_BENCHMARK_2026_10_22

Our readings benchmarked against the e-texts that witness them. source_fidelity.py measures one text at a time against
its witness (data/source_fidelity/<witness>__<reading>.json); this reads every such report and puts them side by side:
how far each engine's reading agrees with the e-text, text by text and over all, what each engine misreads on its
own where two readings of one print exist, what the commonest substitutions are, and how many of the witness's
units our scan lacks (the gaps the witness fills). Free and read-only: it reads the reports, exports\\source_ledger.csv
and the page folders; it opens no database and calls no API.

  python scripts\\ocr_benchmark.py                  the table, written to exports\\ocr_benchmark.csv and .json
  python scripts\\ocr_benchmark.py --no-write       the table only

What the numbers are, and are not:
  agree     the share of the witness's aksharas a reading has right (source_fidelity's agree_pct). It counts our
            misreadings AND every place where our print and the e-text's edition differ: a ceiling, not an error rate.
  own       where two readings of one print exist (vision and Tesseract, or ours and archive.org's), the aksharas
            in 100 each misreads on its own: there the other reading has the e-text's letter, so the print has it.
            This is an engine's error rate on that print; "shared" (both lack it) is the print's or the edition's.
  gaps      the witness's units, inside the span our scan covers, that our reading does not hold.
  confusions  the commonest short substitutions (e-text -> reading), summed per engine; one that two engines make
            on the same text is marked "both": more likely the print or the e-text's convention than a misreading.
A text whose only reading is Tesseract's has no "own": a vision pass of its pages would give it one (the estimate
uses the metered Gemini Flash rate of the 22 Oct pre-flight, $0.00387 a page; nothing here spends).
"""
from __future__ import annotations
import argparse, collections, csv, glob, json, os, re, sys
from pathlib import Path

MARK = "OCR_BENCHMARK_2026_10_22"
ROOT = Path(__file__).resolve().parent.parent
FLASH_PER_PAGE = 0.00387   # the Pro pilot's pre-flight, 22 Oct: Gemini Flash's metered rate a page


def engine_of(spec: str, note: str, ledger: dict) -> str:
    kind, _, name = spec.partition(":")
    if kind == "raw":
        return "tesseract"
    if kind == "vision":
        m = re.search(r"\(([a-z0-9\-]+-vision:[a-z0-9.\-]+)", note or "")
        return m.group(1) if m else "vision"
    if kind == "merged":
        return "consensus"
    if kind == "file":
        return "archive.org OCR" if name.lower().endswith("_djvu.txt") else "file"
    if kind == "db":
        e = (ledger.get(name, {}).get("engines") or "").strip()
        first = e.split(";")[0].strip()
        m = re.match(r"([A-Za-z0-9\-]+(?::[A-Za-z0-9.\-]+)?)\s+(\d+)%", first)
        if m and m.group(1) not in ("?",):
            return m.group(1)
        return "database (engine not recorded)"
    return kind


def family(engine: str) -> str:
    return ("vision" if "vision" in engine else "tesseract" if engine.startswith("tesseract") else
            "archive.org" if engine.startswith("archive.org") else "unrecorded")


def read_ledger(root: Path) -> dict:
    p = root / "exports" / "source_ledger.csv"
    if not p.exists():
        return {}
    with open(p, encoding="utf-8-sig") as f:
        return {r.get("doc", ""): r for r in csv.DictReader(f)}


def pages_of(root: Path, doc: str) -> dict:
    out = {}
    for sub in ("raw", "raw_vision", "raw_merged"):
        out[sub] = sum(1 for p in (root / "data" / sub).glob("%s_[0-9]*.jsonl" % doc)
                       if re.fullmatch(re.escape(doc) + r"_\d{3,5}\.jsonl", p.name)) if (root / "data" / sub).exists() else 0
    return out


def collect(root: Path) -> dict:
    ledger = read_ledger(root)
    rows, pairs, conf = [], [], collections.defaultdict(collections.Counter)
    seen_conf = collections.defaultdict(lambda: collections.defaultdict(set))   # (x, y) -> text -> families
    for f in sorted((root / "data" / "source_fidelity").glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        ref = d.get("ref") or ""
        wit = ref.split(":", 1)[-1]
        readings = {k: v for k, v in (d.get("readings") or {}).items()
                    if isinstance(v, dict) and v.get("agree_pct") is not None}
        sig = lambda v: (v.get("units"), v.get("found"), v.get("aksharas"), v.get("errors"))
        for spec, v in readings.items():
            eng = engine_of(spec, v.get("note", ""), ledger)
            same = [k for k, w in readings.items() if k != spec and not k.startswith("db:") and sig(w) == sig(v)]
            dup = bool(spec.startswith("db:") and same)
            if dup:   # the database holds that very reading (the Nirukta's text is Tesseract's): counted once
                eng = engine_of(same[0], readings[same[0]].get("note", ""), ledger) + " (the database's text)"
            text = spec.split(":", 1)[-1]
            if spec.startswith("file:"):   # sources\<doc>\<file>: the text is its folder
                m = re.search(r"sources[\\/]+([^\\/]+)[\\/]", text)
                text = m.group(1) if m else (wit.split("__w_")[0] or wit)
            rows.append({"report": f.name, "witness": wit, "text": text, "reading": spec[:80], "engine": eng,
                         "family": family(eng), "units": v.get("units"), "found": v.get("found"),
                         "gaps": v.get("missing_in_span") or 0, "aksharas": v.get("aksharas") or 0,
                         "agree_pct": v.get("agree_pct"), "median_pct": v.get("unit_median_pct"),
                         "ge95_pct": v.get("ge95_pct"), "lt90_pct": v.get("lt90_pct"), "at": d.get("at", ""),
                         "dup": dup})
            if dup:
                continue
            for x, y, c in v.get("confusions") or []:
                conf[family(eng)][(x, y)] += c
                seen_conf[(x, y)][wit].add(family(eng))
        for p in d.get("pairs") or []:
            a, b = p.get("a", ""), p.get("b", "")
            note_of = {k: (v.get("note", "") if isinstance(v, dict) else "") for k, v in (d.get("readings") or {}).items()}
            pairs.append({"report": f.name, "witness": wit, "a": a[:80], "b": b[:80],
                          "engine_a": engine_of(a, note_of.get(a, ""), ledger),
                          "engine_b": engine_of(b, note_of.get(b, ""), ledger),
                          "aksharas": p.get("aksharas") or 0, "own_a_per100": p.get("own_a_per100"),
                          "own_b_per100": p.get("own_b_per100"), "shared_per100": p.get("shared_per100")})
    both = {k for k, by_text in seen_conf.items() if any(len(fams) > 1 for fams in by_text.values())}
    return {"rows": rows, "pairs": pairs, "conf": conf, "both": both, "ledger": ledger}


def summary(c: dict) -> dict:
    fam = collections.defaultdict(lambda: [0, 0.0, set()])
    for r in c["rows"]:
        if r.get("dup"):
            continue
        s = fam[r["family"]]
        s[0] += r["aksharas"]
        s[1] += r["aksharas"] * (r["agree_pct"] or 0) / 100.0
        s[2].add(r["text"])
    own = collections.defaultdict(lambda: [0, 0.0])
    for p in c["pairs"]:
        for side in ("a", "b"):
            v = p["own_%s_per100" % side]
            if v is not None:
                o = own[family(p["engine_" + side])]
                o[0] += p["aksharas"]
                o[1] += p["aksharas"] * v
    return {f: {"texts": len(s[2]), "aksharas": s[0], "agree_pct": round(100.0 * s[1] / s[0], 2) if s[0] else None,
                "own_per100": round(own[f][1] / own[f][0], 2) if own.get(f) and own[f][0] else None}
            for f, s in sorted(fam.items())}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="our readings against their e-text witnesses (free, read-only)")
    ap.add_argument("--root", default="")
    ap.add_argument("--out-dir", default="", help="where the csv and json go (exports)")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):   # a pipe on Windows is cp1252: a Devanagari confusion must not stop it
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError):
            pass
    root = Path(a.root).resolve() if a.root else ROOT
    c = collect(root)
    if not c["rows"]:
        print("%s: no reports in data\\source_fidelity (python scripts\\source_fidelity.py --ref ... first)" % MARK)
        return 1
    s = summary(c)
    print("%s: %d readings of %d texts against %d witnesses" % (
        MARK, len(c["rows"]), len({r["text"] for r in c["rows"]}), len({r["witness"] for r in c["rows"]})))
    print("\n  %-34s %-34s %7s %6s %6s %6s" % ("text", "engine", "agree%", "found", "units", "gaps"))
    for r in sorted(c["rows"], key=lambda r: (r["text"], -(r["agree_pct"] or 0))):
        print("  %-34s %-34s %7.2f %6s %6s %6s" % (r["text"][:34], r["engine"][:34], r["agree_pct"], r["found"],
                                                 r["units"], r["gaps"]))
    if c["pairs"]:
        print("\n  two readings of one print (own misreadings in 100 aksharas; shared = the print's or the edition's):")
        for p in c["pairs"]:
            print("  %-34s %s %.2f | %s %.2f | shared %.2f" % (p["witness"][:34], p["engine_a"][:28], p["own_a_per100"],
                                                           p["engine_b"][:28], p["own_b_per100"], p["shared_per100"]))
    print("\n  by engine (agreement weighted by aksharas; own where a pair exists):")
    for f, v in s.items():
        print("  %-12s texts %2d  aksharas %7d  agree %6s%%  own %s" % (
            f, v["texts"], v["aksharas"], v["agree_pct"], ("%.2f in 100" % v["own_per100"]) if v["own_per100"] else "-"))
    print("\n  commonest substitutions (e-text -> reading), by engine; 'both' = two engines on one text:")
    for f, cnt in sorted(c["conf"].items()):
        print("  %-12s %s" % (f, "; ".join("%s>%s %d%s" % (x or "-", y or "-", n, " both" if (x, y) in c["both"] else "")
                                         for (x, y), n in cnt.most_common(12))))
    # texts read by Tesseract alone: what a vision pass would cost to give them a pair
    alone = []
    by_text = collections.defaultdict(set)
    for r in c["rows"]:
        by_text[r["text"]].add(r["family"])
    for t, fams in sorted(by_text.items()):
        if "vision" not in fams:
            pg = pages_of(root, t)
            if pg["raw"] and not pg["raw_vision"]:
                alone.append((t, pg["raw"], round(pg["raw"] * FLASH_PER_PAGE, 2)))
    if alone:
        print("\n  read by Tesseract alone (a vision pass gives each a pair; estimate at $%.5f a page):" % FLASH_PER_PAGE)
        for t, n, usd in alone:
            print("  %-34s %4d pages  about $%.2f" % (t[:34], n, usd))
    if not a.no_write:
        out = Path(a.out_dir) if a.out_dir else root / "exports"
        out.mkdir(parents=True, exist_ok=True)
        cols = ["text", "witness", "engine", "family", "agree_pct", "median_pct", "ge95_pct", "lt90_pct", "found",
                "units", "gaps", "aksharas", "reading", "report", "at", "dup"]
        with open(out / "ocr_benchmark.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(cols)
            for r in sorted(c["rows"], key=lambda r: (r["text"], r["engine"])):
                w.writerow([r[k] for k in cols])
        with open(out / "ocr_confusions.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["family", "etext", "reading", "count", "two_engines_on_one_text"])
            for fam_, cnt in sorted(c["conf"].items()):
                for (x, y), n in cnt.most_common(60):
                    w.writerow([fam_, x, y, n, "yes" if (x, y) in c["both"] else ""])
        (out / "ocr_benchmark.json").write_text(json.dumps(
            {"mark": MARK, "summary": s, "pairs": c["pairs"], "rows": c["rows"],
             "tesseract_alone": [{"text": t, "pages": n, "usd": u} for t, n, u in alone]},
            ensure_ascii=False, indent=1), encoding="utf-8")
        print("\nwritten: %s, ocr_confusions.csv, ocr_benchmark.json" % (out / "ocr_benchmark.csv"))
    best = max((v["agree_pct"] or 0, f) for f, v in s.items())
    print("VERDICT: %d readings measured; the best agreement by engine is %s's %.2f%%%s" % (
        len(c["rows"]), best[1], best[0],
        ("; where one print has two readings, vision misreads %.2f and Tesseract %.2f aksharas in 100 on its own" % (
            s["vision"]["own_per100"], s["tesseract"]["own_per100"]))
        if s.get("vision", {}).get("own_per100") and s.get("tesseract", {}).get("own_per100") else ""))
    print("NEXT: read the worst units of each report beside the print (data\\source_fidelity), then decide per text: "
          "adopt the witness, or repair the scan")
    return 0


if __name__ == "__main__":
    sys.exit(main())
