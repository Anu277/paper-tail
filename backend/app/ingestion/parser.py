import xml.etree.ElementTree as ET
from typing import TypedDict

import requests

GROBID_URL = "http://127.0.0.1:8070"
TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}


class Section(TypedDict):
    heading: str
    text: str


class Reference(TypedDict):
    title: str


class ParsedPaper(TypedDict):
    title: str
    sections: list[Section]
    references: list[Reference]


def parse_pdf(pdf_path: str) -> ParsedPaper:
    """Real Phase 1 parser — sends the PDF to a running GROBID instance
    (docker run -p 8070:8070 grobid/grobid:0.8.1) and extracts real
    structure instead of pymupdf's flat text dump: title, section headings
    each paired with their own paragraphs, and parsed references.

    Verified against a real paper (2607.01852): correctly separated
    "Related Work" from "Methodology > Chunking Strategies" into distinct
    sections with no page-footer text bleeding into the body — see
    parsing-comparison.html for the concrete before/after.
    """
    with open(pdf_path, "rb") as f:
        response = requests.post(
            f"{GROBID_URL}/api/processFulltextDocument",
            files={"input": f},
            timeout=120,
        )
    response.raise_for_status()
    root = ET.fromstring(response.text)

    title_el = root.find(".//tei:titleStmt/tei:title", TEI_NS)
    title = (title_el.text or "").strip() if title_el is not None else ""

    sections: list[Section] = []
    for div in root.iter("{http://www.tei-c.org/ns/1.0}div"):
        head = div.find("tei:head", TEI_NS)
        if head is None or not head.text:
            continue
        paragraphs = ["".join(p.itertext()).strip() for p in div.findall("tei:p", TEI_NS)]
        text = "\n\n".join(p for p in paragraphs if p)
        if text:
            sections.append({"heading": head.text.strip(), "text": text})

    references: list[Reference] = []
    for bibl in root.iter("{http://www.tei-c.org/ns/1.0}biblStruct"):
        title_ref = bibl.find(".//tei:title", TEI_NS)
        references.append({"title": (title_ref.text or "").strip() if title_ref is not None else ""})

    return {"title": title, "sections": sections, "references": references}
