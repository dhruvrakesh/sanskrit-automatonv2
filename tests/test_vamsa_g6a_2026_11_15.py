# -*- coding: ascii -*-
"""VAMSA_G6A_2026_11_15 (G6a). Asked on 15 Nov: "authoritative genealogies of these kings ... the sanskrit texts (primary
and critical editions, wherever possible)". vamsa_read.py is taught the genealogical chapters of the Harivamsa, the
Ramayana, the Mahabharata's Adiparvan and the Puranas of GRETIL's archive: each work's verse marks as they are written
(two numbers, no closing //, half-verses, the Mahabharata's lines), the colophons, headings, page marks and footnotes
out, a star passage out, a misprinted mark mended, a number given twice kept. The three works of G5a are cut as before
and are still all that --work all (and the site's dynasties) reads. A run with a stubbed Claude: nothing is sent.
Temp folders only; small texts written here in the files' own shapes (never GRETIL's text)."""
import argparse, io, json, sqlite3, subprocess, sys, tempfile, unittest, zipfile
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import vamsa_read as VR                    # noqa: E402
import claude_engine as CE                 # noqa: E402
import test_vamsa_read_2026_11_11 as T0    # noqa: E402  (its stubbed SDK, its message)

MARK = "VAMSA_G6A_2026_11_15"
PLAIN = "1_sanskr/tei/transformations/plaintext/"

HV = "\n".join([
    "HV_nn.nn = HV(=constituted text)_adhy\u0101ya.verse",
    "ya ida\u1e43 \u015b\u1e5b\u1e47uy\u0101n nityam // HV_8.48", "",
    "manor vaivasvatasy\u0101san putr\u0101 vai nava tatsam\u0101\u1e25 ",
    "ik\u1e63v\u0101ku\u015b caiva n\u0101bh\u0101ga\u015b ca dh\u1e5b\u1e63\u1e47u\u1e25 \u015bary\u0101tir eva ca // HV_9.1", "",
    "nari\u1e63yantas tath\u0101 pr\u0101\u1e43\u015bur n\u0101bh\u0101nedi\u1e63\u1e6dasaptama\u1e25 // HV_9.2", "",
    "satyavratas tu bhakty\u0101 ca k\u1e5bpay\u0101 ca pratij\u00f1ay\u0101 // HV_10.1", "",
    "anyad eva tu // HV_11.1"])
RAM = "\n".join([
    "evam uktv\u0101 tu R_1,068.019", "",
    "ik\u1e63v\u0101kos tu suta\u1e25 \u015br\u012bm\u0101n kuk\u1e63ir ity eva vi\u015bruta\u1e25",
    "kuk\u1e63er ath\u0101tmajo v\u012bro vikuk\u1e63ir udapadyata R_1,069.018", "",
    "vikuk\u1e63es tu mah\u0101tej\u0101 b\u0101\u1e47a\u1e25 putra\u1e25 prat\u0101pav\u0101n R_1,069.019", "",
    "r\u0101j\u0101bh\u016bt tri\u1e63u loke\u1e63u nimi\u1e25 R_1,070.002", "",
    "im\u0101\u1e43 lokasamutpatti\u1e43 lokan\u0101tha nibodha me R_2,102.002", "",
    "tata\u1e25 R_3,001.001"])
BNDP = "\n".join([
    "pr\u0101g eva // bndp_2,60.44 //",
    "eti \u015br\u012bbrahm\u0101\u1e47\u1e0de mah\u0101pur\u0101\u1e47e v\u0101yuprokte madhyamabh\u0101ge n\u0101ma dvi\u1e63a\u1e63\u1e6ditamo 'dhy\u0101ya\u1e25 // 62//",
    "s\u016bta uv\u0101ca",
    "kakudminas tu ta\u1e43 loka\u1e43 /",
    "raivatasya gatasya ha // bndp_2,63.1 //", "",
    "[verses 2,63.2 - 3 not available at present]",
    "tad vai bhr\u0101t\u1e5b\u015bata\u1e43 tasya / 63.4// s\u0101 hi satyavat\u012b pu\u1e47y\u0101 // bndp_2,63.5 //",
    "anvav\u0101yas tu sumah\u0101n // bndp_2,63. //",
    "\u015b\u0101ry\u0101t\u0101 iti vikhy\u0101t\u0101\u1e25 // bndp_2,63.7 //",
    "aparam // bndp_3,1.1 //"])
