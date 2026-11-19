#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
vamsa_findings.py  (2026-11-19)  VAMSA_FINDINGS_2026_11_19   (R1 on the dynasties)

Our findings on each dynasty of G6c: a sentence or three in our own words that joins what no one source says alone,
every source cited. The rule is docs\\PEOPLES_FINDINGS_2026-11-11.md (11 Nov): B. C. Law's book stays private; a finding
of ours, with its citations, may be published. Asked on 18 Nov: "the geneaologies work should carry tool tips and
reference to dishitar, raychaudhary, bc law and any analyses built from iterative, statistical analysis of their works".

For each dynasty (data\\vamsa_read\\aligned.json, vamsa_align.py) the desk makes a pack, read-only:
  g:N            the generation as the texts give it, side by side (G6c's status: agree, most, differ, one)
  v:WORK:REF     each text's name for that king, with its verse and the Sanskrit words
  pi:N           V. R. Ramachandra Dikshitar's person in the Purana Index, and whether it gives the same father
  r:KEY          H. C. Raychaudhuri's claims (Political History of Ancient India, 1923; public domain) that the site
                 carries already (C23's rule), tied by machine to a name of this dynasty (one candidate only)
  l:ID           B. C. Law's claims (Ancient Indian Tribes, 1926; in copyright to the end of 2029: private reading on
                 this PC), tied the same way; the page is kept, his words are not sent anywhere but to the model here
One Claude call per dynasty asks for 2 to 6 findings as JSON (agreement, disagreement, new_link, open_question), each
citing ids of the pack. Before a person sees one, the machine checks it: every id is in the pack; a disagreement cites
two items or more; a new link cites two kinds of source; no run of 8 words is shared with Law's pages (claims.db
claim_pages, law1926); the length is a finding's. A finding that fails is "refused" and never shown; one that passes
is "proposed" until a person approves it (--approve) or drops it (--drop). Only approved findings go on, later.

  python scripts\\vamsa_findings.py                         the plan: each dynasty's pack, the estimate (free)
  python scripts\\vamsa_findings.py --show kuru             the pack as it would be sent (free; Law's claims shown here)
  python scripts\\vamsa_findings.py --dynasty kuru --yes    a trial: one dynasty (the Claude credit, a few cents)
  python scripts\\vamsa_findings.py --dynasty all --yes     every dynasty not read yet (--max-usd, default 3)
  python scripts\\vamsa_findings.py --report                the findings and their checks; exports\\vamsa_findings.md
  python scripts\\vamsa_findings.py --approve kuru:1,kuru:3 --drop kuru:2      a person's decision (free)
  python scripts\\vamsa_findings.py --reparse               the stored replies checked again (free)

  writes   data\\vamsa_findings\\<dynasty>.json (the reply, the findings, their checks and status; Law cited by id and
           page only); exports\\vamsa_findings.md (the review page, with the sources resolved; exports\\ is not in git)
  reads    data\\context.db, data\\shelf\\kin.db, data\\shelf\\claims.db (read-only), data\\vamsa_read
  meters   usage_log, kind vamsa_findings (the Claude credit; claude_engine.budget_ok before each call)

The last lines are VERDICT:, NEXT: and ALSO:, as the other scripts'.
"""
from __future__ import annotations

import argparse, collections, datetime, hashlib, json, os, re, sqlite3, sys, time, unicodedata
from pathlib import Path

MARK = "VAMSA_FINDINGS_2026_11_19"
PROMPT_VERSION = "vamsa-findings-v1"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
MODEL = "claude-sonnet-5-5"
EFFORT = "medium"
MAX_TOKENS = 16000
CAP_USD = 3.0                # the default most one run spends
OUT_TOKENS = 6000            # the answer and its thinking, for the estimate (a guess until the trial measures it)
KINDS = ("agreement", "disagreement", "new_link", "open_question")
RAY_MAX, LAW_MAX = 60, 40    # a pack's claims, at most (those naming two persons of the dynasty first)
WORDS_MAX = 140              # a verse's words, in characters, at most
RUN = 8                      # a finding may not share a run of this many words with Law's pages
TEXT_MIN, TEXT_MAX = 40, 700
TRIAL = "kuru"               # the trial's dynasty: the one with most of both scholars (18 Nov: Law 49, Raychaudhuri 172)
SOURCE_KIND = {"g": "text", "v": "text", "pi": "index", "r": "raychaudhuri", "l": "law"}
LAW_WORK, RAY_WORK = "law1926", "phai1923"
LAW_CREDIT = "B. C. Law, Ancient Indian Tribes (Lahore, 1926)"
RAY_CREDIT = "H. C. Raychaudhuri, Political History of Ancient India (Calcutta, 1923)"
PI_CREDIT = "V. R. Ramachandra Dikshitar, The Purana Index (Madras, 1951-55)"

SYSTEM = """You are a careful historian of ancient India. You write short research findings in plain English.

You are given, for one dynasty, a pack of sources, each with an id:
- g:N, a generation as several Sanskrit texts tell it, side by side; v:WORK:REF, one text's name for that king, with
  its verse and the Sanskrit words that say it;
- pi:N, the person in V. R. R. Dikshitar's Purana Index, and whether the Index gives him the same father;
- r:KEY, a claim of H. C. Raychaudhuri, Political History of Ancient India (1923);
- l:N, a claim of B. C. Law, Ancient Indian Tribes (1926).
The scholars' claims were tied to a name of this dynasty by machine: a name may be another person of the same name
(two Janamejayas, two Pariksits), so judge before you use one, and say so when it matters.

Write 2 to 6 findings, fewer when the evidence is thin. A finding is one to three sentences in your own words that says
something no single source says alone:
- agreement: two sources of different kinds say the same (cite both);
- disagreement: they differ; set the readings side by side, do not rule between them (cite each);
- new_link: a tie the sources do not make themselves (cite at least two kinds of source);
- open_question: what they leave unsettled, asked as a question.
Cite every source a finding rests on by its id, and nothing that is not in the pack. Never copy Law's wording:
paraphrase him (at most a few words in quotation marks). State no date, place or fact that the pack does not give.

Reply with JSON only, no prose before or after:
{"findings": [{"kind": "agreement", "text": "...", "cites": ["g:3", "v:hv:HV 23.107", "r:phai1923:19:5"]}]}"""


def say(verdict: str, nxt: str = "", also=()):
    print("VERDICT: " + verdict)
    print("NEXT: " + nxt)
    for x in also:
        print("ALSO: " + x)


# --------------------------------------------------------------------------------------------- the inputs (read-only)
def law_claims(claims_db: str, immutable: bool = False) -> tuple:
    """({entity id: [claim id]}, {claim id: {page, claim}}): Law's claims tied to one of our entities alone (one
    candidate), their quotation found on the page; for the model only, never sent to the site."""
    if not claims_db or not Path(claims_db).exists():
        return {}, {}
    uri = Path(claims_db).resolve().as_uri() + ("?mode=ro&immutable=1" if immutable else "?mode=ro")
    con = sqlite3.connect(uri, uri=True, timeout=10)
    by, of = collections.defaultdict(list), {}
    try:
        have = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        if not {"claims", "claim_links"} <= have:
            return {}, {}
        for eid, cid, printed, page, claim in con.execute(
                "SELECT l.entity_id, c.id, c.printed, c.pdf_page, c.claim FROM claim_links l JOIN claims c "
                "ON c.id = l.claim_id WHERE c.work = ? AND l.role IN ('subject', 'object') AND coalesce(l.cands, 0) = 1 "
                "AND c.quote_check IN ('exact', 'close') ORDER BY c.pdf_page, c.n", (LAW_WORK,)):
            of[cid] = {"page": printed or "scan %s" % page, "claim": claim or ""}
            if cid not in by[eid]:
                by[eid].append(cid)
    finally:
        con.close()
    return dict(by), of


def law_pages(claims_db: str, immutable: bool = False) -> list:
    """Law's pages as the scan reads them (claim_pages), for the check that no finding shares a run of his words."""
    if not claims_db or not Path(claims_db).exists():
        return []
    uri = Path(claims_db).resolve().as_uri() + ("?mode=ro&immutable=1" if immutable else "?mode=ro")
    con = sqlite3.connect(uri, uri=True, timeout=10)
    try:
        return [r[0] or "" for r in con.execute("SELECT text FROM claim_pages WHERE work = ?", (LAW_WORK,))]
    except sqlite3.Error:
        return []
    finally:
        con.close()


