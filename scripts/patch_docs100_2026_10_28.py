#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_docs100_2026_10_28.py  (2026-10-28)  DOCS100_2026_10_28

The week's asks verified and recorded. docs\\ASKS_2026-10-22.md (the register of the asks) gains section 13: every ask
of 25 to 28 Oct with what was done (its evidence) and what is left (its state), the standing asks and the open keys
read again, the new keys; the register had stopped at section 12 (DOCS96 to DOCS99 wrote to STATE and the RUNBOOK
only). docs\\STATE_2026-10-18.md gains section 35; RUNBOOK.md the commands of 28 Oct, evening.

Needs DOCS95_2026_10_25 in the register and DOCS99_2026_10_28 in STATE and the RUNBOOK; requires
scripts\\tags_2026_10_28.ps1, scripts\\patch_rights_noise_2026_10_28.py and docs\\cloud\\CHECKS_rights_2026-10-28.sql (its R3).
Anchored, all-or-nothing, marker-idempotent; line endings kept; .bak_docs100_<date> copies.

  python scripts\\patch_docs100_2026_10_28.py --check
  python scripts\\patch_docs100_2026_10_28.py
  python scripts\\docs_map.py --write
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS100_2026_10_28'
TAG = 'docs100'
FILES = ['docs/ASKS_2026-10-22.md', 'docs/STATE_2026-10-18.md', 'RUNBOOK.md']
NEEDS = {'docs/ASKS_2026-10-22.md': 'DOCS95_2026_10_25', 'docs/STATE_2026-10-18.md': 'DOCS99_2026_10_28', 'RUNBOOK.md': 'DOCS99_2026_10_28'}
REQUIRES = {'scripts/tags_2026_10_28.ps1': 'TAGS_2026_10_28', 'scripts/patch_rights_noise_2026_10_28.py': 'RIGHTS_NOISE_2026_10_28', 'docs/cloud/CHECKS_rights_2026-10-28.sql': 'RIGHTS_NOISE_2026_10_28'}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/ASKS_2026-10-22.md', 1, '  or when a step would replace paid translations.\n- **"Trace the evolution of the project":** docs/EVOLUTION_2026-10-25.md, and the brain page.\n',
     '  or when a step would replace paid translations.\n- **"Trace the evolution of the project":** docs/EVOLUTION_2026-10-25.md, and the brain page.\n## 13. 25 to 28 Oct: every ask of the week, verified on 28 Oct, evening (DOCS100_2026_10_28)\n\nRead on 28 Oct from the backup of 16:51 IST (`D:\\backups\\context_pre_witness_476948-Rgveda-samhita_Vol-ii__w_gretil_20261028_165143.db`,\nread-only and immutable), the mirror\'s and the maintenance logs, the register files in `data\\` and the checks pasted\non the site (E1, R1, R2). This register had stopped at section 12: DOCS96 to DOCS99 recorded their rounds in STATE\nand the RUNBOOK but not here; this section closes that gap.\n\n**Done in full? No.** Of the 15 asks of 25 to 28 Oct below, 9 are done and 6 are partly done; what is left of each\nis named, with its state. Of the standing asks, load-ux did not advance this week.\n\n| Date | Ask | Done (the evidence) | Left (its state) |\n|---|---|---|---|\n| 25 Oct | Authoritative genealogies of the kings, read in the Sanskrit, critical editions wherever they exist | The Vamsa page; of the 7,098 citations of texts we hold, both names stand in the cited verse for 4,910 (vamsa_check); the Visnu in Pathak\'s edition, the Harivamsa and the Ramayana in GRETIL\'s; the Mahabharata by reference only | Done |\n| 25 Oct | Our own correlations beside the inferences | Our passages and the epics\' counts on each step; Raychaudhuri\'s view on each step (B2) | A commentary on a whole line (G2): Money, priced before it runs; not built |\n| 25 Oct | The repair automated, approval only to raise the limit | The rounds (AUTO_REPAIR); stalled 9 times on one text, unstuck by REPAIR_PARTIAL (the Padma Patala\'s round read 14 pages for $0.125, 138 to go, about $1.24); the cap raised to $135 by you | Running: 10 texts in the queue |\n| 25 Oct | Trace the evolution of the project | docs\\EVOLUTION_2026-10-25.md | Done |\n| 25 Oct, evening | "why isnt scholary and prose available on srangam?" | C22 and SCHOLAR_SITE: every text with a scholarly English, and its prose; S1 equals the desk (Markandeya 1,198 rows and 210 that share a sentence; Surya 433 and 70; MBh I 24; Tantrik Texts 16) | Done; 7 Surya verses stale until their English is made again |\n| 25 Oct, night | "the geneaologies of kings on a react front end and our carefully built db mirrored" | INDEX_SITE: C21, corpus-index, /corpus/genealogies; 8 tables equal at 14:33 and 16:32 | Done |\n| 28 Oct | B2, the historian\'s view of each step | C23; 1,904 claims on the site (E1: exact 1,675, close 229, citing 953, the subject tied 894, the object 613) | Done |\n| 28 Oct | X1c, a search in the scholarly English | C24; the search on /corpus and /corpus/scholarly | Done |\n| 28 Oct | "GENEALOGIES UI/UX ARE CUTTING EDGE?" | Answered: not yet | Next: G3c (a graph of a line), one person across the three indexes; G2 and G4 priced first |\n| 28 Oct | Is the Hayasirsa\'s ingestion beyond repair? | No: INLINE_MARKS applied (854 note numbers out, 0 left); its apparatus of variant readings found (141 passages typed as verse or prose) and its title pages and contents (20) | Yours: the tags (RUNBOOK, 28 Oct, evening); then its English and Hindi (about $7 each for 1,453 passages: both fit the cap); then its release |\n| 28 Oct | The Karanagama: "are you sure about this" | Read again: 33 passages of the editor\'s Hindi tagged (applied); 149 more of the edition\'s own matter found (title pages, the contents, the verse index, the bibliography, two pages of another book) | Yours: the tags; then the 1994 rights; then --restore |\n| 28 Oct | The highest-fidelity open sources | 15 open e-texts in the database (the Astadhyayi and the Rgveda padapatha added today); VEDIC_LLA (the Nirukta mended: 41 passages, 0 left); GRETIL\'s Natyasastra reads 74% of the Gandharva Veda edition\'s pages, in order | Yours: the Nirukta\'s release (its English is done); Money: the other witnesses\' English; Next: the Gandharva Veda\'s witness (free) |\n| 28 Oct | Update the project doc; the rationalised documentation | DOCS99; docs\\DOCS_MAP.md; the brain page; this section | Done with DOCS100 |\n| 28 Oct | Is local and cloud coming along well? | Yes: 368 groups equal, 0 different; the claims on the site; R1 and R2 of CHECKS_rights as expected | Done; the Hayasirsa\'s old own matter is still on the site (R1: 108 rows with words) until it is released |\n| 28 Oct | The commands ("extensive powershell and / or sql commands") | Each round ends with them, no placeholders; this round\'s are in the RUNBOOK (28 Oct, evening) | Done |\n\n**The standing asks, read again:**\n\n| Key | 28 Oct |\n|---|---|\n| load-ux | Not advanced this week: the new pages (genealogies, scholarly, search) were built, but load times and the first-visit cut P2 (waiting since 10 Oct for a check in Hindi and Tamil) were not measured or cut. Next |\n| full-review | gdrive-image-proxy read again: it fetches a file by id from drive.google.com\'s public view link, with no credentials, so only a file already shared publicly can pass through it; any content type, no size limit, any origin. A smaller risk than recorded on 22 Oct, still open: limit it to images and a size (Next) |\n| cost | The cap $135 (raised by you), $112.06 spent, $22.94 left; the Claude credit $0.915, to 11 Nov |\n| rights | RIGHTS_FRONTMATTER live (R1: 48, 43, 194 and 1 rows withheld; R2: no Hindi row of them live); RIGHTS_NOISE built (the editions\' apparatus) |\n| surgical | 218 modules, 1,631 tests pass on the PC; releases `471dd836` and `cd7eff74` (Automaton), `7c7767f` (Srangam) |\n| docs-coherence | This register brought up to date; the map (DOCS_MAP) made by docs_map.py |\n\n**The open keys of section 3, read again:**\n\n| Key | 28 Oct |\n|---|---|\n| nirukta-text | The witness has its English (647 of 649), mended (VEDIC_LLA); not judged, not released. Yours |\n| witness-adopt | Thirteen witnesses local (the eight, the Nirukta, two of the Satapatha, the Astadhyayi, the Rgveda padapatha), none adopted, none with English but the Nirukta\'s. Money: about $163 at today\'s price for the twelve without English (33,929 passages); the thinking A/B first |\n| witness-vision-pairs | Not run: no page of the Narasimha, Manu, Yajnavalkya, Parasara, Gautama, Bodhicaryavatara or Surya scans is vision read. Money |\n| markandeya-full-en | 0 of 5,240. The estimate of 22 Oct ($4.12) was made before the thinking was metered; at today\'s price about $25. Money |\n| hayasirsa-finish | Superseded by its repair: see the Hayasirsa above |\n| daivat-rights | Done (withdrawn, 24 Oct) |\n| satapatha-ch | Open: the witness\'s "ch" not restored, Samasrami\'s print not read. Next |\n| rgveda-witness | Done as a witness (28 Oct: 10,564 verses; it reads 76% of vol. ii\'s pages in order and offers a reading for the 100 the scan cannot read). Its English: Money |\n| shelf-on-site, claims-on-site | Done (C21 with credit; C23) |\n| backticks | Open and grown: 3,520 passages of the working English carry backticks (1,687 on 22 Oct). Yours: italics in the reader, or as they are |\n| source-first-queue | Running (the rounds) |\n| ganita-scholarly | Money: about $30; the Claude credit has $0.915 |\n| english-coverage | Next: vectors and names from the scholarly English (E2); not built |\n| professor-bot | On the PC\'s Ask (23 Oct); on the site (A2) not built. Next |\n| carmichael | Waiting |\n| pro-pilot, companion-seo-commits, gretil-legacy-terms | Not read again this round |\n\n**New keys (28 Oct):** hayasirsa-apparatus and karanagama-matter (Yours: the tags), karanagama-rights (Yours),\nhayasirsa-path (Yours: its English and Hindi, then release), gandharva-witness (Next, free), thinking-ab (Next: a\nmeasured A/B of the working English\'s thinking budget, built before any change), muktabodha (Yours: the letter),\nproxy-limit (Next: gdrive-image-proxy to images and a size).\n')