BRAHMA = "\n".join([
    "yay\u0101ticarita\u1e43 nityam // BrP_6.51", "",
    "puro\u1e25 putra\u1e25 suv\u012bro 'bh\u016bn manasyus tasya c\u0101tmaja\u1e25 // BrP_13.3", "",
    "na t\u1e5bptim adhigacch\u0101ma\u1e25 // BrP_13*.1", "",
    "eva\u1e43 caturvy\u016bham \u0101tm\u0101na\u1e43 k\u1e5btv\u0101 ||(BrP_13.4)", "",
    "tathaiv\u0101bhayadasy\u0101s\u012bt sudhanv\u0101 n\u0101ma p\u0101rthiva\u1e25 // BrP_13.5", "",
    "sudhanvana\u015b ca putro 'bh\u016bt // BrP_3.6", "",
    "tasya putro mah\u0101bala\u1e25 // BrP_13.7", "",
    "anyat // BrP_17.1"])
KURMA = "\n".join([
    "iti \u015br\u012bk\u016brmapur\u0101\u1e47e \u1e63a\u1e6ds\u0101hastry\u0101\u1e43 sa\u1e43hit\u0101y\u0101\u1e43 p\u016brvavibh\u0101ge ekonavi\u1e43\u015bo 'dhy\u0101ya\u1e25", "",
    "s\u016bta uv\u0101ca",
    "tridhanv\u0101 r\u0101japutras tu dharme\u1e47\u0101p\u0101layan mah\u012bm /",
    "tasya putro 'bhavad vidv\u0101\u1e43s trayy\u0101ru\u1e47a iti sm\u1e5bta\u1e25 // k\u016brmp_1,20.1 //", "",
    "anyat // k\u016brmp_2,1.1 //"])
GARUDA = "\n".join([
    "brahm\u0101 ca pitaro 'pare // garp_1,137.19 //", "",
    "iti \u015br\u012bg\u0101ru\u1e0de mah\u0101pur\u0101\u1e47e p\u016brvakha\u1e47\u1e0de n\u0101ma saptatri\u1e43\u015baduttara\u015batatamo 'dhy\u0101ya\u1e25", "",
    "\u015br\u012bgaru\u1e0damah\u0101pur\u0101\u1e47am- 138 ",
    "(iti vrat\u0101ni sam\u0101pt\u0101ni) /",
    "hariruv\u0101ca /",
    "r\u0101j\u00f1\u0101\u1e43 va\u1e43\u015b\u0101n pravak\u1e63y\u0101mi // garp_1,138.1 //", "",
    "\u015bukyaudak\u0101n pak\u1e63iga\u1e47\u0101n / (a\u015bv\u0101n u\u1e63\u1e6dr\u0101n t\u0101mr\u0101va\u1e43\u015ba\u1e25 58 //) vinat\u0101y\u0101s tu putrau dvau // garp_1,138.2 //",
    "prak\u1e63iptam // garp_1,138.2*1 //",
    "il\u0101y\u0101\u1e43 tu budh\u0101j j\u0101ta\u1e25 // garp_1,138.3 //"])