def load_inputs(db: str, kin_db: str, claims_db: str, vamsa_read_dir: str, immutable: bool = False) -> dict:
    """Everything a pack needs, by the roads index_sync.py takes to the site (the same rows, the same ties)."""
    import index_sync as ix
    import relations_view as rv
    if immutable:
        rv.ro = ix.ro_immutable
    import vamsa_view as vv
    g = vv._graph(db, kin_db)
    dyn = ix.dynasty_rows(vamsa_read_dir, db, kin_db, g, set(), "every")
    _works, claims, cix = ix._claims(claims_db, set(), immutable)
    ent = ix._entity_claims(claims_db, {c["key"] for c in claims}, immutable)
    vam = ix.vamsa_rows(vamsa_read_dir, dyn, g, {}, claims, cix[1], ent)
    names = rv._names(db)["ents"]
    lby, lof = law_claims(claims_db, immutable)
    return {"vamsas": vam, "entity_of": g.get("entity_of") or {},
            "canon": {e: v[0] for e, v in names.items()}, "claim_of": {c["key"]: c for c in claims},
            "ray_by_ent": ent, "law_by_ent": lby, "law_of": lof}


# --------------------------------------------------------------------------------------------- the pack
def entity_of_person(person: str, entity_of: dict):
    src, _c, e = (person or "").partition(":")
    return entity_of.get((src, int(e))) if e.lstrip("-").isdigit() else None


