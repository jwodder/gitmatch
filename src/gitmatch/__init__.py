"""
Gitignore-style path matching

``gitmatch`` provides ``gitignore``-style pattern matching of file paths.
Simply pass in a sequence of ``gitignore`` patterns and you'll get back an
object for testing whether a given relative path matches the patterns.

Visit <https://github.com/jwodder/gitmatch> or <https://gitmatch.rtfd.io> for
more information.
"""

from __future__ import annotations
from collections.abc import Iterable
from dataclasses import asdict, dataclass
import os
from pathlib import PurePosixPath, PureWindowsPath
import posixpath
import re
from typing import Any, AnyStr, Generic, Optional

__version__ = "0.1.0"
__author__ = "John Thorvald Wodder II"
__author_email__ = "gitmatch@varonathe.org"
__license__ = "MIT"
__url__ = "https://github.com/jwodder/gitmatch"

__all__ = [
    "Gitignore",
    "InvalidPathError",
    "InvalidPatternError",
    "Match",
    "Pattern",
    "Regex",
    "compile",
    "pattern2regex",
]


@dataclass
class Gitignore(Generic[AnyStr]):
    """A collection of compiled gitignore patterns"""

    #: :meta private:
    patterns: list[Pattern[AnyStr]]

    def match(
        self, path: AnyStr | os.PathLike[AnyStr], is_dir: bool = False
    ) -> Optional[Match[AnyStr]]:
        """
        Test whether the given relative path matches the collection of
        patterns.  If ``is_dir`` is true or if ``path`` ends in a slash,
        ``path`` is treated as a path to a directory; otherwise, it treated as
        a path to a file.

        If on Windows and ``path`` is not an instance of
        `pathlib.PurePosixPath`, or if on any OS and ``path`` is an instance of
        `pathlib.PureWindowsPath`, any backslashes in ``path`` will be
        converted to forward slashes before matching.

        If a match is found, a `Match` object is returned containing
        information about the matching pattern and the path or portion thereof
        that matched.  The `Match` object may be either "truthy" or "falsy"
        depending on whether the matching pattern is negative or not.  If none
        of the patterns match the path, `match()` returns `None`.  Hence, if
        you're just interested in whether the patterns say the path should be
        gitignored, call `bool()` on the result or use it in a boolean context
        like an ``if ... :`` line.

        :raises InvalidPathError:
            If ``path`` is empty, is absolute, is not normalized (aside from an
            optional trailing slash), contains a NUL character, or starts with
            ``..``.
        """
        orig = path
        path = os.fspath(path)
        if isinstance(path, str):
            NUL = "\0"
            SLASH = "/"
            SEP = os.sep
            WINSEP = "\\"
            CURDIR = "."
            PARDIR = ".."
        else:
            NUL = b"\0"
            SLASH = b"/"
            SEP = os.sep.encode("us-ascii")
            WINSEP = b"\\"
            CURDIR = b"."
            PARDIR = b".."
        if not path:
            raise InvalidPathError("Empty path", orig)
        if NUL in path:
            raise InvalidPathError("Path contains NUL byte", orig)
        if os.path.isabs(path):
            raise InvalidPathError("Path is not relative", orig)
        if SEP != SLASH and not isinstance(orig, PurePosixPath):
            path = path.replace(SEP, SLASH)
        elif isinstance(orig, PureWindowsPath):
            path = path.replace(WINSEP, SLASH)
        if path.endswith(SLASH):
            is_dir = True
            path = path[:-1]
        if posixpath.normpath(path) != path:
            raise InvalidPathError("Path is not normalized", orig)
        if path.split(SLASH)[0] == PARDIR:
            raise InvalidPathError("Path cannot begin with '..'", orig)
        if path == CURDIR:
            return None
        for p in pathway(path):
            for pat in reversed(self.patterns):
                if pat.match(p, is_dir=(is_dir if p == path else True)):
                    if not pat.negative:
                        return Match(pat, p)
                    elif p == path:
                        return Match(pat, p)
                    else:
                        break
        return None


