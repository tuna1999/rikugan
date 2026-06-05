"""Project-level pytest configuration.

Adds the parent directory to ``sys.path`` so that ``import rikugan.core.types``
and ``from rikugan.providers.foo import Bar`` work from tests that live in
``<project_root>/tests``.  Without this, only modules that do not use
``..``-relative imports can be imported, which excludes most of the
Rikugan code base.
"""

from __future__ import annotations

import os
import sys


def _add_project_root_to_path() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    # ``here`` is the directory containing the inner ``rikugan`` package
    # (e.g. ``C:\Users\kiennd14\.rikugan\rikugan``).  The parent directory
    # is what makes ``import rikugan.X`` resolve to the package.
    project_root = os.path.dirname(here)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


_add_project_root_to_path()
