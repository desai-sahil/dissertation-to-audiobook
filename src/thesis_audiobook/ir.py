"""The intermediate representation (IR): the typed contract between stages.

Stages populate `spoken`, `handling`, `keep`, and the document-level `script` and
`chunks`. They never overwrite `text`. Every model forbids extra fields so a
malformed transform fails fast at the stage boundary.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class BlockType(StrEnum):
    paragraph = "paragraph"
    heading = "heading"
    figure_caption = "figure_caption"
    table = "table"
    equation_display = "equation_display"
    equation_inline = "equation_inline"
    footnote = "footnote"
    reference_list = "reference_list"
    frontmatter = "frontmatter"
    backmatter = "backmatter"
    code = "code"


class Handling(StrEnum):
    speak = "speak"
    skip = "skip"
    gloss = "gloss"
    summarize = "summarize"
    announce = "announce"


class StrictModel(BaseModel):
    """Base model that forbids extra fields so malformed transforms fail fast."""

    model_config = ConfigDict(extra="forbid")


class Block(StrictModel):
    id: str
    type: BlockType
    chapter: int | None = None
    section: str | None = None
    page: int | None = None
    text: str
    spoken: str | None = None
    keep: bool = True
    handling: Handling = Handling.speak
    refs: list[str] = []
    latex: str | None = None
    confidence: float = 1.0
    notes: list[str] = []

    def current_text(self) -> str:
        """The text a stage should transform: the latest spoken form, else the source."""
        return self.spoken if self.spoken is not None else self.text


class Figure(StrictModel):
    id: str
    caption: str
    ref_points: list[str] = []
    page: int | None = None
    spoken: str | None = None


class Equation(StrictModel):
    id: str
    latex: str | None = None
    gloss: str | None = None


class Table(StrictModel):
    id: str
    raw: str
    summary: str | None = None


class Citation(StrictModel):
    marker: str
    bib_key: str | None = None
    spoken: str | None = None


class BibEntry(StrictModel):
    key: str
    authors: list[str] = []
    year: int | None = None
    title: str | None = None


class Chunk(StrictModel):
    """One unit of text handed to TTS, with neighbor pointers for prosody continuity."""

    id: str
    text: str
    chapter: int | None = None
    block_ids: list[str] = []
    prev_id: str | None = None
    next_id: str | None = None


class DocumentMeta(StrictModel):
    title: str
    author: str | None = None
    degree_date: str | None = None
    profile: str = "committee"


class Document(StrictModel):
    meta: DocumentMeta
    blocks: list[Block] = []
    figures: dict[str, Figure] = {}
    equations: dict[str, Equation] = {}
    tables: dict[str, Table] = {}
    citations: dict[str, Citation] = {}
    bibliography: dict[str, BibEntry] = {}
    # Derived artifacts, populated by the assemble_script stage.
    script: str | None = None
    chunks: list[Chunk] = []
