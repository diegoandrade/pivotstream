from __future__ import annotations

import html as html_lib
import io
import math
import re
import zipfile
import asyncio
from html.parser import HTMLParser
from pathlib import PurePosixPath
from typing import List
from xml.etree import ElementTree as ET


from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from pypdf import PdfReader
from pydantic import BaseModel

app = FastAPI(title="PivotStream Studio")
IMPORT_TIMEOUT_SECONDS = 15


class ParseRequest(BaseModel):
    text: str


class Token(BaseModel):
    core: str
    prefix: str
    suffix: str
    orp_index: int
    pause_mult: float


PUNCT_STRONG = set(".!?")
PUNCT_MED = set(":;")
PUNCT_LIGHT = set(",")

APOSTROPHES = {"'", "’"}
HYPHENS = {"-", "‑"}
BLOCK_TAGS = {
    "p",
    "div",
    "section",
    "article",
    "header",
    "footer",
    "aside",
    "li",
    "ul",
    "ol",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: List[str] = []

    def handle_data(self, data: str) -> None:
        if data:
            self.parts.append(data)

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "br" or tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in BLOCK_TAGS:
            self.parts.append("\n")


class _TitleExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.heading = ""
        self._in_title = False
        self._in_heading = False
        self._title_parts: List[str] = []
        self._heading_parts: List[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "title":
            self._in_title = True
            return
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"} and not self.heading:
            self._in_heading = True

    def handle_data(self, data: str) -> None:
        if not data:
            return
        if self._in_heading:
            self._heading_parts.append(data)
        elif self._in_title:
            self._title_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
            if not self.title:
                self.title = _normalize_space("".join(self._title_parts))
            return
        if self._in_heading and tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._in_heading = False
            if not self.heading:
                self.heading = _normalize_space("".join(self._heading_parts))


class _NavTocParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.entries: List[dict] = []
        self._in_toc_nav = False
        self._list_depth = 0
        self._in_link = False
        self._current_href = ""
        self._current_text: List[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        attr_map = {name.lower(): value for name, value in attrs}
        if tag == "nav":
            nav_type = attr_map.get("epub:type") or attr_map.get("role") or attr_map.get("id") or ""
            if "toc" in nav_type:
                self._in_toc_nav = True
        if self._in_toc_nav and tag in {"ol", "ul"}:
            self._list_depth += 1
        if self._in_toc_nav and tag == "a":
            self._in_link = True
            self._current_href = attr_map.get("href", "")
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._in_link and data:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._in_toc_nav and tag == "a" and self._in_link:
            title = _normalize_space("".join(self._current_text))
            if self._current_href and title:
                level = max(0, self._list_depth - 1)
                self.entries.append({"href": self._current_href, "title": title, "level": level})
            self._in_link = False
            self._current_href = ""
            self._current_text = []
        if self._in_toc_nav and tag in {"ol", "ul"}:
            self._list_depth = max(0, self._list_depth - 1)
        if tag == "nav" and self._in_toc_nav:
            self._in_toc_nav = False
            self._list_depth = 0

def _orp_index(word: str) -> int:
    length = len(word)
    if length <= 1:
        return 0
    if length <= 5:
        return 1
    if length <= 9:
        return 2
    if length <= 13:
        return 3
    return 4 if length > 4 else length - 1


def _pause_multiplier(core: str, suffix: str) -> float:
    punct_mult = 1.0
    if any(ch in PUNCT_STRONG for ch in suffix):
        punct_mult = 2.0
    elif any(ch in PUNCT_MED for ch in suffix):
        punct_mult = 1.8
    elif any(ch in PUNCT_LIGHT for ch in suffix):
        punct_mult = 1.4

    extra = max(0, len(core) - 8)
    long_mult = 1.0
    if extra > 0:
        long_mult += min(0.1 * math.ceil(extra / 4), 0.5)

    return round(punct_mult * long_mult, 3)


def _extract_core(raw: str) -> str:
    chars = list(raw)
    keep: List[str] = []
    for i, ch in enumerate(chars):
        if ch.isalnum():
            keep.append(ch)
            continue
        if ch in APOSTROPHES or ch in HYPHENS:
            prev_ok = i > 0 and chars[i - 1].isalnum()
            next_ok = i < len(chars) - 1 and chars[i + 1].isalnum()
            if prev_ok and next_ok:
                keep.append(ch)
    return "".join(keep)


def _split_token(raw: str) -> Token | None:
    if not raw:
        return None

    first = next((i for i, ch in enumerate(raw) if ch.isalnum()), None)
    if first is None:
        return None

    last_from_end = next((i for i, ch in enumerate(reversed(raw)) if ch.isalnum()), None)
    if last_from_end is None:
        return None
    last = len(raw) - 1 - last_from_end

    prefix = raw[:first]
    suffix = raw[last + 1 :]
    core_raw = raw[first : last + 1]
    core = _extract_core(core_raw)
    if not core:
        return None

    orp_index = min(_orp_index(core), len(core) - 1)
    pause_mult = _pause_multiplier(core, suffix)

    return Token(
        core=core,
        prefix=prefix,
        suffix=suffix,
        orp_index=orp_index,
        pause_mult=pause_mult,
    )


def _normalize_text(text: str) -> str:
    text = html_lib.unescape(text)
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _normalize_posix(path: str) -> str:
    parts: List[str] = []
    for part in PurePosixPath(path).parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if parts and parts[-1] != "..":
                parts.pop()
                continue
        parts.append(part)
    return "/".join(parts)


def _html_to_text(html_source: str) -> str:
    parser = _TextExtractor()
    parser.feed(html_source)
    text = "".join(parser.parts)
    return _normalize_text(text)

def _extract_title(html_source: str) -> str | None:
    parser = _TitleExtractor()
    parser.feed(html_source)
    if parser.heading:
        return parser.heading
    if parser.title:
        return parser.title
    return None


def _count_tokens(text: str) -> int:
    count = 0
    for raw in text.split():
        if _split_token(raw):
            count += 1
    return count


def _parse_nav_toc(zf: zipfile.ZipFile, opf_dir: PurePosixPath, nav_href: str | None) -> List[dict]:
    if not nav_href:
        return []
    nav_path = str(opf_dir / PurePosixPath(nav_href))
    try:
        nav_bytes = zf.read(nav_path)
    except KeyError:
        return []
    nav_source = nav_bytes.decode("utf-8", errors="ignore")
    parser = _NavTocParser()
    parser.feed(nav_source)
    if not parser.entries:
        return []
    nav_dir = PurePosixPath(nav_href).parent
    entries: List[dict] = []
    for entry in parser.entries:
        href = entry.get("href", "")
        base = href.split("#")[0]
        if not base:
            continue
        target = _normalize_posix(str(opf_dir / nav_dir / PurePosixPath(base)))
        entries.append({"title": entry["title"], "level": entry["level"], "path": target})
    return entries


def _parse_ncx_toc(zf: zipfile.ZipFile, opf_dir: PurePosixPath, ncx_href: str | None) -> List[dict]:
    if not ncx_href:
        return []
    ncx_path = str(opf_dir / PurePosixPath(ncx_href))
    try:
        ncx_bytes = zf.read(ncx_path)
    except KeyError:
        return []
    try:
        root = ET.fromstring(ncx_bytes)
    except ET.ParseError:
        return []
    ncx_dir = PurePosixPath(ncx_href).parent
    entries: List[dict] = []

    def walk(node: ET.Element, level: int) -> None:
        for child in list(node):
            if not child.tag.endswith("navPoint"):
                continue
            title = ""
            for nav_label in child.iter():
                if nav_label.tag.endswith("text") and nav_label.text:
                    title = _normalize_space(nav_label.text)
                    if title:
                        break
            href = ""
            for content in child.iter():
                if content.tag.endswith("content"):
                    href = content.attrib.get("src", "")
                    break
            base = href.split("#")[0] if href else ""
            if base and title:
                target = _normalize_posix(str(opf_dir / ncx_dir / PurePosixPath(base)))
                entries.append({"title": title, "level": level, "path": target})
            walk(child, level + 1)

    nav_map = next((elem for elem in root.iter() if elem.tag.endswith("navMap")), root)
    walk(nav_map, 0)
    return entries


def _extract_epub_data(data: bytes) -> tuple[str, List[dict]]:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        try:
            container_xml = zf.read("META-INF/container.xml")
        except KeyError as exc:
            raise ValueError("EPUB is missing container.xml") from exc

        root = ET.fromstring(container_xml)
        rootfile = None
        for elem in root.iter():
            if elem.tag.endswith("rootfile"):
                rootfile = elem.attrib.get("full-path")
                if rootfile:
                    break
        if not rootfile:
            raise ValueError("EPUB rootfile not found")

        opf_data = zf.read(rootfile)
        opf_root = ET.fromstring(opf_data)

        manifest: dict[str, dict] = {}
        for item in opf_root.iter():
            if item.tag.endswith("item"):
                item_id = item.attrib.get("id")
                href = item.attrib.get("href")
                if not item_id or not href:
                    continue
                manifest[item_id] = {
                    "href": href,
                    "media_type": item.attrib.get("media-type", ""),
                    "properties": item.attrib.get("properties", ""),
                }

        nav_href = None
        ncx_href = None
        for item_id, item in manifest.items():
            properties = item.get("properties", "")
            if not nav_href and "nav" in properties.split():
                nav_href = item.get("href")
            if not ncx_href and (
                item.get("media_type") == "application/x-dtbncx+xml" or item_id == "ncx"
            ):
                ncx_href = item.get("href")

        spine_ids: List[str] = []
        for itemref in opf_root.iter():
            if itemref.tag.endswith("itemref"):
                idref = itemref.attrib.get("idref")
                if idref:
                    spine_ids.append(idref)

        if not spine_ids:
            spine_ids = list(manifest.keys())

        allowed_types = {
            "application/xhtml+xml",
            "text/html",
            "application/x-dtbook+xml",
        }

        opf_dir = PurePosixPath(rootfile).parent
        spine_items: List[dict] = []
        for idref in spine_ids:
            item = manifest.get(idref)
            if not item:
                continue
            media_type = item.get("media_type", "")
            if media_type and media_type not in allowed_types:
                continue
            href = item.get("href")
            if not href:
                continue
            zip_path = str(opf_dir / PurePosixPath(href))
            try:
                html_bytes = zf.read(zip_path)
            except KeyError:
                continue
            try:
                html_source = html_bytes.decode("utf-8", errors="ignore")
            except UnicodeDecodeError:
                html_source = html_bytes.decode("latin-1", errors="ignore")
            try:
                text = _html_to_text(html_source)
                title = _extract_title(html_source)
            except Exception:
                continue
            spine_items.append(
                {
                    "href": href,
                    "path": _normalize_posix(str(opf_dir / PurePosixPath(href))),
                    "text": text,
                    "title": title,
                }
            )

        full_text = _normalize_text("\n\n".join(item["text"] for item in spine_items if item["text"]))
        if not full_text:
            raise ValueError("EPUB had no readable text")

        counts = [_count_tokens(item["text"]) for item in spine_items]
        starts: List[int] = []
        total = 0
        for count in counts:
            starts.append(total)
            total += count

        spine_path_map = {item["path"]: idx for idx, item in enumerate(spine_items)}

        toc_entries = _parse_nav_toc(zf, opf_dir, nav_href) or _parse_ncx_toc(zf, opf_dir, ncx_href)

        chapters: List[dict] = []
        if toc_entries:
            for entry in toc_entries:
                idx = spine_path_map.get(entry["path"])
                if idx is None:
                    continue
                chapters.append(
                    {
                        "title": entry["title"],
                        "start_index": starts[idx],
                        "level": entry.get("level", 0),
                    }
                )

        if not chapters:
            for idx, item in enumerate(spine_items):
                title = item["title"] or f"Chapter {idx + 1}"
                chapters.append({"title": title, "start_index": starts[idx], "level": 0})

        return full_text, chapters


def _extract_pdf_data(data: bytes) -> tuple[str, int]:
    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:
        raise ValueError("Invalid PDF file") from exc

    if not reader.pages:
        raise ValueError("PDF had no pages")

    chunks: List[str] = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception:
            continue
        if text:
            chunks.append(text)

    full_text = _normalize_text("\n\n".join(chunks))
    if not full_text:
        raise ValueError("PDF had no readable text")
    return full_text, len(reader.pages)


def parse_text(text: str) -> List[Token]:
    # Split on whitespace then extract prefix/core/suffix from each chunk.
    tokens: List[Token] = []
    for raw in text.split():
        token = _split_token(raw)
        if token:
            tokens.append(token)
    return tokens


@app.post("/api/parse")
def parse_endpoint(payload: ParseRequest):
    tokens = parse_text(payload.text)
    return {"tokens": [token.model_dump() for token in tokens]}


@app.post("/api/epub")
async def epub_endpoint(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
    if not file.filename.lower().endswith(".epub"):
        raise HTTPException(status_code=400, detail="File must be a .epub")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="File is empty")

    try:
        text, chapters = await asyncio.wait_for(
            asyncio.to_thread(_extract_epub_data, data),
            timeout=IMPORT_TIMEOUT_SECONDS,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=408, detail="EPUB import timed out") from exc
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail="Invalid EPUB archive") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="EPUB import failed") from exc

    return {"text": text, "chapters": chapters}


@app.post("/api/pdf")
async def pdf_endpoint(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a .pdf")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="File is empty")

    try:
        text, pages = await asyncio.wait_for(
            asyncio.to_thread(_extract_pdf_data, data),
            timeout=IMPORT_TIMEOUT_SECONDS,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=408, detail="PDF import timed out") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="PDF import failed") from exc

    return {"text": text, "pages": pages}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
