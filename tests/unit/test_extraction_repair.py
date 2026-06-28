from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from thesis_audiobook.cli import app
from thesis_audiobook.extraction_repair import (
    RepairEdit,
    apply_repairs,
    is_faithful_artifact,
    is_safe_repair,
    parse_repair_plan,
)

runner = CliRunner()


@pytest.mark.parametrize(
    "broken,fixed",
    [
        ("Scholander ¨", "Scholander"),  # detached diaeresis removed
        ("Forster ¨ distance", "Forster distance"),  # detached diaeresis dropped (non-alnum)
        ("g  s", "g s"),  # collapse spacing (same tokens)
        ("the  cat", "the cat"),
        ("word , word", "word, word"),  # stray space before punctuation
    ],
)
def test_guard_accepts_noise_only_edits(broken: str, fixed: str) -> None:
    assert is_safe_repair(broken, fixed)


@pytest.mark.parametrize(
    "broken,fixed",
    [
        ("<sup>0</sup>.1", "0.1"),  # shredded decimal reassembled
        ("<sup>8</sup>.<sup>314</sup>", "8.314"),
        ("< <sup>111</sup> >", "1 1 1"),  # Miller index, brackets dropped, read digit by digit
        ("<sup>±</sup> <sup>0</sup>.1", "±0.1"),  # plus-or-minus preserved
        ("C<sub>s</sub>", "C s"),  # subscript variable de-shredded, letters kept
    ],
)
def test_artifact_guard_accepts_faithful_rerender(broken: str, fixed: str) -> None:
    assert is_faithful_artifact(broken, fixed)


@pytest.mark.parametrize(
    "broken,fixed",
    [
        ("<sup>0</sup>.15", "0.5"),  # digit dropped -> value changed
        ("<sup>8</sup>.<sup>314</sup>", "314.8"),  # digits reordered
        ("<sup>2</sup>", "3"),  # digit invented
        ("<sup>±</sup> <sup>0</sup>.1", "0.1"),  # plus-or-minus dropped
        ("5% yield", "5 yield"),  # percent dropped
        ("<sup>-</sup><sup>5</sup>", "5"),  # minus sign dropped -> sign flip
        ("5", "5%"),  # symbol invented (was not in the source)
        ("C<sub>s</sub>", "C r"),  # subscript variable SWAPPED (new letter) -> different quantity
    ],
)
def test_artifact_guard_rejects_invented_or_dropped_value(broken: str, fixed: str) -> None:
    assert not is_faithful_artifact(broken, fixed)


def test_guard_accepts_decomposed_vs_precomposed_accent() -> None:
    decomposed = "cafe\u0301"  # e + combining acute
    precomposed = "caf\u00e9"  # é
    assert decomposed != precomposed
    assert is_safe_repair(decomposed, precomposed)


@pytest.mark.parametrize(
    "broken,fixed",
    [
        ("is not significant", "is significant"),  # drops a negation -> claim flip
        ("cannot", "can"),  # drops "not" inside a word
        ("increased", "decreased"),  # word changed
        ("10", "100"),  # number changed
        ("rnodel", "model"),  # OCR letter substitution (content)
        ("the cat", "the dog"),  # word swapped
        ("p < 0.05", "p < 0.01"),  # number changed
        ("5½ kg", "512 kg"),  # NFKD fraction-decomposition bypass (caught by NFC)
        ("10²", "102"),  # superscript-decomposition bypass (caught by NFC)
        # red-team finds: case, word merge/split, semantic hyphen, direction
        ("US", "us"),  # case change (acronym -> pronoun)
        ("pH", "PH"),  # case carries meaning
        ("not able", "notable"),  # word merge -> audible claim flip
        ("may be", "maybe"),  # word merge changes the modal
        ("a part", "apart"),  # word merge
        ("re-cover the wound", "recover the wound"),  # semantic hyphen removal
        ("co-op", "coop"),  # semantic hyphen removal
        ("me-asurable", "measurable"),  # hyphenation rejoin -> curator's job, not here
        ("recreation", "re-creation"),  # direction: adding a split
        ("", "x"),  # empty broken
        ("same", "same"),  # no-op
    ],
)
def test_guard_rejects_any_content_change(broken: str, fixed: str) -> None:
    assert not is_safe_repair(broken, fixed)


