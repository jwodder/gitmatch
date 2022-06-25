from __future__ import annotations
from collections.abc import Iterable
import os
from typing import Generic, AnyStr

class Gitignore(Generic[AnyStr]):
    def match(self, path: AnyStr | os.PathLike[AnyStr], is_dir: bool = False) -> bool:
        raise NotImplementedError

def compile(patterns: Iterable[AnyStr], ignorecase: bool = False) -> Gitignore[AnyStr]:
    raise NotImplementedError
