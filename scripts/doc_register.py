#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
doc_register.py  (2026-10-22)  DOC_REGISTER_2026_10_22

The ENTERPRISE_PATH's tables, read as one register. Every addendum ends with a table of items (| # | Item | State |),
and the short labels in its first column are reused: on 22 Oct, 77 of the 200 labels named different items in
different addenda (S1 named eight things, T2 fourteen), so "the latest state of S1" means nothing. This reads every
row, groups them by item (the label together with the first words of the item, so a reused label stays apart), and
keeps each item's last state and the date of the addendum that last recorded it. Free and read-only.

  python scripts\\doc_register.py                       the summary; exports\\ep_register.csv
  python scripts\\doc_register.py --open --before 2026-10-15   the items still open, last recorded before that date

"Open" is read from the state's first words (not Done, Applied, Live, Released, Fixed, Built, Mended, Decided ...):
a hint for a person to verify, not a verdict. docs/ASKS_2026-10-22.md is the register a person keeps; this is its
check.
"""
from __future__ import annotations
import argparse, collections, csv, re, sys
from pathlib import Path

MARK = "DOC_REGISTER_2026_10_22"
ROOT = Path(__file__).resolve().parent.parent
# a short label (S1, T2b) or, from DOCS88 on, a key of docs/ASKS_2026-10-22.md (nirukta-text): stable, never reused
ROW = re.compile(r"^\|\s*([A-Z][A-Za-z]?\d+[a-z]?|[a-z][a-z0-9]*(?:-[a-z0-9]+)+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$")
DONE = re.compile(r"(?i)^(\*\*)?(done|applied|live|released|fixed|built and tested|built|mended|closed|decided|"
                  r"confirmed|complete|explained|corrected|made|guarded|withdrawn|all in|superseded)\b")


def key_of(label: str, item: str) -> str:
    words = re.sub(r"[^a-z ]", " ", item.lower()).split()
    words = [w for w in words if w not in ("the", "a", "an", "of", "s")]
    return label + ":" + " ".join(words[:2])


def read(path: Path) -> list:
    rows, section, date = [], "", ""
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^## (.*)", line)
        if m:
            section = m.group(1).strip()
            d = re.search(r"(20\d\d-\d\d-\d\d)", section)
            date = d.group(1) if d else date
            continue
        m = ROW.match(line)
        if m and m.group(1) != "#":
            rows.append({"label": m.group(1), "item": m.group(2), "state": m.group(3), "section": section,
                         "date": date})
    return rows


def register(rows: list) -> dict:
    items = collections.OrderedDict()
    for r in rows:
        k = key_of(r["label"], r["item"])
        it = items.setdefault(k, {"label": r["label"], "item": r["item"], "first": r["date"], "times": 0})
        it.update(item=r["item"], state=r["state"], last=r["date"], section=r["section"])
        it["times"] += 1
    for it in items.values():
        it["open"] = not DONE.search(it["state"].strip())
    return items


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="the ENTERPRISE_PATH's tables as one register (read-only)")
    ap.add_argument("--root", default="")
    ap.add_argument("--open", action="store_true", help="list the items whose last state reads as open")
    ap.add_argument("--before", default="", help="with --open: only those last recorded before YYYY-MM-DD")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    root = Path(a.root).resolve() if a.root else ROOT
    eps = sorted((root / "docs").glob("ENTERPRISE_PATH_*.md"))
    eps = [p for p in eps if not re.search(r"\.bak_|\.tmp", p.name)]
    if not eps:
        print("%s: no docs\\ENTERPRISE_PATH_*.md" % MARK)
        return 1
    rows = []
    for p in eps:
        rows += read(p)
    items = register(rows)
    labels = collections.defaultdict(set)
    for k, it in items.items():
        labels[it["label"]].add(k)
    reused = {l: ks for l, ks in labels.items() if len(ks) > 1}
    open_items = [it for it in items.values() if it["open"]]
    print("%s: %d rows in %s; %d items under %d labels; %d labels name more than one item" % (
        MARK, len(rows), ", ".join(p.name for p in eps), len(items), len(labels), len(reused)))
    worst = sorted(reused.items(), key=lambda kv: -len(kv[1]))[:5]
    print("  most reused: " + "; ".join("%s %d items" % (l, len(ks)) for l, ks in worst))
    print("  open by their last state: %d (last recorded: %s)" % (len(open_items), ", ".join(
        "%s %d" % (d, n) for d, n in sorted(collections.Counter(it["last"] for it in open_items).items()))))
    if a.open:
        shown = [it for it in open_items if not a.before or it["last"] < a.before]
        print()
        for it in sorted(shown, key=lambda it: (it["last"], it["label"])):
            print("  %s  %-5s %-60s | %s" % (it["last"], it["label"], it["item"][:60], it["state"][:70]))
    if not a.no_write:
        out = root / "exports"
        out.mkdir(parents=True, exist_ok=True)
        with open(out / "ep_register.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["label", "item", "state", "open", "first", "last", "times", "label_reused", "section"])
            for it in items.values():
                w.writerow([it["label"], it["item"], it["state"], "yes" if it["open"] else "", it["first"], it["last"],
                            it["times"], "yes" if it["label"] in reused else "", it["section"]])
        print("written: %s" % (out / "ep_register.csv"))
    print("VERDICT: %d items, %d open by their last state; %d labels reused (cite docs/ASKS_2026-10-22.md's keys)" % (
        len(items), len(open_items), len(reused)))
    print("NEXT: python scripts\\doc_register.py --open --before 2026-10-15   (the old ones, to verify or close)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
