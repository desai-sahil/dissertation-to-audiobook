from __future__ import annotations

import json
from collections.abc import Sequence

from eval.score import Labels, StructureResult, score_structure
from eval.vision_run import collect_structure

from thesis_audiobook.adapters.mocks import MockVision
from thesis_audiobook.vision_structure import (
    VisionStructureMap,
    build_structure_prompt,
    chapters_detected,
    merge_maps,
    parse_structure_map,
    read_regions,
    region_decision,
    review_regions,
    skipped_regions,
)

_ZHU_CHAPTERS = [
    {"number": "I", "title": "INTRODUCTION", "start_page": 9},
    {"number": "II", "title": "BACKGROUND", "start_page": 15},
    {"number": "III", "title": "MATERIALS and METHODS", "start_page": 30},
    {"number": "IV", "title": "RESULTS AND DISCUSSION", "start_page": 55},
    {"number": "V", "title": "FUTURE WORK", "start_page": 90},
    {"number": "VI", "title": "CONCLUSION", "start_page": 110},
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
    raw = json.dumps({"chapters": _ZHU_CHAPTERS[:2], "regions": ["Abstract", "References"]})
    m = parse_structure_map(raw)
    assert [c.number for c in m.chapters] == ["I", "II"]
    assert m.chapters[0].start_page == 9
    assert m.regions == ["abstract", "references"]  # lowercased


def test_parse_tolerates_legacy_skip_regions_key() -> None:
    # an older reply that still uses "skip_regions" is read into the neutral regions field
    m = parse_structure_map(json.dumps({"chapters": [], "skip_regions": ["appendix"]}))
    assert m.regions == ["appendix"]


def test_parse_strips_code_fences() -> None:
    raw = "```json\n" + json.dumps({"chapters": [_ZHU_CHAPTERS[0]]}) + "\n```"
    assert chapters_detected(parse_structure_map(raw)) == 1


def test_parse_garbage_is_empty_not_crash() -> None:
    for raw in ("not json at all", "", "[1,2,3]", '{"chapters": "oops"}'):
        assert parse_structure_map(raw) == VisionStructureMap()


def test_parse_skips_malformed_entries_and_bool_pages() -> None:
    raw = json.dumps(
        {
            "chapters": [
                {"number": "I", "title": "INTRO", "start_page": True},  # bool is not a page
                {"number": "", "title": ""},  # empty -> skipped
                "garbage",  # non-dict -> skipped
                {"number": "II", "title": "BACKGROUND", "start_page": 15},
            ]
        }
    )
    m = parse_structure_map(raw)
    assert [c.number for c in m.chapters] == ["I", "II"]
    assert m.chapters[0].start_page is None  # the bool was rejected


def test_merge_dedupes_by_number_and_orders_by_page() -> None:
    a = parse_structure_map(json.dumps({"chapters": _ZHU_CHAPTERS[3:], "regions": ["appendix"]}))
    b = parse_structure_map(
        json.dumps({"chapters": _ZHU_CHAPTERS[:4], "regions": ["references"]})
    )  # IV overlaps the batch boundary
    merged = merge_maps([a, b])
    assert [c.number for c in merged.chapters] == ["I", "II", "III", "IV", "V", "VI"]  # ordered
    assert merged.regions == ["appendix", "references"]  # unioned + sorted


def test_region_policy_keeps_front_matter_skips_navigation_and_backmatter() -> None:
    # the author's call (reaffirmed): abstract + acknowledgements are READ, not skipped.
    assert region_decision("abstract") == "read"
    assert region_decision("Acknowledgements") == "read"  # case-insensitive
    assert region_decision("references") == "skip"
    assert region_decision("table_of_contents") == "skip"
    assert region_decision("appendix") == "skip"
    assert region_decision("epilogue") == "review"  # unknown kind never silently skipped

    # the exact regions vision found for Zhu split the way the user wants
    zhu = VisionStructureMap(
        regions=[
            "abstract",
            "acknowledgements",
            "appendix",
            "list_of_figures",
            "references",
            "table_of_contents",
        ]
    )
    assert read_regions(zhu) == ["abstract", "acknowledgements"]
    assert skipped_regions(zhu) == [
        "appendix",
        "list_of_figures",
        "references",
        "table_of_contents",
    ]
    assert review_regions(zhu) == []


def test_collect_structure_batches_and_scores_against_labels() -> None:
    # the end-to-end proof of the plumbing: IF vision returns Zhu's 6 chapters across two page
    # batches, the harness scores structure 6/6 = 1.0 (v1 baseline was 0/6). The billed run only
    # swaps this fake for the real client.
    batch1 = json.dumps({"chapters": _ZHU_CHAPTERS[:3]})
    batch2 = json.dumps({"chapters": _ZHU_CHAPTERS[3:]})
    fake = _FakeVision([batch1, batch2])
    images = [f"page{i}".encode() for i in range(60)]  # 60 pages -> 2 batches of 50/10

    structure = collect_structure(images, fake, batch=50)
    assert fake.calls == 2
    assert chapters_detected(structure) == 6

    labels = Labels(thesis_id="zhu", expected_chapters=["I", "II", "III", "IV", "V", "VI"])
    score = score_structure(StructureResult(chapters_detected=chapters_detected(structure)), labels)
    assert score.rate == 1.0


def test_mock_vision_is_offline_noop() -> None:
    images = [b"p1", b"p2"]
    structure = collect_structure(images, MockVision(), batch=50)
    assert structure == VisionStructureMap()  # non-JSON reply -> empty map, never bills


def test_prompt_mentions_absolute_page_range() -> None:
    prompt = build_structure_prompt(51, 100)
    assert "51 to 100" in prompt and "BODY" in prompt
