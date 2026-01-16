# SPDX-License-Identifier: LGPL-2.1-or-later
"""External integrations for AI Assistant."""

from .parts_library import (
    get_library_path,
    scan_library,
    get_context as get_parts_context,
    search as search_parts,
    insert as insert_part,
    is_available as parts_available,
)

__all__ = [
    "get_library_path",
    "scan_library",
    "get_parts_context",
    "search_parts",
    "insert_part",
    "parts_available",
]
