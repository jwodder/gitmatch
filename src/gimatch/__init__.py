"""
Gitignore-style path matching

Visit <https://github.com/jwodder/gimatch> for more information.
"""

from __future__ import annotations
from collections.abc import Iterable
from dataclasses import dataclass
import os
import posixpath
import re
from typing import AnyStr, Generic, Optional

__version__ = "0.1.0.dev1"
__author__ = "John Thorvald Wodder II"
__author_email__ = "gimatch@varonathe.org"
__license__ = "MIT"
__url__ = "https://github.com/jwodder/gimatch"


@dataclass
class Gitignore(Generic[AnyStr]):
    patterns: list[Pattern[AnyStr]]

    def match(self, path: AnyStr | os.PathLike[AnyStr], is_dir: bool = False) -> bool:
        path = os.fspath(path)
        ### TODO: Check path for relativeness and normalization, etc.
        if path.endswith("/"):
            is_dir = True
            path = path[:-1]
        for p in pathway(path):
            for pat in reversed(self.patterns):
                if pat.match(p, is_dir=(is_dir if p == path else True)):
                    if not pat.negative:
                        return True
                    elif p == path:
                        return False
                    else:
                        break
        return False


@dataclass
class Pattern(Generic[AnyStr]):
    regex: re.Pattern[AnyStr]
    negative: bool
    dir_only: bool

    def match(self, path: AnyStr, is_dir: bool = False) -> bool:
        if self.dir_only and not is_dir:
            return False
        return bool(self.regex.fullmatch(path))


@dataclass
class Regex(Generic[AnyStr]):
    regex: AnyStr
    negative: bool
    dir_only: bool

    def compile(self) -> Pattern[AnyStr]:
        return Pattern(
            regex=re.compile(self.regex), negative=self.negative, dir_only=self.dir_only
        )


def compile(patterns: Iterable[AnyStr], ignorecase: bool = False) -> Gitignore[AnyStr]:
    compiled_patterns: list[Pattern[AnyStr]] = []
    for pat in patterns:
        try:
            regex = pattern2regex(pat, ignorecase=ignorecase)
        except InvalidPatternError:
            continue
        if regex is None:
            continue
        compiled_patterns.append(regex.compile())
    return Gitignore(compiled_patterns)


POSIX_CLASSES = {
    "alpha": r"A-Za-z",
    "alnum": r"A-Za-z0-9",
    "blank": r" \t",
    "cntrl": r"\0-\x1F\x7F",
    "digit": r"0-9",
    "graph": r"!-~",
    "lower": r"a-z",
    "print": r" -~",
    "punct": r"!-/:-@[-`{-~",
    "space": r"\t\n\r ",
    "upper": r"A-Z",
    "xdigit": r"0-9A-Fa-f",
}

PARSER = re.compile(
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
)

RANGE_PARSER = re.compile(
    r"""
    (?P<left>\x5C[^\0]|[^\0\x5C])-(?P<right>\x5C[^\0]|[^\0\x5C\x5D])
    |\[:(?P<posix_class>[^\]]*):\]
    |(?P<char>\x5C[^\0]|[^\0\x5C\x5D])
    |(?P<end>\])
""",
    flags=re.X,
)


def pattern2regex(pattern: AnyStr, ignorecase: bool = False) -> Optional[Regex[AnyStr]]:
    orig = pattern
    pattern = trim_trailing_spaces(pattern.rstrip("\r\n"))
    if pattern.startswith("#"):
        return None
    if pattern.startswith("!"):
        negative = True
        pattern = pattern[1:]
        if not pattern:
            return None
    else:
        negative = False
    if pattern.endswith("/"):
        dir_only = True
        pattern = pattern[:-1]
    else:
        dir_only = False
    if not pattern:
        return None
    pos = 0
    regex = r"(?ai:" if ignorecase else r"(?a:"
    m = re.match(r"\*\*/(?:\*\*/)*", pattern)
    if m or not re.search(r"^/|/.", pattern):
        regex += r"(?:[^/\0]+/)*"
        if m:
            pos += m.end()
    if not m and pattern.startswith("/"):
        pos += 1
    while pos < len(pattern):
        m = PARSER.match(pattern, pos)
        if not m:
            raise InvalidPatternError(f"Invalid gitignore pattern: {orig!r}")
        pos += m.end() - m.start()
        if m["slash_globstar"] is not None:
            regex += r"(?:(?:/[^/\0]+)+/?|/)"
        elif m["slash_globstar_slash"] is not None:
            regex += r"/(?:[^/\0]+/)*"
        elif m["globstar_slash"] is not None:
            regex += r"(?:[^/\0]*/)?(?:[^/\0]+/)*"
        elif m["qm"] is not None:
            regex += r"[^/\0]"
        elif m["star"] is not None:
            regex += r"[^/\0]*"
        elif m["openrange"] is not None:
            regex += r"(?![/\0])["
            if pattern[pos : pos + 1] in ("^", "!"):
                regex += "^"
                pos += 1
            if re.match(r"\](?!-[^\]])", pattern[pos:]):
                regex += "]"
                pos += 1
            while True:
                m = RANGE_PARSER.match(pattern, pos)
                if not m:
                    raise InvalidPatternError(f"Invalid gitignore pattern: {orig!r}")
                pos += m.end() - m.start()
                if m["left"] is not None:
                    regex += (
                        re.escape(m["left"][-1:]) + "-" + re.escape(m["right"][-1:])
                    )
                elif m["posix_class"] is not None:
                    try:
                        regex += POSIX_CLASSES[m["posix_class"]]
                    except KeyError:
                        raise InvalidPatternError(
                            f"Invalid gitignore pattern: {orig!r}"
                        )
                elif m["char"] is not None:
                    regex += re.escape(m["char"][-1:])
                elif m["end"] is not None:
                    regex += "]"
                    break
                else:
                    raise AssertionError(
                        "Unhandled pattern structure"
                    )  # pragma: no cover
        elif m["char"] is not None:
            regex += re.escape(m["char"][-1:])
        else:
            raise AssertionError("Unhandled pattern structure")  # pragma: no cover
    regex += r")"
    return Regex(regex, negative, dir_only=dir_only)


class InvalidPatternError(ValueError):
    pass


def pathway(path: AnyStr) -> list[AnyStr]:
    pway: list[AnyStr] = []
    while path:
        pway.append(path)
        path = posixpath.dirname(path)
    pway.reverse()
    return pway


def trim_trailing_spaces(s: AnyStr) -> AnyStr:
    return re.sub(r"(?<!\\)(?P<keep>(?:\\\\)*(\\[ \t])?)[ \t]*\Z", r"\g<keep>", s)
