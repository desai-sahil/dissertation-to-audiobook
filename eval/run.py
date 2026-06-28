"""Eval runner: score the committed corpus and write eval/scorecard.{md,json}.

Offline by default. It scores the committed produced scripts (eval/corpus/<id>/script.md) against
the committed labels (labels.json) and structure results (result.json), so it costs nothing, hits
no network, and is reproducible. Running it on the current pipeline's output produces the v1
baseline that the v2 rebuild must beat, per dimension.

To refresh a thesis snapshot from a fresh (billed) pipeline run: regenerate out/<slug>.script.md
via `audiobook run ...`, copy it to eval/corpus/<id>/script.md, and update result.json with that
run's chapter count. Production runs stay a separate, explicit, billed step - the runner itself
never spends money.

Usage:
    uv run python -m eval.run        # score the whole corpus, refresh the scorecard, print it
"""

from __future__ import annotations

import json
from pathlib import Path

from eval.score import (
    Labels,
    StructureResult,
    ThesisScore,
    render_scorecard,
    score_thesis,
)

HERE = Path(__file__).parent
CORPUS = HERE / "corpus"
SCORECARD_MD = HERE / "scorecard.md"
SCORECARD_JSON = HERE / "scorecard.json"


def score_corpus_dir(thesis_dir: Path) -> ThesisScore:
    """Score one committed corpus thesis (labels.json + result.json + script.md). Pure I/O at the
    edge; the scoring itself is the pure core in score.py."""
    labels = Labels.model_validate_json((thesis_dir / "labels.json").read_text(encoding="utf-8"))
    result = StructureResult.model_validate_json(
        (thesis_dir / "result.json").read_text(encoding="utf-8")
    )
    script = (thesis_dir / "script.md").read_text(encoding="utf-8")
    return score_thesis(script, result, labels)


def score_corpus(corpus: Path = CORPUS) -> list[ThesisScore]:
    dirs = sorted(d for d in corpus.iterdir() if d.is_dir() and (d / "labels.json").exists())
    return [score_corpus_dir(d) for d in dirs]


def main() -> None:
    scores = score_corpus()
    SCORECARD_MD.write_text(render_scorecard(scores), encoding="utf-8")
    SCORECARD_JSON.write_text(
        json.dumps([s.model_dump() for s in scores], indent=2) + "\n", encoding="utf-8"
    )
    print(render_scorecard(scores))


if __name__ == "__main__":
    main()