AGNI = "\n".join([
    "svargamok\u1e63am av\u0101pnuy\u0101t //ap_271.029cd/",
    "ityagneye mahapura\u1e47e d\u0101n\u0101dim\u0101hatmya\u1e43 n\u0101maika saptatyadhikadvi\u015batatamo 'dhy\u0101ya\u1e25", "",
    "% chapter {272}", "",
    ":\u015b atha dvisaptatyadhikadvi\u015batatamo 'dhy\u0101ya\u1e25", "",
    "s\u016bryava\u1e43\u015bak\u012brtana\u1e43", "",
    "agnir uv\u0101ca",
    "s\u016bryava\u1e43\u015ba\u1e43 somava\u1e43\u015ba\u1e43 vad\u0101mi te /ap_272.001ab/harer brahm\u0101 padmago 'bh\u016bt //ap_272.001cd/mar\u012bce\u1e25 ka\u015byapas "
    "/ap_272.002ab/sa\u1e43j\u00f1\u0101 r\u0101j\u00f1\u012b(1) prabh\u0101 //ap_272.002cd/",
    ":n", "",
    "1 atra ch\u0101yetip\u0101\u1e6dho yukta\u1e25 :p 8",
    "sudyumn\u0101d utkalagayau /ap_272.003ab/utkalasyotkala\u1e43 r\u0101\u1e63\u1e6dra\u1e43 //ap_271.003cd/vikuk\u1e63es tu kakutstho /ap_272.004ab/",
    ":p 9",
    "tasya putra\u1e25 p\u1e5bthur n\u0101ma //ap_272.004cd/pari\u015bi\u1e63\u1e6dam /ap_*272.005ab/",
    "anyat /ap_278.001ab/"])
MARKP = "\n".join([
    "iti \u015br\u012bm\u0101rka\u1e47\u1e0deyapur\u0101\u1e47e du\u1e25sahotpattisam\u0101pana\u1e43 n\u0101maikapa\u00f1c\u0101\u015bau'dhy\u0101ya\u1e25", "",
    "dvipa\u00f1c\u0101\u015bo 'dhy\u0101ya\u1e25- 52", "",
    "m\u0101rka\u1e47\u1e0deya uv\u0101ca", "",
    "ity e\u1e63a t\u0101masa\u1e25 sargo brahma\u1e47o 'vyaktajanmana\u1e25 // markp_52.1 //", "",
    "anyat // markp_54.1 //"])
MBH = "\r\n".join([
    "<html><body>", "% Mahabharata: Adiparvan<BR>",
    "01,088.026c\tyay\u0101te\u015b carita\u1e43 mahat<BR>",
    "01,090.006\tvai\u015ba\u1e43p\u0101yana uv\u0101ca<BR>",
    "01,090.006a\t\u015b\u1e5b\u1e47u r\u0101jan pur\u0101 samya\u1e45 may\u0101 dvaip\u0101yan\u0101c chrutam<BR>",
    "01,090.006c\tprocyam\u0101nam ida\u1e43 k\u1e5btsna\u1e43 svava\u1e43\u015bajanana\u1e43 \u015bubham<BR>",
    "01,090.006d*0896_01\tp\u016bror va\u1e43\u015bam aha\u1e43 dhanya\u1e43<BR>",
    "01,090.007*0897_01\tavyaktaprabhavo brahm\u0101 \u015b\u0101\u015bvato nitya (!) avyaya\u1e25<BR>",
    "01,090.007A\tdak\u1e63asy\u0101diti\u1e25<BR>",
    "01,090.007B\taditer vivasv\u0101n<BR>",
    "01,090.007H*0898_01\ta\u1e45gu\u1e63\u1e6dh\u0101d dak\u1e63am as\u1e5bjat<BR>",
    "01,090.008d@051_0001\tpari\u015bi\u1e63\u1e6dam<BR>",
    "01,090.008A\tyay\u0101ter dve bh\u0101rye babh\u016bvatu\u1e25<BR>",
    "02,090.001a\tsabh\u0101parva\u1e47i<BR>", "</body></html>"])
