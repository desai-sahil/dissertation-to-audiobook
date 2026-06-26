"""GROBID BibParser adapter: structured bibliography + inline citation linkage.

GROBID is a free, local Java service (HTTP, default :8070). This adapter uses only the
standard library (urllib + ElementTree) so it adds no dependencies and stays
importable. The HTTP call runs only live; the TEI-to-IR step (tei_to_bibresult) is a
pure function tested offline against a committed TEI cassette. If GROBID is
unreachable, a clear typed error is raised rather than crashing.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

from thesis_audiobook.ir import BibEntry, Citation
from thesis_audiobook.ports.bib import BibResult

_TEI = "http://www.tei-c.org/ns/1.0"
_XML = "http://www.w3.org/XML/1998/namespace"
_NS = {"t": _TEI}
_YEAR = re.compile(r"\d{4}")
_BOUNDARY = "----thesisaudiobookGROBIDboundary7f3a91"


class GrobidUnavailableError(RuntimeError):
    """GROBID is not reachable, or returned a response that could not be parsed."""


def tei_to_bibresult(tei_xml: str) -> BibResult:
    """Pure: parse a GROBID TEI document into a bibliography and citation map."""
    try:
        root = ET.fromstring(tei_xml)
    except ET.ParseError as error:
        raise GrobidUnavailableError(f"invalid TEI from GROBID: {error}") from error

    bibliography: dict[str, BibEntry] = {}
    for bibl in root.iterfind(".//t:listBibl/t:biblStruct", _NS):
        key = bibl.get(f"{{{_XML}}}id") or f"b{len(bibliography)}"
        # itertext() so markup-wrapped names/titles (<surname><hi>...) are not dropped.
        surnames: list[str] = []
        for surname in bibl.iterfind(".//t:author//t:surname", _NS):
            text = "".join(surname.itertext()).strip()
            if text:
                surnames.append(text)
        dates = bibl.findall(".//t:date", _NS)
        date = next((d for d in dates if d.get("type") == "published"), dates[0] if dates else None)
        year: int | None = None
        if date is not None:
            match = _YEAR.search(date.get("when") or "".join(date.itertext()))
            year = int(match.group()) if match else None
        title_el = bibl.find(".//t:title", _NS)
        title = "".join(title_el.itertext()).strip() if title_el is not None else ""
        bibliography[key] = BibEntry(key=key, authors=surnames, year=year, title=title or None)

    citations: dict[str, Citation] = {}
    for ref in root.iterfind(".//t:ref[@type='bibr']", _NS):
        target = ref.get("target")
        marker = (ref.text or "").strip().strip("[]").strip()
        if target and marker:
            citations[marker] = Citation(marker=marker, bib_key=target.lstrip("#"))
    return BibResult(bibliography=bibliography, citations=citations)


def _multipart(pdf_bytes: bytes) -> tuple[bytes, str]:
    head = (
        f"--{_BOUNDARY}\r\n"
        'Content-Disposition: form-data; name="input"; filename="input.pdf"\r\n'
        "Content-Type: application/pdf\r\n\r\n"
    ).encode()
    body = head + pdf_bytes + f"\r\n--{_BOUNDARY}--\r\n".encode()
    return body, f"multipart/form-data; boundary={_BOUNDARY}"


class GrobidClient:
    def __init__(self, base_url: str = "http://localhost:8070", *, timeout: float = 60.0) -> None:
        self._base = base_url.rstrip("/")
        self._timeout = timeout

    def is_alive(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self._base}/api/isalive", timeout=self._timeout) as resp:
                return resp.read().strip() in (b"true", b"True", b"1")
        except (urllib.error.URLError, OSError):
            return False

    def parse(self, pdf_bytes: bytes) -> BibResult:
        return tei_to_bibresult(self._process_fulltext(pdf_bytes))

    def _process_fulltext(self, pdf_bytes: bytes) -> str:  # pragma: no cover - live only
        body, content_type = _multipart(pdf_bytes)
        request = urllib.request.Request(
            f"{self._base}/api/processFulltextDocument",
            data=body,
            headers={"Content-Type": content_type, "Accept": "application/xml"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, OSError) as error:
            raise GrobidUnavailableError(
                f"GROBID not reachable at {self._base}: {error}"
            ) from error