@dataclass
class Match(Generic[AnyStr]):
    """
    Information about a successful match of a path against a pattern.  A
    `Match` is truthy if the pattern was not negative and falsy otherwise.
    """

    #: The compiled `Pattern` object that matched the path
    pattern_obj: Pattern[AnyStr]

    #: The path that matched.  This may be a parent path of the value passed to
    #: `~Gitignore.match()`.
    path: AnyStr

    @property
    def pattern(self) -> AnyStr:
        """
        The original gitignore pattern provided to `compile()`, with trailing
        spaces stripped
        """
        return self.pattern_obj.pattern

    def __bool__(self) -> bool:
        return not self.pattern_obj.negative


@dataclass
class Pattern(Generic[AnyStr]):
    """A compiled gitignore pattern"""

    #: The original gitignore pattern provided to `compile()`, with trailing
    #: spaces stripped
    pattern: AnyStr

    #: A compiled regular expression pattern
    regex: re.Pattern[AnyStr]

    #: Whether the pattern is negative or not
    negative: bool

    #: Whether the pattern only matches directories
    dir_only: bool

    #: Whether the pattern is case-insensitive
    ignorecase: bool

    def match(self, path: AnyStr, is_dir: bool = False) -> bool:
        """
        Test whether the pattern matches the given path.  ``path`` is assumed
        to be a relative, normalized, ``/``-separated path.  If ``is_dir`` is
        true, the path is assumed to refer to a directory; otherwise, it is
        assumed to refer to a file.

        Unlike `Gitignore.match()`, this method only tests ``path`` itself, not
        any of its parent paths.
        """
        if self.dir_only and not is_dir:
            return False
        return bool(self.regex.fullmatch(path))


@dataclass
class Regex(Generic[AnyStr]):
    """A gitignore pattern that has been converted to a regular expression"""

    #: The original gitignore pattern provided to `compile()`, with trailing
    #: spaces stripped
    pattern: AnyStr

    #: The regular expression equivalent of the pattern
    regex: AnyStr

    #: Whether the pattern is negative or not
    negative: bool

    #: Whether the pattern only matches directories
    dir_only: bool

    #: Whether the pattern is case-insensitive
    ignorecase: bool

    def compile(self) -> Pattern[AnyStr]:
        """Compile the regular expression"""
        return Pattern(
            pattern=self.pattern,
            regex=re.compile(self.regex),
            negative=self.negative,
            dir_only=self.dir_only,
            ignorecase=self.ignorecase,
        )


def compile(patterns: Iterable[AnyStr], ignorecase: bool = False) -> Gitignore[AnyStr]:
    """
    Compile a collection of gitignore patterns into a `Gitignore` instance.
    Any invalid or empty patterns are discarded.

    Trailing newlines are stripped from the patterns before compiling, so you
    can compile a pre-existing :file:`.gitignore` file by simply doing:

    .. code:: python

        with open("path/to/.gitignore") as fp:
            gi = gitmatch.compile(fp)

    :param patterns: an iterable of gitignore patterns
    :param bool ignorecase:
        Whether the patterns should match case-insensitively
    """
    compiled_patterns: list[Pattern[AnyStr]] = []
    for pat in patterns:
        try:
            regex = pattern2regex(chomp(pat), ignorecase=ignorecase)
        except InvalidPatternError:
            continue
        if regex is None:
            continue
        compiled_patterns.append(regex.compile())
    return Gitignore(compiled_patterns)


@dataclass
class ParserStrs(Generic[AnyStr]):
    """
    A collection of either `str` or `bytes` constants used by `pattern2regex()`
    """

    posix_classes: dict[AnyStr, AnyStr]
    parser: re.Pattern[AnyStr]
    range_parser: re.Pattern[AnyStr]
    octothorpe: AnyStr
    bang: AnyStr
    slash: AnyStr
    start: AnyStr
    istart: AnyStr
    end: AnyStr
    leading_globstar_slash: re.Pattern[AnyStr]
    is_anchored: re.Pattern[AnyStr]
    unanchored_start: AnyStr
    slash_globstar: AnyStr
    slash_globstar_slash: AnyStr
    globstar_slash: AnyStr
    qm: AnyStr
    star: AnyStr
    openrange: AnyStr
    caret: AnyStr
    close_bracket: AnyStr
    close_bracket_in_range: re.Pattern[AnyStr]
    hyphen: AnyStr

    def encode(self: ParserStrs[str]) -> ParserStrs[bytes]:
        return ParserStrs(
            **{name: self.encode_field(value) for name, value in asdict(self).items()}
        )

    @staticmethod
    def encode_field(value: Any) -> Any:
        if isinstance(value, str):
            return value.encode("us-ascii")
        elif isinstance(value, re.Pattern):
            return re.compile(
                value.pattern.encode("us-ascii"), flags=value.flags & ~re.U
            )
        elif isinstance(value, dict):
            return {
                k.encode("us-ascii"): v.encode("us-ascii") for k, v in value.items()
            }
        else:
            raise TypeError(value)  # pragma: no cover