VIPC = "\n".join([
    "[[iti \u015br\u012bvi\u1e63\u1e47upur\u0101\u1e47e t\u1e5bt\u012by\u0101\u1e43\u015be '\u1e63\u1e6d\u0101da\u015bo 'dhy\u0101ya\u1e25 ]]", "",
    "bhagavan yan narai\u1e25 k\u0101rya\u1e43 s\u0101dhukarma\u1e47y avasthitai\u1e25 ",
    "tan mahya\u1e43 guru\u1e47\u0101khy\u0101ta\u1e43 // ViP_4,1.1", "",
    "maitreya \u015br\u016byat\u0101m aya\u1e43 brahm\u0101dir m\u0101navo va\u1e43\u015ba\u1e25 ||(ViP_4,1.2|)", "",
    "prak\u1e63ipta\u1e25 \u015bloka\u1e25 // ViP_4,1.2*12:1", "",
    "tridhanvanas trayy\u0101ru\u1e47a\u1e25 ||(ViP_4,1.3|)", "",
    "tasm\u0101d dhari\u015bcandra\u1e25 // ViP_4,1.4", "",
    "tasm\u0101t satyavrato yo 'sau tri\u015ba\u1e45kusa\u1e43j\u00f1\u0101m av\u0101pa ||(ViP_4,1.3|)", "",
    "n\u1e5bp\u0101\u1e47\u0101\u1e43 kathita\u1e25 sarva\u1e25 // ViP_5,1.1"])
FILES_OF = {"sa_harivaMza.txt": HV, "sa_rAmAyaNa.txt": RAM, "sa_brahmANDapurANa.txt": BNDP,
            "sa_brahmapurANa-1-246.txt": BRAHMA, "sa_kUrmapurANa.txt": KURMA, "sa_garuDapurANa.txt": GARUDA,
            "sa_agnipurANa.txt": AGNI, "sa_mArkaNDeyapurANa1-93.txt": MARKP, "sa_viSNupurANa-crit.txt": VIPC}


def refs(work, text):
    return [r for _c, _v, r, _t in VR.verses_of(work, text)]


def text_of(work, text, ref):
    return dict((r, t) for _c, _v, r, t in VR.verses_of(work, text))[ref]


