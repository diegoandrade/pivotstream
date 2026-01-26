import io
import zipfile

import pytest
from pypdf import PdfWriter

from main import _extract_epub_data, _extract_pdf_data, _extract_pdf_sections


CONTAINER_XML = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml" />
  </rootfiles>
</container>
"""


def make_epub(with_nav: bool = True) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("META-INF/container.xml", CONTAINER_XML)
        manifest_items = [
            '<item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml" />'
        ]
        if with_nav:
            manifest_items.insert(
                0,
                '<item id="nav" href="toc.xhtml" media-type="application/xhtml+xml" properties="nav" />',
            )
        manifest = "\n      ".join(manifest_items)
        opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="3.0">
  <manifest>
      {manifest}
  </manifest>
  <spine>
    <itemref idref="chapter1" />
  </spine>
</package>
"""
        zf.writestr("OEBPS/content.opf", opf)
        chapter = """<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Chapter 1</title></head>
<body><h1>Chapter 1</h1><p>Hello world.</p></body></html>"""
        zf.writestr("OEBPS/chapter1.xhtml", chapter)
        if with_nav:
            nav = """<html xmlns="http://www.w3.org/1999/xhtml"><body>
<nav epub:type="toc"><ol><li><a href="chapter1.xhtml">Chapter 1</a></li></ol></nav>
</body></html>"""
            zf.writestr("OEBPS/toc.xhtml", nav)
    return buf.getvalue()


def test_extract_epub_with_nav():
    data = make_epub(with_nav=True)
    text, chapters = _extract_epub_data(data)
    assert "Hello world." in text
    assert chapters
    assert chapters[0]["title"] == "Chapter 1"
    assert chapters[0]["start_index"] == 0


def test_extract_epub_without_nav_fallback():
    data = make_epub(with_nav=False)
    text, chapters = _extract_epub_data(data)
    assert "Hello world." in text
    assert len(chapters) == 1


def test_extract_pdf_empty_text_raises():
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    writer.write(buf)
    with pytest.raises(ValueError, match="no readable text"):
        _extract_pdf_data(buf.getvalue())


def test_extract_pdf_invalid_raises():
    with pytest.raises(ValueError, match="Invalid PDF"):
        _extract_pdf_data(b"not a pdf")


def test_extract_pdf_sections_filters_noise():
    text = """
2.1 Problem Statement
1.1. Requirements definition
5. XML-CAD data generation step
IV. Conclusion and future works
iv. lower roman conclusion
A. Appendix
V. Methods
II. Results
1.3.Functional architecture definition
136.01 MB are adopted
0 to 1 with an interval
I. Introduction
"""
    sections = _extract_pdf_sections(text)
    titles = [section["title"] for section in sections]
    assert "2.1 Problem Statement" in titles
    assert "1.1 Requirements definition" in titles
    assert "5 XML-CAD data generation step" in titles
    assert "IV Conclusion and future works" in titles
    assert "IV lower roman conclusion" in titles
    assert "A Appendix" in titles
    assert "V Methods" in titles
    assert "II Results" in titles
    assert "1.3 Functional architecture definition" in titles
    assert "I Introduction" in titles
    assert not any("136.01" in title for title in titles)
    assert not any(title.startswith("0 ") for title in titles)
