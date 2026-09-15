"""Splits arbitrary regulation text into bounded pieces for LLM extraction.

Unlike app.compiler.regulation_parser.split_sections (which only understands
the synthetic "=== TYPE: ID ===" demo-fixture format), this works on real
prose -- PDF-extracted text, pasted statute text, anything -- with no special
markers required. A document that already fits in one chunk degenerates to a
single-chunk result, so small documents compile exactly as before.

Chunk boundaries are tracked as exact (start, end) offsets into the original
source text throughout, rather than reconstructed afterwards, so a chunk's
`text` is always precisely `source_text[char_start:char_end]`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ~4 chars/token is a common rough estimate for English prose; there's no
# tokenizer dependency in this project, so this stays an explicit,
# documented approximation (same spirit as the maxTokens comments in
# llm_provider.py) rather than an exact count.
DEFAULT_CHUNK_CHAR_BUDGET = 12_000

_HEADING_RE = re.compile(
    r"(?m)^\s*(?:"
    r"§\s?\d+[\w.\-]*"
    r"|Section\s+\d+[\w.\-]*"
    r"|Article\s+[IVXLCDM]+"
    r"|Part\s+\d+"
    r"|\d+\.\d+(?:\.\d+)*\s+[A-Z]"
    r")"
)
_PARAGRAPH_SEP_RE = re.compile(r"\n\s*\n")
_SENTENCE_SEP_RE = re.compile(r"(?<=[.!?])\s+")

Span = tuple[int, int]


@dataclass(frozen=True)
class TextChunk:
    index: int
    text: str
    char_start: int
    char_end: int


def _segments_between(text: str, offset: int, sep_pattern: re.Pattern[str]) -> list[Span]:
    """Non-overlapping spans of `text` (absolute, shifted by `offset`) split
    on `sep_pattern`, with the separator itself excluded -- used where the
    separator is just whitespace to discard (paragraph/sentence breaks)."""
    spans: list[Span] = []
    pos = 0
    for m in sep_pattern.finditer(text):
        if m.start() > pos:
            spans.append((offset + pos, offset + m.start()))
        pos = m.end()
    if pos < len(text):
        spans.append((offset + pos, offset + len(text)))
    return spans


def _heading_spans(source_text: str) -> list[Span] | None:
    matches = list(_HEADING_RE.finditer(source_text))
    if len(matches) < 2:
        return None
    spans: list[Span] = []
    if matches[0].start() > 0:
        spans.append((0, matches[0].start()))
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(source_text)
        spans.append((match.start(), end))
    return [(s, e) for s, e in spans if source_text[s:e].strip()]


def _expand_oversized(source_text: str, span: Span, char_budget: int) -> list[Span]:
    """Break one atomic span that itself exceeds char_budget: by sentence,
    falling back to a hard character split only if there's no punctuation
    to split on at all (the only path that can cut mid-sentence)."""
    start, end = span
    if end - start <= char_budget:
        return [span]
    sub_spans = _segments_between(source_text[start:end], start, _SENTENCE_SEP_RE)
    if len(sub_spans) <= 1:
        return [(i, min(i + char_budget, end)) for i in range(start, end, char_budget)]
    result: list[Span] = []
    for sub in sub_spans:
        result.extend(_expand_oversized(source_text, sub, char_budget))
    return result


def _pack_spans(spans: list[Span], char_budget: int) -> list[Span]:
    """Greedily merge consecutive spans into runs up to char_budget. Each
    merged run's bounds are (first span's start, last span's end) -- a
    contiguous slice of the source, so any original whitespace between
    packed pieces is preserved inside a chunk (only lost at chunk seams)."""
    chunks: list[Span] = []
    run_start: int | None = None
    run_end: int | None = None
    for start, end in spans:
        if run_start is None:
            run_start, run_end = start, end
        elif end - run_start <= char_budget:
            run_end = end
        else:
            chunks.append((run_start, run_end))
            run_start, run_end = start, end
    if run_start is not None:
        chunks.append((run_start, run_end))
    return chunks


def chunk_regulation_text(
    source_text: str, char_budget: int = DEFAULT_CHUNK_CHAR_BUDGET
) -> list[TextChunk]:
    if len(source_text) <= char_budget:
        return [TextChunk(index=0, text=source_text, char_start=0, char_end=len(source_text))]

    spans = _heading_spans(source_text)
    if spans is None:
        spans = _segments_between(source_text, 0, _PARAGRAPH_SEP_RE)
    if not spans:
        spans = [(0, len(source_text))]

    atomic: list[Span] = []
    for span in spans:
        atomic.extend(_expand_oversized(source_text, span, char_budget))

    packed = _pack_spans(atomic, char_budget)
    return [
        TextChunk(index=i, text=source_text[start:end], char_start=start, char_end=end)
        for i, (start, end) in enumerate(packed)
    ]