class TheMarks(unittest.TestCase):
    def test_two_numbers_and_no_closing_mark(self):
        self.assertEqual(refs("hv", HV), ["HV 9.1", "HV 9.2", "HV 10.1"])
        self.assertTrue(text_of("hv", HV, "HV 9.1").startswith("manor vaivasvatasy\u0101san"), "not the verse before")
        self.assertTrue(text_of("hv", HV, "HV 9.1").endswith("\u015bary\u0101tir eva ca"), "the mark is not in the text")

    def test_the_ramayana_has_no_marks_but_its_references(self):
        self.assertEqual(refs("ram1", RAM), ["R 1,69.18", "R 1,69.19", "R 1,70.2"])
        self.assertEqual(refs("ram2", RAM), ["R 2,102.2"])
        self.assertIn("kuk\u1e63ir ity eva vi\u015bruta\u1e25 kuk\u1e63er ath\u0101tmajo", text_of("ram1", RAM, "R 1,69.18"), "two lines, one verse")

    def test_colophon_gap_note_and_a_mark_without_its_number(self):
        self.assertEqual(refs("bndp2", BNDP), ["BndP 2,63.1", "BndP 2,63.5", "BndP 2,63.7"])
        self.assertEqual(refs("bndp1", BNDP), [])
        self.assertEqual(text_of("bndp2", BNDP, "BndP 2,63.1"), "s\u016bta uv\u0101ca kakudminas tu ta\u1e43 loka\u1e43 / raivatasya gatasya ha")
        five = text_of("bndp2", BNDP, "BndP 2,63.5")
        self.assertNotIn("not available", five); self.assertNotIn("63.4", five)
        self.assertIn("bhr\u0101t\u1e5b\u015bata\u1e43", five); self.assertIn("satyavat\u012b", five)
        seven = text_of("bndp2", BNDP, "BndP 2,63.7")
        self.assertIn("anvav\u0101yas", seven, "the verse whose mark lost its number goes to the next")
        self.assertIn("\u015b\u0101ry\u0101t\u0101", seven); self.assertNotIn("bndp", seven)

    def test_a_star_chapter_out_and_a_misprinted_chapter_mended(self):
        self.assertEqual(refs("brahma", BRAHMA), ["BrP 13.3", "BrP 13.4", "BrP 13.5", "BrP 13.6", "BrP 13.7"])
        self.assertNotIn("t\u1e5bptim", " ".join(t for _c, _v, _r, t in VR.verses_of("brahma", BRAHMA)))
        self.assertEqual(text_of("brahma", BRAHMA, "BrP 13.4"), "eva\u1e43 caturvy\u016bham \u0101tm\u0101na\u1e43 k\u1e5btv\u0101", "a prose mark")

    def test_the_prefix_with_a_long_u(self):
        self.assertEqual(refs("kurma1", KURMA), ["KurmP 1,20.1"])
        self.assertTrue(text_of("kurma1", KURMA, "KurmP 1,20.1").startswith("s\u016bta uv\u0101ca tridhanv\u0101"))

    def test_headings_and_a_number_left_in_the_line(self):
        self.assertEqual(refs("garuda1", GARUDA), ["GarP 1,138.1", "GarP 1,138.2", "GarP 1,138.3"])
        self.assertEqual(text_of("garuda1", GARUDA, "GarP 1,138.1"), "hariruv\u0101ca / r\u0101j\u00f1\u0101\u1e43 va\u1e43\u015b\u0101n pravak\u1e63y\u0101mi")
        two = text_of("garuda1", GARUDA, "GarP 1,138.2")
        self.assertNotIn("58", two); self.assertIn("t\u0101mr\u0101va\u1e43\u015ba\u1e25", two)
        self.assertEqual(text_of("garuda1", GARUDA, "GarP 1,138.3"), "il\u0101y\u0101\u1e43 tu budh\u0101j j\u0101ta\u1e25", "the star passage is out")

    def test_half_verses_footnotes_and_a_misprinted_mark(self):
        vs = VR.verses_of("agni", AGNI)
        self.assertEqual([r for _c, _v, r, _t in vs], ["AgP 272.1", "AgP 272.2", "AgP 272.3", "AgP 272.4"])
        t = dict((r, x) for _c, _v, r, x in vs)
        self.assertEqual(t["AgP 272.2"], "mar\u012bce\u1e25 ka\u015byapas sa\u1e43j\u00f1\u0101 r\u0101j\u00f1\u012b prabh\u0101", "the halves joined, the note's call out")
        self.assertEqual(t["AgP 272.3"], "sudyumn\u0101d utkalagayau utkalasyotkala\u1e43 r\u0101\u1e63\u1e6dra\u1e43", "ap_271.003cd is 272's")
        self.assertEqual(t["AgP 272.4"], "vikuk\u1e63es tu kakutstho tasya putra\u1e25 p\u1e5bthur n\u0101ma", "across the page's mark")
        whole = " ".join(t.values())
        for no in ("ch\u0101yeti", "chapter", "'dhy\u0101ya\u1e25", "pari\u015bi\u1e63\u1e6dam", "ap_", ":p"):
            self.assertNotIn(no, whole, no)
        self.assertTrue(t["AgP 272.1"].endswith("harer brahm\u0101 padmago 'bh\u016bt"))

    def test_the_markandeya(self):
        self.assertEqual(refs("markp", MARKP), ["MarkP 52.1"])
        self.assertEqual(text_of("markp", MARKP, "MarkP 52.1"),
                         "m\u0101rka\u1e47\u1e0deya uv\u0101ca ity e\u1e63a t\u0101masa\u1e25 sargo brahma\u1e47o 'vyaktajanmana\u1e25")

    def test_the_mahabharata_lines(self):
        vs = VR.verses_of("mbh1", MBH)
        self.assertEqual([r for _c, _v, r, _t in vs], ["MBh 1,90.6", "MBh 1,90.7", "MBh 1,90.8"])
        t = dict((r, x) for _c, _v, r, x in vs)
        self.assertEqual(t["MBh 1,90.6"], "\u015b\u1e5b\u1e47u r\u0101jan pur\u0101 samya\u1e45 may\u0101 dvaip\u0101yan\u0101c chrutam procyam\u0101nam ida\u1e43 k\u1e5btsna\u1e43 "
                                          "svava\u1e43\u015bajanana\u1e43 \u015bubham")
        self.assertEqual(t["MBh 1,90.7"], "dak\u1e63asy\u0101diti\u1e25 aditer vivasv\u0101n", "the prose sentences of one number")
        whole = " ".join(t.values())
        for no in ("uv\u0101ca", "p\u016bror va\u1e43\u015bam", "avyaktaprabhavo", "a\u1e45gu\u1e63\u1e6dh\u0101d", "pari\u015bi\u1e63\u1e6dam", "sabh\u0101parva\u1e47i", "BR"):
            self.assertNotIn(no, whole, no)

    def test_the_critical_visnu_and_a_number_given_twice(self):
        self.assertEqual(refs("vipc4", VIPC), ["ViPc 4,1.1", "ViPc 4,1.2", "ViPc 4,1.3", "ViPc 4,1.4", "ViPc 4,1.3b"])
        self.assertEqual(text_of("vipc4", VIPC, "ViPc 4,1.2"), "maitreya \u015br\u016byat\u0101m aya\u1e43 brahm\u0101dir m\u0101navo va\u1e43\u015ba\u1e25")
        self.assertEqual(text_of("vipc4", VIPC, "ViPc 4,1.3"), "tridhanvanas trayy\u0101ru\u1e47a\u1e25", "the star passage is out")
        self.assertTrue(text_of("vipc4", VIPC, "ViPc 4,1.1").startswith("bhagavan"), "the colophon is out")
        g = VR.gaps([(c, v, r, t) for c, v, r, t in VR.verses_of("vipc4", VIPC)])
        self.assertEqual((g[1]["verses"], g[1]["missing"], g[1]["again"]), (5, [], [3]))


