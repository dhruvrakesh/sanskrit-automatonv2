#!/usr/bin/env python3
# -*- coding: ascii -*-
"""


patch_docs101_2026_10_28.py  (2026-10-28)  DOCS101_2026_10_28

The asks read again on 28 Oct, night. docs\\ASKS_2026-10-22.md gains section 14: the ask that was missing from it
(carrying Raychaudhuri forward, our correlations, the tribes as B. C. Law wrote of them), begun by PEOPLES and priced
for the rest; the Professor's cut answers (ASK_ROOM); the tags, RIGHTS_NOISE, the Karanagama, the Gandharva Veda, the
Nirukta's release (corrected) and the Padma, each with its state; the cap's order. docs\\STATE_2026-10-18.md gains
section 36; RUNBOOK.md the commands of 28 Oct, night. tests\\test_docs100_2026_10_28.py reads section 13 up to
section 14 (its count of the week's asks was reading on into section 14's).

Needs DOCS100_2026_10_28 in the four files; requires scripts\\peoples_index.py, the ASK_ROOM and CLAIMS_PART2
patchers, docs\\PEOPLES_2026-10-28.md and docs\\cloud\\CHECKS_night_2026-10-28.sql. Anchored, all-or-nothing,
marker-idempotent; line endings kept; .bak_docs101_<date> copies.

  python scripts\\patch_docs101_2026_10_28.py --check
  python scripts\\patch_docs101_2026_10_28.py
  python scripts\\docs_map.py --write
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS101_2026_10_28'
TAG = 'docs101'
FILES = ['docs/ASKS_2026-10-22.md', 'docs/STATE_2026-10-18.md', 'RUNBOOK.md', 'tests/test_docs100_2026_10_28.py']
NEEDS = {'docs/ASKS_2026-10-22.md': 'DOCS100_2026_10_28', 'docs/STATE_2026-10-18.md': 'DOCS100_2026_10_28', 'RUNBOOK.md': 'DOCS100_2026_10_28', 'tests/test_docs100_2026_10_28.py': 'DOCS100_2026_10_28'}
REQUIRES = {'scripts/peoples_index.py': 'PEOPLES_2026_10_28', 'scripts/patch_ask_room_2026_10_28.py': 'ASK_ROOM_2026_10_28', 'scripts/patch_claims_part2_2026_10_28.py': 'CLAIMS_PART2_2026_10_28', 'docs/PEOPLES_2026-10-28.md': 'PEOPLES_2026_10_28', 'docs/cloud/CHECKS_night_2026-10-28.sql': 'DOCS101_2026_10_28'}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/ASKS_2026-10-22.md', 1, "measured A/B of the working English's thinking budget, built before any change), muktabodha (Yours: the letter),\nproxy-limit (Next: gdrive-image-proxy to images and a size).\n",
     'measured A/B of the working English\'s thinking budget, built before any change), muktabodha (Yours: the letter),\nproxy-limit (Next: gdrive-image-proxy to images and a size).\n## 14. 28 Oct, night: the asks read again; the peoples of the lists; the Professor\'s room (DOCS101_2026_10_28)\n\nRead on 28 Oct, night, from these sources:\n\n- the backup of 17:48 IST (`D:\\backups\\context_pre_witness_gandharva_veda_natya_shastra__w_gretil_20261028_174808.db`,\n  read-only and immutable);\n- the mirror\'s log (the tick of 18:33), `data\\mark_passages_log.jsonl`, `data\\shelf\\claims.db`, `data\\text_path.json`\n  (17:48) and usage_log;\n- the checks you pasted (R1 and R3 at 17:50, before that tick).\n\n**Done in full? No.**\n\nOne ask was missing from this register: "original ideas/correlations from additional translations, carrying forward\nRaychaudhuri\'s work and correlating it with the tribes of ancient India by B. C. Law" (recalled on 28 Oct). Neither\nthis register nor the session\'s record keeps its first wording, so its date is not given.\n\nIts nearest records:\n\n- professor-bot (21 Oct: "relations, the known synchronisms rebuilt, then hypotheses");\n- "our own correlations" (25 Oct, section 12);\n- the copyrighted scholars as private reading (BRAIN_PATH section 2).\n\nIt is now begun, not done.\n\n| Date | Ask | Done (the evidence) | Left (its state) |\n|---|---|---|---|\n| (recalled 28 Oct) | Carry Raychaudhuri forward; our own correlations; the tribes, as B. C. Law wrote of them | PEOPLES (built, free): the 289 peoples of the Puranas\' lists of the lands, as Dikshitar\'s Purana Index cites them. Read in GRETIL\'s verses (Matsya 109 of 115, Brahmanda 131 of 144, Visnu 19 of 20), with each people\'s region as the text words it: the two Puranas agree on 47 of the 50 both place. 39 of them stand side by side with Raychaudhuri\'s Part I (371 claims), and his p. 44 citing the Matsya\'s *daksinapathavasinah* is borne out by its verses. Written up in docs\\PEOPLES_2026-10-28.md | Money: Part II (CLAIMS_PART2 built: about $1.94, up to about $3.10); the hypotheses (professor-bot, G2: about $2 to $3). Yours: B. C. Law\'s *Tribes in Ancient India* as private reading, from a copy you hold lawfully (in copyright in India to the end of 2029). Next: the Carmichael Lectures, Jayaswal\'s *Hindu Polity*, and the other lists (the Bhismaparvan, the Brhatsamhita, Panini) |\n| 28 Oct | The Professor\'s answer cut short ("genealogy of janamjeya ans parshurama") | Found: gemini-2.5-flash counts its thinking inside the limit. The last two answers used 3,068 of 3,072 tokens, for 545 and 423 characters of text. ASK_ROOM built: 16,384 tokens for the Professor, and a cut answer now says so | Yours: apply it, restart the dashboard when idle, then ask again. Only a whole answer can show whether it keeps the Janamejayas apart (ASK_HOMONYM) |\n| 28 Oct | The tags | Applied (mark_passages_log: 88 of the Hayasirsa\'s, 182 of the Karanagama\'s; classify_apparatus 73). The Hayasirsa: noise 189, frontmatter 64, 1,453 to translate. The Karanagama: frontmatter 993, noise 5, 755 to translate | Done |\n| 28 Oct | RIGHTS_NOISE | Applied. The tick of 18:33 sent the Mallapurana\'s 44, the Ganita\'s 9 and the Akasabhairava\'s 38. Your R3 at 17:50 was before it | Yours: N1 (docs\\cloud\\CHECKS_night_2026-10-28.sql) |\n| 28 Oct | The Karanagama\'s rights | Restored by you. On the site since 18:33: 1,909 passages, 1,491 translations (229 of its own matter not sent), 156 vectors | Yours: N2, N3. Money: its English and Hindi (755 passages, about $3.62 a language) |\n| 28 Oct | The Gandharva Veda | GRETIL\'s Natyasastra ingested as its witness (4,423 passages). The edition\'s own text was ingested at 16:43 (794 passages, Tesseract, no English) and has been on the site since 18:33; text_path.json (17:48) sends it to vision first | Yours: keep it on the site as Tesseract reads it, or repair it (`--repair --max-usd 4.40`; the site keeps this version until --release), or withdraw it |\n| 28 Oct | The Nirukta\'s release (a correction) | Section 13 said its English was done, which is true (647 of 648), but `repair_text.py --release` refuses until its Hindi is made, unless --force | Money: its Hindi (text_path.json: about $3.72), then --release |\n| 28 Oct | The Padma Patala | Vision has read 278 of 364 pages; the drift check found 267 changed pages to reingest now | Yours: reingest_pages.py, then --apply. The rounds: 86 pages left (about $0.77) |\n\n**The cap:** $112.44 of $135 spent, $22.56 left. The asks priced above come to about $35:\n\n| Item | Cost |\n|---|---|\n| the Hayasirsa\'s English and Hindi | about $14 |\n| the Karanagama\'s English and Hindi | $7.24 |\n| the Nirukta\'s Hindi | $3.72 |\n| Part II | up to $3.10 |\n| the hypotheses | up to $3 |\n| the Gandharva\'s vision | $4.40 |\n| the Padma | $0.77 |\n\nSo not all of them fit. What fits, if you keep the cap: Part II, the Hayasirsa\'s two languages and the Nirukta\'s Hindi\n(about $21). The rest wait for the allowance\'s days, or for you to raise the cap.\n\n**The standing asks, read again:**\n\n| Key | 28 Oct, night |\n|---|---|\n| load-ux | Not advanced |\n| cost | As above |\n| rights | B. C. Law kept private: peoples_index.py does not read him. If his claims are ever added, the Professor marks a work in copyright as private reading (ASK_ROOM), and index_sync.py sends only the public-domain works |\n| surgical | After DOCS100: 221 modules and 1,643 tests passing on the PC. This round adds 4 test modules |\n| docs-coherence | This section; docs\\PEOPLES_2026-10-28.md |\n\n**New keys (28 Oct, night):**\n\n| Key | State |\n|---|---|\n| peoples | Done: built and run |\n| claims-part2 | Money |\n| professor-hypotheses | Money, after ASK_ROOM |\n| law-tribes | Yours: a copy held lawfully |\n| vamsa-skeleton | Next. vamsa_check\'s skeleton drops an m before a stop even across a vowel, so Magadha is keyed by two consonants and looked for only by its case forms. Mending it re-checks the Vamsa page, free |\n| gandharva-site | Yours |\n| cap-order | Yours: what to spend the $22.56 on |\n')

edit('docs/STATE_2026-10-18.md', 1, "| Decisions | the Hayasirsa's release after its translation; the Karanagama's rights; the Nirukta's release; Muktabodha; the thinking A/B |\n| Next | thinking-ab; proxy-limit; load-ux measured; G3c; E2 |\n",
     "| Decisions | the Hayasirsa's release after its translation; the Karanagama's rights; the Nirukta's release; Muktabodha; the thinking A/B |\n| Next | thinking-ab; proxy-limit; load-ux measured; G3c; E2 |\n## 36. 28 Oct, night: the peoples of the lists; the Professor's room; Part II made ready (DOCS101_2026_10_28)\n\n| What | State |\n|---|---|\n| Release | `e61b052b` pushed (RIGHTS_NOISE, DOCS100). Applied by you: the tags (the Hayasirsa's noise 189 and frontmatter 64; the Karanagama's frontmatter 993 and noise 5); the Gandharva Veda's text (16:43) and its GRETIL witness (17:48, 4,423); the Karanagama restored |\n| Verified | the 17:48 backup; the mirror's tick of 18:33 (374 groups equal; the Karanagama, the Gandharva Veda and the editions' noise sent) |\n| The asks | docs\\ASKS_2026-10-22.md section 14: the Raychaudhuri and tribes ask was missing from the register; it is now begun (PEOPLES), not done |\n| Found | the Professor's answers cut by its own thinking (3,068 of 3,072 tokens); the Gandharva Veda live with Tesseract's text; the Nirukta's release needs its Hindi; the Matsya and the Brahmanda place 3 peoples differently, and the Brahmanda names Pancalas in its northern list; vamsa_check's skeleton keys Magadha by two consonants |\n| Built | ASK_ROOM_2026_10_28 (dashboard.py), CLAIMS_PART2_2026_10_28 (scholar_claims.py), PEOPLES_2026_10_28 (scripts\\peoples_index.py, docs\\PEOPLES_2026-10-28.md), docs\\cloud\\CHECKS_night_2026-10-28.sql, DOCS101 |\n| To do | the three patchers, docs_map.py --write, run_tests; the dashboard restarted idle; the Professor asked again; peoples_index.py --yes; N1 to N4 |\n| Decisions | the cap's order ($22.56 left, about $35 asked); the Gandharva Veda on the site; B. C. Law's copy |\n| Next | Part II (Money); the hypotheses (Money); vamsa-skeleton; thinking-ab; proxy-limit; load-ux |\n")

edit('RUNBOOK.md', 1, "5. After the next mirror tick: R3 of docs\\cloud\\CHECKS_rights_2026-10-28.sql (RIGHTS_NOISE: the listed editions'\n   noise withheld too: the Ganita's 9, the Mallapurana's 44, the Akasabhairava's 38), and R1 again.\n",
     '5. After the next mirror tick: R3 of docs\\cloud\\CHECKS_rights_2026-10-28.sql (RIGHTS_NOISE: the listed editions\'\n   noise withheld too: the Ganita\'s 9, the Mallapurana\'s 44, the Akasabhairava\'s 38), and R1 again.\n## 28 Oct, night: the Professor\'s room, Raychaudhuri\'s Part II, the peoples of the lists (DOCS101_2026_10_28)\n\ndocs\\ASKS_2026-10-22.md, section 14, and docs\\PEOPLES_2026-10-28.md. From the repository root:\n\n1. `python scripts\\patch_ask_room_2026_10_28.py --check`, then without --check; the same for\n   `patch_claims_part2_2026_10_28.py` and `patch_docs101_2026_10_28.py`. Then `python scripts\\docs_map.py --write` and\n   `powershell -ExecutionPolicy Bypass -File scripts\\run_tests.ps1`.\n2. Restart the dashboard when it is idle (ASK_ROOM loads). Ask the Professor again on http://127.0.0.1:5057/ask:\n   "give me a brief story about the genealogy of Janamejaya and Parasurama". usage_log\'s last ask_prof row shows its\n   tokens; an answer cut at the limit now says so.\n3. The peoples (free): `python scripts\\peoples_index.py`, then `python scripts\\peoples_index.py --yes` (writes\n   data\\shelf\\peoples_index.json and .csv), and `python scripts\\peoples_index.py --name Kekaya`.\n4. Raychaudhuri\'s Part II (Money, Google\'s cap): `python scripts\\scholar_claims.py --part 2` (the plan, free; 216 pages,\n   about $1.94); then `python scripts\\scholar_claims.py --part 2 --yes --max-usd 3.50`; `python scripts\\scholar_claims.py\n   --reparse` if a page failed; `python scripts\\scholar_claims.py --link`; `python scripts\\peoples_index.py --yes`. The\n   next index tick sends the new claims to the site.\n5. After the 18:33 tick: N1 to N4 of docs\\cloud\\CHECKS_night_2026-10-28.sql, one query per paste.\n6. Within the cap ($22.56 left): the Hayasirsa\'s English and Hindi\n   (`python scripts\\repair_auto.py --allow-translate HAYASHIRSHA_PANCARATRA --usd 15.00`); the Nirukta\'s Hindi (Add\n   Hindi in the Library), then `python scripts\\repair_text.py --doc nirukta__w_gretil --release`. The Padma Patala:\n   `python scripts\\reingest_pages.py --doc SP_4214_Pataal_Khanda_from_Padma_Puran_1895_-_Sri_Venkateshwar_Press`, then\n   the same with `--apply`.\n')

edit('tests/test_docs100_2026_10_28.py', 1, '        s = REG.read_text(encoding="utf-8")\n        sec = s[s.index("## 13. 25 to 28 Oct"):]\n        flat = " ".join(sec.split())\n        for k in ("Done in full? No.", "9 are done and 6 are partly done", "load-ux", "hayasirsa-apparatus",',
     '        s = REG.read_text(encoding="utf-8")\n        sec = s[s.index("## 13. 25 to 28 Oct"):]\n        sec = sec.split("\\n## 14. ", 1)[0]   # DOCS101_2026_10_28: section 13 only (section 14 has its own asks)\n        flat = " ".join(sec.split())\n        for k in ("Done in full? No.", "9 are done and 6 are partly done", "load-ux", "hayasirsa-apparatus",')


def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    for f, m in REQUIRES.items():
        if not Path(f).exists() or m.encode() not in Path(f).read_bytes():
            print("REFUSE: %s does not carry %s (apply it first). Nothing written." % (f, m)); return 1
    plan = {}
    for f in FILES:
        p = Path(f)
        if not p.exists():
            print("REFUSE: %s is not here (run this from the repository root). Nothing written." % f); return 1
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (f, MARK)); continue
        need = NEEDS.get(f)
        if need and need.encode() not in raw:
            print("REFUSE: %s does not carry %s (apply that first). Nothing written." % (f, need)); return 1
        nl = nl_of(raw)
        text = raw.decode("utf-8").replace("\r\n", "\n")
        for ff, n, old, new in E:
            if ff != f:
                continue
            k = text.count(old)
            if k != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (f, n, k)); return 1
            text = text.replace(old, new)
        plan[f] = (text.replace("\n", "\r\n") if nl == "\r\n" else text).encode("utf-8")
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for f, data in plan.items():
        if f.endswith(".py"):
            with tempfile.TemporaryDirectory() as td:
                t = Path(td) / Path(f).name
                t.write_bytes(data)
                try:
                    py_compile.compile(str(t), cfile=str(t) + "c", doraise=True)
                except py_compile.PyCompileError as e:
                    print("FAIL: %s would not compile (%s). Nothing written." % (f, e)); return 1
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    done = []
    try:
        for f, data in plan.items():
            p = Path(f)
            shutil.copy2(p, p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp)))
            tmp = p.with_name(p.name + ".tmp_" + TAG)
            tmp.write_bytes(data)
            os.replace(tmp, p)
            done.append(f)
            print("wrote %s" % f)
    except OSError as e:
        print("FAIL while writing (%s). Restore from the .bak_%s_%s copies: %s" % (e, TAG, stamp, ", ".join(done)))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())

