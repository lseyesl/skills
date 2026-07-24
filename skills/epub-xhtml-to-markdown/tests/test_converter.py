#!/usr/bin/env python3

import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "epub_xhtml_to_markdown.py"


class ConverterTest(unittest.TestCase):
    def make_epub(self, root: Path) -> Path:
        epub = root / "sample.epub"
        files = {
            "mimetype": b"application/epub+zip",
            "META-INF/container.xml": b"""<?xml version="1.0"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles><rootfile full-path="OEBPS/content.opf"/></rootfiles>
</container>""",
            "OEBPS/content.opf": b"""<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Sample Book</dc:title><dc:creator>Alice</dc:creator>
    <dc:language>en</dc:language>
  </metadata>
  <manifest>
    <item id="two" href="text/chapter%202.xhtml" media-type="application/xhtml+xml"/>
    <item id="one" href="text/chapter1.xhtml" media-type="application/xhtml+xml"/>
    <item id="extra" href="text/extra.xhtml" media-type="application/xhtml+xml"/>
    <item id="cover" href="images/cover image.png" media-type="image/png"/>
  </manifest>
  <spine>
    <itemref idref="one"/>
    <itemref idref="two"/>
    <itemref idref="extra" linear="no"/>
  </spine>
</package>""",
            "OEBPS/text/chapter1.xhtml": b"""<html xmlns="http://www.w3.org/1999/xhtml">
<body><h1>First</h1><p>Hello <strong>world</strong>.</p>
<ul><li>Alpha</li><li>Beta</li></ul>
<img src="../images/cover%20image.png" alt="Cover"/></body></html>""",
            "OEBPS/text/chapter 2.xhtml": b"""<html xmlns="http://www.w3.org/1999/xhtml">
<body><h2>Second</h2><blockquote><p>Quoted</p></blockquote>
<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table></body></html>""",
            "OEBPS/text/extra.xhtml": b"""<html xmlns="http://www.w3.org/1999/xhtml">
<body><h2>Hidden appendix</h2></body></html>""",
            "OEBPS/images/cover image.png": b"\x89PNG\r\n\x1a\nfixture",
        }
        with zipfile.ZipFile(epub, "w") as archive:
            for name, content in files.items():
                archive.writestr(name, content)
        return epub

    def test_spine_xhtml_and_images(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            epub = self.make_epub(root)
            output = root / "book.md"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(epub), str(output)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            assembly = output.read_text(encoding="utf-8")
            first_path = root / "book_chapters" / "001-First.md"
            second_path = root / "book_chapters" / "002-Second.md"
            first = first_path.read_text(encoding="utf-8")
            second = second_path.read_text(encoding="utf-8")
            self.assertIn("1. [[book_chapters/001-First|First]]", assembly)
            self.assertIn("2. [[book_chapters/002-Second|Second]]", assembly)
            self.assertLess(
                assembly.index("![[book_chapters/001-First]]"),
                assembly.index("![[book_chapters/002-Second]]"),
            )
            self.assertNotIn("Hidden appendix", assembly)
            self.assertIn("**world**", first)
            self.assertIn("- Alpha", first)
            self.assertIn("> Quoted", second)
            self.assertIn("| A | B |", second)
            self.assertIn("../book_assets/OEBPS/images/cover%20image.png", first)
            self.assertTrue(
                (root / "book_assets" / "OEBPS" / "images" / "cover image.png").is_file()
            )
            self.assertIn('title: "Sample Book"', assembly)
            self.assertIn("converted 2 XHTML chapter(s)", result.stdout)

    def test_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            epub = self.make_epub(root)
            output = root / "book.md"
            output.write_text("keep me", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(epub), str(output)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_text(encoding="utf-8"), "keep me")
            self.assertIn("output already exists", result.stderr)

    def test_include_nonlinear(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            epub = self.make_epub(root)
            output = root / "book.md"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    str(epub),
                    str(output),
                    "--include-nonlinear",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(
                (root / "book_chapters" / "003-Hidden appendix.md").is_file()
            )
            self.assertIn(
                "![[book_chapters/003-Hidden appendix]]",
                output.read_text(encoding="utf-8"),
            )
            self.assertIn("converted 3 XHTML chapter(s)", result.stdout)

    def test_single_file_compatibility_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            epub = self.make_epub(root)
            output = root / "book.md"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    str(epub),
                    str(output),
                    "--single-file",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            markdown = output.read_text(encoding="utf-8")
            self.assertLess(markdown.index("# First"), markdown.index("## Second"))
            self.assertFalse((root / "book_chapters").exists())
            self.assertIn("book_assets/OEBPS/images/cover%20image.png", markdown)


if __name__ == "__main__":
    unittest.main()
