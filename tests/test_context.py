from pathlib import Path

from olive.context import rank_files_by_relevance


def test_ranks_more_relevant_content_higher():
    files = [
        (Path("unrelated.py"), "def foo():\n    return 42\n"),
        (Path("auth.py"), "def login(username, password):\n    return authenticate(username, password)\n"),
    ]

    ranked = rank_files_by_relevance(files, query="user authentication login")

    assert ranked[0].path == Path("auth.py")
    assert ranked[0].score > ranked[1].score


def test_path_match_boosts_score():
    files = [
        (Path("random_module.py"), "x = 1\n"),
        (Path("authentication.py"), "y = 2\n"),
    ]

    ranked = rank_files_by_relevance(files, query="authentication")

    assert ranked[0].path == Path("authentication.py")


def test_limit_truncates_results():
    files = [
        (Path(f"file{i}.py"), "authentication login user")
        for i in range(10)
    ]

    ranked = rank_files_by_relevance(files, query="authentication", limit=3)

    assert len(ranked) == 3


def test_empty_query_preserves_order_unscored():
    files = [
        (Path("b.py"), "content"),
        (Path("a.py"), "content"),
    ]

    ranked = rank_files_by_relevance(files, query="")

    assert [sf.path for sf in ranked] == [Path("b.py"), Path("a.py")]
    assert all(sf.score == 0.0 for sf in ranked)


def test_no_matching_terms_still_returns_all_files():
    files = [
        (Path("a.py"), "completely unrelated content"),
        (Path("b.py"), "also nothing to do with it"),
    ]

    ranked = rank_files_by_relevance(files, query="database migration schema")

    assert len(ranked) == 2


def test_longer_file_does_not_automatically_win_on_raw_count():
    short_relevant = (Path("short.py"), "authentication authentication authentication")
    long_diluted = (
        Path("long.py"),
        "authentication " + "padding word here " * 200,
    )

    ranked = rank_files_by_relevance(
        [long_diluted, short_relevant], query="authentication"
    )

    assert ranked[0].path == Path("short.py")


def test_case_insensitive_matching():
    files = [(Path("a.py"), "AUTHENTICATION LOGIC HERE")]

    ranked = rank_files_by_relevance(files, query="authentication")

    assert ranked[0].score > 0