class TheTable(unittest.TestCase):
    def test_the_three_of_g5a_are_as_they_were(self):
        self.assertEqual(list(VR.WORKS), ["vip4", "bhp9", "bhp12"], "what vamsa_join and the site read")
        self.assertEqual(VR.GROUPS["all"], list(VR.WORKS))
        self.assertEqual(VR.GROUPS["g6"], list(VR.G6_WORKS))
        self.assertFalse(set(VR.WORKS) & set(VR.G6_WORKS))
        self.assertEqual([r for _c, _v, r, _t in VR.verses_of("vip4", T0.TEXT)],
                         ["ViP 4,1.1", "ViP 4,1.2", "ViP 4,1.3", "ViP 4,2.1"])

    def test_every_work_of_g6(self):
        import re
        self.assertEqual(sorted(VR.G6_WORKS), sorted(["hv", "ram1", "ram2", "matsya", "bndp1", "bndp2", "brahma",
                                                      "linga1", "kurma1", "garuda1", "agni", "markp", "mbh1", "vipc4"]))
        for wk, w in VR.G6_WORKS.items():
            for k in ("member", "book", "chapters", "title", "entry", "ref"):
                self.assertIn(k, w, wk)
            if w.get("form") != "mbh":
                rx = re.compile(w["marker"])
                self.assertIn("c", rx.groupindex, wk); self.assertIn("v", rx.groupindex, wk)
                self.assertEqual("b" in rx.groupindex, w["book"] is not None, wk)
            self.assertEqual(w["ref"].count("%d"), 3 if w["book"] is not None else 2, wk)
            self.assertTrue(w["title"].isascii() and w["entry"].isascii(), wk)
        self.assertEqual(VR.G6_WORKS["hv"]["chapters"], [2, 3, 9, 10, 15, 23, 24, 25, 26, 27, 28, 98, 99])
        self.assertEqual(VR.G6_WORKS["mbh1"]["chapters"], [59, 60, 61, 70, 80, 89, 90, 91, 92, 100, 107, 111])
        self.assertIn("for reference only", VR.source_of("mbh1"))
        self.assertIn("CC BY-NC-SA 4.0", VR.source_of("hv"))

    def test_the_site_does_not_get_g6(self):
        import vamsa_join as vj
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "hv" / "09.json"
            p.parent.mkdir(parents=True)
            p.write_text(json.dumps({"chapter": 9, "statements": [
                {"ref": "HV 9.1", "a": "Ik\u1e63v\u0101ku", "rel": "son_of", "b": "Manu", "words": "x", "check": "verified"}]}),
                encoding="utf-8")
            self.assertEqual(vj.dynasties(td, str(Path(td) / "no.db"), str(Path(td) / "no_kin.db")), {},
                             "a reading of G6 alone gives the site nothing")


