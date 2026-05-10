"""Permission catalog stub. Filled out in Phase 2 (Auth & RBAC)."""

from enum import Enum


class Permission(str, Enum):
    """Placeholder enum so other modules can import the symbol in Phase 0."""

    PLATFORM_FULL = "platform.*"


# Phase 2 will replace this with the full 50+ permission catalog.
