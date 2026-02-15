#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Build a Sanskrit gazetteer focused on tribes, clans, and geographies.

Sources:
- Seed JSONL you provide (type, surface, aliases).
- Optional live scraping from the Cologne Sanskrit Lexicon (Monier-Williams) and
  Sanskrit Heritage dictionary to harvest proper names and geo entities.

⚠️ Respect robots.txt and site terms. This script is rate-limited and best used
   against a local dump or offline export if possible.

Outputs:
- JSONL gazetteer at --out
- GraphML at --graphml (for Neo4j/Gephi import) [optional]

Example:
  python scripts/build_gazetteer.py --seed data/seeds/seed_tribes_regions.jsonl --out data/processed/gazetteer.jsonl --graphml data/processed/gazetteer.graphml
"""
import json, argparse, time, re
from typing import Dict, Any, Iterable, List
from pathlib import Path

import requests
from bs4 import BeautifulSoup
import networkx as nx

MW_BASE = "https://www.sanskrit-lexicon.uni-koeln.de/scans/MWScan/2020/web/webtc/servepdf.php?dict=MW&key={key}"
HEADWORD_RX = re.compile(r"^[A-Za-zāīūṛṝṅñṭḍṇśṣḥ\-]+$")

def load_seed(path: str) -> List[Dict[str, Any]]:
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            items.append(json.loads(line))
    return items

def scrape_mw_entry(key: str) -> Dict[str, Any]:
    # Heuristic: fetch HTML view via alternate endpoint; MW pages vary.
    # We try a simpler query page if available.
    url = f"https://www.sanskrit-lexicon.uni-koeln.de/scans/MWScan/2020/web/webtc/indexcaller.php?key={key}&input=slp1&output=deva"
    r = requests.get(url, timeout=20)
    if r.status_code != 200:
        return {"key": key, "ok": False}
    soup = BeautifulSoup(r.text, "lxml")
    # MW displays HTML blocks with gloss; look for "lex" class or content area
    gloss = " ".join(x.get_text(" ", strip=True) for x in soup.select(".disp, .entry, .lex") or soup.select("body"))
    gloss = re.sub(r"\s+", " ", gloss)
    # Crude type heuristics
    t = None
    if re.search(r"\btribe\b|\bpeople\b|\bnation\b", gloss, flags=re.I):
        t = "TRIBE"
    elif re.search(r"\bcity\b|\btown\b|\bcapital\b|\bkingdom\b", gloss, flags=re.I):
        t = "LOC"
    elif re.search(r"\briver\b|\bnad[iī]\b", gloss, flags=re.I):
        t = "RIVER"
    elif re.search(r"\bmountain\b|\bparvata\b", gloss, flags=re.I):
        t = "MOUNTAIN"
    return {"key": key, "ok": True, "gloss": gloss, "type_guess": t}

def harvest_from_mw(keys: Iterable[str], delay=1.2) -> List[Dict[str, Any]]:
    rows = []
    for k in keys:
        try:
            row = scrape_mw_entry(k)
            row["source"] = "MW"
            rows.append(row)
        except Exception as e:
            rows.append({"key": k, "ok": False, "error": str(e), "source": "MW"})
        time.sleep(delay)
    return rows

def to_graphml(entries: List[Dict[str, Any]], path: str):
    G = nx.Graph()
    for e in entries:
        key = e.get("surface") or e.get("key")
        if not key: 
            continue
        G.add_node(key, **{k:v for k,v in e.items() if k not in ("aliases","links")})
        for a in e.get("aliases", []):
            G.add_node(a, alias=True, surface=a)
            G.add_edge(key, a, kind="alias_of")
    nx.write_graphml(G, path)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", required=True, help="Seed JSONL with surface/type/aliases")
    ap.add_argument("--out", required=True, help="Output gazetteer JSONL")
    ap.add_argument("--graphml", default=None, help="Optional GraphML output")
    ap.add_argument("--mw-headwords", default=None, help="Optional file with MW headwords (SLP1 or Devanagari) to harvest")
    args = ap.parse_args()

    seed = load_seed(args.seed)
    base = []
    for s in seed:
        base.append({
            "surface": s["surface"],
            "type": s.get("type", "UNKNOWN"),
            "aliases": s.get("aliases", []),
            "source": "SEED",
            "notes": s.get("notes", "")
        })

    mw_rows = []
    if args.mw_headwords:
        with open(args.mw_headwords, "r", encoding="utf-8") as f:
            headwords = [ln.strip() for ln in f if ln.strip()]
        mw_rows = harvest_from_mw(headwords)

    # Merge MW guesses into base (by surface = key where possible)
    key_set = {b["surface"] for b in base}
    for r in mw_rows:
        if not r.get("ok"):
            continue
        surface = r["key"]
        if surface not in key_set:
            base.append({"surface": surface, "type": r.get("type_guess") or "UNKNOWN",
                         "aliases": [], "source": "MW", "notes": r.get("gloss","")})

    with open(args.out, "w", encoding="utf-8") as out:
        for b in base:
            out.write(json.dumps(b, ensure_ascii=False) + "\n")

    if args.graphml:
        to_graphml(base, args.graphml)

    print(f"Wrote {len(base)} gazetteer entries to {args.out}")
    if args.graphml:
        print(f"Wrote GraphML to {args.graphml}")

if __name__ == "__main__":
    main()