def test_apply_repairs_applies_safe_rejects_unsafe_and_missing() -> None:
    md = "We used the Scholander ¨ chamber. It increased then."
    repairs = [
        RepairEdit(broken="Scholander ¨", fixed="Scholander", reason="detached mark"),
        RepairEdit(broken="increased", fixed="decreased", reason="bad"),  # unsafe -> rejected
        RepairEdit(broken="café ¨", fixed="café"),  # safe but absent -> not found
    ]
    cleaned, applied, rejected = apply_repairs(md, repairs)
    assert cleaned == "We used the Scholander chamber. It increased then."
    assert [a.broken for a in applied] == ["Scholander ¨"] and applied[0].count == 1
    whys = {r.broken: r.why for r in rejected}
    assert "change content" in whys["increased"]
    assert "not found" in whys["café ¨"]


def test_apply_repairs_artifact_kind_uses_digit_guard() -> None:
    # the real gao artifacts: a shredded decimal and a Miller index, de-shredded faithfully;
    # plus an artifact edit that would alter a digit, which the digit guard rejects.
    md = "value <sup>0</sup>.1 MPa on a < <sup>111</sup> > wafer; ratio <sup>9</sup>.<sup>87</sup>x"
    repairs = [
        RepairEdit(broken="<sup>0</sup>.1", fixed="0.1", kind="artifact", reason="shredded dec"),
        RepairEdit(broken="< <sup>111</sup> >", fixed="1 1 1", kind="artifact", reason="miller"),
        RepairEdit(broken="<sup>9</sup>.<sup>87</sup>", fixed="9.8", kind="artifact", reason="BAD"),
    ]
    cleaned, applied, rejected = apply_repairs(md, repairs)
    assert "0.1 MPa" in cleaned and "1 1 1 wafer" in cleaned  # faithful re-renders applied
    assert "<sup>9</sup>.<sup>87</sup>" in cleaned  # the value-altering one (drops a 7) NOT applied
    kinds = {a.broken: a.kind for a in applied}
    assert kinds["<sup>0</sup>.1"] == "artifact"
    assert any(r.broken == "<sup>9</sup>.<sup>87</sup>" and "invent" in r.why for r in rejected)


def test_apply_repairs_replaces_all_occurrences() -> None:
    md = "Scholander ¨ ... again Scholander ¨ ..."
    cleaned, applied, _ = apply_repairs(md, [RepairEdit(broken="Scholander ¨", fixed="Scholander")])
    assert "¨" not in cleaned and applied[0].count == 2


def test_parse_repair_plan_valid_fenced_and_garbage() -> None:
    plan = parse_repair_plan(
        '```json\n{"summary":"ok","repairs":[{"broken":"a ¨","fixed":"a","reason":"mark"}],'
        '"issues":[]}\n```'
    )
    assert len(plan.repairs) == 1 and plan.repairs[0].fixed == "a"
    assert parse_repair_plan("a mock gloss for input zzzz").is_empty()


def test_repair_extraction_cli_offline_is_noop(tmp_path: Path) -> None:
    md = tmp_path / "thesis.md"
    md.write_text("# Intro\n\nClean prose with no defects.\n", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "repair-extraction",
            str(md),
            "--llm",
            "mock",
            "--out",
            str(tmp_path / "out"),
            "--cache-dir",
            str(tmp_path / "cache"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "applied     : 0 edits" in result.output
    cleaned = (tmp_path / "out" / "thesis.cleaned.md").read_text(encoding="utf-8")
    assert cleaned == md.read_text(encoding="utf-8")  # mock = exact passthrough