def pack_of(v: dict, inp: dict) -> dict:
    """{"key", "text", "ids": {id: {"kind", "page"?}}, "counts"}: one dynasty's sources, each with its id, as the
    model reads them. The scholars' claims: those naming two persons of the dynasty first, then in its order."""
    lines, ids = [], {}
    head = "DYNASTY %s: %s (founder %s%s); vamsa %s; told by %d text(s): %s." % (
        v["key"], v.get("title") or v["key"], v.get("anchor") or "?",
        (", son of %s" % v["father"]) if v.get("father") else "", v.get("vamsa") or "-", len(v.get("works") or []),
        ", ".join(v.get("works") or []))
    c = v.get("counts") or {}
    lines += [head, "The texts on its generations (the desk's alignment): %d agree, %d mostly agree, %d differ, %d told by "
              "one text only." % tuple(int(c.get(k) or 0) for k in ("agree", "most", "differ", "one")), "",
              "GENERATIONS"]
    ents = []
    for gen in v.get("rows") or []:
        gid = "g:%s" % gen.get("gen")
        ids[gid] = {"kind": "text"}
        pi = gen.get("pui") or {}
        pi_txt = ""
        if pi.get("person"):
            pid = "pi:%s" % pi["person"].split(":")[-1]
            ids[pid] = {"kind": "index"}
            said = {"agrees": "the Index gives the same father", "differs": "the Index gives another father",
                    "new": "the Index has no father for him", "absent": ""}.get(pi.get("index") or "", "")
            pi_txt = " | %s %s%s" % (pid, pi.get("head") or "", ("; " + said) if said else "")
            e = entity_of_person(pi["person"], inp.get("entity_of") or {})
            if e is not None and e not in ents:
                ents.append(e)
        lines.append("%s %s [%s]%s" % (gid, gen.get("name") or "", gen.get("status") or "", pi_txt))
        for wk, cell in sorted((gen.get("cells") or {}).items()):
            if not cell.get("ref"):
                continue
            vid = "v:%s:%s" % (wk, cell["ref"])
            ids[vid] = {"kind": "text"}
            lines.append("  %s %s: %s" % (vid, cell.get("name") or "", (cell.get("words") or "")[:WORDS_MAX]))
    canon = inp.get("canon") or {}

    def ranked(by_ent):
        seen, both = collections.OrderedDict(), collections.Counter()
        for e in ents:
            for k in by_ent.get(e) or []:
                both[k] += 1
                seen.setdefault(k, e)
        return sorted(seen, key=lambda k: (-both[k], ents.index(seen[k]))), seen
    rk, rwho = ranked(inp.get("ray_by_ent") or {})
    rk = [k for k in rk if k in (inp.get("claim_of") or {})][:RAY_MAX]
    lk, lwho = ranked(inp.get("law_by_ent") or {})
    lk = [k for k in lk if k in (inp.get("law_of") or {})][:LAW_MAX]
    if rk:
        lines += ["", "RAYCHAUDHURI, Political History of Ancient India (1923); the name each claim was tied to in brackets"]
        for k in rk:
            cl = inp["claim_of"][k]
            rid = "r:%s" % k
            ids[rid] = {"kind": "raychaudhuri", "page": cl.get("printed") or "scan %s" % cl.get("pdf_page")}
            lines.append("%s (p. %s) [%s] %s" % (rid, ids[rid]["page"], canon.get(rwho[k], "?"), cl.get("claim") or ""))
    if lk:
        lines += ["", "LAW, Ancient Indian Tribes (1926); in copyright: paraphrase only; the name each claim was tied to "
                  "in brackets"]
        for k in lk:
            cl = inp["law_of"][k]
            lid = "l:%s" % k
            ids[lid] = {"kind": "law", "page": cl.get("page") or ""}
            lines.append("%s (p. %s) [%s] %s" % (lid, cl.get("page") or "", canon.get(lwho[k], "?"), cl.get("claim") or ""))
    text = "\n".join(lines)
    return {"key": v["key"], "text": text, "ids": ids,
            "counts": {"generations": len(v.get("rows") or []), "raychaudhuri": len(rk), "law": len(lk),
                       "chars": len(text)}}


