"""
Gitignore-style path matching

Visit <https://github.com/jwodder/gimatch> for more information.
"""

from __future__ import annotations
from collections.abc import Iterable
import os
from typing import AnyStr, Generic

__version__ = "0.1.0.dev1"
__author__ = "John Thorvald Wodder II"
__author_email__ = "gimatch@varonathe.org"
__license__ = "MIT"
__url__ = "https://github.com/jwodder/gimatch"


class Gitignore(Generic[AnyStr]):
    def match(self, path: AnyStr | os.PathLike[AnyStr], is_dir: bool = False) -> bool:
        raise NotImplementedError


def compile(patterns: Iterable[AnyStr], ignorecase: bool = False) -> Gitignore[AnyStr]:
    raise NotImplementedError
