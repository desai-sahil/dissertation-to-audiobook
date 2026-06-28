from __future__ import annotations

import json
from collections.abc import Sequence

from eval.score import Labels, StructureResult, score_structure
from eval.vision_run import collect_structure

from thesis_audiobook.adapters.mocks import MockVision
from thesis_audiobook.vision_structure import (
    VisionStructureMap,
    body_chapters,
    build_structure_prompt,
    chapters_detected,
    merge_maps,
    parse_structure_map,
    read_sections,
    review_sections,
    section_decision,
    skipped_sections,
)


def _ch(number: str, title: str, page: int, kind: str = "body_chapter") -> dict[str, object]:
    return {"number": number, "title": title, "start_page": page, "kind": kind}


# Zhu numbers its back matter in the same roman sequence as its chapters: VII REFERENCES,
# VIII APPENDIX. Classified by KIND, those are references/appendix, not body chapters.
_ZHU_SECTIONS = [
    _ch("I", "INTRODUCTION", 9),
    _ch("II", "BACKGROUND", 15),
    _ch("III", "MATERIALS and METHODS", 30),
    _ch("IV", "RESULTS AND DISCUSSION", 55),
    _ch("V", "FUTURE WORK", 90),
    _ch("VI", "CONCLUSION", 100),
    _ch("VII", "REFERENCES", 110, kind="references"),
    _ch("VIII", "APPENDIX", 115, kind="appendix"),
]
_FRONT = [
    _ch("", "Abstract", 5, kind="abstract"),
    _ch("", "Acknowledgements", 6, kind="acknowledgements"),
]


class _FakeVision:
    """A VisionClient that replays a queued reply per batch call (FIFO)."""

    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self.calls = 0

    def describe(
        self,
        prompt: str,
        images: Sequence[bytes],
        *,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        self.calls += 1
        return self._replies.pop(0) if self._replies else "{}"


def test_parse_valid_json() -> None:
    raw = json.dumps({"sections": _ZHU_SECTIONS[:2]})
    m = parse_structure_map(raw)
    assert [s.number for s in m.sections] == ["I", "II"]
    assert m.sections[0].start_page == 9
    assert m.sections[0].kind == "body_chapter"


def test_parse_lowercases_kind_and_keeps_unknown_for_review() -> None:
    raw = json.dumps({"sections": [_ch("", "Epilogue", 8, kind="Epilogue")]})
    m = parse_structure_map(raw)
    assert m.sections[0].kind == "epilogue"  # lowercased, kept verbatim
    assert section_decision(m.sections[0].kind) == "review"  # unrecognized -> review


def test_parse_strips_code_fences() -> None:
    raw = "```json\n" + json.dumps({"sections": [_ZHU_SECTIONS[0]]}) + "\n```"
    assert chapters_detected(parse_structure_map(raw)) == 1


def test_parse_garbage_is_empty_not_crash() -> None:
    for raw in ("not json at all", "", "[1,2,3]", '{"sections": "oops"}'):
        assert parse_structure_map(raw) == VisionStructureMap()


def test_parse_skips_malformed_entries_and_bool_pages() -> None:
    raw = json.dumps(
        {
            "sections": [
                {"number": "I", "title": "INTRO", "start_page": True, "kind": "body_chapter"},
                {"number": "", "title": "", "kind": "body_chapter"},  # empty -> skipped
                "garbage",  # non-dict -> skipped
                _ch("II", "BACKGROUND", 15),
                {"number": "III", "title": "METHODS", "start_page": 30},  # missing kind -> unknown
            ]
        }
    )
    m = parse_structure_map(raw)
    assert [s.number for s in m.sections] == ["I", "II", "III"]
    assert m.sections[0].start_page is None  # the bool was rejected
    assert m.sections[2].kind == "unknown"  # missing kind defaults to unknown (-> review)


def test_merge_dedupes_by_number_and_orders_by_page() -> None:
    a = parse_structure_map(json.dumps({"sections": _ZHU_SECTIONS[3:]}))
    b = parse_structure_map(json.dumps({"sections": _ZHU_SECTIONS[:4]}))  # IV overlaps the boundary
    merged = merge_maps([a, b])
    assert [s.number for s in merged.sections] == ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]


def test_body_chapters_exclude_numbered_back_matter() -> None:
    # the bug this whole refactor fixes: VII REFERENCES / VIII APPENDIX are numbered like chapters
    # but must NOT be counted (or read) as body chapters.
    m = parse_structure_map(json.dumps({"sections": _FRONT + _ZHU_SECTIONS}))
    assert [s.number for s in body_chapters(m)] == ["I", "II", "III", "IV", "V", "VI"]
    assert chapters_detected(m) == 6  # not 8

    read_titles = [s.title for s in read_sections(m)]
    assert "Abstract" in read_titles and "Acknowledgements" in read_titles  # front matter spoken
    assert "INTRODUCTION" in read_titles  # chapters spoken
    skip_kinds = {s.kind for s in skipped_sections(m)}
    assert skip_kinds == {"references", "appendix"}
    assert review_sections(m) == []


def test_section_policy() -> None:
    assert section_decision("body_chapter") == "read"
    assert section_decision("Abstract") == "read"  # case-insensitive
    assert section_decision("acknowledgements") == "read"
    assert section_decision("references") == "skip"
    assert section_decision("appendix") == "skip"
    assert section_decision("table_of_contents") == "skip"
    assert section_decision("glossary") == "review"  # unknown kind never silently skipped


def test_collect_structure_batches_scores_and_excludes_back_matter() -> None:
    # the end-to-end proof: vision returns 8 numbered divisions across two page batches, but only
    # the 6 body chapters count, so the harness scores structure 6/6 = 1.0 (v1 was 0/6) AND the
    # references/appendix land in skip, not read.
    batch1 = json.dumps({"sections": _FRONT + _ZHU_SECTIONS[:3]})
    batch2 = json.dumps({"sections": _ZHU_SECTIONS[3:]})
    fake = _FakeVision([batch1, batch2])
    images = [f"page{i}".encode() for i in range(60)]  # 60 pages -> 2 batches of 50/10

    structure = collect_structure(images, fake, batch=50)
    assert fake.calls == 2
    assert chapters_detected(structure) == 6  # VII/VIII excluded

    labels = Labels(thesis_id="zhu", expected_chapters=["I", "II", "III", "IV", "V", "VI"])
    score = score_structure(StructureResult(chapters_detected=chapters_detected(structure)), labels)
    assert score.rate == 1.0
    assert {s.kind for s in skipped_sections(structure)} == {"references", "appendix"}


def test_mock_vision_is_offline_noop() -> None:
    structure = collect_structure([b"p1", b"p2"], MockVision(), batch=50)
    assert structure == VisionStructureMap()  # non-JSON reply -> empty map, never bills


def test_prompt_classifies_by_kind_not_number() -> None:
    prompt = build_structure_prompt(51, 100)
    assert "51 to 100" in prompt
    assert "kind" in prompt and "body_chapter" in prompt and "references" in prompt
    assert "VII. REFERENCES" in prompt  # explicitly tells the model not to call it a chapter