def estimate(chars: int, model: str = MODEL) -> float:
    import claude_engine as CE
    p_in, p_out = CE.PRICES[model][:2]
    return ((chars / 3.0 + len(SYSTEM) / 3.0) * p_in + OUT_TOKENS * p_out) / 1e6


# --------------------------------------------------------------------------------------------- the reply and its checks
def parse_reply(text: str) -> list:
    """The findings of a reply (its last object that has a list "findings"); raises ValueError when none."""
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip())
    dec, objs, i = json.JSONDecoder(strict=False), [], 0
    while True:
        i = s.find("{", i)
        if i < 0:
            break
        try:
            obj, end = dec.raw_decode(s, i)
        except ValueError:
            i += 1
            continue
        if isinstance(obj, dict) and isinstance(obj.get("findings"), list):
            objs.append(obj)
        i = end
    if not objs:
        raise ValueError("the reply has no list of findings")
    return [x for x in objs[-1]["findings"] if isinstance(x, dict)]


def words(s: str) -> list:
    t = unicodedata.normalize("NFKD", str(s or "")).lower()
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    return re.findall(r"[a-z0-9]+", t)


def grams(pages: list, n: int = RUN) -> set:
    out = set()
    for p in pages:
        w = words(p)
        for i in range(len(w) - n + 1):
            out.add(tuple(w[i:i + n]))
    return out