edit('docs/STATE_2026-10-18.md', 1, "| Decisions | the Hayasirsa: path A (its English through the rounds, about $7.75), B (release now) or C (both languages, about $15.50); the Karanagama: the 33 tagged, then its 1994 rights; the Nirukta released; Muktabodha asked; the thinking A/B |\n| Next | the Astadhyayi and the Rgveda padapatha witnesses; the smaller smrtis translated; GRETIL's Pancaratra and Saiva texts on the Agama shelf; a documentation map for Srangam |\n",
     "| Decisions | the Hayasirsa: path A (its English through the rounds, about $7.75), B (release now) or C (both languages, about $15.50); the Karanagama: the 33 tagged, then its 1994 rights; the Nirukta released; Muktabodha asked; the thinking A/B |\n| Next | the Astadhyayi and the Rgveda padapatha witnesses; the smaller smrtis translated; GRETIL's Pancaratra and Saiva texts on the Agama shelf; a documentation map for Srangam |\n## 35. 28 Oct, evening: the week's asks verified; the editions' own matter found (DOCS100_2026_10_28)\n\n| What | State |\n|---|---|\n| Release | `cd7eff74` pushed (the four mends, DOCS99); applied: mend_marks (the Hayasirsa: 0 note numbers left), mend_witness (the Nirukta: 0 vowel l left), the Karanagama's 33 tags; the Astadhyayi and the Rgveda padapatha witnesses ingested (3,947 and 10,564 passages); the cap raised to $135 |\n| Verified | the 16:51 backup; E1 (1,904 claims); R1 and R2 (the editions' own matter withheld: 48, 43, 194, 1); the mirror's ticks at 14:31 and 16:31 |\n| The asks | docs\\ASKS_2026-10-22.md section 13: of the 15 asks of 25 to 28 Oct, 9 done, 6 partly; load-ux not advanced |\n| Found | the Hayasirsa's apparatus of variant readings in 141 passages typed as verse or prose (classify_apparatus.py finds 73), its title pages and contents (20); the Karanagama's title pages, contents, verse index and bibliography (144) and 5 pages of debris; the Hayasirsa's old own matter still on the site (108 rows) until it is released; the Gandharva Veda Natyasastra (507 pages, Tesseract) read 74% by GRETIL's text; gdrive-image-proxy passes public files only |\n| Built | RIGHTS_NOISE (a listed edition's noise withheld as its frontmatter is); scripts\\tags_2026_10_28.ps1 (the tags, a dry run first); DOCS100 |\n| To do | the two patchers, docs_map.py --write, run_tests; a backup; tags_2026_10_28.ps1, then -Apply; the Hayasirsa's English and Hindi through the rounds; the Gandharva Veda's witness; text_path.py |\n| Decisions | the Hayasirsa's release after its translation; the Karanagama's rights; the Nirukta's release; Muktabodha; the thinking A/B |\n| Next | thinking-ab; proxy-limit; load-ux measured; G3c; E2 |\n")

