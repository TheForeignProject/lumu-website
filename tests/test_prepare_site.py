"""Exercise the publishing boundary without third-party dependencies."""

import importlib.util
import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prepare_site.py"


class PrepareSiteTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.source = Path(self.scratch.name)
        self.output = self.source / "_site"
        self.original = (
            b'<!DOCTYPE html>\r\n<html><head><title>lumu website</title>'
            b'<meta name="viewport" content="width=440">'
            b'<style>body { background: #EAEBD5; }</style></head>\r\n'
            b'<body><script src="lumu%20website.hyperesources/'
            b'lumuwebsite_hype_generated_script.js?97637"></script>'
            b'<p>Caf\xc3\xa9</p></body></html>\r\n'
        )
        (self.source / "index.html").write_bytes(self.original)
        resources = self.source / "lumu website.hyperesources"
        resources.mkdir()
        (resources / "lumuwebsite_hype_generated_script.js").write_bytes(b"Hype();\r\n")
        (resources / "photo.jpg").write_bytes(b"original image bytes")
        shutil.copytree(ROOT / "site", self.source / "site")
        self.assertTrue(SCRIPT.is_file(), "Publishing script has not been implemented")
        spec = importlib.util.spec_from_file_location("prepare_site", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.prepare = module.prepare_site

    def test_publishes_brand_head_and_icons_without_changing_export(self):
        self.prepare(self.source)
        published = (self.output / "index.html").read_text(encoding="utf-8")
        self.assertEqual(re.findall(r"<title>(.*?)</title>", published), ["LUMU Singapore"])
        self.assertIn('property="og:site_name" content="LUMU Singapore"', published)
        self.assertIn('rel="canonical" href="https://lumu.sg/"', published)
        data = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', published, re.S).group(1))
        self.assertEqual(data, {
            "@context": "https://schema.org", "@type": "WebSite",
            "name": "LUMU Singapore", "alternateName": "LUMU", "url": "https://lumu.sg/",
        })
        self.assertEqual((self.source / "index.html").read_bytes(), self.original)
        self.assertEqual((self.output / "index.html").read_bytes().split(b"</head>")[1], self.original.split(b"</head>")[1])
        self.assertIn('<meta name="viewport" content="width=440">', published)
        for path in (self.source / "lumu website.hyperesources").iterdir():
            self.assertEqual((self.output / "lumu website.hyperesources" / path.name).read_bytes(), path.read_bytes())
        for name in ("favicon.png", "favicon.ico"):
            self.assertEqual((self.output / name).read_bytes(), (self.source / "site" / "icons" / name).read_bytes())
        self.assertEqual(set(p.name for p in self.output.iterdir()), {"index.html", "lumu website.hyperesources", "favicon.png", "favicon.ico"})

    def test_new_designer_export_keeps_branding_and_removes_stale_assets(self):
        self.prepare(self.source)
        (self.output / "stale.txt").write_text("previous publication")
        (self.source / "lumu website.hyperesources" / "photo.jpg").unlink()
        (self.source / "index.html").write_bytes(self.original.replace(b"lumu website", b"new designer export"))
        self.prepare(self.source)
        self.assertIn("<title>LUMU Singapore</title>", (self.output / "index.html").read_text())
        self.assertFalse((self.output / "stale.txt").exists())
        self.assertFalse((self.output / "lumu website.hyperesources" / "photo.jpg").exists())

    def test_existing_brand_metadata_is_replaced_without_duplicates(self):
        old_metadata = (
            b'<meta property="og:title" content="old">'
            b'<meta property="og:site_name" content="old">'
            b'<meta property="og:url" content="http://old.example/">'
            b'<link rel="canonical" href="http://old.example/">'
            b'<link rel="shortcut icon" href="/old.ico">'
            b'<script type="application/ld+json">{"@context":"https://schema.org","@type":"WebSite","name":"old"}</script>'
            b'<script type="application/ld+json">{"@type":"Organization","name":"LUMU"}</script>'
        )
        (self.source / "index.html").write_bytes(self.original.replace(b"</head>", old_metadata + b"</head>"))
        self.prepare(self.source)
        published = (self.output / "index.html").read_text()
        self.assertNotIn("old.example", published)
        self.assertNotIn("/old.ico", published)
        self.assertEqual(published.count('property="og:title"'), 1)
        self.assertEqual(published.count('"@type": "WebSite"'), 1)
        self.assertIn('"@type":"Organization"', published)

    def test_missing_icon_fails_before_replacing_previous_publication(self):
        self.prepare(self.source)
        previous = (self.output / "index.html").read_bytes()
        (self.source / "site" / "icons" / "favicon.png").unlink()
        with self.assertRaisesRegex(ValueError, "favicon.png"):
            self.prepare(self.source)
        self.assertEqual((self.output / "index.html").read_bytes(), previous)

    def test_array_form_website_type_is_replaced(self):
        old = b'<script type="application/ld+json">{"@type":["WebSite"],"name":"Old brand"}</script>'
        (self.source / "index.html").write_bytes(self.original.replace(b"</head>", old + b"</head>"))
        self.prepare(self.source)
        published = (self.output / "index.html").read_text()
        self.assertNotIn("Old brand", published)
        self.assertEqual(published.count('"@type": "WebSite"'), 1)

    def test_array_form_website_in_mixed_graph_requires_explicit_merge(self):
        graph = b'<script type="application/ld+json">{"@graph":[{"@type":["WebSite"],"name":"Old brand"},{"@type":"Organization","name":"LUMU"}]}</script>'
        (self.source / "index.html").write_bytes(self.original.replace(b"</head>", graph + b"</head>"))
        with self.assertRaisesRegex(ValueError, "merge"):
            self.prepare(self.source)
        self.assertFalse(self.output.exists())

    def test_missing_hype_script_is_rejected(self):
        (self.source / "lumu website.hyperesources" / "lumuwebsite_hype_generated_script.js").unlink()
        with self.assertRaisesRegex(ValueError, "Hype"):
            self.prepare(self.source)
        self.assertFalse(self.output.exists())

    def test_malformed_head_or_title_is_rejected(self):
        for html in (
            b"<html><body>No head</body></html>",
            self.original.replace(b"</head>", b""),
            self.original.replace(b"</head>", b"<title>duplicate</title></head>"),
            self.original.replace(b"<title>lumu website</title>", b""),
        ):
            with self.subTest(html=html):
                (self.source / "index.html").write_bytes(html)
                with self.assertRaises(ValueError):
                    self.prepare(self.source)
                self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
