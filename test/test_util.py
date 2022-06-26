import pytest
from gimatch import pathway, trim_trailing_spaces


@pytest.mark.parametrize(
    "long,trimmed",
    [
        ("foo", "foo"),
        ("foo ", "foo"),
        ("foo  ", "foo"),
        ("foo\t", "foo"),
        (r"foo\ ", r"foo\ "),
        ("foo\\\t", "foo\\\t"),
        (r"foo\  ", r"foo\ "),
        (r"foo\\ ", r"foo\\"),
        (r"foo\\\ ", r"foo\\\ "),
        (r"foo \ ", r"foo \ "),
        (r"foo \  ", r"foo \ "),
        (r"foo \ \ ", r"foo \ \ "),
        (r"foo \ \  ", r"foo \ \ "),
    ],
)
def test_trim_trailing_spaces(long: str, trimmed: str) -> None:
    assert trim_trailing_spaces(long) == trimmed


@pytest.mark.parametrize(
    "path,ways",
    [
        ("foo", ["foo"]),
        ("foo/bar", ["foo", "foo/bar"]),
        ("foo/bar/baz/quux", ["foo", "foo/bar", "foo/bar/baz", "foo/bar/baz/quux"]),
    ],
)
def test_pathway(path: str, ways: list[str]) -> None:
    assert pathway(path) == ways