PARSER_STRS = ParserStrs(
    posix_classes={
        "alpha": r"A-Za-z",
        "alnum": r"A-Za-z0-9",
        "blank": r" \t",
        "cntrl": r"\0-\x1F\x7F",
        "digit": r"0-9",
        "graph": r"!-\~",
        "lower": r"a-z",
        "print": r" -\~",
        "punct": r"!-/:-@[-`{-\~",
        "space": r"\t\n\r ",
        "upper": r"A-Z",
        "xdigit": r"0-9A-Fa-f",
    },
    parser=re.compile(
        r"""
        (?P<slash_globstar>/\*\*\Z)
        |(?P<slash_globstar_slash>/\*\*(/\*\*)*/)
        |(?P<globstar_slash>\*\*/(\*\*/)*)
        |(?P<qm>\?)
        |(?P<star>\*\*?)
        |(?P<openrange>\[)
        |(?P<char>\x5C[^\0]|[^\0\x5C])
    """,
        flags=re.X,
    ),
    range_parser=re.compile(
        r"""
        (?P<left>\x5C[^\0]|[^\0\x5C])-(?P<right>\x5C[^\0]|[^\0\x5C\x5D])
        |\[:(?P<posix_class>[^\]]*):\]
        |(?P<char>\x5C[^\0]|[^\0\x5C\x5D])
        |(?P<end>\])
    """,
        flags=re.X,
    ),
    octothorpe="#",
    bang="!",
    slash="/",
    start=r"(?a:",
    istart=r"(?ai:",
    end=r")",
    leading_globstar_slash=re.compile(r"\*\*/(?:\*\*/)*"),
    is_anchored=re.compile(r"^/|/."),
    unanchored_start=r"(?:[^/\0]+/)*",
    slash_globstar=r"(?:(?:/[^/\0]+)+/?|/)",
    slash_globstar_slash=r"/(?:[^/\0]+/)*",
    globstar_slash=r"(?:[^/\0]*/)?(?:[^/\0]+/)*",
    qm=r"[^/\0]",
    star=r"[^/\0]*",
    openrange=r"(?![/\0])[",
    caret="^",
    close_bracket="]",
    close_bracket_in_range=re.compile(r"\](?!-[^\]])"),
    hyphen="-",
)

PARSER_BYTES = PARSER_STRS.encode()