def problems(f: dict, ids: dict, law_grams: set) -> list:
    """What keeps a finding from a person's eyes; [] when it may be proposed."""
    out = []
    kind, text, cites = f.get("kind"), f.get("text"), f.get("cites")
    if kind not in KINDS:
        out.append("kind %r is not one of %s" % (kind, ", ".join(KINDS)))
    if not isinstance(text, str) or not (TEXT_MIN <= len(text.strip()) <= TEXT_MAX):
        out.append("the text is not between %d and %d characters" % (TEXT_MIN, TEXT_MAX))
    if not isinstance(cites, list) or not cites or not all(isinstance(c, str) for c in cites):
        out.append("no citation")
        return out
    unknown = [c for c in cites if c not in ids]
    if unknown:
        out.append("not in the pack: %s" % ", ".join(unknown[:5]))
    kinds = {ids[c]["kind"] for c in cites if c in ids}
    if kind == "new_link" and len(kinds) < 2:
        out.append("a new link cites two kinds of source")
    if kind == "disagreement" and len(set(cites)) < 2:
        out.append("a disagreement cites two items")
    if isinstance(text, str) and law_grams:
        w = words(text)
        if any(tuple(w[i:i + RUN]) in law_grams for i in range(len(w) - RUN + 1)):
            out.append(LAW_RUN)
    return out


LAW_RUN = "a run of %d words is Law's" % RUN
WITHHELD = "(withheld: it shared a run of %d words with Law's pages; Law's words are not kept in git)" % RUN


def withhold(rec: dict) -> dict:
    """A finding that shares a run of Law's words keeps its checks, not its text; the reply goes too (data\\vamsa_
    findings is in git, and Law's book is in copyright)."""
    hit = [f for f in rec.get("findings") or [] if LAW_RUN in (f.get("problems") or [])]
    for f in hit:
        f["text"], f["withheld"] = WITHHELD, True
    if hit:
        rec["reply"], rec["reply_withheld"] = None, WITHHELD
    return rec


def checked(raw: list, ids: dict, law_grams: set, before=None) -> list:
    """The findings numbered, each with its problems and status; a person's decision on the same text is kept."""
    kept = {(b.get("text") or "").strip(): b for b in (before or []) if b.get("status") in ("approved", "dropped")}
    out = []
    for n, f in enumerate(raw, 1):
        p = problems(f, ids, law_grams)
        x = {"n": n, "kind": f.get("kind"), "text": (f.get("text") or "").strip(), "cites": f.get("cites") or [],
             "problems": p, "status": "refused" if p else "proposed"}
        b = kept.get(x["text"])
        if b and not p:
            x["status"], x["reviewed_at"] = b["status"], b.get("reviewed_at")
        out.append(x)
    return out


# --------------------------------------------------------------------------------------------- the store
def out_path(out_dir, key: str) -> Path:
    return Path(out_dir) / ("%s.json" % key)


def stored(out_dir, key: str) -> dict:
    try:
        return json.loads(out_path(out_dir, key).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def store(out_dir, key: str, rec: dict) -> Path:
    p = out_path(out_dir, key)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, p)
    return p


def done(out_dir, key: str) -> bool:
    d = stored(out_dir, key)
    return d.get("prompt_version") == PROMPT_VERSION and not d.get("error")


def chosen(spec: str, keys: list) -> list:
    if spec in ("", "all"):
        return list(keys)
    want = [s.strip() for s in spec.split(",") if s.strip()]
    bad = [s for s in want if s not in keys]
    if bad:
        raise ValueError("no dynasty %s here (there are: %s)" % (", ".join(bad), ", ".join(keys)))
    return want


def credit_line(db) -> str:
    try:
        import claude_engine as CE
        if not Path(db).exists():
            return "the credit: no database here"
        con = sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True, timeout=30)
        try:
            return CE.credit_line(CE.credit(con))
        finally:
            con.close()
    except Exception as e:
        return "the credit could not be read (%s)" % e


# --------------------------------------------------------------------------------------------- the steps
def do_plan(a, packs: list) -> int:
    todo, usd = 0, 0.0
    for p in packs:
        d = done(a.out, p["key"])
        e = estimate(p["counts"]["chars"], a.model)
        todo += 0 if d else 1
        usd += 0.0 if d else e
        print("  %-8s %3d generations, %3d of Raychaudhuri, %3d of Law, %6d characters; %s"
              % (p["key"], p["counts"]["generations"], p["counts"]["raychaudhuri"], p["counts"]["law"],
                 p["counts"]["chars"], "read" if d else "to read, about $%.3f" % e))
    print("  %s" % credit_line(a.db))
    say("%d dynasties to read, about $%.2f with %s (a guess until the trial measures it)" % (todo, usd, a.model),
        "python scripts\\vamsa_findings.py --dynasty %s --yes   (a trial)" % TRIAL if todo else
        "python scripts\\vamsa_findings.py --report")
    return 0


