## Phase AW - Our findings on the vamsa page (VAMSA_FINDINGS_SITE_2026_11_19, 2026-11-19)

Asked on 18 and 19 Nov: "the geneaologies work should carry tool tips and reference to dikshitar, raychaudhary, bc law
and any analyses built from iterative , statistical analysis of their works". On 19 Nov the desk (the automaton's R1,
scripts/vamsa_findings.py) read the ten dynasties of the vamsa page with the three scholars' notes; 49 findings were
proposed, each was read against its verses, and a person approved 20 and dropped 29. The approved ones now stand
beside their dynasty.

### AW.1 - What changes
- src/pages/corpus/CorpusVamsas.tsx: a dynasty's summary says how many findings it has; opened, "Our findings" comes
  above its generations: each finding's kind (the sources agree, differ, a link, an open question), the finding in our
  own words, its sources as small chips with their words on hover (the generation, which it points to on the page; the
  verse, which opens its text's line; Dikshitar's entry, which opens the person; Raychaudhuri's claim and page; B. C.
  Law's page only), and how it was made (proposed by a model, checked by machine, approved by a person, with the
  days). Each generation carries an id for a finding to point at.
- src/lib/indexSite.ts: the types, loadVamsaFindings (one read for every dynasty: corpus_reader_index_vamsa_findings,
  docs/cloud/C31_vamsa_findings_2026-11-19.sql in the automaton repo), FINDING_KIND, findingCiteText, findingMade,
  dayOf; the guide's "Our findings".
- src/__tests__/vamsa-findings.test.tsx: new.

### AW.2 - Not done, named
- Findings are proposed and approved on the desk only; the site never writes them.
- The 29 dropped findings and their reasons stay on the desk (exports/vamsa_findings.md is not in git: it names Law's
  claims).

### Invariants added (Phase AW)
73. A finding reaches the vamsa page only when a person approved it on the desk; it is shown in our own words with its
    sources, and B. C. Law (in copyright) is cited by his page alone, never his words. Until C31 is pasted the page
    shows nothing new and nothing else changes.
