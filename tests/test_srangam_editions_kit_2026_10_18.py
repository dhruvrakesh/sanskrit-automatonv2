# -*- coding: ascii -*-
"""EDITIONS_SITE_2026_10_18: the Srangam kit (docs/srangam/EDITIONS_2026-10-18/, scripts/patch_srangam_editions_
2026_10_18.py) is whole: every file it writes is in the payload and carries the marker, the header's config is JSON
with "Editions" for everyone, the route and the menu entry are there, the page links only through its index, and the
patcher is ASCII. The kit's own dry run on Srangam's files is the user's (it needs that repo)."""
import importlib.machinery, importlib.util, json, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
KIT = REPO / "docs" / "srangam" / "EDITIONS_2026-10-18"
PAT = REPO / "scripts" / "patch_srangam_editions_2026_10_18.py"
MARK = "EDITIONS_SITE_2026_10_18"


@unittest.skipUnless(PAT.exists() and KIT.exists(), "the kit is not here")
class TheKit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        loader = importlib.machinery.SourceFileLoader("patch_srangam_editions", str(PAT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        cls.p = importlib.util.module_from_spec(spec)
        loader.exec_module(cls.p)

    def test_every_file_is_in_the_payload_with_the_marker(self):
        for rel in list(self.p.REPLACE) + self.p.NEW + [self.p.AUDIT_APPEND]:
            f = KIT / rel
            self.assertTrue(f.exists(), rel)
            t = f.read_text(encoding="utf-8")
            if not rel.endswith((".json", ".xml")):
                self.assertIn(MARK, t, rel)
            self.assertNotIn("\r\n", t, rel + ": the payload is LF; the patcher keeps each file's own endings")

    def test_the_header_route_and_menu(self):
        nav = json.loads((KIT / "public/config/nav.config.json").read_text(encoding="utf-8"))
        labels = [x.get("label") for x in nav["primary"]]
        self.assertEqual(labels[:2], ["Articles", "Editions"])
        self.assertEqual(nav["primary"][1]["href"], "/editions")
        app = (KIT / "src/App.tsx").read_text(encoding="utf-8")
        self.assertIn('<Route path="/editions" element={<Editions />} />', app)
        self.assertIn('const Editions = lazy(() => import("./pages/Editions"));', app)
        menu = (KIT / "src/components/navigation/CorpusMenu.tsx").read_text(encoding="utf-8")
        self.assertIn("{ label: 'Scholarly editions', href: '/editions',", menu)
        self.assertIn("<loc>https://srangam.nartiang.org/editions</loc>", (KIT / "public/sitemap.xml").read_text(encoding="utf-8"))

    def test_the_page_links_only_through_its_index(self):
        lib = (KIT / "src/lib/editions.ts").read_text(encoding="utf-8")
        self.assertIn("export const EDITIONS_INDEX = '/scholarly/index.json';", lib)
        self.assertIn("const FILE = /^\\/scholarly\\/[a-z0-9][a-z0-9-]{1,59}\\.html$/;", lib)
        page = (KIT / "src/pages/Editions.tsx").read_text(encoding="utf-8")
        self.assertNotIn('href="/scholarly', page, "no literal link: the index gives each file")
        self.assertIn("This is a loading failure, not an empty list.", page)

    def test_the_patcher(self):
        b = PAT.read_bytes()
        self.assertTrue(all(x < 128 for x in b))
        self.assertIn(MARK.encode(), b)
        self.assertEqual(self.p.PREREQ, ("vitest.config.ts", "TEST_WAIT_2026_10_16"))


if __name__ == "__main__":
    unittest.main()
