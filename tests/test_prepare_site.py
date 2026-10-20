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
            b'<style>body { background: #EAEBD5; }</style>'
            b'<script>window.designerCode = true;</script></head>\r\n'
            b'<body><script src="lumu%20website.hyperesources/'
            b'lumuwebsite_hype_generated_script.js?97637"></script>'
            b'<p>Caf\xc3\xa9</p></body></html>\r\n'
        )
        (self.source / "index.html").write_bytes(self.original)
        resources = self.source / "lumu website.hyperesources"
        resources.mkdir()
        (resources / "lumuwebsite_hype_generated_script.js").write_bytes(b"Hype();\r\n")
        (resources / "photo.jpg").write_bytes(b"original image bytes")
        self.resource_bytes = {path.name: path.read_bytes() for path in resources.iterdir()}
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
        for name, original in self.resource_bytes.items():
            self.assertEqual((self.source / "lumu website.hyperesources" / name).read_bytes(), original)
            self.assertEqual((self.output / "lumu website.hyperesources" / name).read_bytes(), original)
        for name in ("favicon.png", "favicon.ico"):
            self.assertEqual((self.output / name).read_bytes(), (self.source / "site" / "icons" / name).read_bytes())
        self.assertEqual(set(p.name for p in self.output.iterdir()), {"index.html", "lumu website.hyperesources", "favicon.png", "favicon.ico", "hype-hash-router.js", "lumu-analytics.js"})

    def test_router_loads_once_at_end_of_head_before_generated_hype(self):
        self.prepare(self.source)
        published = (self.output / "index.html").read_bytes()
        router = b'<script src="hype-hash-router.js" data-hype-route-exclude=\'["dh"]\'></script>'
        head = published.split(b"</head>")[0]
        self.assertEqual(published.count(b'src="hype-hash-router.js"'), 1)
        self.assertTrue(head.rstrip().endswith(router))
        self.assertLess(head.index(b"window.designerCode = true;"), head.index(router))
        self.assertLess(published.index(router), published.index(b"lumuwebsite_hype_generated_script.js"))
        self.assertEqual(published.split(b"</head>")[1], self.original.split(b"</head>")[1])

    def test_google_tag_is_published_once_in_head_without_changing_export(self):
        self.prepare(self.source)
        published = (self.output / "index.html").read_text(encoding="utf-8")
        head = published.split("</head>")[0]
        loader = 'https://www.googletagmanager.com/gtag/js?id=G-30MZQRG993'
        self.assertEqual(published.count(loader), 1)
        self.assertEqual(head.count("gtag('config', 'G-30MZQRG993')"), 1)
        self.assertLess(head.index(loader), head.index("window.designerCode"))
        self.assertIn('<script async src="' + loader + '"></script>', head)
        self.assertEqual((self.source / "index.html").read_bytes(), self.original)
        self.assertEqual(published.count('src="lumu-analytics.js"'), 1)
        self.assertEqual((self.output / "lumu-analytics.js").read_bytes(), (self.source / "site" / "lumu-analytics.js").read_bytes())

    def test_missing_analytics_files_preserve_previous_publication(self):
        self.prepare(self.source)
        previous = (self.output / "index.html").read_bytes()
        for name in ("analytics-head.html", "lumu-analytics.js"):
            with self.subTest(name=name):
                path = self.source / "site" / name
                original = path.read_bytes()
                path.unlink()
                with self.assertRaisesRegex(ValueError, re.escape(name)):
                    self.prepare(self.source)
                self.assertEqual((self.output / "index.html").read_bytes(), previous)
                path.write_bytes(original)

    def test_designer_google_tag_requires_review_before_publishing_duplicates(self):
        for tag in (
            b'<script async src="https://www.googletagmanager.com/gtag/js?id=G-OLD"></script>',
            b'<script src="https://www.googletagmanager.com/gtm.js?id=GTM-OLD"></script>',
            b"<script>gtag('config', 'G-OLD');</script>",
        ):
            with self.subTest(tag=tag):
                (self.source / "index.html").write_bytes(self.original.replace(b"</head>", tag + b"</head>"))
                with self.assertRaisesRegex(ValueError, "Google tag"):
                    self.prepare(self.source)
                self.assertFalse(self.output.exists())

    def test_publishes_router_bytes_without_changing_source(self):
        self.prepare(self.source)
        self.assertTrue((self.output / "hype-hash-router.js").is_file())
        self.assertEqual((self.output / "hype-hash-router.js").read_bytes(), (ROOT / "site" / "hype-hash-router.js").read_bytes())
        self.assertEqual((self.source / "site" / "hype-hash-router.js").read_bytes(), (ROOT / "site" / "hype-hash-router.js").read_bytes())

    def test_new_designer_export_keeps_branding_and_router_and_removes_stale_assets(self):
        self.prepare(self.source)
        (self.output / "stale.txt").write_text("previous publication")
        (self.source / "lumu website.hyperesources" / "photo.jpg").unlink()
        replacement = self.original.replace(b"lumu website", b"new designer export").replace(b"Caf\xc3\xa9", b"New menu")
        (self.source / "index.html").write_bytes(replacement)
        self.prepare(self.source)
        self.assertIn("<title>LUMU Singapore</title>", (self.output / "index.html").read_text())
        self.assertEqual((self.output / "index.html").read_bytes().count(b'src="hype-hash-router.js"'), 1)
        self.assertEqual((self.output / "hype-hash-router.js").read_bytes(), (self.source / "site" / "hype-hash-router.js").read_bytes())
        self.assertEqual((self.source / "index.html").read_bytes(), replacement)
        self.assertEqual((self.output / "index.html").read_bytes().split(b"</head>")[1], replacement.split(b"</head>")[1])
        self.assertFalse((self.output / "stale.txt").exists())
        self.assertFalse((self.output / "lumu website.hyperesources" / "photo.jpg").exists())
        self.assertEqual((self.output / "index.html").read_text().count('https://www.googletagmanager.com/gtag/js?id=G-30MZQRG993'), 1)
        self.assertEqual((self.output / "lumu-analytics.js").read_bytes(), (self.source / "site" / "lumu-analytics.js").read_bytes())

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

    def test_missing_router_fails_before_replacing_previous_publication(self):
        self.prepare(self.source)
        previous = {path.relative_to(self.output): path.read_bytes() for path in self.output.rglob("*") if path.is_file()}
        (self.source / "site" / "hype-hash-router.js").unlink(missing_ok=True)
        with self.assertRaisesRegex(ValueError, "hype-hash-router.js"):
            self.prepare(self.source)
        self.assertEqual({path.relative_to(self.output): path.read_bytes() for path in self.output.rglob("*") if path.is_file()}, previous)

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
