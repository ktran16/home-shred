"""Local "semantic-ish" exercise search (SPEC §17.3 A3).

A dependency-free, in-process lexical ranker over the exercise catalogue — token
overlap across name / muscles / pattern / category with field weights and a small
synonym map. This is the **baseline** for A3: it ships today with zero model
downloads and runs on the CPU-only host. A true embedding backend (all-MiniLM-L6 via
fastembed / ONNX Runtime, ~80 MB) can drop in later behind the same
`rank_exercises` interface without touching the API or FE. Pure functions are
unit-testable; `search_exercises` is the thin DB wrapper.
"""

import re
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Exercise
from app.services.exercises import list_exercises

# rationale (SPEC §17.3 A3): a tiny domain synonym map bridges the vocabulary gap a
# pure lexical match would miss (e.g. "rdl" → romanian deadlift / hinge). Kept small
# and explicit; an embedding model would subsume this later.
SYNONYMS: dict[str, list[str]] = {
    "rdl": ["romanian", "deadlift", "hinge", "hamstring"],
    "abs": ["core", "abdominal"],
    "ab": ["core", "abdominal"],
    "delts": ["shoulder", "deltoid"],
    "delt": ["shoulder", "deltoid"],
    "lats": ["back", "lat"],
    "lat": ["back"],
    "quads": ["quad", "squat", "legs"],
    "glutes": ["glute", "hinge"],
    "hammies": ["hamstring", "hinge"],
    "hams": ["hamstring", "hinge"],
    "chest": ["pec", "horizontal_push"],
    "press": ["push"],
    "row": ["horizontal_pull"],
    "pullup": ["vertical_pull"],
    "chinup": ["vertical_pull"],
    "squat": ["legs", "quad"],
}

# common filler words that carry no retrieval signal.
STOPWORDS = frozenset(
    {"a", "an", "the", "for", "to", "of", "like", "with", "my", "exercise", "exercises", "and"}
)

# field weights: a name hit matters more than a secondary-muscle hit.
_WEIGHT_NAME = 3.0
_WEIGHT_PRIMARY = 2.0
_WEIGHT_PATTERN = 1.5
_WEIGHT_CATEGORY = 1.0
_WEIGHT_SECONDARY = 1.0


@dataclass
class SearchDoc:
    id: int
    name: str
    primary_muscles: list[str]
    secondary_muscles: list[str]
    pattern: str | None
    category: str | None


@dataclass
class SearchHit:
    id: int
    score: float


def tokenize(text: str) -> set[str]:
    """Lowercase alphanumeric tokens, stopwords removed, length ≥ 2."""
    raw = re.split(r"[^a-z0-9]+", text.lower())
    return {t for t in raw if len(t) >= 2 and t not in STOPWORDS}


def expand(tokens: set[str]) -> set[str]:
    """Add synonym expansions for query tokens (SPEC §17.3 A3)."""
    out = set(tokens)
    for token in tokens:
        out.update(SYNONYMS.get(token, ()))
    return out


def _field_tokens(*values: str | None) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        if value:
            tokens |= tokenize(value)
    return tokens


def score_doc(query_tokens: set[str], doc: SearchDoc) -> float:
    """Weighted token-overlap score for one document. Pure / testable."""
    name = _field_tokens(doc.name)
    primary = _field_tokens(*doc.primary_muscles)
    secondary = _field_tokens(*doc.secondary_muscles)
    pattern = _field_tokens(doc.pattern)
    category = _field_tokens(doc.category)

    score = 0.0
    for token in query_tokens:
        if token in name:
            score += _WEIGHT_NAME
        elif token in primary:
            score += _WEIGHT_PRIMARY
        elif token in pattern:
            score += _WEIGHT_PATTERN
        elif token in category:
            score += _WEIGHT_CATEGORY
        elif token in secondary:
            score += _WEIGHT_SECONDARY
    return score


def rank_exercises(query: str, docs: list[SearchDoc]) -> list[SearchHit]:
    """Rank docs by relevance to the query, dropping zero-score docs.

    Ties break by id for determinism. Pure / unit-testable.
    """
    query_tokens = expand(tokenize(query))
    if not query_tokens:
        return []
    hits = [SearchHit(id=doc.id, score=round(score_doc(query_tokens, doc), 2)) for doc in docs]
    hits = [h for h in hits if h.score > 0]
    hits.sort(key=lambda h: (-h.score, h.id))
    return hits


async def search_exercises(
    db: AsyncSession, query: str, limit: int = 10
) -> list[tuple[Exercise, float]]:
    """Top-`limit` (exercise, score) pairs ranked by relevance to `query` (SPEC §17.3 A3)."""
    exercises = await list_exercises(db)
    docs = [
        SearchDoc(
            id=e.id,
            name=e.name,
            primary_muscles=e.primary_muscles,
            secondary_muscles=e.secondary_muscles,
            pattern=e.pattern.value if e.pattern is not None else None,
            category=e.category,
        )
        for e in exercises
    ]
    ranked = rank_exercises(query, docs)[:limit]
    by_id = {e.id: e for e in exercises}
    return [(by_id[hit.id], hit.score) for hit in ranked]
