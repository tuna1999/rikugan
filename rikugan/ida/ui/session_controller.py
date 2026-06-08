"""IDA session controller.

Performance note
----------------
``create_default_registry`` imports the entire IDA tool module tree
(``ida.tools.navigation``, ``functions``, ``strings``, etc.) — about
20 tool modules, ~20ms cold. The panel constructs an
``IdaSessionController`` immediately on user click, so we defer that
import to the moment the session controller is actually instantiated.
"""

from __future__ import annotations

from ...core.config import RikuganConfig
from ...core.host import get_database_path
from ...ui.session_controller_base import SessionControllerBase


def _lazy_create_ida_registry():
    """Return a registry of all built-in IDA tools.

    Imports ``ida.tools.registry`` (and its 12 submodules) on the first
    call. The factory is invoked by ``SessionControllerBase.__init__``
    which itself is called from a background thread, so the cost lands
    off the user-click path.
    """
    from ..tools.registry import create_default_registry

    return create_default_registry()


class IdaSessionController(SessionControllerBase):
    """IDA-oriented controller."""

    def __init__(self, config: RikuganConfig):
        super().__init__(
            config=config,
            tool_registry_factory=_lazy_create_ida_registry,
            database_path_getter=get_database_path,
            host_name="IDA Pro",
        )


# Backwards-compatible alias
SessionController = IdaSessionController