edit('RUNBOOK.md', 1, '6. The Karanagama (section 4 of the account): mark_passages.py on the 33 passages, a dry run first; the two mixed\n   ones read by a person; then the decision on its rights before `repair_text.py --restore`.\n',
     "6. The Karanagama (section 4 of the account): mark_passages.py on the 33 passages, a dry run first; the two mixed\n   ones read by a person; then the decision on its rights before `repair_text.py --restore`.\n## 28 Oct, evening: the week's asks verified; the editions' own matter (DOCS100_2026_10_28)\n\ndocs\\ASKS_2026-10-22.md, section 13. From the repository root:\n\n1. `python scripts\\patch_rights_noise_2026_10_28.py --check`, then without --check; the same for\n   `patch_docs100_2026_10_28.py`. Then `python scripts\\docs_map.py --write` and\n   `powershell -ExecutionPolicy Bypass -File scripts\\run_tests.ps1`.\n2. With the dashboard idle: `python scripts\\db_backup.py data\\context.db D:\\backups\\context_pre_tags_20261028.db`;\n   `powershell -ExecutionPolicy Bypass -File scripts\\tags_2026_10_28.ps1` (the dry run: 73 by classify_apparatus.py,\n   68 listed and 20 of the Hayasirsa; 143, 1 and 5 of the Karanagama); read it; then the same with `-Apply`.\n   Page 19, passage 12 of the Hayasirsa is a person's (half a verse, then the notes).\n3. The Hayasirsa's English and Hindi through the rounds: `python scripts\\repair_auto.py --allow-translate\n   HAYASHIRSHA_PANCARATRA --usd 15.00` (1,453 passages, about $7 a language); when both are done the round asks for\n   its release (`python scripts\\repair_text.py --doc HAYASHIRSHA_PANCARATRA --release`), which also takes its old\n   own matter off the site.\n4. The Gandharva Veda Natyasastra: `python scripts\\text_path.py` (every text's path charted again, free; it writes\n   data\\text_path.json, which the desk reads: its chart of 22 Oct said nothing was in the database); GRETIL's\n   Natyasastra as its witness: `python scripts\\gretil_library.py --extract\n   1_sanskr/tei/transformations/html/sa_bharata-nATyazAstra-1-1618-303335-37.htm --doc gandharva_veda_natya_shastra`,\n   then `etext_witness.py` with `--file` (the preview), `--write` and `--ingest`, as for the Astadhyayi.\n5. After the next mirror tick: R3 of docs\\cloud\\CHECKS_rights_2026-10-28.sql (RIGHTS_NOISE: the listed editions'\n   noise withheld too: the Ganita's 9, the Mallapurana's 44, the Akasabhairava's 38), and R1 again.\n")


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