def do_run(a, packs: list, law_grams: set, client=None, con=None) -> int:
    import claude_engine as CE
    todo = [p for p in packs if a.again or not done(a.out, p["key"])]
    if not todo:
        say("nothing to read: every dynasty asked for is read", "python scripts\\vamsa_findings.py --report")
        return 0
    need = sum(estimate(p["counts"]["chars"], a.model) for p in todo)
    if need > a.max_usd * 1.5:
        print("REFUSE: the estimate is $%.2f, above --max-usd %.2f by half again" % (need, a.max_usd))
        say("nothing sent", "python scripts\\vamsa_findings.py --dynasty %s --yes" % TRIAL)
        return 1
    own = None
    if con is None:
        import db_utils
        con = own = db_utils.connect(a.db)
    try:
        if client is None:
            try:
                client = CE.Client(a.model, a.effort)
            except RuntimeError as e:
                print("REFUSE: %s" % e)
                say("nothing sent", "")
                return 1
        spent, n_ok, n_prop, n_ref = 0.0, 0, 0, 0
        for i, p in enumerate(todo, 1):
            est = estimate(p["counts"]["chars"], a.model)
            if spent + est > a.max_usd:
                print("  stopped before %s: $%.3f spent, the next about $%.3f, --max-usd %.2f"
                      % (p["key"], spent, est, a.max_usd))
                break
            if not CE.budget_ok(con, est):
                print("  stopped: the Claude credit (python scripts\\claude_engine.py --credit)")
                break
            before = stored(a.out, p["key"]).get("findings")
            rec = {"mark": MARK, "dynasty": p["key"], "prompt_version": PROMPT_VERSION, "model": a.model,
                   "effort": a.effort, "pack": dict(p["counts"], digest=hashlib.md5(p["text"].encode("utf-8")).hexdigest()),
                   "ids": {k: v for k, v in p["ids"].items()},
                   "at": datetime.datetime.now().isoformat(timespec="seconds")}
            t0 = time.time()
            try:
                msg = client.create(SYSTEM, p["text"], MAX_TOKENS)
            except Exception as e:
                rec["error"] = "%s: %s" % (type(e).__name__, str(e)[:300])
                store(a.out, p["key"], rec)
                print("  [%d/%d] %s: the API did not answer (%s)" % (i, len(todo), p["key"], rec["error"][:120]))
                break
            cost = CE.meter(con, "vamsa_findings", p["key"], a.model, msg.usage, time.time() - t0, units=1)
            spent += cost
            rec.update(reply=CE.text_of(msg), stop=CE.stop_of(msg), cost_usd=round(cost, 5), tokens=CE.tokens(msg.usage))
            try:
                rec["findings"] = checked(parse_reply(rec["reply"]), p["ids"], law_grams, before)
            except ValueError as e:
                rec["error"] = "the reply was not read: %s%s" % (e, "; it was cut (max_tokens)"
                                                                 if rec["stop"] == "max_tokens" else "")
            store(a.out, p["key"], withhold(rec))
            fs = rec.get("findings") or []
            pr = sum(1 for f in fs if f["status"] != "refused")
            n_ok += 0 if rec.get("error") else 1
            n_prop += pr
            n_ref += len(fs) - pr
            print("  [%d/%d] %s: %d finding(s), %d proposed, %d refused by the checks, $%.4f%s"
                  % (i, len(todo), p["key"], len(fs), pr, len(fs) - pr, cost,
                     ("  (%s)" % rec["error"][:100]) if rec.get("error") else ""), flush=True)
        say("%d dynasty(ies) read, %d finding(s) proposed, %d refused; $%.3f spent of the Claude credit"
            % (n_ok, n_prop, n_ref, spent), "python scripts\\vamsa_findings.py --report")
        return 0
    finally:
        if own is not None:
            own.close()


