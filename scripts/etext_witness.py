#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
etext_witness.py  (2026-10-11)  ETEXT_WITNESS_2026_10_11

An e-text as a witness (the Source desk's S2, and the missing page, S3). A Unicode text from GRETIL or
sanskritdocuments.org, or an archive.org OCR text (_djvu.txt), becomes the page JSONL that
ingest_jsonl_fast.py reads, as a text of its own (<doc>__w_<site>), and is measured against the scan it
is meant to replace or repair:

  read      HTML or plain text, in Devanagari, IAST (ISO 15919 too), Harvard-Kyoto, Velthuis or ITRANS
            (--scheme, else detected). English lines (headers, licences, notes) are dropped and counted.
  verses    lines are grouped into verses by their double danda and their references (BhG_1.1,
            // 1.1 //, || 12 ||, Devanagari numerals); romanized text is put into Devanagari with
            indic_transliteration, as import_mbh_gretil.py does, with / and // as the dandas.
  pages     an archive.org OCR text keeps its own pages (form feeds) and is segmented at ingest; an e-text
            is cut into pages of --per-page verses that never cross a chapter.
  measured  against the scan's passages in the database (read-only): which of its readable pages the
            witness reads (6-letter n-grams of the consonant skeleton, so sandhi spacing, the nasals
            and most OCR slips do not count), whether in the same order, and, for each page the scan cannot read, the
            witness's verses between the neighbouring pages it does read: the missing page, offered.
  written   (--write) data/raw_witness/<witness>/<witness>_NNNN.jsonl, witness.json and align.json; a line
            in data/witnesses.jsonl; and the register (data/source_verdicts.jsonl) says "witness", so the
            mirror (corpus_sync.py) leaves it alone until it is adopted.
  ingested  (--ingest) a backup first (db_backup.py), then ingest_jsonl_fast.py, as its own text.
  adopted   when translated: repair_text.py --release (it refuses before).

Never writes the scan's passages. The preview is the default and writes nothing; --url only saves the
file into sources\\<doc>\\ (with its provenance beside it), then previews it.

  python scripts\\etext_witness.py --doc X --file sources\\X\\bodhi.htm
  python scripts\\etext_witness.py --doc X --url https://gretil.sub.uni-goettingen.de/gretil/.../file.htm
  python scripts\\etext_witness.py --doc X --file sources\\X\\bodhi.htm --page 12
  python scripts\\etext_witness.py --doc X --file sources\\X\\bodhi.htm --write
  python scripts\\etext_witness.py --doc X --ingest
  python scripts\\etext_witness.py --list

ETEXT_PROSE_2026_10_21: a prose e-text whose units stand under their own reference lines (GRETIL's Satapatha:
"13.1.1.[1]") is read unit by unit, each with its reference, never cut at 12 lines, with no danda added; --file may
name a folder (its .htm, .html and .txt files in the order of their names are one text); --category names a new
text's category when it is no scan's witness.

  python scripts\\etext_witness.py --doc satapatha_madhyandina --file sources\\satapatha_gretil --category brahmana --per-page 10

The last lines are VERDICT:, NEXT: and ALSO:, as repair_text.py's, for the dashboard.
"""
from __future__ import annotations
import argparse, datetime, hashlib, html, json, os, re, shutil, sqlite3, sys, unicodedata, urllib.parse, urllib.request
from pathlib import Path

MARK = "ETEXT_WITNESS_2026_10_11"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import repair_text as rt  # noqa: E402  (run, writers_running, verdicts, PY, SCRIPTS: one way of doing each)

UA = {"User-Agent": "SanskritAutomaton-EtextWitness/1.0 (scholarly, non-commercial)"}
HOSTS = ["gretil.sub.uni-goettingen.de", "sanskritdocuments.org", "archive.org", "raw.githubusercontent.com",
         "dsbcproject.org"] + [   # QUALITY_2026_10_11: the Digital Sanskrit Buddhist Canon
    h.strip().lower() for h in (os.environ.get("SA_ETEXT_HOSTS") or "").split(",") if h.strip()]
MAX_BYTES = 40_000_000
K = 6                     # n-gram length on the consonant skeleton
QUALITY = 0.95            # an e-text's passages; the OCR scorer under-scores clean e-texts (ingest_jsonl_fast.py)
MATCH, WEAK = 0.30, 0.10  # a page's score: read by the witness / touched / not

DANDA, DDANDA = "\u0964", "\u0965"
DEV_LETTER = re.compile(r"[\u0904-\u0939\u093d\u0950\u0958-\u0961\u0972-\u097f]")
SKEL = re.compile(r"[\u0915-\u0939\u0958-\u095f]")
NASAL = re.compile(r"[\u0919\u091e\u0923\u0928\u092e]\u094d(?=[\u0915-\u0939])")   # a nasal before a stop: the anusvara
ASCII_LETTER = re.compile(r"[A-Za-z]")
LATIN = re.compile(r"[A-Za-z\u00c0-\u024f\u1e00-\u1eff]")
IAST_MARKS = set("\u0101\u012b\u016b\u1e5b\u1e5d\u1e37\u1e39\u1e43\u1e41\u1e25\u1e45\u00f1\u1e6d\u1e0d\u1e47\u015b\u1e63"
                 "\u0100\u012a\u016a\u1e5a\u1e5c\u1e36\u1e38\u1e42\u1e40\u1e24\u1e44\u00d1\u1e6c\u1e0c\u1e46\u015a\u1e62")
DIGITS = str.maketrans("\u0966\u0967\u0968\u0969\u096a\u096b\u096c\u096d\u096e\u096f", "0123456789")
NUM = r"[0-9\u0966-\u096f]+(?:[.,][0-9\u0966-\u096f]+)*"
R_ABBR = re.compile(r"(?<![A-Za-z])[A-Z][A-Za-z]{0,12}_(" + NUM + r")([a-f]{1,2})?(?:/(\d+))?(?![A-Za-z0-9])")
R_HEAD = re.compile(r"^[A-Z][A-Za-z]{0,12} (\d+(?:\.\d+)+)([a-f]{1,2})?(?=\s)")
R_DBL = re.compile(r"(?://|\|\||\u0965)\s*(" + NUM + r")\s*(?://|\|\||\u0965)")
R_TAIL = re.compile(r"(//|\|\||\u0965)\s*(" + NUM + r")\s*$")
R_PAR = re.compile(r"\(\s*(" + NUM + r")\s*\)\s*$")
ITI = "\u0907\u0924\u093f"
COLOPHON = re.compile("(" + "|".join([
    "\u0927\u094d\u092f\u093e\u092f", "\u0938\u0930\u094d\u0917", "\u092a\u091f\u0932",
    "\u092a\u0930\u093f\u091a\u094d\u091b\u0947\u0926", "\u092a\u094d\u0930\u0915\u0930\u0923",
    "\u0938\u092e\u093e\u092a\u094d\u0924", "\u0909\u0932\u094d\u0932\u093e\u0938", "\u0915\u093e\u0923\u094d\u0921",
    "\u0905\u0919\u094d\u0915", "\u092a\u094d\u0930\u092a\u093e\u0920\u0915", "\u0906\u0939\u094d\u0928\u093f\u0915",
    "\u0916\u0923\u094d\u0921", "\u0938\u094d\u0915\u0928\u094d\u0927", "\u0905\u0927\u093f\u0915\u0930\u0923"]) + ")")
STOP = (set(rt.ENGLISH) - {"a", "om", "p", "ms", "mss"}) | set("""gretil http https www copyright input entered entry
data version revised electronic license licence creative commons university press published publisher translated
translation based file files contents header encoding unicode proofread proofreading transliterated transliteration
document documents information please send corrections web site available reproduced distributed""".split())
SITES = (("gretil", "gretil"), ("sanskritdocuments", "sdoc"), ("archive.org", "archive"), ("_djvu", "archive"),
         ("githubusercontent", "github"))


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _letters(s: str):
    return len(DEV_LETTER.findall(s)), len(LATIN.findall(s))


def skel(s: str) -> str:
    """The consonants only, a nasal before a consonant read as the anusvara (sanjaya and samjaya are one):
    what OCR, sandhi spacing (kim akurvata, kimakurvata), the vowel signs and the editions disturb least."""
    return "".join(SKEL.findall(NASAL.sub("", s or "")))


def is_english(line: str) -> bool:
    low = line.lower()
    if "http" in low or "@" in low or "gretil" in low or "copyright" in low or "\u00a9" in line:
        return True
    toks = re.findall(r"[a-z\u00c0-\u024f\u1e00-\u1eff']+", low)
    if not toks:
        return False
    sw = sum(1 for t in toks if t.strip("'") in STOP)
    marks = sum(1 for ch in line if ch in IAST_MARKS)
    return (sw >= 2 and sw >= 0.2 * len(toks)) or (sw >= 1 and len(toks) >= 4 and not marks)


# ---- reading -------------------------------------------------------------------------------------
def decode(data: bytes):
    """(text, encoding, note)."""
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16", "replace"), "utf-16", ""
    try:
        return data.decode("utf-8-sig"), "utf-8", ""
    except UnicodeDecodeError:
        t = data.decode("utf-8", "replace")
        bad = t.count("\ufffd")
        if bad <= max(5, len(t) // 2000):
            return t, "utf-8", "%d byte(s) are not UTF-8 and were replaced" % bad
        return data.decode("cp1252", "replace"), "cp1252", "not UTF-8: read as Windows-1252, which is rarely right for Sanskrit"


def html_to_text(s: str) -> str:
    s = re.sub(r"(?is)<(script|style|head)\b.*?</\1\s*>", " ", s)
    if len(re.findall(r"(?i)<br\b", s)) >= 10:
        # the lines are marked by <br>: a newline in the source is only a space, except inside <pre>
        parts = re.split(r"(?is)(<pre\b.*?</pre\s*>)", s)
        s = "".join(x if x[:4].lower() == "<pre" else re.sub(r"[ \t]*\n[ \t]*", " ", x) for x in parts)
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</(p|div|h[1-6]|li|tr|pre|blockquote|table)\s*>", "\n", s)
    s = re.sub(r"(?i)<(p|div|h[1-6]|li|tr|pre|blockquote|hr)\b[^>]*>", "\n", s)
    s = re.sub(r"(?s)<!--.*?-->", " ", s)
    s = re.sub(r"<[^>]+>", "", s)
    return html.unescape(s).replace("\u00a0", " ")


def read_text(path: Path):
    data = path.read_bytes()
    text, enc, note = decode(data)
    head = text[:6000].lower()
    kind = "html" if ("<html" in head or "<body" in head or "<br" in head or "<p>" in head) else "text"
    if kind == "html":
        text = html_to_text(text)
    return text, {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "encoding": enc,
                  "kind": kind, "note": note}


# ETEXT_PROSE_2026_10_21: a folder of files is one text, a break between them
FILE_BREAK = "@@ETEXT_FILE_BREAK@@"


def read_source(src: Path):
    """(text, info) of a file (read_text), or of a folder: its .htm, .html and .txt files in the order of their names
    (GRETIL's Satapatha, a file a kanda), joined with FILE_BREAK; info["files"]: each one's name, bytes and sha256."""
    if not src.is_dir():
        return read_text(src)
    files = sorted(p for p in src.iterdir() if p.is_file() and p.suffix.lower() in (".htm", ".html", ".txt"))
    texts, infos = [], []
    for p in files:
        t, i = read_text(p)
        texts.append(t)
        infos.append(dict(i, name=p.name))
    info = {"bytes": sum(i["bytes"] for i in infos),
            "sha256": hashlib.sha256("".join(i["sha256"] for i in infos).encode("ascii")).hexdigest(),
            "encoding": ", ".join(sorted({i["encoding"] for i in infos})) or "-",
            "kind": ", ".join(sorted({i["kind"] for i in infos})) or "-",
            "note": "; ".join(i["note"] for i in infos if i["note"]),
            "files": [{"name": i["name"], "bytes": i["bytes"], "sha256": i["sha256"]} for i in infos]}
    return ("\n%s\n" % FILE_BREAK).join(texts), info


def detect_scheme(lines: list) -> str:
    d = l = marks = words = hk = vel = itr = 0
    for ln in lines[:6000]:
        if not ln.strip() or is_english(ln):
            continue
        dd, ll = _letters(ln)
        d += dd; l += ll
        marks += sum(1 for ch in ln if ch in IAST_MARKS)
        vel += len(re.findall(r"\.[mhrntdsl]|~n|\"n", ln))
        itr += len(re.findall(r"aa|ii|uu|sh|Sh|RRi|\.N|~N|\^", ln))
        for w in re.findall(r"[A-Za-z]{2,}", ln):
            words += 1
            if re.search(r"[a-z][AIURLMHGJTDNS]|z", w):
                hk += 1
    if d + l == 0:
        return "unknown"
    if d >= l:
        return "devanagari"
    if marks >= 0.01 * l:
        return "iast"
    if vel >= 0.01 * l:
        return "velthuis"
    if words and hk >= 0.12 * words:
        return "itrans" if itr > 2 * hk else "hk"
    return "unknown"


# ETEXT_ORTHO_2026_10_21 ---------------------------------------------------------------------------
# The Surya Siddhanta's GRETIL e-text (21 Oct) writes IAST with H for the visarga, +a for an a merged into the vowel
# before it, N.NNa: for a pada and (B ...) for an edition's variant: lowered before its transliteration, the visarga
# became h with a virama in 362 of its 515 passages. gretil_marks() reads them as the e-text means them; the labels
# and the sigla are set aside (private-use characters, which indic_transliteration passes through) and put back.
KEEP0 = 0xE100
G_LABEL = re.compile(r"(?<![\w.])(\d+\.\d+[a-f]?:)")                     # 1.30a: the e-text's pada label
G_SIGLUM = re.compile("\\(\\s*([A-Z]|\u1e0d)(?=\\s)")                  # (B kevalam); (\u1e0d ...) is its D, dotted
G_SIGLUM_OUT = re.compile(r"\(\s*[A-Z](?=\s)")
G_VISARGA = re.compile("(?<=[aeiou\u0101\u012b\u016b\u1e5b\u1e5d\u1e37\u1e39])H")   # namaH, tejaHsahaH
G_MERGED_SIGLUM = re.compile("([\ue100-\ue1ff]\\s)\\+a")                # (C +any\u0101 ...): after a siglum
G_MERGED = re.compile(r"\s?\+a")                                        # puru\u1e63o +aya\u1e43, v\u0101 +arka
G_NOTE = re.compile(r"(\(\s*\d[\d,\s]*\))\s*checked\b")                  # 1.30b: "(2296832) checked", the inputter's


def gretil_marks(s: str):
    """ETEXT_ORTHO_2026_10_21: (s, kept): an IAST line with the e-text's H (the visarga) and +a (an a merged into the
    vowel before it, written with the avagraha) read as meant, the note "checked" after a number dropped, and the pada
    labels and sigla replaced by private-use characters; kept[k] is what chr(KEEP0 + k) stands for."""
    kept = []

    def put(text):
        kept.append(text)
        return chr(KEEP0 + len(kept) - 1)
    s = G_NOTE.sub(r"\1", s)
    s = G_LABEL.sub(lambda m: put(m.group(1)), s)
    s = G_SIGLUM.sub(lambda m: "(" + put("D" if m.group(1) == "\u1e0d" else m.group(1)), s)
    s = G_VISARGA.sub("\u1e25", s)
    s = G_MERGED_SIGLUM.sub(r"\1'", s)
    s = G_MERGED.sub("'", s)
    return s, kept


def kept_out(text: str) -> str:
    """ETEXT_ORTHO_2026_10_21: a verse without the labels and sigla gretil_marks() keeps in Latin letters."""
    return G_SIGLUM_OUT.sub("(", G_LABEL.sub(" ", text or ""))


def gretil_header(lines: list) -> set:
    """ETEXT_ORTHO_2026_10_21: the numbers (from 1) of the lines of a GRETIL TEI header, from a line "Header" to a line
    "Text", when the block names GRETIL: its English (Contribution, Source, Licence, Notes, Revisions) is not the text;
    its short lines were read as verses on the Surya Siddhanta's page 1 and the Markandeya's. Else empty."""
    first = None
    for i, raw in enumerate(lines[:400], 1):
        t = raw.strip()
        if first is None and t == "Header":
            first = i
        elif first is not None and t == "Text":
            return set(range(first, i + 1)) if "gretil" in " ".join(lines[first - 1:i]).lower() else set()
    return set()


def to_deva(s: str, scheme: str, ortho: bool = True) -> str:
    if scheme == "devanagari":
        return s.replace(DANDA + DANDA, DDANDA).replace("||", DDANDA).replace("|", DANDA)
    s = unicodedata.normalize("NFC", s)
    s = (s.replace("\u2019", "'").replace("r\u0325\u0304", "\u1e5d").replace("r\u0325", "\u1e5b").replace("l\u0325\u0304", "\u1e39")
         .replace("l\u0325", "\u1e37").replace("\u1e41", "\u1e43"))
    kept = []
    if scheme == "iast":
        if ortho:   # ETEXT_ORTHO_2026_10_21: ortho=False reads as before 21 Oct (mend_witness.py compares the two)
            s, kept = gretil_marks(s)
        s = s.lower()
    s = re.sub(r"(?<=[^\W\d_])-(?=[^\W\d_])", "", s)          # compound hyphens: one word in Devanagari
    s = s.replace("||", "\x01").replace("|", "\x02")
    if scheme != "velthuis":                                    # in Velthuis, / is the candrabindu
        s = s.replace("//", "\x01").replace("/", "\x02")
    from indic_transliteration import sanscript
    sch = {"iast": sanscript.IAST, "hk": sanscript.HK, "velthuis": sanscript.VELTHUIS, "itrans": sanscript.ITRANS}[scheme]
    out = sanscript.transliterate(s, sch, sanscript.DEVANAGARI)
    out = out.replace("\x01", DDANDA).replace("\x02", DANDA)
    for k, v in enumerate(kept):   # ETEXT_ORTHO_2026_10_21: the labels and sigla, as the e-text writes them
        out = out.replace(chr(KEEP0 + k), v)
    return out


def norm_ref(r: str) -> str:
    parts = [p for p in re.split(r"[.,]", (r or "").translate(DIGITS)) if p != ""]
    try:
        return ".".join(str(int(p)) for p in parts)
    except ValueError:
        return ""


# ETEXT_REFS_2026_10_21: a line that begins with the e-text's pada label (1.31a: ... 1.31b: ...//(364220)) has its
# reference there; the number in brackets at its end is the e-text's value of the verse's numerals (364220, Jupiter's
# revolutions in a yuga), not a reference: read as one (R_PAR) until 21 Oct, it was taken out of the text of 18 of the
# Surya Siddhanta's verses, and the chapter came from the colophons (1, then 2), not from the labels (1 to 14). A
# chapter's first verse begins with its title in brackets ([spa\u1e63\u1e6d\u0101dhik\u0101raH] 2.01a: ...).
G_LABEL_HEAD = re.compile(r"^\s*(?:\[[^\]\n]{1,80}\]\s*)?(\d+\.\d+)[a-f]?:")   # [bh\u016bgola] 12.01a: a chapter's first

# ETEXT_PROSE_2026_10_21: a prose unit's reference on a line of its own (GRETIL's Satapatha: 13.1.1.[1], kanda, adhyaya,
# brahmana, [kandika]), or followed by the unit's first words
G_PROSE_REF = re.compile(r"^\s*(\d{1,3}(?:\.\d{1,3}){1,4})\.\[(\d{1,4})\](?:\s+(.*\S))?\s*$")
# ETEXT_PROSE2_2026_10_22: GRETIL's Satapatha in full has its numbers in other shapes too, read once a bracketed one has
# been seen: the brackets put in wrongly (1.1.3[.1]1, 1.1.3[[.]]5, 4.5.7.[9]]), none (14.4.1.1), a brahmana's own number
# (14.6.4.), a number glued to its text (11.7.4.2prajapatirha); and an appendix after a line of asterisks
G_PROSE_GLUED = re.compile(r"^\s*(\d{1,3}(?:\.\d{1,3}){3})(?=[^\W\d_])(.+)$")
G_SEPARATOR = re.compile(r"^\s*[*=~_-]{5,}\s*$")


def prose_ref(ln: str, on: bool):
    """(ref, rest, kind) of a prose unit's reference line, or None. kind: "unit" (13.1.1.[1]; once on, 1.1.3[.1]1 and
    14.4.1.1), "glued" (once on: 11.7.4.2text) or "heading" (once on: 14.6.4., a brahmana's own number)."""
    m = G_PROSE_REF.match(ln)
    if m:
        return norm_ref(m.group(1) + "." + m.group(2)), (m.group(3) or "").strip(), "unit"
    if not on:
        return None
    if re.fullmatch(r"[\d.\[\]\s]+", ln):
        parts = re.sub(r"[\[\]\s]", "", ln).strip(".").split(".")
        if all(p.isdigit() and len(p) <= 3 for p in parts) and len(parts) in (3, 4):
            return ".".join(str(int(p)) for p in parts), "", ("unit" if len(parts) == 4 else "heading")
        return None
    m = G_PROSE_GLUED.match(ln)
    if m:
        return norm_ref(m.group(1)), m.group(2).strip(), "glued"
    return None


def take_ref(line: str, labels: bool = True):
    """(text without its reference, ref, where): where is "end", "start" or "part" (a pada, a line of a verse).
    ETEXT_REFS_2026_10_21: a line that begins with a pada label (1.31a:) keeps all its text, the label too, and its
    reference is the label's verse; labels=False reads as before (mend_witness.py compares the two)."""
    if labels:
        m = G_LABEL_HEAD.match(line)
        if m:
            return line, norm_ref(m.group(1)), "part"
    m = R_ABBR.search(line)
    if m:
        where = "part" if (m.group(2) or m.group(3)) else ("start" if not line[:m.start()].strip() else "end")
        rest = (line[:m.start()] + " " + line[m.end():]).strip()
        rest = re.sub(r"(//|\|\|)\s*(//|\|\|)\s*$", r"\1", rest)   # "// BhG_1.1 //" leaves "// //"
        return rest, norm_ref(m.group(1)), where
    m = R_HEAD.match(line)
    if m:
        return line[m.end():].strip(), norm_ref(m.group(1)), "part" if m.group(2) else "start"
    m = R_DBL.search(line)
    if m:
        dd = DDANDA if DDANDA in m.group(0) else "//"
        return (line[:m.start()].rstrip() + " " + dd + " " + line[m.end():].lstrip()).strip(), norm_ref(m.group(1)), "end"
    m = R_TAIL.search(line)
    if m:
        return (line[:m.start()].rstrip() + " " + m.group(1)).strip(), norm_ref(m.group(2)), "end"
    m = R_PAR.search(line)
    if m:
        return line[:m.start()].rstrip(), norm_ref(m.group(1)), "end"
    return line, "", ""


def _ends_verse(s: str) -> bool:
    t = s.rstrip()
    return t.endswith("//") or t.endswith("||") or t.endswith(DDANDA)


def parse(text: str, scheme: str = "auto", pages: str = "auto") -> dict:
    """{"mode": "verses" | "pages", "scheme", "verses": [...], "pages": [...], "stats": {...}}."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    st = {"lines": len(lines), "kept": 0, "dropped_english": 0, "blank": 0, "romanized": 0, "devanagari": 0,
          "refs": 0, "colophons": 0}
    sch = detect_scheme(lines) if scheme == "auto" else scheme
    out = {"scheme": sch, "stats": st, "verses": [], "pages": []}
    if sch == "unknown":
        out["mode"] = "verses"
        return out
    if pages == "source" or (pages == "auto" and text.count("\f") >= 5):
        out["mode"] = "pages"
        for n, block in enumerate(text.split("\f"), 1):
            keep = []
            for ln in block.split("\n"):
                d, l = _letters(ln)
                if d >= 3 and d >= l:
                    keep.append(to_deva(ln.strip(), "devanagari")); st["kept"] += 1; st["devanagari"] += 1
                elif ln.strip():
                    st["dropped_english"] += 1
                else:
                    st["blank"] += 1
            if keep:
                out["pages"].append({"page": n, "text": "\n".join(keep)})
        return out
    out["mode"] = "verses"
    verses = out["verses"]
    cur = {"lines": [], "roman": [], "ref": "", "src": 0}
    chap = [1]
    prose = [False]   # ETEXT_PROSE_2026_10_21: a unit's reference line seen: each unit runs to the next
    appendix, last_unit, top = [()], [""], [()]   # ETEXT_PROSE2_2026_10_22: the highest number before a separator line,
                                                  # the last unit's number, the highest number so far

    def flush():
        if cur["lines"]:
            deva = "\n".join(x.strip() for x in cur["lines"] if x.strip()).strip()
            if DEV_LETTER.search(deva):
                ref = cur["ref"]
                chapter = ".".join(ref.split(".")[:-1]) if ref.count(".") else ""
                if prose[0] and ref.count(".") >= 2:   # ETEXT_PROSE_2026_10_21: the adhyaya (13.1), not the brahmana
                    chapter = ".".join(ref.split(".")[:2])
                colo = ITI in deva and COLOPHON.search(deva) is not None and len(deva) < 400
                has_danda = DANDA in deva or DDANDA in deva
                tt = "colophon" if colo else ("mula" if has_danda else
                                              ("frontmatter" if not verses and len(DEV_LETTER.findall(deva)) < 25 else "prose"))
                if prose[0]:   # ETEXT_PROSE2_2026_10_22: a numbered kandika is prose, with its danda (kandas 1 to 9 put
                    tt, has_danda, colo = "prose", False, False   # one after its first clause) or not; never a colophon
                verses.append({"text": deva, "ref": ref, "chapter": chapter or str(chap[0]), "type": tt,
                               "padas": 2 * len(cur["lines"]) if has_danda else 0, "src_line": cur["src"],
                               "roman": "\n".join(cur["roman"]) if cur["roman"] else ""})
                if appendix[0] and ref.replace(".", "").isdigit() and \
                        tuple(int(x) for x in ref.split(".")) < appendix[0]:   # ETEXT_PROSE2_2026_10_22: an appendix,
                    verses[-1]["appendix"] = True                              # numbered below what came before it
                if colo:
                    st["colophons"] += 1
                    if not chapter:
                        chap[0] += 1
        cur.update({"lines": [], "roman": [], "ref": "", "src": 0})

    skip = gretil_header(lines)   # ETEXT_ORTHO_2026_10_21: GRETIL's English header, "Header" to "Text"
    for i, raw in enumerate(lines, 1):
        ln = raw.strip().replace(DANDA + DANDA, DDANDA)     # "\u0964\u0964" typed for the double danda
        if i in skip and ln:
            st["dropped_english"] += 1
            continue
        if raw.strip() == FILE_BREAK:   # ETEXT_PROSE_2026_10_21: the next file: what follows its title is a new unit
            flush()
            appendix[0] = ()   # ETEXT_PROSE2_2026_10_22: a separator's appendix ends with its file
            continue
        if prose[0] and G_SEPARATOR.match(ln or ""):   # ETEXT_PROSE2_2026_10_22: ****: what follows it, numbered below
            flush()                                    # what came before it, is an appendix
            appendix[0] = top[0]
            st["separators"] = st.get("separators", 0) + 1
            continue
        pr = prose_ref(ln, prose[0]) if ln else None   # ETEXT_PROSE_2026_10_21 (13.1.1.[1]); ETEXT_PROSE2_2026_10_22
        if pr:
            flush()
            ref_, rest_, kind_ = pr
            if kind_ == "glued" and last_unit[0]:   # ETEXT_PROSE2_2026_10_22: the typist's slip, 11.7.4.2 after 1.7.4.1
                a_ = last_unit[0].split(".")
                want = ".".join(a_[:-1] + [str(int(a_[-1]) + 1)])
                if ref_ != want and ref_[1:] == want:
                    ref_ = want
                    st["repaired"] = st.get("repaired", 0) + 1
            prose[0] = True
            cur["ref"] = ref_
            st["refs"] += 1
            if ref_.replace(".", "").isdigit():
                top[0] = max(top[0], tuple(int(x) for x in ref_.split(".")))
            if kind_ == "heading":
                st["headings"] = st.get("headings", 0) + 1
            else:
                st["prose_units"] = st.get("prose_units", 0) + 1
                last_unit[0] = ref_
            if not rest_:
                continue
            ln = rest_
        if not ln:
            st["blank"] += 1
            if not prose[0]:   # ETEXT_PROSE_2026_10_21: a prose unit runs to the next reference, blank lines and all
                flush()
            continue
        body, ref, where = take_ref(ln) if not prose[0] else (ln, "", "")
        d, l = _letters(body)
        if d + l < 3 and not ref:
            continue                                   # punctuation, a lone numeral
        if d < l and (sch == "devanagari" or is_english(body)):
            st["dropped_english"] += 1             # in a Devanagari text, a Latin line is never the text
            continue
        if ref and cur["ref"] and ref != cur["ref"] and cur["lines"]:
            flush()
        if ref:
            st["refs"] += 1
            cur["ref"] = ref
        if d + l >= 3:
            if not cur["lines"]:
                cur["src"] = i
            if d >= l:
                cur["lines"].append(to_deva(body, "devanagari")); st["devanagari"] += 1
            else:
                cur["lines"].append(to_deva(body, sch)); cur["roman"].append(body); st["romanized"] += 1
            st["kept"] += 1
        elif cur["lines"] and (ref or _ends_verse(body)):
            last = cur["lines"][-1].rstrip()          # a reference or a double danda on a line of its own
            if not last.endswith(DDANDA):
                cur["lines"][-1] = last + " " + DDANDA
        if not prose[0] and (_ends_verse(body) or (ref and where == "end") or len(cur["lines"]) >= 12):
            flush()   # ETEXT_PROSE_2026_10_21: a prose unit is not cut at 12 lines
    flush()
    if prose[0]:   # ETEXT_PROSE_2026_10_21: what stands outside a unit (a file's title, its notes) is not the text
        keep = [v for v in verses if v["ref"]]
        st["outside"] = len(verses) - len(keep)
        verses[:] = keep
        seen, keep = set(), []   # ETEXT_PROSE2_2026_10_22: a unit repeated word for word (the appendix's 14.3.2) once
        for v in verses:
            key = (v["ref"], re.sub(r"\s+", " ", v["text"]).strip())
            if key in seen:
                st["repeats"] = st.get("repeats", 0) + 1
                continue
            seen.add(key)
            keep.append(v)
        verses[:] = keep
        st["appendix_units"] = sum(1 for v in verses if v.get("appendix"))
        order = [tuple(int(x) for x in v["ref"].split(".")) for v in verses if v["ref"].replace(".", "").isdigit()]
        st["out_of_order"] = sum(1 for a_, b_ in zip(order, order[1:]) if b_ <= a_)
    return out


def paginate(verses: list, per_page: int) -> list:
    pages, cur, cur_ch = [], [], None
    for v in verses:
        ch = v.get("chapter")
        if cur and (len(cur) >= per_page or (ch and cur_ch and ch != cur_ch)):
            pages.append(cur); cur = []
        cur.append(v); cur_ch = ch
    if cur:
        pages.append(cur)
    return pages


def leftover_latin(verses: list) -> float:
    """The share of verses whose Devanagari still holds Latin letters: a wrong scheme, or notes in the lines."""
    if not verses:
        return 0.0
    return sum(1 for v in verses if ASCII_LETTER.search(kept_out(v["text"]))) / float(len(verses))   # ETEXT_ORTHO_2026_10_21


# ---- measured against the scan -------------------------------------------------------------------
def _uri(db: str) -> str:
    return Path(db).resolve().as_uri() + "?mode=ro"          # as dashboard.py's repair page: spaces and drives


def load_scan(db: str, doc: str):
    """{page_no: text} of the scan's passages (noise and front matter left out), or None when it is not there."""
    try:
        con = sqlite3.connect(_uri(db), uri=True, timeout=10)
    except sqlite3.Error:
        return None
    try:
        cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
        scope = " AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')" if "text_type" in cols else ""
        rows = con.execute("SELECT p.page_no, p.text FROM passages p JOIN docs d ON d.id=p.doc_id WHERE d.code=?%s "
                           "ORDER BY p.page_no, p.idx" % scope, (doc,)).fetchall()
    except sqlite3.Error:
        return None
    finally:
        con.close()
    if not rows:
        return None
    pages = {}
    for pg, t in rows:
        pages.setdefault(int(pg or 0), []).append(t or "")
    return {p: "\n".join(v) for p, v in pages.items()}


def doc_facts(db: str, doc: str) -> dict:
    """{"category", "passages", "english"} of a text, read-only; {} when it is not there."""
    try:
        con = sqlite3.connect(_uri(db), uri=True, timeout=10)
    except sqlite3.Error:
        return {}
    try:
        r = con.execute("SELECT d.id, d.category FROM docs d WHERE d.code=?", (doc,)).fetchone()
        if not r:
            return {}
        n, en = con.execute("SELECT COUNT(*), SUM(CASE WHEN TRIM(COALESCE(translation,''))<>'' THEN 1 ELSE 0 END) "
                            "FROM passages WHERE doc_id=?", (r[0],)).fetchone()
        return {"category": r[1], "passages": int(n or 0), "english": int(en or 0)}
    except sqlite3.Error:
        return {}
    finally:
        con.close()


def readable(text: str):
    """(readable, why) of one page of the scan."""
    d = len(DEV_LETTER.findall(text))
    a = len(ASCII_LETTER.findall(text))
    if d < 60:
        return False, "it has %d Devanagari letters" % d
    if a > 0.30 * (a + d):
        return False, "%d%% of its letters are Latin (Devanagari misread)" % round(100.0 * a / (a + d))
    return True, ""


def measure(verses: list, scan: dict) -> dict:
    """How the witness reads the scan, page by page, and the readings it offers for the pages the scan cannot read."""
    n_v = len(verses)
    wsk = [skel(v["text"]) for v in verses]
    index = {}
    for vi, s in enumerate(wsk):
        for i in range(len(s) - K + 1):
            lst = index.setdefault(s[i:i + K], [])
            if len(lst) <= 8 and (not lst or lst[-1] != vi):
                lst.append(vi)
    vgrams = [{s[i:i + K] for i in range(len(s) - K + 1)} for s in wsk]
    pages_all = sorted(scan)
    vpp = max(1.0, n_v / float(max(1, len(pages_all))))
    R = max(12, int(3 * vpp))
    res = {}
    for p in pages_all:
        text = scan[p]
        ok, why = readable(text)
        s = skel(text)
        grams = {s[i:i + K] for i in range(len(s) - K + 1)}
        hits = []
        for g in grams:
            lst = index.get(g)
            if lst and len(lst) <= 3:
                hits.extend((vi, 1.0 / len(lst), g) for vi in lst)
        r = {"readable": ok, "why": why, "grams": len(grams), "score": 0.0, "status": "none", "lo": None, "hi": None}
        if hits and grams:
            hits.sort()
            tot, acc, med = sum(w for _, w, _ in hits), 0.0, hits[0][0]
            for vi, w, _ in hits:
                acc += w
                if acc >= tot / 2:
                    med = vi
                    break
            kept = [(vi, w, g) for vi, w, g in hits if abs(vi - med) <= R]
            kg = {g for _, _, g in kept}
            weight = {}
            for vi, w, _ in kept:
                weight[vi] = weight.get(vi, 0.0) + w
            strong = sorted(vi for vi, w in weight.items() if w >= 2) or sorted(weight)
            lo, hi = strong[0], strong[-1]
            win = set().union(*(vgrams[i] for i in range(lo, hi + 1))) if hi >= lo else set()
            p_in_w = len(kg) / float(len(grams))
            w_in_p = (len(win & grams) / float(len(win))) if win else 0.0
            sc = max(p_in_w, w_in_p) if len(kg) >= 8 else min(p_in_w, w_in_p)
            r.update({"score": round(sc, 3), "lo": lo, "hi": hi, "in_witness": round(p_in_w, 3),
                      "witness_in_page": round(w_in_p, 3)})
            r["status"] = "match" if sc >= MATCH and len(kg) >= 8 else ("weak" if sc >= WEAK else "none")
        res[p] = r
    readable_pages = [p for p in pages_all if res[p]["readable"]]
    matched = [p for p in pages_all if res[p]["status"] == "match"]
    pairs = list(zip(matched, matched[1:]))
    in_order = sum(1 for a, b in pairs if (res[b]["lo"] + res[b]["hi"]) / 2.0 >= (res[a]["lo"] + res[a]["hi"]) / 2.0 - 1)
    order = in_order / float(len(pairs)) if pairs else (1.0 if matched else 0.0)
    cov = len([p for p in readable_pages if res[p]["status"] == "match"]) / float(len(readable_pages)) if readable_pages else 0.0
    span = (min(res[p]["lo"] for p in matched), max(res[p]["hi"] for p in matched)) if matched else None
    # the missing pages: unreadable, absent from the database, or not read while both neighbours are
    lo_pg, hi_pg = (pages_all[0], pages_all[-1]) if pages_all else (0, -1)
    offers = []
    for p in range(lo_pg, hi_pg + 1):
        r = res.get(p)
        if r is None:
            why = "the page is not in the database"
        elif not r["readable"]:
            why = "the scan cannot read it: " + r["why"]
        elif r["status"] != "match":
            why = "the witness does not find it (score %.2f), though it reads the pages around it" % r["score"]
        else:
            continue
        a = max((q for q in matched if q < p), default=None)
        b = min((q for q in matched if q > p), default=None)
        if a is None or b is None or b - a > 5:
            continue
        if r is not None and r["readable"] and r["status"] != "match" and (p - a > 1 or b - p > 1):
            continue                                      # a readable page the witness misses, far from both: not a gap
        g0, g1 = res[a]["hi"] + 1, res[b]["lo"] - 1
        if r is not None and r.get("lo") is not None and g0 <= r["lo"] <= r["hi"] <= g1:
            v0, v1 = r["lo"], r["hi"]                     # its own weak hits fall in the gap: its own window
        else:
            gap_pages = b - a - 1
            n = g1 - g0 + 1
            if n <= 0:
                offers.append({"page": p, "why": why, "from": [a, b], "lo": None, "hi": None, "refs": "",
                               "text": "", "note": "the witness has nothing between pages %d and %d: this page may be "
                                                  "commentary, a plate or a note" % (a, b)})
                continue
            k = p - a - 1
            v0 = g0 + (n * k) // gap_pages
            v1 = g0 + (n * (k + 1)) // gap_pages - 1
        if v1 < v0:
            continue
        if v1 - v0 + 1 > 4 * vpp + 5:
            offers.append({"page": p, "why": why, "from": [a, b], "lo": v0, "hi": v1, "refs": "", "text": "",
                           "note": "%d verses: too many for one page; read it beside the e-text" % (v1 - v0 + 1)})
            continue
        refs = [verses[i]["ref"] for i in range(v0, v1 + 1) if verses[i]["ref"]]
        offers.append({"page": p, "why": why, "from": [a, b], "lo": v0, "hi": v1,
                       "refs": ("%s-%s" % (refs[0], refs[-1]) if len(refs) > 1 else (refs[0] if refs else "")),
                       "text": "\n".join(verses[i]["text"] for i in range(v0, v1 + 1))[:4000], "note": ""})
    return {"pages": res, "scan_pages": len(pages_all), "readable": len(readable_pages), "matched": len(matched),
            "matched_readable": len([p for p in readable_pages if res[p]["status"] == "match"]),   # QUALITY_2026_10_11
            "coverage": round(cov, 3), "order": round(order, 3), "span": span, "verses": n_v, "offers": offers,
            "verses_per_page": round(vpp, 2)}


def judged_level(doc: str) -> str:
    try:
        return str(json.loads((ROOT / "data" / "source_judged" / ("%s.json" % doc)).read_text(encoding="utf-8"))
                   .get("level") or "")
    except (OSError, ValueError):
        return ""


def opinion(m, doc: str) -> str:
    if m is None:
        return "the scan is not in the database: nothing to measure; the witness can still be its own text"
    mr, rd, n = m.get("matched_readable", m["matched"]), m["readable"], m["scan_pages"]
    if rd < max(3, 0.1 * n):
        # QUALITY_2026_10_11: a scan this damaged is measured by all its pages; the witness still finds a damaged
        # page when enough of its letters survive (on 11 Oct the Bodhicaryavatara read 3 of 253 pages, and
        # "159 of 3 readable pages" was printed)
        share = m["matched"] / float(n) if n else 0.0
        if m["matched"] >= 10 and share >= 0.5 and m["order"] >= 0.8:
            return ("the same work, in the same order, by the scan's damaged pages: the scan reads %d of its %d pages, and "
                    "the witness still finds %d of them (%.0f%%, in order %.0f%%)" % (rd, n, m["matched"], 100 * share,
                                                                                   100 * m["order"]))
        if m["matched"] >= 10 and share >= 0.2:
            return ("probably the same work, in part: the scan reads %d of its %d pages, and the witness finds %d of them "
                    "(%.0f%%, in order %.0f%%)" % (rd, n, m["matched"], 100 * share, 100 * m["order"]))
        return ("the scan reads %d of its %d pages: too few to tell whether it is the same text (the witness finds %d); "
                "the witness can stand in for it" % (rd, n, m["matched"]))
    if m["coverage"] >= 0.6 and m["order"] >= 0.8:
        return "the same work, in the same order: it reads %d of the scan's %d readable pages (%.0f%%, in order %.0f%%)" % (
            mr, rd, 100 * m["coverage"], 100 * m["order"])
    if m["coverage"] >= 0.25:
        return ("the same work in part, or another recension: it reads %d of %d readable pages (%.0f%%, in order %.0f%%)"
                % (mr, rd, 100 * m["coverage"], 100 * m["order"]))
    lv = judged_level(doc)
    return ("not the same text as the scan, or the scan is too garbled to tell (%d of %d readable pages read%s)"
            % (mr, rd, "; its debris is judged %s" % lv if lv else ""))


# ---- the Devanagari judged (QUALITY_2026_10_11) ---------------------------------------------------
# A reading can be free of Latin letters and still be noise: archive.org's OCR of the 1960 Bodhicaryavatara
# has no Latin, and noise in 9.4% of its words (malformed 3.2%, stray marks 5.5%). Three measures; the first two need
# no reference text:
#   glued      a Latin letter or a stray mark stuck to Devanagari in one word: the vision model's "V" for
#              a printed pratika mark (Rgveda vol. ii: 8,602 words on 230 of its 446 vision pages), OCR's "^", "~", "+"
#   malformed  a Devanagari word that cannot be written so: it starts with a vowel sign, an anusvara or a
#              virama, or has two vowel signs, a vowel sign after a virama or after an independent vowel;
#              and the marks that are no Sanskrit (^ ~ + = < > ...) standing alone
#   plausible  the share of its letter trigrams (within words) that occur twice or more in a clean Sanskrit
#              text: the BORI Mahabharata, Adiparvan, from GRETIL (data/raw/MBh01_*, SA_QUALITY_REF names
#              another). It depends on the genre (an agama reads 87-89%, the Shatapatha 93%), so it compares
#              readings of one text; it is no grade by itself.
# Critical apparatus ("-B, C."), Vedic accents, numerals and dandas are not counted as noise.
QA_ACCENTS = re.compile("[\u0951-\u0954\u1cd0-\u1cff\ua8e0-\ua8ff]")
QA_STRIP = re.compile("[\u0964\u0965\u0966-\u096f\u0970\u0971.,;:!?()\\[\\]{}'\"\u2018\u2019\u201c\u201d\u2013\u2014\\-_*|/\\\\0-9\u00b7\u2022]")
QA_START = re.compile("^[\u0900-\u0903\u093a\u093b\u093c\u093e-\u094d\u094e\u094f\u0955-\u0957\u0962\u0963]")
QA_MATRA = "[\u093e-\u094c\u0962\u0963]"
QA_BAD = re.compile(QA_MATRA + QA_MATRA + "|\u094d" + QA_MATRA + "|\u094d\u094d|[\u0905-\u0914]" + QA_MATRA)
QA_GLUED = re.compile("[\u0900-\u097f][A-Za-z^~`$#@%&=+<>]|[A-Za-z^~`$#@%&=+<>][\u0900-\u097f]")
QA_GLUE = re.compile(r"[A-Za-z^~`$#@%&=+<>]+")
QA_JUNKSYM = re.compile(r"^[\^~`$#@%&=+<>]+$")
QA_WORD = re.compile("[\u0900-\u0963\u0971-\u097f]+")
QA_REF = os.environ.get("SA_QUALITY_REF") or "data/raw/MBh01_*.jsonl"
# Measured on 11 Oct: the GRETIL Adiparvan 0.0% of its words; vision OCR of a clean print 0.06-0.86% (the Shatapatha,
# Karan, the Markandeya, the Mallapurana, Sandilya, Hayashirsha, the Tantric Texts); Tesseract 2.7-7.4%; archive.org's
# OCR of the 1960 Bodhicaryavatara 9.4%. A witness no cleaner than Tesseract adds nothing to the scan.
NOISY, NOISE_WARN = 3.0, 1.5      # % of words: a damaged OCR text (Tesseract's grade) / some noise (above vision's)
_REF = []


def _trigrams(text: str) -> list:
    out = []
    for w in QA_WORD.findall(QA_ACCENTS.sub("", text or "")):
        w = " " + w + " "
        out.extend(w[i:i + 3] for i in range(len(w) - 2))
    return out


def reference_trigrams() -> set:
    """The letter trigrams seen twice or more in the clean reference text (read once); empty when it is not there."""
    if _REF:
        return _REF[0]
    import glob as _glob
    counts = {}
    for p in sorted(_glob.glob(QA_REF)):
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if line.strip():
                        try:
                            for g in _trigrams(json.loads(line).get("text") or ""):
                                counts[g] = counts.get(g, 0) + 1
                        except ValueError:
                            continue
        except OSError:
            continue
    _REF.append({g for g, c in counts.items() if c >= 2})
    return _REF[0]


def quality(texts, plausible: bool = True) -> dict:
    """The noise in the Devanagari of a reading (see above): {words, glued_pct, malformed_pct, symbols_pct,
    noise_pct, plausible_pct, glued_top}. Latin-only words are the judge's (repair_text.judge), not counted here."""
    words = glued = malformed = junk = tg = hit = 0
    ref = reference_trigrams() if plausible else set()
    top = {}
    for t in texts:
        for tok in (t or "").split():
            raw = QA_ACCENTS.sub("", tok)
            if QA_JUNKSYM.match(raw):
                words += 1; junk += 1
                continue
            if not DEV_LETTER.search(raw):
                continue
            words += 1
            if QA_GLUED.search(raw):
                glued += 1
                for g in QA_GLUE.findall(raw):
                    top[g] = top.get(g, 0) + 1
                continue
            core = QA_STRIP.sub("", raw)
            if core and (QA_START.search(core) or QA_BAD.search(core)):
                malformed += 1
        if ref:
            for g in _trigrams(t):
                tg += 1
                hit += g in ref
    pct = lambda x: round(100.0 * x / words, 2) if words else 0.0
    return {"words": words, "glued_pct": pct(glued), "malformed_pct": pct(malformed), "symbols_pct": pct(junk),
            "noise_pct": pct(glued + malformed + junk), "plausible_pct": round(100.0 * hit / tg, 1) if (ref and tg) else None,
            "glued_top": [g for g, _ in sorted(top.items(), key=lambda x: -x[1])[:3]]}


def quality_line(label: str, q) -> str:
    if not q:
        return "%s: -" % label
    return ("%s: noise in %.1f%% of its words (glued %.1f, malformed %.1f, stray marks %.1f)%s"
            % (label, q["noise_pct"], q["glued_pct"], q["malformed_pct"], q["symbols_pct"],
               (", plausible %.1f%%" % q["plausible_pct"]) if q.get("plausible_pct") is not None else ""))


# ---- the files -------------------------------------------------------------------------------------
def site_of(path: Path, url: str = "") -> str:
    side = {}
    try:
        side = json.loads(path.with_name(path.name + ".json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    probe = " ".join([url, str(side.get("url") or ""), str(side.get("details") or ""), path.name]).lower()
    for key, site in SITES:
        if key in probe:
            return site
    return "etext"


def host_ok(host: str) -> bool:
    host = (host or "").lower()
    return any(host == h or host.endswith("." + h) for h in HOSTS)


def fetch_url(url: str, doc: str, dest_root: Path):
    """Save an e-text into sources/<doc>/ with its provenance beside it. -> (path, error)."""
    u = urllib.parse.urlparse(url)
    if u.scheme not in ("http", "https") or not host_ok(u.hostname):
        return None, ("refused: %s is not one of the e-text hosts (%s; SA_ETEXT_HOSTS adds more)"
                      % (u.hostname or url, ", ".join(HOSTS)))
    if "archive.org" in (u.hostname or "") and "/details/" in u.path:
        ident = u.path.split("/details/", 1)[1].split("/")[0]
        return None, ("an archive.org page, not a file: python scripts\\source_desk.py --doc %s --fetch %s --kind text"
                      % (doc, ident))
    name = re.sub(r"[^A-Za-z0-9._\-]", "_", Path(urllib.parse.unquote(u.path)).name or "etext.html")[:120]
    if "." not in name:
        name += ".html"
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=120) as f:
            data = f.read(MAX_BYTES + 1)
    except Exception as e:  # noqa: BLE001 - one line is enough for the dashboard
        return None, "could not fetch %s: %s" % (url, str(e)[:160])
    if len(data) > MAX_BYTES:
        return None, "refused: more than %d MB" % (MAX_BYTES // 1_000_000)
    dest = dest_root / doc
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / name
    tmp = target.with_name(target.name + ".part")
    tmp.write_bytes(data)
    os.replace(tmp, target)
    side = {"doc": doc, "kind": "etext", "url": url, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "at": _now(), "mark": MARK}
    target.with_name(target.name + ".json").write_text(json.dumps(side, ensure_ascii=False, indent=1), encoding="utf-8")
    return target, ""


def witnesses(path: Path) -> dict:
    """witness -> its latest line in data/witnesses.jsonl."""
    out = {}
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if isinstance(r, dict) and r.get("witness"):
                out[r["witness"]] = dict(out.get(r["witness"], {}), **r)
    except OSError:
        pass
    return out


def _append(path: Path, rec: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def records(parsed: dict, pages: list, engine: str, doc: str, src: str) -> list:
    """[(page_no, [record, ...])] for ingest_jsonl_fast.py."""
    out = []
    if parsed["mode"] == "pages":
        for n, pg in enumerate(pages, 1):
            out.append((n, [{"text": pg["text"], "engine": engine, "page_no": n,
                             "meta": {"witness_of": doc, "src": src, "src_page": pg["page"]}}]))
        return out
    for n, pg in enumerate(pages, 1):
        recs = []
        for v in pg:
            r = {"text": v["text"], "engine": engine, "page_no": n, "verse_ref": v["ref"] or None,
                 "chapter": v["chapter"] or None, "text_type": v["type"], "padas": v["padas"],
                 "quality_score": QUALITY, "meta": {"witness_of": doc, "src": src, "src_line": v["src_line"]}}
            if v.get("roman"):
                r["meta"]["roman_source"] = v["roman"]
            if v.get("appendix"):   # ETEXT_PROSE2_2026_10_22: after the e-text's separator line
                r["meta"]["after_separator"] = True
            recs.append(r)
        out.append((n, recs))
    return out


# ---- the steps -------------------------------------------------------------------------------------
def say(verdict: str, nxt: str = "", also=()):
    print("VERDICT: " + verdict)
    print("NEXT: " + nxt)
    for x in also:
        print("ALSO: " + x)


def page_example(m) -> list:
    """ETEXT_PAGE_2026_10_18: a real page for the ALSO line (on 18 Oct its "--page N" was run as it stood): the first
    page of the scan the witness reads, else the first it offers for a page the scan cannot read, else the scan's first
    page; [] with no scan to compare (--page would refuse)."""
    if not m:
        return []
    pages = m.get("pages") or {}
    hit = sorted(p for p, r in pages.items() if (r or {}).get("status") == "match")
    off = sorted(o.get("page") for o in (m.get("offers") or []) if o.get("text") and o.get("page") is not None)
    first = hit or off or sorted(pages)
    return [first[0]] if first else []


def also_page(q: str, m, what: str) -> list:
    """ETEXT_PAGE_2026_10_18: the ALSO line, with a page that exists, or none."""
    return [q + " --page %d   (%s)" % (p, what) for p in page_example(m)]


def show_page(m: dict, verses: list, page: int):
    r = m["pages"].get(page)
    offer = next((o for o in m["offers"] if o["page"] == page), None)
    if r and r["status"] == "match":
        refs = [verses[i]["ref"] for i in range(r["lo"], r["hi"] + 1) if verses[i]["ref"]]
        print("  page %d: the witness reads it (score %.2f): its verses %d-%d%s" % (
            page, r["score"], r["lo"] + 1, r["hi"] + 1, (" (%s-%s)" % (refs[0], refs[-1])) if refs else ""))
        for i in range(r["lo"], r["hi"] + 1):
            print("    " + verses[i]["text"].replace("\n", " "))
    elif offer and offer.get("text"):
        print("  page %d: %s; the witness reads, between pages %d and %d (verses %d-%d%s):" % (
            page, offer["why"], offer["from"][0], offer["from"][1], offer["lo"] + 1, offer["hi"] + 1,
            (", " + offer["refs"]) if offer["refs"] else ""))
        for ln in offer["text"].split("\n"):
            print("    " + ln)
    elif offer:
        print("  page %d: %s; %s" % (page, offer["why"], offer["note"]))
    else:
        print("  page %d: %s" % (page, ("status %s (score %.2f)" % (r["status"], r["score"])) if r else "not in the scan"))


def preview_or_write(a) -> int:
    doc = a.doc
    src = Path(a.file) if a.file else None
    if a.url and not src:
        src, err = fetch_url(a.url, doc, Path(a.sources))
        if err:
            say(err, "")
            return 1
        print("saved %s (%d bytes) with its provenance beside it" % (src, src.stat().st_size))
    if not src or not (src.is_file() or src.is_dir()):   # ETEXT_PROSE_2026_10_21: a folder of files is one text
        say("no such file: %s" % (src or "(none)"), "")
        return 1
    text, info = read_source(src)
    parsed = parse(text, a.scheme, a.pages)
    st = parsed["stats"]
    site = a.slug or site_of(src, a.url or "")
    engine = "etext:archive-ocr" if site == "archive" else "etext:" + site
    wcode = "%s__w_%s" % (doc, re.sub(r"[^A-Za-z0-9]", "", site).lower() or "etext")
    print("%s: %s (%d bytes, %s, %s) as a witness of %s" % (MARK, src.name, info["bytes"], info["kind"], info["encoding"], doc))
    if info["note"]:
        print("  note: " + info["note"])
    if info.get("files"):   # ETEXT_PROSE_2026_10_21
        print("  files: %d, read in this order: %s" % (len(info["files"]), ", ".join(f["name"] for f in info["files"])))
    if parsed["scheme"] == "unknown":
        say("cannot tell the script of %s: it is not Devanagari, and no IAST marks, Harvard-Kyoto capitals or Velthuis "
            "dots were found" % src.name,
            'python scripts\\etext_witness.py --doc %s --file "%s" --scheme hk   (or iast, velthuis, itrans)' % (doc, src))
        return 1
    if parsed["scheme"] != "devanagari":
        try:
            import indic_transliteration  # noqa: F401
        except ImportError:
            say("the text is romanized (%s) and indic_transliteration is not installed" % parsed["scheme"],
                "pip install indic_transliteration")
            return 1
    print("  read: %d lines; kept %d (romanized %d, Devanagari %d); dropped %d English or header line(s); scheme %s"
          % (st["lines"], st["kept"], st["romanized"], st["devanagari"], st["dropped_english"], parsed["scheme"]))
    if parsed["mode"] == "pages":
        units = parsed["pages"]
        pages = units
        verses = [{"text": p["text"], "ref": "", "chapter": "", "type": "mula", "padas": 0, "src_line": 0, "roman": ""}
                  for p in units]
        print("  pages: %d, as the source has them (form feeds); segmented into verses at ingest" % len(pages))
    else:
        verses = parsed["verses"]
        pages = paginate(verses, a.per_page)
        chs = len({v["chapter"] for v in verses})
        print("  verses: %d (with a reference %d; chapters %d; colophons %d); pages of up to %d verses: %d"
              % (len(verses), sum(1 for v in verses if v["ref"]), chs, st["colophons"], a.per_page, len(pages)))
    if st.get("prose_units"):   # ETEXT_PROSE_2026_10_21
        longest = max((len(v["text"]) for v in verses), default=0)
        print("  prose: %d units by their reference lines (13.1.1.[1]); %d passage(s) outside a unit left out (a file's "
              "title, its notes); the longest unit %d characters; no danda added" % (st["prose_units"],
                                                                                    st.get("outside", 0), longest))
        if any(st.get(k) for k in ("headings", "repeats", "repaired", "separators", "out_of_order")):   # ETEXT_PROSE2_2026_10_22
            print("  prose, the e-text's other shapes: %d brahmana number(s) over its text or as a heading (14.6.4.); %d "
                  "unit(s) repeated word for word left out; %d number(s) mistyped and read by their neighbours (11.7.4.2 "
                  "for 1.7.4.2); %d separator line(s), %d unit(s) after one (an appendix: read them beside the text); %d "
                  "unit(s) out of order" % (st.get("headings", 0), st.get("repeats", 0), st.get("repaired", 0),
                                            st.get("separators", 0), st.get("appendix_units", 0),
                                            st.get("out_of_order", 0)))
    for v in verses[:3]:
        print("  sample%s: %s" % ((" " + v["ref"]) if v["ref"] else "", v["text"].replace("\n", " ")[:160]))
    lat = leftover_latin(verses)
    if lat > 0.02:
        print("  Latin letters are left in %.0f%% of the verses" % (100 * lat))
    if len(verses) < 5:
        say("%s holds %d verse(s) of Sanskrit: too little to be a witness" % (src.name, len(verses)), "")
        return 1
    scan = load_scan(a.db, doc)
    m = measure(verses, scan) if scan else None
    wq = quality(v["text"] for v in verses)                      # QUALITY_2026_10_11: the witness's own Devanagari
    info["quality"] = wq
    sq = quality(scan.values()) if scan else None
    print("  quality: " + quality_line("the witness", wq) + ((" | " + quality_line("the scan", sq)) if sq else ""))
    if m:
        print("  against the scan (%s): %d pages, %d readable; the witness finds %d of the readable ones (%.0f%%) and %d "
              "pages in all, in the scan's order %.0f%%" % (a.db, m["scan_pages"], m["readable"], m.get("matched_readable", 0),
                                                         100 * m["coverage"], m["matched"], 100 * m["order"]))
        if m["span"]:
            print("  the scan's pages run over the witness's verses %d-%d of %d" % (m["span"][0] + 1, m["span"][1] + 1, len(verses)))
        got = [o for o in m["offers"] if o.get("text")]
        if m["offers"]:
            print("  pages the scan cannot read: %d; the witness offers a reading for %d: %s" % (
                len(m["offers"]), len(got), ", ".join(str(o["page"]) for o in got[:30]) + (" ..." if len(got) > 30 else "")))
    op = opinion(m, doc)
    print("WITNESS: " + op)
    if a.page is not None:
        if not m:
            say("no scan to compare page %d with" % a.page, "")
            return 1
        show_page(m, verses, a.page)
        say("page %d of %s, as the witness reads it" % (a.page, doc), "")
        return 0
    q = 'python scripts\\etext_witness.py --doc %s --file "%s"' % (doc, src)
    if lat > 0.10:
        say("not a witness yet: Latin letters are left in %.0f%% of its verses (a wrong scheme, or notes inside the lines)"
            % (100 * lat), q + " --scheme hk   (or iast, velthuis, itrans; or clean the file)")
        return 1
    weak = bool(m) and m["readable"] >= 10 and m["coverage"] < 0.10
    # QUALITY_2026_10_11: an OCR text as damaged as the scan does not repair it; it trades the scan's Latin debris
    # for its own Devanagari debris
    noisy = wq["noise_pct"] > NOISY
    if noisy:
        print("  the witness is itself a damaged OCR text: %.1f%% of its words are malformed or carry stray marks "
              "(vision OCR of a clean print has under 1.5%%; a clean e-text none)" % wq["noise_pct"])
    elif wq["noise_pct"] > NOISE_WARN:
        print("  the witness has some noise of its own (%.1f%% of its words): read its pages beside the scan" % wq["noise_pct"])
    if not a.write:
        if weak or noisy:
            print("  (--write --force makes it a witness all the same)")
            say("%s: %s; it should not be made a witness of this text%s" % (
                src.name, op, ": its own text is damaged (noise %.1f%%)" % wq["noise_pct"] if noisy else ""), "",
                also_page(q, m, "the witness's reading of one page of the scan"))   # ETEXT_PAGE_2026_10_18
            return 0
        say("%s reads as %d verses in %d pages: %s" % (src.name, len(verses), len(pages), op), q + " --write",
            also_page(q, m, "the witness's reading of one page of the scan"))   # ETEXT_PAGE_2026_10_18
        return 0
    if (weak or noisy) and not a.force:
        say("refused: %s; --force makes it a witness all the same" % (
            op if weak else "the witness is itself a damaged OCR text (noise in %.1f%% of its words)" % wq["noise_pct"]), "")
        return 1
    return write(a, doc, wcode, parsed, pages, verses, m, src, info, site, engine, op)


def write(a, doc, wcode, parsed, pages, verses, m, src, info, site, engine, op) -> int:
    out = Path(a.out_dir) / wcode
    facts = doc_facts(a.db, wcode)
    if facts.get("passages"):
        say("refused: %s is in the database already (%d passages): rewriting its pages would leave its translations "
            "beside a different text. Wipe it first (python scripts\\wipe_doc.py --doc %s --yes) or choose another --slug"
            % (wcode, facts["passages"], wcode), "")
        return 1
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if out.exists() and any(out.glob("*.jsonl")):
        if not a.force:
            say("refused: %s holds a witness already; --force keeps it as %s.bak_%s and writes this one" % (out, out.name, stamp), "")
            return 1
        shutil.move(str(out), str(out.with_name(out.name + ".bak_" + stamp)))
    out.mkdir(parents=True, exist_ok=True)
    recs = records(parsed, pages, engine, doc, src.name)
    for n, rs in recs:
        p = out / ("%s_%04d.jsonl" % (wcode, n))
        tmp = p.with_name(p.name + ".tmp")
        tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rs), encoding="utf-8")
        os.replace(tmp, p)
    scan_facts = doc_facts(a.db, doc)
    side = {}
    try:
        side = json.loads(src.with_name(src.name + ".json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    meta = {"witness": wcode, "doc": doc, "site": site, "engine": engine, "mode": parsed["mode"],
            "scheme": parsed["scheme"], "file": str(src), "url": a.url or side.get("url") or side.get("details") or "",
            "sha256": info["sha256"], "bytes": info["bytes"], "pages": len(recs), "verses": len(verses),
            "category": scan_facts.get("category") or a.category or None,   # ETEXT_PROSE_2026_10_21: a new text's
            "files": info.get("files"), "stats": parsed["stats"], "opinion": op, "at": _now(), "mark": MARK,
            "quality": info.get("quality")}   # QUALITY_2026_10_11
    (out / "witness.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    align = {"doc": doc, "witness": wcode, "at": meta["at"], "mark": MARK, "k": K, "opinion": op}
    if m:
        align.update({k: m[k] for k in ("scan_pages", "readable", "matched", "coverage", "order", "span", "offers",
                                         "verses_per_page")})
        align["pages"] = {str(p): r for p, r in m["pages"].items()}
    (out / "align.json").write_text(json.dumps(align, ensure_ascii=False, indent=1), encoding="utf-8")
    line = {"doc": doc, "witness": wcode, "site": site, "engine": engine, "mode": parsed["mode"], "file": src.name,
            "url": meta["url"], "sha256": info["sha256"], "pages": len(recs), "verses": len(verses),
            "coverage": m["coverage"] if m else None, "order": m["order"] if m else None,
            "offered": len([o for o in (m or {}).get("offers", []) if o.get("text")]), "opinion": op,
            "noise_pct": (info.get("quality") or {}).get("noise_pct"),   # QUALITY_2026_10_11
            "at": meta["at"], "mark": MARK}
    _append(Path(a.witnesses), line)
    # BENCHMARK_2026_10_11: always. The witness is not in the database (refused above), so a "released" of its
    # name is stale (on 11 Oct a placeholder command wrote one for Bodhicaryavatara__w_gretil)
    _append(Path(a.verdicts), {"doc": wcode, "status": "witness", "of": doc, "site": site,
                               "reason": "an e-text witness of %s (%s): local only until it is adopted" % (doc, site),
                               "at": meta["at"], "by": "etext_witness.py", "mark": MARK})
    print("wrote %d page file(s), %d verses, to %s (witness.json and align.json beside them)" % (len(recs), len(verses), out))
    say("%s is written: %d verses in %d pages; local only (the register says witness, so the mirror leaves it alone); "
        "the database is not touched" % (wcode, len(verses), len(recs)),
        "python scripts\\etext_witness.py --doc %s --ingest --witness %s" % (doc, wcode),
        also_page('python scripts\\etext_witness.py --doc %s --file "%s"' % (doc, src), m,
                  "the witness's reading of a page"))   # ETEXT_PAGE_2026_10_18
    return 0


def ingest(a) -> int:
    doc = a.doc
    ws = {w: r for w, r in witnesses(Path(a.witnesses)).items() if r.get("doc") == doc}
    wcode = a.witness or (max(ws.values(), key=lambda r: r.get("at", ""))["witness"] if ws else "")
    if not wcode or not re.match(r"^[A-Za-z0-9_\-]+$", wcode) or not wcode.startswith(doc + "__w_"):
        say("no witness of %s to ingest: write one first (--file ... --write)" % doc, "")
        return 1
    out = Path(a.out_dir) / wcode
    try:
        meta = json.loads((out / "witness.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        say("%s has no witness.json: write it again (--write --force)" % out, "")
        return 1
    files = sorted(out.glob("%s_*.jsonl" % wcode))
    if not files:
        say("%s holds no pages" % out, "")
        return 1
    have = doc_facts(a.db, wcode)
    if have.get("passages"):
        say("%s is in the database already: %d passages, %d with English" % (wcode, have["passages"], have["english"]),
            "translate %s: English, then Hindi, from the Library" % wcode)
        return 0
    w = rt.writers_running(a.from_dashboard, doc)
    if w:
        say("not now: the dashboard runs a database writer (%s)" % ", ".join("%s %s" % (j.get("kind"), j.get("doc")) for j in w),
            "python scripts\\etext_witness.py --doc %s --ingest --witness %s" % (doc, wcode))
        return 1
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = Path(a.backup_dir) / ("context_pre_witness_%s_%s.db" % (wcode, stamp))
    if rt.run([rt.PY, rt.SCRIPTS / "db_backup.py", a.db, backup]) != 0 or not backup.exists():
        say("the backup failed; nothing was changed", "")
        return 1
    argv = [rt.PY, rt.SCRIPTS / "ingest_jsonl_fast.py", "--doc", wcode, "--glob", str(out / ("%s_*.jsonl" % wcode)),
            "--db", a.db, "--source", "given"]
    if meta.get("mode") != "pages":
        argv.append("--no-segment")
    if meta.get("category"):
        argv += ["--category", str(meta["category"])]
    if rt.run(argv) != 0:
        say("the ingest failed; the backup made before is %s (the scan was not touched)" % backup, "")
        return 1
    now = doc_facts(a.db, wcode)
    _append(Path(a.witnesses), {"doc": doc, "witness": wcode, "ingested": now.get("passages", 0), "backup": str(backup),
                                "at": _now(), "mark": MARK})
    say("%s is in the database as its own text: %d passages; local only until it is translated and adopted; backup %s"
        % (wcode, now.get("passages", 0), backup),
        "translate %s: English, then Hindi, from the Library (Not yet readable)" % wcode,
        ["python scripts\\repair_text.py --doc %s --release   (adopt it: publish it to the site once translated)" % wcode,
         "python scripts\\diag_retire_check.py --src %s --keep %s, then python scripts\\retire_doc.py --doc %s "
         "--supersedes %s --dry-run   (only if the witness replaces the scan)" % (doc, wcode, doc, wcode)])
    return 0


def list_witnesses(a) -> int:
    reg = rt.verdicts(Path(a.verdicts))
    ws = witnesses(Path(a.witnesses))
    rows = [r for r in ws.values() if not a.doc or r.get("doc") == a.doc]
    for r in sorted(rows, key=lambda x: x.get("at", "")):
        st = (reg.get(r["witness"]) or {}).get("status") or "-"
        print("%s  %-9s %-60s %s verses, %s pages, coverage %s%s" % (
            str(r.get("at", "?"))[:16], st, r["witness"][:60], r.get("verses", "?"), r.get("pages", "?"),
            ("%.0f%%" % (100 * r["coverage"])) if isinstance(r.get("coverage"), (int, float)) else "-",
            ("; ingested %s" % r["ingested"]) if r.get("ingested") is not None else ""))
    say("%d witness(es)%s" % (len(rows), (" of " + a.doc) if a.doc else ""), "")
    return 0


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description="An e-text as a witness of a scan (ETEXT_WITNESS_2026_10_11)")
    ap.add_argument("--doc")
    ap.add_argument("--file")
    ap.add_argument("--url")
    ap.add_argument("--write", action="store_true", help="write the witness's pages (never the database)")
    ap.add_argument("--ingest", action="store_true", help="a backup, then ingest the written witness as its own text")
    ap.add_argument("--witness", help="with --ingest: which witness (default: the latest of --doc)")
    ap.add_argument("--page", type=int, default=None, help="the witness's reading of this page of the scan")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--scheme", choices=("auto", "devanagari", "iast", "hk", "velthuis", "itrans"), default="auto")
    ap.add_argument("--pages", choices=("auto", "source", "verses"), default="auto",
                    help="auto: the source's own pages when it has form feeds, else pages of --per-page verses")
    ap.add_argument("--per-page", type=int, default=20)
    ap.add_argument("--slug", default=None, help="the witness's name after __w_ (default: the site)")
    ap.add_argument("--category", default=None,   # ETEXT_PROSE_2026_10_21
                    help="a new text's category (brahmana, veda, ...), when it is no scan's witness")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--sources", default="sources")
    ap.add_argument("--out-dir", default="data/raw_witness")
    ap.add_argument("--witnesses", default="data/witnesses.jsonl")
    ap.add_argument("--verdicts", default="data/source_verdicts.jsonl")
    ap.add_argument("--backup-dir", default=os.environ.get("SA_BACKUP_DIR") or r"D:\backups")
    ap.add_argument("--from-dashboard", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    os.chdir(ROOT)
    if a.list:
        return list_witnesses(a)
    if not a.doc or not re.match(r"^[A-Za-z0-9_\-]+$", a.doc):
        print("FAIL: --doc <code> is needed (letters, digits, _ and -)."); return 2
    if a.slug and not re.match(r"^[A-Za-z0-9]{1,20}$", a.slug):
        print("FAIL: --slug is letters and digits (up to 20)."); return 2
    if a.category and not re.match(r"^[a-z][a-z_]{1,30}$", a.category):   # ETEXT_PROSE_2026_10_21
        print("FAIL: --category is lower-case letters and _ (brahmana, veda, ...)."); return 2
    if a.ingest:
        return ingest(a)
    if not a.file and not a.url:
        print("FAIL: --file <path> or --url <link> is needed (or --ingest, or --list)."); return 2
    a.per_page = max(1, min(200, a.per_page))
    return preview_or_write(a)


if __name__ == "__main__":
    sys.exit(main())
