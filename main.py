from __future__ import annotations

import html as html_lib
import io
import math
import re
import zipfile
from html.parser import HTMLParser
from pathlib import PurePosixPath
from typing import List
from xml.etree import ElementTree as ET


from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="PivotStream Studio")


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
        punct_mult = 2.2
    elif any(ch in PUNCT_MED for ch in suffix):
        punct_mult = 1.8
    elif any(ch in PUNCT_LIGHT for ch in suffix):
        punct_mult = 1.5

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


def _html_to_text(html_source: str) -> str:
    parser = _TextExtractor()
    parser.feed(html_source)
    text = "".join(parser.parts)
    return _normalize_text(text)


def _extract_epub_text(data: bytes) -> str:
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

        manifest: dict[str, str] = {}
        for item in opf_root.iter():
            if item.tag.endswith("item"):
                media_type = item.attrib.get("media-type", "")
                if media_type in {
                    "application/xhtml+xml",
                    "text/html",
                    "application/x-dtbook+xml",
                }:
                    item_id = item.attrib.get("id")
                    href = item.attrib.get("href")
                    if item_id and href:
                        manifest[item_id] = href

        spine_ids: List[str] = []
        for itemref in opf_root.iter():
            if itemref.tag.endswith("itemref"):
                idref = itemref.attrib.get("idref")
                if idref:
                    spine_ids.append(idref)

        if not spine_ids:
            spine_ids = list(manifest.keys())

        opf_dir = PurePosixPath(rootfile).parent
        chunks: List[str] = []
        for idref in spine_ids:
            href = manifest.get(idref)
            if not href:
                continue
            path = str(opf_dir / PurePosixPath(href))
            try:
                html_bytes = zf.read(path)
            except KeyError:
                continue
            html_source = html_bytes.decode("utf-8", errors="ignore")
            text = _html_to_text(html_source)
            if text:
                chunks.append(text)

        full_text = _normalize_text("\n\n".join(chunks))
        if not full_text:
            raise ValueError("EPUB had no readable text")
        return full_text


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
        text = _extract_epub_text(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail="Invalid EPUB archive") from exc

    return {"text": text}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