def do_reparse(a, packs: list, law_grams: set) -> int:
    n = 0
    for p in packs:
        d = stored(a.out, p["key"])
        if not d.get("reply"):
            continue
        try:
            d["findings"] = checked(parse_reply(d["reply"]), d.get("ids") or p["ids"], law_grams, d.get("findings"))
            d.pop("error", None)
            withhold(d)
        except ValueError as e:
            d["error"] = "the reply was not read: %s" % e
        store(a.out, p["key"], d)
        n += 1
    say("%d stored reply(ies) checked again (free)" % n, "python scripts\\vamsa_findings.py --report")
    return 0


def decide(out_dir, approve: str, drop: str) -> int:
    """A person's decision on proposed findings: kuru:1,kuru:3. Refused ones cannot be approved."""
    asked = [("approved", s) for s in approve.split(",") if s.strip()] + [("dropped", s) for s in drop.split(",") if s.strip()]
    changed, bad = 0, []
    for status, s in asked:
        key, _c, n = s.strip().partition(":")
        d = stored(out_dir, key)
        hit = [f for f in d.get("findings") or [] if str(f.get("n")) == n]
        if not hit or (status == "approved" and hit[0]["status"] == "refused"):
            bad.append(s.strip())
            continue
        hit[0]["status"] = status
        hit[0]["reviewed_at"] = datetime.datetime.now().isoformat(timespec="seconds")
        store(out_dir, key, d)
        changed += 1
    say("%d decision(s) recorded%s" % (changed, ("; not done: %s (no such finding, or refused by the checks)"
                                                 % ", ".join(bad)) if bad else ""),
        "python scripts\\vamsa_findings.py --report")
    return 1 if bad else 0


def do_report(a, keys: list, inp=None) -> int:
    """The counts here; the review page with the sources resolved (exports\\, not in git: it names Law's claims)."""
    lines = ["# Our findings on the dynasties (%s)" % MARK, "",
             "Each finding as the model proposed it, its checks, its status. Approve with --approve, drop with --drop.",
             "Sources: %s; %s; %s (private reading)." % (PI_CREDIT, RAY_CREDIT, LAW_CREDIT), ""]
    tot, first = collections.Counter(), ""
    for key in keys:
        d = stored(a.out, key)
        if not d:
            continue
        lines += ["## %s (%s, $%.4f)" % (key, d.get("at", ""), float(d.get("cost_usd") or 0)), ""]
        if d.get("error"):
            lines += ["error: %s" % d["error"], ""]
        for f in d.get("findings") or []:
            tot[f["status"]] += 1
            if f["status"] == "proposed" and not first:
                first = "%s:%s" % (key, f["n"])
            lines.append("%d. [%s] %s: %s" % (f["n"], f["status"], f["kind"], f["text"]))
            for c in f["cites"]:
                lines.append("   - %s%s" % (c, resolve(c, d.get("ids") or {}, inp)))
            if f.get("problems"):
                lines.append("   - checks: %s" % "; ".join(f["problems"]))
            lines.append("")
        print("  %-8s %s" % (key, ", ".join("%d %s" % (sum(1 for f in d.get("findings") or [] if f["status"] == s), s)
                                            for s in ("proposed", "approved", "dropped", "refused"))))
    p = Path(a.exports) / "vamsa_findings.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    say("%d proposed, %d approved, %d dropped, %d refused; the review page: %s"
        % (tot["proposed"], tot["approved"], tot["dropped"], tot["refused"], p),
        ("python scripts\\vamsa_findings.py --approve %s   (or --drop %s), once read" % (first, first)) if first else "")
    return 0