class TheDesk(unittest.TestCase):
    def setUp(self):
        import os
        self.keep = dict(os.environ)
        os.environ["ANTHROPIC_API_KEY"] = "test-not-a-key"
        self.tmp = tempfile.TemporaryDirectory()
        t = self.t = Path(self.tmp.name)
        self.zip = t / "g.zip"
        with zipfile.ZipFile(self.zip, "w") as z:
            for name, text in FILES_OF.items():
                z.writestr(PLAIN + name, text)
            z.writestr("1_sanskr/2_epic/mbh/mbh_01_u.htm", MBH)
        import cost_tracker
        self.db = t / "u.db"
        con = sqlite3.connect(str(self.db))
        cost_tracker.ensure_usage_schema(con)
        con.close()
        self.out = str(t / "out")

    def tearDown(self):
        import os
        os.environ.clear(); os.environ.update(self.keep)
        self.tmp.cleanup()

    def cli(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = VR.main(["--zip", str(self.zip), "--db", str(self.db), "--out", self.out, "--exports",
                          str(self.t / "ex")] + list(argv))
        return rc, buf.getvalue()

    def test_the_plan_names_a_trial_that_exists(self):
        rc, out = self.cli("--work", "hv")
        self.assertEqual(rc, 0, out)
        self.assertIn("VERDICT: 2 part(s) to read, about $", out)
        self.assertIn("NEXT: python scripts\\vamsa_read.py --work hv --chapters 9-10 --yes", out)
        rc, out = self.cli("--work", "ram1")
        self.assertIn("--work ram1 --chapters 69-70 --yes", out)
        rc, out = self.cli("--work", "mbh1")
        self.assertIn("Mahabharata, Adiparvan", out); self.assertIn("--work mbh1 --chapters 90 --yes", out)
        self.assertFalse(Path(self.out).exists(), "nothing written")

    def test_a_group_reads_what_is_here_or_says_what_is_not(self):
        rc, out = self.cli("--work", "g6")
        self.assertEqual(rc, 1)
        self.assertIn("REFUSE: sa_matsyapurANa1-176.txt is not in", out)
        rc, out = self.cli()
        self.assertEqual(rc, 1); self.assertIn("REFUSE: sa_viSNupurANa.txt is not in", out, "all is still G5a's three")

    def test_show_and_verses_are_free(self):
        rc, out = self.cli("--work", "agni", "--show", "2")
        self.assertEqual(rc, 0, out)
        self.assertIn("[AgP 272.2] mar\u012bce\u1e25 ka\u015byapas sa\u1e43j\u00f1\u0101 r\u0101j\u00f1\u012b prabh\u0101", out)
        self.assertNotIn("AgP 272.3", out)
        self.assertIn("as they would be sent (free; nothing sent)", out)
        rc, out = self.cli("--work", "vipc4", "--verses")
        self.assertIn("vipc4    chapter   1:    5 verses, 1 to 4; twice: 3", out)
        self.assertIn("VERDICT: 5 verses in 1 work(s); 1 chapter(s) with a gap or a number twice", out)
        self.assertFalse(Path(self.out).exists(), "nothing written")

    def test_a_reading_of_the_harivamsa_stubbed(self):
        reply = json.dumps({"statements": [
            {"ref": "HV 9.1", "a": "Ik\u1e63v\u0101ku", "rel": "son_of", "b": "Manu",
             "words": "manor vaivasvatasy\u0101san putr\u0101", "doubt": False},
            {"ref": "HV 9.2", "a": "Nari\u1e63yanta", "rel": "son_of", "b": "Kakutstha", "words": "nari\u1e63yantas tath\u0101"},
            {"ref": "HV 8.48", "a": "X", "rel": "son_of", "b": "Y", "words": "ya ida\u1e43"}]}, ensure_ascii=False)
        a = argparse.Namespace(work="hv", chapters="9", yes=True, max_usd=8.0, model=VR.MODEL, effort="medium",
                               db=str(self.db), zip=str(self.zip), out=self.out, exports=str(self.t / "ex"),
                               reparse=False, report=False, show=0, verses=False)
        sdk = T0.FakeSDK([T0.msg(reply)])
        con = sqlite3.connect(str(self.db))
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                rc = VR.do_run(a, VR.plan_units(a), client=CE.Client(a.model, a.effort, sdk=sdk), con=con)
            rows = con.execute("SELECT kind, doc, passages FROM usage_log").fetchall()
        finally:
            con.close()
        self.assertEqual(rc, 0, buf.getvalue())
        self.assertEqual(len(sdk.requests), 1)
        sent = sdk.requests[0]["messages"][0]["content"]
        self.assertIn("Harivamsa (Vaidya's constituted text), chapter 9", sent)
        self.assertIn("[HV 9.2] nari\u1e63yantas", sent); self.assertNotIn("HV 10.1", sent)
        self.assertEqual(sdk.requests[0]["system"], getattr(VR, "SYSTEM_G6", VR.SYSTEM),
                         "G5a's prompt; VAMSA_G6B_READY_2026_11_16: its second, for the works of G6")
        d = json.loads((Path(self.out) / "hv" / "09.json").read_text(encoding="utf-8"))
        self.assertEqual([s["check"] for s in d["statements"]], ["verified", "words", "bad"])
        self.assertEqual(d["title"], "Harivamsa (Vaidya's constituted text)")
        self.assertIn("sa_harivaMza.txt; GRETIL", d["source"])
        self.assertEqual(rows, [("vamsa_read", "hv", 2)])
        rc, out = self.cli("--work", "hv", "--report")
        self.assertIn("hv     1 part(s) read (0 not), 3 statements", out)
        rc, out = self.cli("--report")
        self.assertNotIn("hv ", out, "the report of all is G5a's three")


PAT = REPO / "scripts" / "patch_vamsa_g6a_2026_11_15.py"
FILES = ("scripts/vamsa_read.py",)


@unittest.skipUnless(PAT.exists(), "patch_vamsa_g6a_2026_11_15.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as tdir:
            t = Path(tdir)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_vamsag6a_*"))
                srcb = (bak[0] if bak else p).read_bytes()
                if MARK.encode() in srcb:
                    self.skipTest("only patched copies to replay against")
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                (t / rel).write_bytes(srcb)
            run = lambda *a: subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(t), capture_output=True,
                                            text=True)
            r = run("--check")
            self.assertIn("CHECK OK: %d file(s)" % len(FILES), r.stdout, r.stdout + r.stderr)
            self.assertEqual(run().returncode, 0)
            for rel in FILES:
                want = (REPO / rel).read_bytes()
                later = sorted((REPO / rel).parent.glob(Path(rel).name + ".bak_vamsag6b_*"))   # VAMSA_G6B_READY came after
                if later and b"VAMSA_G6B_READY_2026_11_16" in want:
                    want = later[0].read_bytes()
                self.assertEqual((t / rel).read_bytes(), want, rel)
            self.assertIn("Nothing to do", run().stdout)


class TheFile(unittest.TestCase):
    def test_ascii_and_mark(self):
        for p in (SCRIPTS / "vamsa_read.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(b.isascii(), p.name)
            self.assertIn(MARK.encode(), b, p.name)


if __name__ == "__main__":
    unittest.main()