def pattern2regex(pattern: AnyStr, ignorecase: bool = False) -> Optional[Regex[AnyStr]]:
    """
    Convert a gitignore pattern to a regular expression and return a `Regex`
    object.  If the pattern is empty or a comment, returns `None`.

    :param pattern: a gitignore pattern
    :param bool ignorecase: Whether the pattern should match case-insensitively
    :raises InvalidPatternError: If the given pattern is invalid
    """
    strs: ParserStrs
    if isinstance(pattern, str):
        strs = PARSER_STRS
    else:
        strs = PARSER_BYTES
    orig = pattern
    pattern = source = trim_trailing_spaces(pattern)
    if pattern.startswith(strs.octothorpe):
        return None
    if pattern.startswith(strs.bang):
        negative = True
        pattern = pattern[1:]
        if not pattern:
            return None
    else:
        negative = False
    if pattern.endswith(strs.slash):
        dir_only = True
        pattern = pattern[:-1]
    else:
        dir_only = False
    if not pattern:
        return None
    pos = 0
    regex = strs.istart if ignorecase else strs.start
    m = strs.leading_globstar_slash.match(pattern)
    if m or not strs.is_anchored.search(pattern):
        regex += strs.unanchored_start
        if m:
            pos += m.end()
    if not m and pattern.startswith(strs.slash):
        pos += 1
    while pos < len(pattern):
        m = strs.parser.match(pattern, pos)
        if not m:
            raise InvalidPatternError(orig)
        pos += m.end() - m.start()
        if m["slash_globstar"] is not None:
            regex += strs.slash_globstar
        elif m["slash_globstar_slash"] is not None:
            regex += strs.slash_globstar_slash
        elif m["globstar_slash"] is not None:
            regex += strs.globstar_slash
        elif m["qm"] is not None:
            regex += strs.qm
        elif m["star"] is not None:
            regex += strs.star
        elif m["openrange"] is not None:
            regex += strs.openrange
            if pattern[pos : pos + 1] in (strs.caret, strs.bang):
                regex += strs.caret
                pos += 1
            if strs.close_bracket_in_range.match(pattern, pos=pos):
                regex += strs.close_bracket
                pos += 1
            while True:
                m = strs.range_parser.match(pattern, pos)
                if not m:
                    raise InvalidPatternError(orig)
                pos += m.end() - m.start()
                if m["left"] is not None:
                    lchar = m["left"][-1:]
                    rchar = m["right"][-1:]
                    if ord(lchar) > ord(rchar):
                        raise InvalidPatternError(orig)
                    regex += re.escape(lchar) + strs.hyphen + re.escape(rchar)
                elif m["posix_class"] is not None:
                    try:
                        regex += strs.posix_classes[m["posix_class"]]
                    except KeyError:
                        raise InvalidPatternError(orig)
                elif m["char"] is not None:
                    regex += re.escape(m["char"][-1:])
                elif m["end"] is not None:
                    regex += strs.close_bracket
                    break
                else:
                    raise AssertionError(
                        "Unhandled pattern structure"
                    )  # pragma: no cover
        elif m["char"] is not None:
            regex += re.escape(m["char"][-1:])
        else:
            raise AssertionError("Unhandled pattern structure")  # pragma: no cover
    regex += strs.end
    return Regex(
        pattern=source,
        regex=regex,
        negative=negative,
        dir_only=dir_only,
        ignorecase=ignorecase,
    )


class InvalidPathError(ValueError):
    """Raised by `Gitignore.match()` when given an invalid path"""

    def __init__(
        self, msg: str, path: str | bytes | os.PathLike[str] | os.PathLike[bytes]
    ) -> None:
        #: A description of the problem with the path
        self.msg = msg
        #: The invalid path
        self.path = path

    def __str__(self) -> str:
        return f"{self.msg}: {self.path!r}"


class InvalidPatternError(ValueError):
    """Raised by `pattern2regex()` when given an invalid pattern"""

    def __init__(self, pattern: str | bytes) -> None:
        #: The invalid pattern
        self.pattern = pattern

    def __str__(self) -> str:
        return f"Invalid gitignore pattern: {self.pattern!r}"


def pathway(path: AnyStr) -> list[AnyStr]:
    """
    Return a list of parent paths of ``path`` (not including the root) plus
    ``path`` itself
    """
    pway: list[AnyStr] = []
    while path:
        pway.append(path)
        path = posixpath.dirname(path)
    pway.reverse()
    return pway


TRIM_RGX = r"(?<!\\)(?P<keep>(?:\\\\)*(\\[ \t])?)[ \t]*\Z"
TRIM_STR = re.compile(TRIM_RGX)
TRIM_BYTES = re.compile(TRIM_RGX.encode("us-ascii"))


def trim_trailing_spaces(s: AnyStr) -> AnyStr:
    """Remove trailing unescaped space and tab characters from ``s``"""
    if isinstance(s, str):
        rgx = TRIM_STR
        keep = r"\g<keep>"
    else:
        rgx = TRIM_BYTES
        keep = rb"\g<keep>"
    return rgx.sub(keep, s)


def chomp(s: AnyStr) -> AnyStr:
    """Remove trailing newline, if any"""
    if s and ord(s[-1:]) == 10:
        s = s[:-1]
    if s and ord(s[-1:]) == 13:
        s = s[:-1]
    return s