def resolve(cid: str, ids: dict, inp=None) -> str:
    meta = ids.get(cid) or {}
    if cid.startswith("l:") and inp:
        c = (inp.get("law_of") or {}).get(int(cid[2:]) if cid[2:].isdigit() else cid[2:])
        return " (Law, p. %s): %s" % (meta.get("page", ""), c["claim"]) if c else " (Law, p. %s)" % meta.get("page", "")
    if cid.startswith("r:") and inp:
        c = (inp.get("claim_of") or {}).get(cid[2:])
        return " (Raychaudhuri, p. %s): %s" % (meta.get("page", ""), c["claim"]) if c else ""
    return (" (p. %s)" % meta["page"]) if meta.get("page") else ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="our findings on the dynasties (%s)" % MARK)
    ap.add_argument("--dynasty", default="all", help="all, or keys: kuru,solar")
    ap.add_argument("--yes", action="store_true", help="read (the Claude credit); without it, the plan")
    ap.add_argument("--again", action="store_true", help="read again a dynasty already read")
    ap.add_argument("--max-usd", type=float, default=CAP_USD)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--effort", default=EFFORT)
    ap.add_argument("--show", default="", help="print a dynasty's pack as it would be sent (free)")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--reparse", action="store_true")
    ap.add_argument("--approve", default="")
    ap.add_argument("--drop", default="")
    ap.add_argument("--db", default=str(ROOT / "data" / "context.db"))
    ap.add_argument("--kin-db", default=str(ROOT / "data" / "shelf" / "kin.db"))
    ap.add_argument("--claims-db", default=str(ROOT / "data" / "shelf" / "claims.db"))
    ap.add_argument("--vamsa-read", default=str(ROOT / "data" / "vamsa_read"))
    ap.add_argument("--out", default=str(ROOT / "data" / "vamsa_findings"))
    ap.add_argument("--exports", default=str(ROOT / "exports"))
    ap.add_argument("--immutable", action="store_true", help="the database is a backup copy: read it as immutable")
    a = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError):
            pass
    try:
        import env_loader
        env_loader.load_env()
    except Exception:
        pass
    import claude_engine as CE
    print("vamsa_findings.py  %s  %s" % (MARK, "READ" if a.yes else "FREE"))
    if a.approve or a.drop:
        return decide(a.out, a.approve, a.drop)
    if a.model not in CE.PRICES:
        print("REFUSE: %s is not one of %s" % (a.model, ", ".join(sorted(CE.PRICES))))
        say("nothing read", "")
        return 1
    for pth, what in ((a.db, "the database"), (a.kin_db, "the kinships (kin.db)"),
                      (Path(a.vamsa_read) / "aligned.json", "G6c's alignment (python scripts\\vamsa_align.py)")):
        if not Path(pth).exists():
            print("REFUSE: %s is not here (%s)" % (what, pth))
            say("nothing read", "")
            return 1
    inp = load_inputs(a.db, a.kin_db, a.claims_db, a.vamsa_read, a.immutable)
    keys = [v["key"] for v in inp["vamsas"]]
    if a.report:
        return do_report(a, keys, inp)
    try:
        want = chosen(a.show or a.dynasty, keys)
    except ValueError as e:
        print("REFUSE: %s" % e)
        say("nothing read", "")
        return 1
    packs = [pack_of(v, inp) for v in inp["vamsas"] if v["key"] in want]
    if a.show:
        for p in packs:
            print(p["text"])
        say("the pack of %s as it would be sent (%d characters; free, nothing sent)"
            % (", ".join(p["key"] for p in packs), sum(p["counts"]["chars"] for p in packs)),
            "python scripts\\vamsa_findings.py --dynasty %s --yes" % packs[0]["key"] if packs else "")
        return 0
    law_grams = grams(law_pages(a.claims_db, a.immutable))
    if a.reparse:
        return do_reparse(a, packs, law_grams)
    if a.yes:
        if not law_grams:
            print("REFUSE: Law's pages are not in claims.db (claim_pages, %s): the check that no finding copies him "
                  "cannot run" % LAW_WORK)
            say("nothing sent", "")
            return 1
        return do_run(a, packs, law_grams)
    return do_plan(a, packs)


if __name__ == "__main__":
    sys.exit(main())
