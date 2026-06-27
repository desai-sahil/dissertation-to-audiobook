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
    summarize = "summarize"
    announce = "announce"


class RegionKind(StrEnum):
    """The thesis-agnostic taxonomy the cartographer classifies regions into.

    Independent of BlockType: a RegionKind is a *semantic* label for a run of blocks
    (e.g. "this span is the abstract"); the cartographer maps each kind to a BlockType
    deterministically so the existing select stage decides keep/handling unchanged.
    """

    title_page = "title_page"
    copyright_page = "copyright_page"
    abstract = "abstract"
    biographical_sketch = "biographical_sketch"
    dedication = "dedication"
    epigraph = "epigraph"
    acknowledgments = "acknowledgments"
    preface_or_foreword = "preface_or_foreword"
    table_of_contents = "table_of_contents"
    list_of_tables = "list_of_tables"
    list_of_figures = "list_of_figures"
    list_of_abbreviations = "list_of_abbreviations"
    chapter_body = "chapter_body"
    chapter_front_note = "chapter_front_note"
    chapter_abstract = "chapter_abstract"
    per_chapter_bibliography = "per_chapter_bibliography"
    bibliography = "bibliography"
    appendix = "appendix"
    appendix_bibliography = "appendix_bibliography"
    supplementary_information = "supplementary_information"
    glossary = "glossary"
    index_section = "index"
    colophon_or_vita = "colophon_or_vita"
    footnotes = "footnotes"
    unknown = "unknown"


class RegionDecision(StrEnum):
    include = "include"
    skip = "skip"
    review = "review"


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


class Region(StrictModel):
    """One classified span of the document. Every field is a label, an enum, a
    confidence, or a back-pointer to an EXISTING block id. There is no free-text field
    that is ever spoken: `label`/`rationale` appear only in the structure.md artifact.
    This is the claim-safety boundary - the cartographer cannot inject audio.
    """

    kind: RegionKind
    decision: RegionDecision
    first_block_id: str
    last_block_id: str
    chapter: int | None = None
    label: str = ""
    heading_anchored: bool = False
    kind_confidence: float = 0.0
    decision_confidence: float = 0.0
    rationale: str = ""
    duplicate_of: str | None = None
    language: str | None = None


class StructureMap(StrictModel):
    # Dissertation title/author the cartographer read from the title-page region. Applied
    # to DocumentMeta only if found verbatim in the document (no fabrication).
    title: str | None = None
    author: str | None = None
    regions: list[Region] = []

    def is_empty(self) -> bool:
        return not self.regions and self.title is None and self.author is None


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
