import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


_WORD_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]{2,}")


@dataclass
class ScoredFile:
    path: Path
    content: str
    score: float


def _tokenize(text: str) -> list[str]:
    return [word.lower() for word in _WORD_RE.findall(text)]


def rank_files_by_relevance(
    files: list[tuple[Path, str]],
    query: str,
    limit: int | None = None,
) -> list[ScoredFile]:
    """Rank (path, content) pairs by relevance to a query, most relevant
    first -- a lightweight, local, no-model alternative to embedding-based
    retrieval, matching the project spec's context strategy (relevant
    files, not the whole repo) without adding a new dependency or model.

    Scoring is term-frequency based: how often each of the query's
    distinct words appears in the file's content and path, normalized by
    file length so large files don't win purely on volume. A path match
    (e.g. a file named after a requirement keyword) counts extra, since
    filenames are usually a strong relevance signal.
    """

    query_terms = set(_tokenize(query))

    if not query_terms:
        # Nothing to rank against -- preserve input order, unscored.
        scored = [
            ScoredFile(path=path, content=content, score=0.0)
            for path, content in files
        ]
        return scored[:limit] if limit is not None else scored

    scored = []

    for path, content in files:
        content_terms = _tokenize(content)
        content_len = len(content_terms) or 1
        counts = Counter(content_terms)

        content_score = sum(counts[term] for term in query_terms) / content_len

        path_terms = set(_tokenize(str(path)))
        path_score = len(query_terms & path_terms)

        score = content_score + path_score * 0.5

        scored.append(ScoredFile(path=path, content=content, score=score))

    scored.sort(key=lambda sf: sf.score, reverse=True)

    return scored[:limit] if limit is not None else scored
