.. currentmodule:: gitmatch

Changelog
=========

v0.3.0 (2025-12-05)
-------------------
- Support Python 3.14
- Drop support for Python 3.8 and 3.9
- Medial ``**/`` is no longer treated as a ``*`` that can match ``/``
    - This aligns with a bugfix in Git 2.52.0.

v0.2.1 (2024-11-29)
-------------------
- Support Python 3.13

v0.2.0 (2024-07-28)
-------------------
- Support Python 3.11 and 3.12
- Migrated from setuptools to hatch
- Drop support for Python 3.7
- `Gitignore.match()` will now raise `InvalidPathError` for Windows paths with
  anchors

v0.1.0 (2022-07-20)
-------------------
Initial release
