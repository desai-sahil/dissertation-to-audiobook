"""Eval harness: a labeled multi-thesis corpus + per-dimension scorers that quantify how well a
produced audiobook script honors each thesis's ground truth (structure, citation/markup strip,
value preservation, raw-notation leak).

It scores OUTPUT against LABELS, so it is architecture-agnostic: the same scorecard grades the
current pipeline (v1) and the planned vision-grounded rebuild (v2). The v1 scorecard is the
baseline the rebuild must beat. See eval/score.py (pure scorers) and eval/run.py (the runner).
"""
