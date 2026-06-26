"""Appendix cross-reference signpost (pure).

When appendices are skipped from the audiobook, in-text references like "see Appendix C"
become dangling pointers. Rather than rewrite the author's words (that would be altering
content), we leave the reference verbatim and add ONE fixed spoken aside per chapter, the
first time that chapter references an appendix, telling the listener the material lives in
the full written text. Detection is a deterministic regex and the aside is a fixed
template, so this is claim-safe: no model authors anything, nothing in the source changes.
"""

from __future__ import annotations

import re

from thesis_audiobook.ir import Block, Handling

APPENDIX_SIGNPOST = (
    "A note for the listener: this thesis refers to appendix material, which is not "
    "included in the audiobook. You can find it in the full written text."
)

# A specific appendix reference: "Appendix C", "Appendix E.1", "Appendices A and B".
# Case-sensitive capitalized form, so the ordinary word "appendix" in prose does not trigger
# it. Note the real plural is "appendices" (stem appendic-), handled explicitly.
_APPENDIX_REF = re.compile(r"\bAppendi(?:x|ces) [A-Z]\b")


def apply_signposts(blocks: list[Block], *, include_appendices: bool) -> int:
    """Append the signpost to the first kept, spoken block of each chapter that references
    an appendix. Returns how many were added. No-op when appendices are included."""
    if include_appendices:
        return 0
    signposted: set[int] = set()
    count = 0
    for block in blocks:
        if not block.keep or block.handling is not Handling.speak:
            continue
        chapter = block.chapter
        if chapter is None or chapter in signposted:
            continue
        if _APPENDIX_REF.search(block.current_text()):
            block.spoken = f"{block.current_text()} {APPENDIX_SIGNPOST}"
            signposted.add(chapter)
            count += 1
    return count
